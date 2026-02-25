from flask import Flask, request, jsonify
import os
import requests
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# API配置
MINIMAX_API_KEY = os.getenv('MINIMAX_API_KEY')
MINIMAX_URL = "https://api.minimax.chat/v1/chat/completions"

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///customers.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 数据库模型
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    interactions = db.relationship('Interaction', backref='customer', lazy=True)

class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    user_message = db.Column(db.Text)
    ai_response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sentiment = db.Column(db.String(20))  # positive, negative, neutral

# 创建数据库表
with app.app_context():
    db.create_all()

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    model = data.get('model', 'MiniMax-M2.5')  # 默认模型
    customer_id = data.get('customer_id')  # 可选
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        if model == 'MiniMax-M2.5':
            ai_response, sentiment = call_minimax(user_message)
        elif model == 'GPT-3.5':
            ai_response, sentiment = call_openai(user_message)
        else:
            return jsonify({'error': 'Unsupported model'}), 400
        
        # 存储交互
        if customer_id:
            interaction = Interaction(
                customer_id=customer_id,
                user_message=user_message,
                ai_response=ai_response,
                sentiment=sentiment
            )
            db.session.add(interaction)
            db.session.commit()
        
        return jsonify({'response': ai_response, 'sentiment': sentiment})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def clean_ai_response(response):
    """清理AI响应，移除markdown、思考过程和特殊格式"""
    import re
    
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

def call_minimax(message):
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "MiniMax-M2.5",
        "messages": [
            {"role": "system", "content": "You are a helpful customer service AI. Respond directly and concisely in plain text only. Do not include any thinking process, reasoning steps, or internal monologue. Do not use any markdown formatting, bold text, italic text, links, code blocks, or special characters. Give direct, helpful answers to customer questions. Do not mention that you are an AI unless specifically asked."},
            {"role": "user", "content": message}
        ],
        "temperature": 0.7,
        "max_tokens": 500,
        "stream": False
    }
    response = requests.post(MINIMAX_URL, headers=headers, json=data)
    response.raise_for_status()
    ai_response = response.json()['choices'][0]['message']['content'].strip()
    ai_response = clean_ai_response(ai_response)
    
    # 情感分析
    sentiment_data = {
        "model": "MiniMax-M2.5",
        "messages": [
            {"role": "system", "content": "Analyze the sentiment of this message and respond with only: positive, negative, or neutral."},
            {"role": "user", "content": message}
        ]
    }
    sentiment_response = requests.post(MINIMAX_URL, headers=headers, json=sentiment_data)
    sentiment_response.raise_for_status()
    sentiment = sentiment_response.json()['choices'][0]['message']['content'].strip().lower()
    sentiment = clean_ai_response(sentiment)
    
    return ai_response, sentiment

def call_openai(message):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful customer service AI. Respond directly and concisely in plain text only. Do not include any thinking process, reasoning steps, or internal monologue. Do not use any markdown formatting, bold text, italic text, links, code blocks, or special characters. Give direct, helpful answers to customer questions. Do not mention that you are an AI unless specifically asked."},
            {"role": "user", "content": message}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    response = requests.post(OPENAI_URL, headers=headers, json=data)
    response.raise_for_status()
    ai_response = response.json()['choices'][0]['message']['content'].strip()
    ai_response = clean_ai_response(ai_response)
    
    # 情感分析
    sentiment_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "Analyze the sentiment of this message and respond with only: positive, negative, or neutral."},
            {"role": "user", "content": message}
        ]
    }
    sentiment_response = requests.post(OPENAI_URL, headers=headers, json=sentiment_data)
    sentiment_response.raise_for_status()
    sentiment = sentiment_response.json()['choices'][0]['message']['content'].strip().lower()
    sentiment = clean_ai_response(sentiment)
    
    return ai_response, sentiment

@app.route('/customers', methods=['GET'])
def get_customers():
    customers = Customer.query.all()
    return jsonify([{'id': c.id, 'name': c.name, 'email': c.email} for c in customers])

@app.route('/customers', methods=['POST'])
def add_customer():
    data = request.json
    new_customer = Customer(name=data['name'], email=data['email'])
    db.session.add(new_customer)
    db.session.commit()
    return jsonify({'id': new_customer.id, 'message': 'Customer added'}), 201

@app.route('/customers/<int:customer_id>/interactions', methods=['GET'])
def get_interactions(customer_id):
    interactions = Interaction.query.filter_by(customer_id=customer_id).all()
    return jsonify([{
        'id': i.id,
        'user_message': i.user_message,
        'ai_response': i.ai_response,
        'timestamp': i.timestamp.isoformat(),
        'sentiment': i.sentiment
    } for i in interactions])

@app.route('/analytics', methods=['GET'])
def analytics():
    # 简单分析：总客户数，总交互数，情感分布
    total_customers = Customer.query.count()
    total_interactions = Interaction.query.count()
    sentiments = db.session.query(Interaction.sentiment, db.func.count(Interaction.sentiment)).group_by(Interaction.sentiment).all()
    sentiment_dict = {s[0]: s[1] for s in sentiments}
    
    return jsonify({
        'total_customers': total_customers,
        'total_interactions': total_interactions,
        'sentiment_distribution': sentiment_dict
    })

@app.route('/models', methods=['GET'])
def get_models():
    models = [
        {'id': 'MiniMax-M2.5', 'name': 'MiniMax M2.5', 'provider': 'MiniMax'},
        {'id': 'GPT-3.5', 'name': 'GPT-3.5 Turbo', 'provider': 'OpenAI'}
    ]
    return jsonify(models)

@app.route('/')
def home():
    with open('index.html', 'r') as f:
        return f.read()

if __name__ == '__main__':
    app.run(debug=True, port=5001)