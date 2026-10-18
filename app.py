from flask import Flask, render_template, request, jsonify
import os
import google.generativeai as genai

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        category = data.get('category', 'سؤال ديني')

        if not API_KEY:
            return jsonify({'reply': 'عذراً، مفتاح الـ API غير مُعد بشكل صحيح على سيرفر الاستضافة (Vercel).'})

        system_instruction = f"أنت مساعد ذكي ومختص في منصة 'ناظرني' للحوار والدراسات الدينية. القسم الحالي هو: {category}. أجب بدقة وعلم وموضوعية."
        
        # استخدام الموديل القياسي المدعوم
      model = genai.GenerativeModel(
    model_name="gemini-pro"
)

response = model.generate_content(
    f"{system_instruction}\n\nسؤال المستخدم: {user_message}"
)

        response = model.generate_content(user_message)
        reply_text = response.text if response and response.text else "لم يتم تلقي رد واضح من نموذج الذكاء الاصطناعي."

        return jsonify({'reply': reply_text})
    except Exception as e:
        return jsonify({'reply': f'حدث خطأ في النظام: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)
