# 🎤 AI 交互式语音教学系统 (TutorAgent)

一个智能交互式语音教学系统，支持图片识别、语音讲解、实时问答。

## ✨ 功能特点

- 📷 **图片识别** - 上传教材截图，AI 自动分析内容
- 🎙️ **语音讲解** - 分段讲解，逐步深入，支持暂停/继续
- ❓ **随时提问** - 暂停讲解，即时解答你的疑问
- 🔗 **无缝衔接** - 解答后平滑过渡，继续主讲解

## 🛠️ 技术栈

### 后端
- **FastAPI** - 高性能 Python Web 框架
- **LangGraph** - 状态机工作流
- **OpenAI / 阿里云通义千问** - LLM 支持

### 前端
- **HTML5 + CSS3 + JavaScript** - 原生实现
- **Web Speech API** - 浏览器语音合成

## 📦 安装

1. 克隆仓库
```bash
git clone https://github.com/Ctrl-Alt-Wang/TutorAgent.git
cd TutorAgent
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

4. 启动服务
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

5. 访问 http://localhost:8000

## ⚙️ 配置说明

在 `.env` 文件中配置：

```env
# LLM 提供商: aliyun, openrouter, openai
LLM_PROVIDER=aliyun

# 阿里云通义千问
ALIYUN_API_KEY=your-api-key
ALIYUN_MODEL=qwen-vl-max
ALIYUN_TEXT_MODEL=qwen-turbo

# OpenRouter (备用)
OPENROUTER_API_KEY=your-api-key
```

## 📁 项目结构

```
TutorAgent/
├── app.py              # FastAPI 后端服务
├── tutorial_agent.py   # AI 教学代理 (LangGraph)
├── LLM_api.py          # LLM API 封装
├── database.py         # SQLite 数据库
├── static/
│   ├── index.html      # 主页面
│   ├── styles.css      # 样式表
│   └── app.js          # 前端逻辑
├── requirements.txt    # Python 依赖
├── .env.example        # 环境变量示例
└── README.md           # 项目说明
```

## 🚀 使用方法

1. **上传内容** - 在侧边栏上传教材图片或输入文本
2. **开始教学** - 点击"开始语音教学"按钮
3. **控制播放** - 使用播放/暂停/上一段/下一段按钮
4. **提问** - 点击"我有问题"按钮，输入你的疑问
5. **继续学习** - 查看答案后点击"继续讲解"

## 📄 License

MIT License

