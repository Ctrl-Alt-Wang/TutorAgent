import time
import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ==================== API 配置 ====================
# 可以选择使用的 LLM 提供商: "openrouter", "aliyun", "openai"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")

# OpenRouter 配置
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-4-scout")

# 阿里云通义千问 VLM 配置
ALIYUN_API_KEY = os.getenv("ALIYUN_API_KEY", "")  # 在 .env 文件中配置
ALIYUN_BASE_URL = os.getenv("ALIYUN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
ALIYUN_MODEL = os.getenv("ALIYUN_MODEL", "qwen-vl-max")  # 通义千问视觉模型
ALIYUN_TEXT_MODEL = os.getenv("ALIYUN_TEXT_MODEL", "qwen-turbo")  # 通义千问文本模型

# OpenAI 配置 (备用)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# ==================== 创建客户端 ====================

def create_client(provider=None):
    """根据提供商创建对应的 OpenAI 客户端"""
    provider = provider or LLM_PROVIDER

    if provider == "aliyun":
        return OpenAI(
            base_url=ALIYUN_BASE_URL,
            api_key=ALIYUN_API_KEY,
        )
    elif provider == "openai":
        return OpenAI(
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
    else:  # 默认使用 openrouter
        return OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )

def get_model_name(provider=None, is_vision=False):
    """获取对应提供商的模型名称"""
    provider = provider or LLM_PROVIDER

    if provider == "aliyun":
        return ALIYUN_MODEL if is_vision else ALIYUN_TEXT_MODEL
    elif provider == "openai":
        return OPENAI_MODEL
    else:
        return OPENROUTER_MODEL

# 创建默认客户端
client = create_client()

# 创建阿里云 VLM 客户端（用于图片分析）
vlm_client = create_client("aliyun") if ALIYUN_API_KEY else client

# ==================== API 调用函数 ====================

def send_request(prompt, provider=None):
    """Send a single request to the API and return the result."""
    provider = provider or LLM_PROVIDER
    current_client = create_client(provider)
    model = get_model_name(provider, is_vision=False)

    print(f"Sending request to {provider} using model {model}...")
    start_time = time.time()

    extra_headers = {}
    if provider == "openrouter":
        extra_headers = {
            "HTTP-Referer": "AI-Tutorial-Agent",
            "X-Title": "AI Tutorial Agent",
        }

    completion = current_client.chat.completions.create(
        extra_headers=extra_headers if extra_headers else None,
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    end_time = time.time()
    elapsed_time = end_time - start_time

    response = completion.choices[0].message.content
    print(f"Response: {response[:100]}..." if len(response) > 100 else f"Response: {response}")
    print(f"Generation time: {elapsed_time:.2f} seconds")

    return response

def send_vision_request(prompt, image_base64, provider=None):
    """发送带图片的请求到 VLM API"""
    # 优先使用阿里云的 VLM，如果没有配置则使用默认提供商
    if ALIYUN_API_KEY:
        provider = "aliyun"
    else:
        provider = provider or LLM_PROVIDER

    current_client = create_client(provider)
    model = get_model_name(provider, is_vision=True)

    print(f"Sending vision request to {provider} using model {model}...")
    start_time = time.time()

    extra_headers = {}
    if provider == "openrouter":
        extra_headers = {
            "HTTP-Referer": "AI-Tutorial-Agent",
            "X-Title": "AI Tutorial Agent",
        }

    # 构建消息内容
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
        ]
    }]

    completion = current_client.chat.completions.create(
        extra_headers=extra_headers if extra_headers else None,
        model=model,
        messages=messages
    )

    end_time = time.time()
    elapsed_time = end_time - start_time

    response = completion.choices[0].message.content
    print(f"Vision Response: {response[:100]}..." if len(response) > 100 else f"Vision Response: {response}")
    print(f"Generation time: {elapsed_time:.2f} seconds")

    return response

def main():
    prompt = "What is the meaning of life?"

    print("Starting request...")
    print(f"Using provider: {LLM_PROVIDER}")
    overall_start_time = time.time()

    response = send_request(prompt)

    overall_end_time = time.time()
    overall_elapsed_time = overall_end_time - overall_start_time

    print(f"\n===== SUMMARY =====")
    print(f"Total execution time: {overall_elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()