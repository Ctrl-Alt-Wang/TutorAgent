"""
FastAPI 后端服务 - AI 交互式语音教学系统
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import base64
import uuid
import json
import os

from tutorial_agent import TutorialAgent
from database import TutorialDatabase

# 创建 FastAPI 应用
app = FastAPI(
    title="AI 交互式语音教学系统",
    description="智能教学助手，支持图片识别、语音讲解、实时问答",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建静态文件目录
os.makedirs("static", exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 存储会话数据
sessions = {}

# ==================== 数据模型 ====================

class StartTeachingRequest(BaseModel):
    session_id: str
    content_text: Optional[str] = ""
    image_base64: Optional[str] = None

class AskQuestionRequest(BaseModel):
    session_id: str
    question: str
    current_segment_index: int

class SessionData(BaseModel):
    conversation_id: Optional[int] = None
    segments: List[dict] = []
    current_segment_index: int = -1
    content_text: str = ""

# ==================== API 路由 ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """返回主页面"""
    return FileResponse("static/index.html")


@app.post("/api/start-teaching")
async def start_teaching(request: StartTeachingRequest):
    """开始语音教学"""
    try:
        agent = TutorialAgent()
        result = agent.start_voice_teaching(
            request.session_id,
            request.content_text or "",
            request.image_base64
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # 保存会话数据
        sessions[request.session_id] = {
            "conversation_id": result.get("conversation_id"),
            "segments": result.get("segments", []),
            "content_text": result.get("content_text", "")
        }
        
        return {
            "success": True,
            "conversation_id": result.get("conversation_id"),
            "segments": result.get("segments", []),
            "content_text": result.get("content_text", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ask-question")
async def ask_question(request: AskQuestionRequest):
    """处理用户提问"""
    try:
        session_data = sessions.get(request.session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        agent = TutorialAgent()
        result = agent.ask_question_during_voice(
            session_data["conversation_id"],
            request.question,
            request.current_segment_index,
            session_data["segments"]
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "success": True,
            "answer": result.get("answer", ""),
            "transition": result.get("transition", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """上传图片并返回 base64"""
    try:
        contents = await file.read()
        image_base64 = base64.b64encode(contents).decode('utf-8')
        return {
            "success": True,
            "image_base64": image_base64,
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """获取会话数据"""
    session_data = sessions.get(session_id)
    if not session_data:
        return {"exists": False}
    return {"exists": True, **session_data}


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    if session_id in sessions:
        del sessions[session_id]
    return {"success": True}


# ==================== 启动服务 ====================

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动 AI 交互式语音教学系统...")
    print("📍 访问地址: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

