import streamlit as st
import uuid
import base64
import json
from tutorial_agent import TutorialAgent

# 页面配置
st.set_page_config(
    page_title="AI 交互式语音教学",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    /* 主标题样式 */
    .main-title {
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }

    /* 副标题样式 */
    .sub-title {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* 卡片样式 */
    .content-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    /* 进度条容器 */
    .progress-container {
        background: #e0e0e0;
        border-radius: 10px;
        margin: 20px 0;
    }

    /* 控制按钮区域 */
    .control-buttons {
        display: flex;
        justify-content: center;
        gap: 10px;
        margin: 20px 0;
    }

    /* 问答卡片 */
    .qa-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
    }

    /* 要点列表 */
    .key-point {
        background: #f0f2f6;
        border-left: 4px solid #667eea;
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 0 8px 8px 0;
    }

    /* 欢迎区域 */
    .welcome-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 20px;
        padding: 30px;
        margin: 20px 0;
    }

    /* 功能卡片 */
    .feature-card {
        background: white;
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }

    .feature-card:hover {
        transform: translateY(-5px);
    }

    /* 侧边栏样式 */
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }

    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 初始化会话状态
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "agent" not in st.session_state:
    st.session_state.agent = TutorialAgent()
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "teaching_segments" not in st.session_state:
    st.session_state.teaching_segments = []
if "current_segment_index" not in st.session_state:
    st.session_state.current_segment_index = -1
if "is_playing" not in st.session_state:
    st.session_state.is_playing = False
if "show_question_input" not in st.session_state:
    st.session_state.show_question_input = False
if "qa_result" not in st.session_state:
    st.session_state.qa_result = None
if "content_image" not in st.session_state:
    st.session_state.content_image = None


def inject_speech_js():
    """注入语音合成JavaScript"""
    st.components.v1.html("""
    <script>
    window.speak = function(text) {
        if (!window.speechSynthesis) return;
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        const voices = window.speechSynthesis.getVoices();
        const chineseVoice = voices.find(v => v.lang.startsWith('zh')) || voices[0];
        if (chineseVoice) utterance.voice = chineseVoice;
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
    };
    window.pauseSpeech = function() {
        if (window.speechSynthesis) window.speechSynthesis.pause();
    };
    window.resumeSpeech = function() {
        if (window.speechSynthesis) window.speechSynthesis.resume();
    };
    window.stopSpeech = function() {
        if (window.speechSynthesis) window.speechSynthesis.cancel();
    };
    // 初始化语音
    if (window.speechSynthesis) {
        window.speechSynthesis.getVoices();
    }
    </script>
    """, height=0)


def start_voice_teaching(content_text, image_base64=None):
    """开始语音教学"""
    try:
        with st.spinner("🔄 正在分析内容并生成讲解..."):
            result = st.session_state.agent.start_voice_teaching(
                st.session_state.session_id,
                content_text,
                image_base64
            )
            if "error" in result:
                st.error(f"❌ 错误: {result['error']}")
                return False
            st.session_state.current_conversation_id = result.get("conversation_id")
            st.session_state.teaching_segments = result.get("segments", [])
            st.session_state.current_segment_index = -1
            st.session_state.is_playing = False
            if st.session_state.teaching_segments:
                return True
            else:
                st.warning("⚠️ 未能生成讲解内容")
                return False
    except Exception as e:
        st.error(f"❌ 启动失败: {str(e)}")
        return False


def handle_user_question(question):
    """处理用户提问"""
    if not st.session_state.current_conversation_id:
        st.warning("请先开始教学")
        return
    try:
        with st.spinner("🤔 正在思考..."):
            result = st.session_state.agent.ask_question_during_voice(
                st.session_state.current_conversation_id,
                question,
                st.session_state.current_segment_index,
                st.session_state.teaching_segments
            )
            if "error" in result:
                st.error(f"❌ 错误: {result['error']}")
                return
            st.session_state.qa_result = {
                "question": question,
                "answer": result.get("answer", ""),
                "transition": result.get("transition", "")
            }
            st.session_state.show_question_input = False
    except Exception as e:
        st.error(f"❌ 处理失败: {str(e)}")


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown("## 📚 教学内容")

        # 上传图片
        st.markdown("### 📷 上传教材图片")
        uploaded_file = st.file_uploader(
            "支持 PNG、JPG、JPEG",
            type=["png", "jpg", "jpeg"],
            key="uploader"
        )

        if uploaded_file:
            try:
                image_bytes = uploaded_file.getvalue()
                st.session_state.content_image = base64.b64encode(image_bytes).decode('utf-8')
                st.image(image_bytes, caption='已上传的图片')
            except Exception as e:
                st.error(f"图片处理失败: {str(e)}")

        st.markdown("---")

        # 文本输入
        st.markdown("### 📝 或输入文本")
        content_input = st.text_area(
            "粘贴教材内容",
            height=120,
            placeholder="输入知识点、题目或概念...",
            key="content_input"
        )

        st.markdown("---")

        # 开始按钮
        if st.button("🚀 开始语音教学", type="primary", use_container_width=True):
            image_b64 = st.session_state.get("content_image")
            text = content_input.strip() if content_input else ""
            if not text and not image_b64:
                st.warning("请上传图片或输入内容")
            else:
                if start_voice_teaching(text, image_b64):
                    st.rerun()

        # 重置按钮
        if st.session_state.teaching_segments:
            if st.button("🔄 重新开始", use_container_width=True):
                st.session_state.teaching_segments = []
                st.session_state.current_segment_index = -1
                st.session_state.is_playing = False
                st.session_state.qa_result = None
                st.session_state.content_image = None
                st.rerun()

        st.markdown("---")
        st.markdown("""
        ### 💡 使用说明
        1. 上传图片或输入文本
        2. 点击"开始语音教学"
        3. 使用控制按钮播放
        4. 随时点击"我有问题"
        """)


