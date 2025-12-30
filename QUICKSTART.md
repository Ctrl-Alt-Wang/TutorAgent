# 🚀 快速开始指南

## 📦 环境准备

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置 API Key（可选）

创建 `.env` 文件：
```bash
cp .env.example .env
```

编辑 `.env` 配置你的 LLM API：
```env
# 使用阿里云通义千问（推荐，支持图片识别）
LLM_PROVIDER=aliyun
ALIYUN_API_KEY=your-api-key-here
ALIYUN_MODEL=qwen-vl-max
ALIYUN_TEXT_MODEL=qwen-turbo

# 或使用 OpenRouter
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-api-key-here
OPENROUTER_MODEL=meta-llama/llama-4-scout

# 或使用 OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o
```

---

## 🏃 启动服务

### 方式一：直接启动
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 方式二：后台运行
```bash
nohup uvicorn app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

### 方式三：Python脚本
```bash
python app.py
```

---

## 🌐 访问系统

打开浏览器访问：
- 本地：http://localhost:8000
- 网络：http://your-server-ip:8000

---

## 💡 使用步骤

### 1️⃣ 上传内容
- **方式A**：拖拽图片到左侧上传区域
- **方式B**：点击上传区域选择图片
- **方式C**：直接在文本框输入内容
- **方式D**：点击快速示例体验

### 2️⃣ 开始讲解
点击 "🚀 开始智能讲解" 按钮

### 3️⃣ 自动播放
- 系统自动分析内容并生成讲解
- 内容逐段显示（打字机效果）
- 语音自动连续播放

### 4️⃣ 随时提问
- 点击右下角 "💬 有疑问？" 浮动按钮
- 输入你的问题
- AI 自动解答并继续讲解

---

## 🎯 核心特性

### ✨ 自动化流程
- ✅ 内容自动逐段播放
- ✅ 无需手动点击下一段
- ✅ 问答后自动恢复

### 🎨 视觉体验
- ✅ 打字机效果呈现内容
- ✅ 现代化渐变设计
- ✅ 流畅的动画过渡

### 💬 智能交互
- ✅ 问答内容内嵌显示
- ✅ 智能过渡语衔接
- ✅ 浮动提问按钮

---

## 🐛 常见问题

### Q1: 页面显示 "unable to open database file"
**解决**：已自动修复，数据库目录会在首次启动时自动创建

### Q2: 语音无法播放
**检查**：
- 确保浏览器支持 Web Speech API
- Chrome、Edge、Safari 支持较好
- Firefox 部分版本可能不支持

### Q3: 图片识别失败
**原因**：需要配置支持视觉的 LLM
**解决**：
- 使用阿里云 qwen-vl-max（推荐）
- 或使用 OpenAI gpt-4o

### Q4: API 请求失败
**检查**：
1. `.env` 文件是否配置正确
2. API Key 是否有效
3. 网络连接是否正常
4. 查看 `server.log` 日志

---

## 📱 浏览器兼容性

| 浏览器 | 版本 | 支持程度 |
|--------|------|---------|
| Chrome | 最新 | ✅ 完美支持 |
| Edge | 最新 | ✅ 完美支持 |
| Safari | 最新 | ✅ 完美支持 |
| Firefox | 最新 | ⚠️ 语音可能不支持 |

---

## 🔧 开发调试

### 查看日志
```bash
tail -f server.log
```

### 测试 API
```bash
# 测试启动教学
curl -X POST http://localhost:8000/api/start-teaching \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "content_text": "勾股定理：a² + b² = c²",
    "image_base64": null
  }'
```

### 重启服务
```bash
# 找到进程
ps aux | grep uvicorn

# 杀掉进程
kill <PID>

# 重新启动
uvicorn app:app --host 0.0.0.0 --port 8000
```

---

## 📚 更多文档

- [README.md](README.md) - 项目概述
- [IMPROVEMENTS.md](IMPROVEMENTS.md) - 详细改进说明
- [config.py](config.py) - 配置参数说明

---

## 🎉 开始体验

现在访问 http://localhost:8000 开始体验全新的 AI 智能教学助手！

**推荐体验流程**：
1. 点击 "勾股定理" 快速示例
2. 观察打字机效果和自动播放
3. 点击浮动按钮提问："能举个实际例子吗？"
4. 体验智能衔接回到主讲解

享受流畅的学习体验！🚀
