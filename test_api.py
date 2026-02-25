import requests
import os

MINIMAX_API_KEY = os.getenv('MINIMAX_API_KEY')
MINIMAX_URL = "https://api.minimax.chat/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {MINIMAX_API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "MiniMax-M2.5",
    "messages": [
        {"role": "system", "content": "你是一个友好的客服助手。请用简单易懂的日常语言回答用户的问题。回答要具体、明确、有帮助。避免使用复杂的专业术语，如果必须使用，要用通俗的话解释清楚。保持友好、耐心、积极的态度。直接回答问题，不要绕弯子。回答要简洁但完整，包含用户需要的所有信息。用自然、流畅的中文表达，就像和朋友聊天一样。"},
        {"role": "user", "content": "请简单介绍一下你自己"}
    ],
    "temperature": 0.5,
    "max_tokens": 1000,
    "stream": False
}

response = requests.post(MINIMAX_URL, headers=headers, json=data)
print("Status Code:", response.status_code)
print("Response:", response.json())