def render_teaching_content():
    """渲染教学内容区域"""
    segments = st.session_state.teaching_segments
    current_idx = st.session_state.current_segment_index
    total = len(segments)

    # 进度条
    if current_idx >= 0:
        progress = (current_idx + 1) / total
        st.progress(progress, text=f"📖 讲解进度: {current_idx + 1} / {total}")
    else:
        st.progress(0.0, text="📖 准备开始讲解...")

    st.markdown("---")

    # 当前分段内容
    if 0 <= current_idx < total:
        segment = segments[current_idx]

        # 标题
        st.markdown(f"## 📌 {segment.get('title', '讲解')}")

        # 内容卡片
        with st.container(border=True):
            st.markdown(f"""
            <div style="font-size: 1.1rem; line-height: 1.8; padding: 15px;">
                {segment.get('content', '')}
            </div>
            """, unsafe_allow_html=True)

        # 关键点
        key_points = segment.get('key_points', [])
        if key_points:
            st.markdown("### 📋 本段要点")
            cols = st.columns(len(key_points) if len(key_points) <= 3 else 3)
            for i, point in enumerate(key_points):
                with cols[i % 3]:
                    st.info(f"**{i+1}.** {point}")
    else:
        # 未开始，显示大纲
        st.info("👆 点击下方「▶️ 开始讲解」按钮开始学习")
        st.markdown("### 📑 讲解大纲")
        for i, seg in enumerate(segments, 1):
            with st.expander(f"第 {i} 段: {seg.get('title', '讲解')}"):
                st.write(seg.get('content', '')[:150] + "...")

    st.markdown("---")

    # 控制按钮
    render_control_buttons(segments, current_idx, total)


