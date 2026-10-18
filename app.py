from flask import Flask, render_template, request, jsonify
import os
import google.generativeai as genai

app = Flask(__name__)

# قراءة مفتاح الـ API من متغيرات البيئة في Vercel
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        category = data.get('category', 'سؤال ديني')

        if not api_key and not os.environ.get("GEMINI_API_KEY"):
            return jsonify({'reply': 'عذراً، مفتاح الـ API غير مُعد بشكل صحيح على سيرفر الاستضافة (Vercel).'})

        system_instruction = f"أنت مساعد ذكي ومختص في منصة 'ناظرني' للحوار والدراسات الدينية. القسم الحالي هو: {category}. أجب بدقة وعلم وموضوعية."
        
        generation_config = {
            "temperature": 0.7,
            "max_output_tokens": 1000,
        }

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_instruction,
            generation_config=generation_config
        )

        response = model.generate_content(user_message)
        reply_text = response.text if response and response.text else "لم يتم تلقي رد واضح من نموذج الذكاء الاصطناعي."

        return jsonify({'reply': reply_text})
    except Exception as e:
        return jsonify({'reply': f'حدث خطأ في النظام: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)
