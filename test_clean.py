import re

def clean_ai_response(response):
    """清理AI响应，移除markdown、思考过程和特殊格式"""
    # 移除思考过程标签 <think>...</think>
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
    response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL | re.IGNORECASE)

    # 移除思考过程文本模式 - 更全面的模式
    thinking_patterns = [
        r'思考.*?(?:。|\n|$)',
        r'Let me think.*?(?:\.|\n|$)',
        r'I\'m thinking.*?(?:\.|\n|$)',
        r'First,.*?(?:\.|\n|$)',
        r'Step \d+:.*?(?:\.|\n|$)',
        r'分析一下.*?(?:。|\n|$)',
        r'让我考虑.*?(?:。|\n|$)',
        r'从.*?\开始.*?(?:。|\n|$)',
        r'需要.*?(?:。|\n|$)',
        r'应该.*?(?:。|\n|$)',
        r'可以.*?(?:。|\n|$)',
        r'最好.*?(?:。|\n|$)',
    ]

    for pattern in thinking_patterns:
        response = re.sub(pattern, '', response, flags=re.IGNORECASE)

    # 移除连续的思考相关句子
    lines = response.split('\n')
    filtered_lines = []
    for line in lines:
        line = line.strip()
        if not any(keyword in line.lower() for keyword in [
            '思考', 'think', '分析', '考虑', '首先', '第一', '然后', '接下来',
            '最后', '总结', '结论', '所以', '因此', '因为', '由于'
        ]):
            filtered_lines.append(line)

    response = '\n'.join(filtered_lines)

    # 移除markdown链接 [text](url)
    response = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', response)

    # 移除markdown粗体 **text**
    response = re.sub(r'\*\*([^\*]+)\*\*', r'\1', response)

    # 移除markdown斜体 *text*
    response = re.sub(r'\*([^\*]+)\*', r'\1', response)

    # 移除markdown代码块 ```code```
    response = re.sub(r'```[^\n]*\n(.*?)\n```', r'\1', response, flags=re.DOTALL)

    # 移除markdown行内代码 `code`
    response = re.sub(r'`([^`]+)`', r'\1', response)

    # 移除多余的换行和空格
    response = re.sub(r'\n+', '\n', response)
    response = response.strip()

    # 如果清理后为空，返回原始响应（避免过度清理）
    if not response:
        return "我理解您的问题，请您详细说明一下。"

    return response

# 测试
test_response = '''<think>
用户要求我简单介绍一下我自己。我应该用友好、简洁的方式回答，像朋友聊天一样。

我是一个客服助手，应该说明我的身份和能做什么。
</think>

你好！我是你的智能客服助手，很高兴为你服务！

我可以帮你：

- 回答各类问题
- 提供信息查询
- 解决常见问题
- 给出建议和帮助

有什么我可以帮到你的吗？😊'''

result = clean_ai_response(test_response)
print("Original:")
print(repr(test_response))
print("\nCleaned:")
print(repr(result))
print("\nFinal result:")
print(result)