def render_control_buttons(segments, current_idx, total):
    """渲染控制按钮"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("⏮️ 上一段", disabled=(current_idx <= 0), use_container_width=True):
            st.session_state.current_segment_index = current_idx - 1
            new_seg = segments[current_idx - 1]
            st.components.v1.html(f"""
            <script>if(window.speak){{window.speak({json.dumps(new_seg.get('content',''))});}}</script>
            """, height=0)
            st.session_state.is_playing = True
            st.rerun()

    with col2:
        if current_idx < 0:
            if st.button("▶️ 开始讲解", type="primary", use_container_width=True):
                st.session_state.current_segment_index = 0
                first_seg = segments[0]
                st.components.v1.html(f"""
                <script>if(window.speak){{window.speak({json.dumps(first_seg.get('content',''))});}}</script>
                """, height=0)
                st.session_state.is_playing = True
                st.rerun()
        elif st.session_state.is_playing:
            if st.button("⏸️ 暂停", use_container_width=True):
                st.components.v1.html("<script>if(window.pauseSpeech){window.pauseSpeech();}</script>", height=0)
                st.session_state.is_playing = False
                st.rerun()
        else:
            if st.button("▶️ 继续", type="primary", use_container_width=True):
                st.components.v1.html("<script>if(window.resumeSpeech){window.resumeSpeech();}</script>", height=0)
                st.session_state.is_playing = True
                st.rerun()

    with col3:
        if st.button("⏭️ 下一段", disabled=(current_idx >= total - 1 or current_idx < 0), use_container_width=True):
            st.session_state.current_segment_index = current_idx + 1
            new_seg = segments[current_idx + 1]
            st.components.v1.html(f"""
            <script>if(window.speak){{window.speak({json.dumps(new_seg.get('content',''))});}}</script>
            """, height=0)
            st.session_state.is_playing = True
            st.rerun()

    with col4:
        if st.button("❓ 我有问题", type="secondary", disabled=(current_idx < 0), use_container_width=True):
            st.components.v1.html("<script>if(window.pauseSpeech){window.pauseSpeech();}</script>", height=0)
            st.session_state.is_playing = False
            st.session_state.show_question_input = True
            st.rerun()


def render_question_input():
    """渲染问题输入区域"""
    st.markdown("---")
    st.markdown("### ❓ 提出你的问题")

    with st.container(border=True):
        question = st.text_input(
            "请描述你的困惑:",
            placeholder="例如: 这个概念怎么理解？能举个例子吗？",
            key="question_text"
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📤 提交问题", type="primary", use_container_width=True):
                if question.strip():
                    handle_user_question(question.strip())
                    st.rerun()
                else:
                    st.warning("请输入问题")
        with col2:
            if st.button("❌ 取消", use_container_width=True):
                st.session_state.show_question_input = False
                st.rerun()


def render_qa_result(segments, current_idx, total):
    """渲染问答结果"""
    st.markdown("---")
    qa = st.session_state.qa_result

    with st.container(border=True):
        st.markdown("### 💬 问答环节")

        # 问题
        st.markdown(f"""
        <div style="background: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0;">
            <strong>❓ 你的问题:</strong><br>{qa.get('question', '')}
        </div>
        """, unsafe_allow_html=True)

        # 解答
        st.markdown("**💡 老师解答:**")
        answer = qa.get('answer', '')
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; padding: 20px; border-radius: 15px; margin: 10px 0;">
            {answer}
        </div>
        """, unsafe_allow_html=True)

        # 播放解答
        st.components.v1.html(f"""
        <script>if(window.speak){{window.speak({json.dumps(answer)});}}</script>
        """, height=0)

        # 过渡语
        if qa.get('transition'):
            st.markdown(f"**🔗 过渡:** {qa.get('transition', '')}")

        # 继续按钮
        if st.button("✅ 明白了，继续讲解", type="primary", use_container_width=True):
            transition = qa.get('transition', '')
            st.session_state.qa_result = None
            if 0 <= current_idx < total:
                content = segments[current_idx].get('content', '')
                full_text = f"{transition} {content}" if transition else content
                st.components.v1.html(f"""
                <script>if(window.speak){{window.speak({json.dumps(full_text)});}}</script>
                """, height=0)
            st.session_state.is_playing = True
            st.rerun()


def render_welcome():
    """渲染欢迎页面"""
    st.markdown("---")

    # 功能介绍
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; padding: 30px; border-radius: 20px; margin: 10px 0;">
            <h2>🎯 功能介绍</h2>
            <p style="font-size: 1.1rem;">这是一个智能交互式语音教学系统：</p>
            <ul style="font-size: 1rem;">
                <li>📷 <strong>图片识别</strong> - 上传教材截图，AI 自动分析</li>
                <li>🎙️ <strong>语音讲解</strong> - 分段讲解，逐步深入</li>
                <li>❓ <strong>随时提问</strong> - 暂停提问，即时解答</li>
                <li>🔗 <strong>无缝衔接</strong> - 解答后平滑继续</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        ### 📋 快速开始
        1. 在左侧边栏 **上传图片** 或 **输入文本**
        2. 点击 **「🚀 开始语音教学」**
        3. 使用控制按钮 **播放/暂停**
        4. 有疑问点击 **「❓ 我有问题」**
        """)

    with col2:
        st.markdown("### 📝 快速体验")
        st.markdown("点击下方示例立即开始：")

        examples = [
            ("🔢 勾股定理", "勾股定理：直角三角形两直角边的平方和等于斜边的平方，即 a² + b² = c²"),
            ("⚡ 牛顿定律", "牛顿第二定律：F=ma，物体的加速度与作用力成正比，与质量成反比"),
            ("🐍 Python", "Python列表推导式：[x**2 for x in range(10)]，可以快速生成列表"),
            ("🌱 光合作用", "光合作用：植物利用光能将二氧化碳和水转化为有机物和氧气")
        ]

        for label, content in examples:
            if st.button(label, key=f"ex_{label}", use_container_width=True):
                if start_voice_teaching(content):
                    st.rerun()


def main():
    """主函数"""
    inject_speech_js()

    # 标题
    st.markdown('<h1 class="main-title">🎤 AI 交互式语音教学</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">上传教材内容，体验智能语音讲解，随时提问！</p>', unsafe_allow_html=True)

    # 侧边栏
    render_sidebar()

    # 主内容区
    if st.session_state.teaching_segments:
        render_teaching_content()

        # 问题输入
        if st.session_state.show_question_input:
            render_question_input()

        # 问答结果
        if st.session_state.qa_result:
            segments = st.session_state.teaching_segments
            current_idx = st.session_state.current_segment_index
            total = len(segments)
            render_qa_result(segments, current_idx, total)
    else:
        render_welcome()


if __name__ == "__main__":
    main()

