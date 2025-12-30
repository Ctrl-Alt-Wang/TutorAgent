from typing import Dict, List, Any, TypedDict, Annotated, Optional, Literal
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from database import TutorialDatabase
import base64
import re
import json
from PIL import Image
import io
import os

# Import the existing API configuration
from LLM_api import client, send_vision_request, get_model_name, create_client, LLM_PROVIDER

# 语音状态
class VoiceState:
    """语音播放状态"""
    def __init__(self):
        self.is_playing = False
        self.current_segment = 0
        self.segments = []
        self.paused_at_segment = None
        self.pending_question = None

# 分段讲解内容模型
class TeachingSegment(TypedDict):
    title: str
    content: str
    key_points: List[str]
    audio_duration: Optional[float]  # 预计音频时长(秒)

class TutorialState(TypedDict):
    """State object for the tutorial agent."""
    messages: Annotated[List[BaseMessage], add_messages]
    subject: str
    conversation_id: int
    current_mode: str  # 'tutorial', 'qa', 'evaluation', 'voice_teaching', 'voice_qa', 'voice_resume'
    evaluation_count: int
    user_understanding: Dict[str, Any]

    # 交互式语音教学相关状态
    content_image: Optional[str]  # Base64编码的图片
    content_text: Optional[str]  # 从图片提取或用户输入的内容
    teaching_segments: List[TeachingSegment]  # 分段讲解内容
    current_segment_index: int  # 当前播放到的分段索引
    is_voice_paused: bool  # 语音是否暂停
    pending_question: Optional[str]  # 用户待回答的问题
    qa_answer: Optional[str]  # 问答回复
    transition_text: Optional[str]  # 过渡衔接语

class TutorialAgent:
    """LangGraph-based AI tutorial agent."""
    
    def __init__(self):
        self.db = TutorialDatabase()
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow."""
        workflow = StateGraph(TutorialState)

        # Workflow is a type of graph builder that allows you to create a graph of nodes and edges.
        # Nodes are the states of the agent, and edges are the transitions between states.
        # Edges are the transitions between states.

        # Add nodes - 原有节点
        workflow.add_node("generate_tutorial", self._generate_tutorial)
        workflow.add_node("handle_question", self._handle_question)
        workflow.add_node("create_evaluation", self._create_evaluation)
        workflow.add_node("evaluate_answer", self._evaluate_answer)

        # Add nodes - 交互式语音教学新节点
        workflow.add_node("analyze_image_content", self._analyze_image_content)
        workflow.add_node("generate_teaching_segments", self._generate_teaching_segments)
        workflow.add_node("handle_voice_question", self._handle_voice_question)
        workflow.add_node("generate_transition", self._generate_transition)

        # Set entry point
        workflow.set_entry_point("generate_tutorial")

        # Add conditional edges based on user input and current mode
        workflow.add_conditional_edges(
            "generate_tutorial",
            self._route_after_tutorial,
            {
                "question": "handle_question",
                "evaluation": "create_evaluation",
                "end": END
            }
        )

        workflow.add_conditional_edges(
            "handle_question",
            self._route_after_question,
            {
                "question": "handle_question",
                "evaluation": "create_evaluation",
                "end": END
            }
        )

        workflow.add_conditional_edges(
            "create_evaluation",
            self._route_after_evaluation,
            {
                "question": "handle_question",
                "evaluation": "create_evaluation",
                "end": END
            }
        )

        workflow.add_conditional_edges(
            "evaluate_answer",
            self._route_after_evaluation_answer,
            {
                "question": "handle_question",
                "evaluation": "create_evaluation",
                "end": END
            }
        )

        # 交互式语音教学的边
        workflow.add_edge("analyze_image_content", "generate_teaching_segments")
        workflow.add_edge("generate_teaching_segments", END)
        workflow.add_edge("handle_voice_question", "generate_transition")
        workflow.add_edge("generate_transition", END)

        return workflow.compile()
    
    def _generate_tutorial(self, state: TutorialState) -> TutorialState:
        """Generate initial tutorial content for the subject."""
        subject = state["subject"]
        
        prompt = f"""You are an expert AI tutor. Create a comprehensive but concise tutorial about {subject}.

Structure your response as follows:
1. Brief introduction to the topic
2. Key concepts and definitions
3. Important examples
4. Common applications or use cases
5. Tips for further learning

Keep the tutorial engaging, educational, and appropriate for beginners to intermediate learners.
Use clear examples and explanations. Aim for about 300-500 words."""

        response = self._call_llm(prompt)
        
        # Save to database
        self.db.add_message(
            state["conversation_id"], 
            "assistant", 
            response, 
            "tutorial"
        )
        
        tutorial_message = AIMessage(content=response)
        
        return {
            **state,
            "messages": state["messages"] + [tutorial_message],
            "current_mode": "qa"
        }
    
    def _handle_question(self, state: TutorialState) -> TutorialState:
        """Handle user questions about the tutorial content."""
        subject = state["subject"]
        user_question = state["messages"][-1].content
        
        # Get conversation context
        context_messages = state["messages"][-5:]  # Last 5 messages for context
        context = "\n".join([f"{msg.__class__.__name__[:-7]}: {msg.content}" for msg in context_messages])
        
        prompt = f"""You are an expert AI tutor teaching about {subject}.

Previous conversation context:
{context}

The student has asked: "{user_question}"

Provide a clear, detailed explanation that directly answers their question. Use examples where helpful.
Be encouraging and educational. If the question is off-topic, gently guide them back to {subject}."""

        response = self._call_llm(prompt)
        
        # Save to database
        self.db.add_message(
            state["conversation_id"], 
            "user", 
            user_question, 
            "question"
        )
        self.db.add_message(
            state["conversation_id"], 
            "assistant", 
            response, 
            "answer"
        )
        
        answer_message = AIMessage(content=response)
        
        return {
            **state,
            "messages": state["messages"] + [answer_message],
            "current_mode": "qa"
        }
    
    def _create_evaluation(self, state: TutorialState) -> TutorialState:
        """Create evaluation questions to test user understanding."""
        subject = state["subject"]
        evaluation_count = state.get("evaluation_count", 0)
        
        # Get tutorial content for context
        tutorial_content = ""
        for msg in state["messages"]:
            if isinstance(msg, AIMessage):
                tutorial_content += msg.content + "\n"
        
        prompt = f"""You are an expert AI tutor. Based on the tutorial content about {subject}, create a thoughtful evaluation question.

Tutorial content covered:
{tutorial_content[:1000]}...

Create ONE evaluation question that:
1. Tests understanding of key concepts
2. Is neither too easy nor too difficult
3. Requires the student to demonstrate comprehension
4. Can be answered in 1-3 sentences

Format your response as:
QUESTION: [Your question here]

This is evaluation question #{evaluation_count + 1}."""

        response = self._call_llm(prompt)
        
        # Save to database
        self.db.add_message(
            state["conversation_id"], 
            "assistant", 
            response, 
            "evaluation_question"
        )
        
        eval_message = AIMessage(content=response)
        
        return {
            **state,
            "messages": state["messages"] + [eval_message],
            "current_mode": "evaluation",
            "evaluation_count": evaluation_count + 1
        }
    
    def _evaluate_answer(self, state: TutorialState) -> TutorialState:
        """Evaluate user's answer to evaluation question."""
        subject = state["subject"]
        user_answer = state["messages"][-1].content
        eval_question = state["messages"][-2].content
        
        prompt = f"""You are an expert AI tutor evaluating a student's answer about {subject}.

Evaluation Question: {eval_question}
Student's Answer: {user_answer}

Provide constructive feedback that:
1. Acknowledges what the student got right
2. Gently corrects any misconceptions
3. Provides additional clarification if needed
4. Encourages continued learning

Be supportive and educational. Rate their understanding and provide specific feedback."""

        response = self._call_llm(prompt)
        
        # Save to database
        self.db.add_message(
            state["conversation_id"], 
            "user", 
            user_answer, 
            "evaluation_answer"
        )
        self.db.add_message(
            state["conversation_id"], 
            "assistant", 
            response, 
            "evaluation_feedback"
        )
        
        feedback_message = AIMessage(content=response)

        return {
            **state,
            "messages": state["messages"] + [feedback_message],
            "current_mode": "qa"
        }

    # ==================== 交互式语音教学方法 ====================

    def _analyze_image_content(self, state: TutorialState) -> TutorialState:
        """分析图片中的教材内容或题目"""
        image_base64 = state.get("content_image", "")
        content_text = state.get("content_text", "")

        # 如果有图片，先分析图片
        if image_base64:
            prompt = """你是一位专业的教育内容分析专家。请仔细分析这张教材图片中的内容。

请识别并提取：
1. 这是知识点讲解还是题目？
2. 图片中的主要文字内容（请完整提取）
3. 涉及的核心概念
4. 所属的学科领域
5. 适合的学习层次（初级/中级/高级）

请用以下JSON格式输出：
{
    "type": "知识点/题目",
    "extracted_text": "提取的完整文字内容",
    "core_concepts": ["概念1", "概念2"],
    "subject_area": "学科领域",
    "difficulty": "难度等级"
}"""
            analysis_result = self._call_llm_with_image(prompt, image_base64)

            # 尝试解析JSON
            try:
                json_match = re.search(r'\{[\s\S]*\}', analysis_result)
                if json_match:
                    analysis_data = json.loads(json_match.group())
                    content_text = analysis_data.get("extracted_text", content_text)
            except json.JSONDecodeError:
                pass

        # 分析内容结构
        analysis_prompt = f"""分析以下教材内容的结构和知识点：

{content_text}

请识别：
1. 内容类型（知识点讲解/例题/练习题）
2. 核心知识点列表
3. 需要掌握的前置知识
4. 学习重点和难点"""

        analysis = self._call_llm(analysis_prompt)

        # 保存到数据库
        self.db.add_message(
            state["conversation_id"],
            "assistant",
            f"📚 内容分析完成：\n{analysis}",
            "content_analysis"
        )

        return {
            **state,
            "content_text": content_text,
            "messages": state["messages"] + [AIMessage(content=analysis)],
            "current_mode": "voice_teaching"
        }

    def _generate_teaching_segments(self, state: TutorialState) -> TutorialState:
        """生成分段讲解内容，适合语音朗读"""
        content_text = state.get("content_text", "")

        system_prompt = """你是一位经验丰富、循循善诱的老师。你的讲解风格：
- 语言亲切自然，像在和学生面对面交流
- 善于用生活中的例子来解释抽象概念
- 每个知识点都会确保学生理解后再继续
- 会适时停顿让学生思考
- 语言口语化，适合语音朗读（避免使用特殊符号和复杂公式表达）"""

        prompt = f"""请为以下内容生成详细的语音讲解脚本，要求：

1. 将内容分成3-6个讲解段落
2. 每个段落聚焦一个知识点或解题步骤
3. 每段讲解要口语化，适合语音朗读（避免书面语）
4. 每段之间要有自然的过渡语
5. 适当加入引导语如"同学们注意"、"这里很重要"等

内容：
{content_text}

请严格按照以下JSON格式输出：
{{
    "segments": [
        {{
            "title": "段落标题（简短）",
            "content": "完整的口语化讲解内容（150-300字）",
            "key_points": ["要点1", "要点2"]
        }}
    ]
}}"""

        response = self._call_llm(prompt, system_prompt)

        # 解析JSON
        segments = []
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                segments_data = json.loads(json_match.group())
                raw_segments = segments_data.get("segments", [])
                for seg in raw_segments:
                    segments.append({
                        "title": seg.get("title", "讲解"),
                        "content": seg.get("content", ""),
                        "key_points": seg.get("key_points", []),
                        "audio_duration": None
                    })
        except json.JSONDecodeError:
            # 如果解析失败，将整个响应作为一个分段
            segments = [{
                "title": "讲解",
                "content": response,
                "key_points": [],
                "audio_duration": None
            }]

        # 保存到数据库
        segments_summary = "\n".join([f"📖 {s['title']}: {s['content'][:50]}..." for s in segments])
        self.db.add_message(
            state["conversation_id"],
            "assistant",
            f"🎙️ 已生成 {len(segments)} 个讲解分段：\n{segments_summary}",
            "teaching_segments"
        )

        return {
            **state,
            "teaching_segments": segments,
            "current_segment_index": 0,
            "is_voice_paused": False,
            "current_mode": "voice_teaching"
        }

    def _handle_voice_question(self, state: TutorialState) -> TutorialState:
        """处理用户在语音讲解过程中提出的问题"""
        pending_question = state.get("pending_question", "")
        content_text = state.get("content_text", "")
        current_segment_index = state.get("current_segment_index", 0)
        teaching_segments = state.get("teaching_segments", [])

        # 获取当前讲解上下文
        current_context = ""
        if teaching_segments and current_segment_index < len(teaching_segments):
            current_segment = teaching_segments[current_segment_index]
            current_context = f"当前正在讲解：{current_segment['title']}\n内容：{current_segment['content']}"

        system_prompt = """你是一位耐心的老师，学生在听你的讲解时提出了困惑。
请针对学生的问题进行详细解答：
- 首先理解学生困惑的点
- 用通俗易懂的语言解释
- 可以举例说明
- 语言要口语化，适合语音朗读
- 解答完后给学生一些鼓励"""

        prompt = f"""学生在听讲解时提出了问题。

原教材内容：
{content_text[:500]}

{current_context}

学生的问题："{pending_question}"

请详细解答这个问题（100-200字，口语化）："""

        qa_answer = self._call_llm(prompt, system_prompt)

        # 保存到数据库
        self.db.add_message(
            state["conversation_id"],
            "user",
            f"❓ 问题：{pending_question}",
            "voice_question"
        )
        self.db.add_message(
            state["conversation_id"],
            "assistant",
            f"💡 解答：{qa_answer}",
            "voice_answer"
        )

        return {
            **state,
            "qa_answer": qa_answer,
            "current_mode": "voice_qa",
            "is_voice_paused": True,
            "messages": state["messages"] + [
                HumanMessage(content=pending_question),
                AIMessage(content=qa_answer)
            ]
        }

    def _generate_transition(self, state: TutorialState) -> TutorialState:
        """生成从问答回到主讲解的过渡衔接语"""
        pending_question = state.get("pending_question", "")
        qa_answer = state.get("qa_answer", "")
        current_segment_index = state.get("current_segment_index", 0)
        teaching_segments = state.get("teaching_segments", [])

        # 获取下一段讲解内容的预览
        next_content = ""
        if teaching_segments and current_segment_index < len(teaching_segments):
            next_segment = teaching_segments[current_segment_index]
            next_content = f"接下来要讲的内容：{next_segment['title']}"

        prompt = f"""刚才解答了学生的问题，现在需要生成一段过渡语，帮助学生从问答环节平滑过渡回主讲解。

刚才的问题：{pending_question}
解答摘要：{qa_answer[:100]}...

{next_content}

请生成一段自然的过渡语（30-50字，口语化），例如：
"好的，这个问题我们已经解答清楚了。现在让我们继续..."
"""

        transition_text = self._call_llm(prompt)

        # 保存到数据库
        self.db.add_message(
            state["conversation_id"],
            "assistant",
            f"🔄 过渡：{transition_text}",
            "transition"
        )

        return {
            **state,
            "transition_text": transition_text,
            "pending_question": None,
            "qa_answer": None,
            "is_voice_paused": False,
            "current_mode": "voice_resume"
        }
    
    def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Call the LLM using the configured API setup."""
        try:
            from LLM_api import send_request, LLM_PROVIDER, create_client, get_model_name

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # 使用配置的客户端和模型
            current_client = create_client()
            model = get_model_name(is_vision=False)

            print(f"Sending text request using model {model}...")

            extra_headers = {}
            if LLM_PROVIDER == "openrouter":
                extra_headers = {
                    "HTTP-Referer": "AI-Tutorial-Agent",
                    "X-Title": "AI Tutorial Agent",
                }

            completion = current_client.chat.completions.create(
                model=model,
                messages=messages,
                extra_headers=extra_headers if extra_headers else None,
            )

            result = completion.choices[0].message.content
            print(f"Text Response: {result[:100]}..." if len(result) > 100 else f"Text Response: {result}")
            return result
        except Exception as e:
            print(f"LLM Error: {str(e)}")
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."

    def _call_llm_with_image(self, prompt: str, image_base64: str) -> str:
        """调用支持视觉的LLM分析图片（优先使用阿里云 VLM）"""
        try:
            # 使用 LLM_api 中的 send_vision_request 函数
            # 该函数会自动选择阿里云 VLM（如果配置了）或其他提供商
            return send_vision_request(prompt, image_base64)
        except Exception as e:
            return f"图片分析失败: {str(e)}"
    
    def _route_after_tutorial(self, state: TutorialState) -> str:
        """Route after tutorial generation - wait for user input."""
        return "end"  # End and wait for user input
    
    def _route_after_question(self, state: TutorialState) -> str:
        """Route after handling a question."""
        return "end"  # End and wait for user input
    
    def _route_after_evaluation(self, state: TutorialState) -> str:
        """Route after creating evaluation question."""
        return "end"  # End and wait for user answer
    
    def _route_after_evaluation_answer(self, state: TutorialState) -> str:
        """Route after evaluating user's answer."""
        return "end"  # End and wait for next user input
    
    def start_tutorial(self, session_id: str, subject: str) -> Dict[str, Any]:
        """Start a new tutorial session."""
        # Create conversation in database
        conversation_id = self.db.create_conversation(session_id, subject)
        
        # Initialize state
        initial_state = TutorialState(
            messages=[],
            subject=subject,
            conversation_id=conversation_id,
            current_mode="tutorial",
            evaluation_count=0,
            user_understanding={}
        )
        
        # Generate tutorial
        result = self.graph.invoke(initial_state)
        
        return {
            "conversation_id": conversation_id,
            "response": result["messages"][-1].content,
            "mode": result["current_mode"]
        }
    
    def continue_conversation(self, conversation_id: int, user_input: str, input_type: str = "question") -> Dict[str, Any]:
        """Continue an existing conversation."""
        # Get conversation history
        history = self.db.get_conversation_history(conversation_id)
        
        # Reconstruct state
        messages = []
        conversation_info = None
        
        # Get conversation info from database
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT subject FROM conversations WHERE id = ?", (conversation_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {"error": "Conversation not found"}
        
        subject = result[0]
        
        # Convert history to messages
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        # Add new user message
        messages.append(HumanMessage(content=user_input))
        
        # Determine current state
        current_mode = "qa"
        evaluation_count = len([msg for msg in history if msg.get("message_type") == "evaluation_question"])
        
        # Check if this is an evaluation answer
        if history and history[-1].get("message_type") == "evaluation_question":
            current_mode = "evaluation_answer"
        
        state = TutorialState(
            messages=messages,
            subject=subject,
            conversation_id=conversation_id,
            current_mode=current_mode,
            evaluation_count=evaluation_count,
            user_understanding={}
        )
        
        # Process based on input type and current mode
        if current_mode == "evaluation_answer":
            result = self._evaluate_answer(state)
        elif input_type == "evaluation_request":
            result = self._create_evaluation(state)
        else:
            result = self._handle_question(state)

        return {
            "response": result["messages"][-1].content,
            "mode": result["current_mode"]
        }

    # ==================== 交互式语音教学入口方法 ====================

    def start_voice_teaching(self, session_id: str, content: str, image_base64: str = None) -> Dict[str, Any]:
        """开始交互式语音教学

        Args:
            session_id: 会话ID
            content: 文本内容（可选，如果有图片会从图片提取）
            image_base64: Base64编码的图片（可选）

        Returns:
            包含讲解分段的响应
        """
        # 创建会话
        subject = "语音讲解教学"
        conversation_id = self.db.create_conversation(session_id, subject)

        # 初始化状态
        initial_state = TutorialState(
            messages=[],
            subject=subject,
            conversation_id=conversation_id,
            current_mode="voice_teaching",
            evaluation_count=0,
            user_understanding={},
            content_image=image_base64,
            content_text=content or "",
            teaching_segments=[],
            current_segment_index=0,
            is_voice_paused=False,
            pending_question=None,
            qa_answer=None,
            transition_text=None
        )

        # 分析内容
        state_after_analysis = self._analyze_image_content(initial_state)

        # 生成分段讲解
        final_state = self._generate_teaching_segments(state_after_analysis)

        return {
            "conversation_id": conversation_id,
            "segments": final_state.get("teaching_segments", []),
            "content_text": final_state.get("content_text", ""),
            "mode": "voice_teaching",
            "message": "讲解内容已生成，准备开始语音播放"
        }

    def ask_question_during_voice(self, conversation_id: int, question: str,
                                   current_segment_index: int,
                                   teaching_segments: List[Dict] = None) -> Dict[str, Any]:
        """在语音讲解过程中提问

        Args:
            conversation_id: 会话ID
            question: 用户的问题
            current_segment_index: 当前播放到的分段索引
            teaching_segments: 当前的讲解分段列表

        Returns:
            包含问答内容和过渡语的响应
        """
        # 获取会话历史
        history = self.db.get_conversation_history(conversation_id)

        # 获取原始内容
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT subject FROM conversations WHERE id = ?", (conversation_id,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return {"error": "会话不存在"}

        # 重建消息历史
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        # 从历史中提取原始内容
        content_text = ""
        for msg in history:
            if msg.get("message_type") == "teaching_segments":
                # 尝试从讲解分段消息中提取内容信息
                break

        # 构建状态
        state = TutorialState(
            messages=messages,
            subject="语音讲解教学",
            conversation_id=conversation_id,
            current_mode="voice_qa",
            evaluation_count=0,
            user_understanding={},
            content_image=None,
            content_text=content_text,
            teaching_segments=teaching_segments or [],
            current_segment_index=current_segment_index,
            is_voice_paused=True,
            pending_question=question,
            qa_answer=None,
            transition_text=None
        )

        # 处理问题
        state_after_qa = self._handle_voice_question(state)

        # 生成过渡语
        final_state = self._generate_transition(state_after_qa)

        return {
            "answer": final_state.get("qa_answer", ""),
            "transition": final_state.get("transition_text", ""),
            "current_segment_index": current_segment_index,
            "mode": "voice_resume",
            "message": "问题已解答，准备继续讲解"
        }

    def get_next_segment(self, conversation_id: int, current_index: int,
                         teaching_segments: List[Dict]) -> Dict[str, Any]:
        """获取下一个讲解分段

        Args:
            conversation_id: 会话ID
            current_index: 当前分段索引
            teaching_segments: 讲解分段列表

        Returns:
            下一个分段的内容
        """
        next_index = current_index + 1

        if next_index >= len(teaching_segments):
            # 已经是最后一段
            return {
                "has_next": False,
                "segment": None,
                "index": current_index,
                "message": "讲解已完成"
            }

        next_segment = teaching_segments[next_index]

        return {
            "has_next": next_index < len(teaching_segments) - 1,
            "segment": next_segment,
            "index": next_index,
            "total": len(teaching_segments),
            "message": f"正在播放第 {next_index + 1}/{len(teaching_segments)} 段"
        }