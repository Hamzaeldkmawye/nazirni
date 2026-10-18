from flask import Flask, render_template, request, jsonify
import os
import requests

app = Flask(__name__)

# قراءة مفتاح الـ API من متغيرات البيئة في Vercel
API_KEY = os.environ.get("GEMINI_API_KEY")

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

        # استخدام نموذج gemini-2.0-flash الحديث والمدعوم على v1beta
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
        
        system_instruction = f"أنت مساعد ذكي ومختص في منصة 'ناظرني' للحوار والدراسات الدينية. القسم الحالي هو: {category}. أجب بدقة وعلم وموضوعية."
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_instruction}\n\nسؤال المستخدم: {user_message}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1000
            }
        }

        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(url, json=payload, headers=headers)
        res_data = response.json()

        if response.status_code == 200:
            try:
                reply_text = res_data['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError):
                reply_text = "لم يتم تلقي رد واضح من نموذج الذكاء الاصطناعي."
        else:
            # تجربة النموذج الاحتياطي تلقائيًا إذا تعذر الأول
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-8b:generateContent?key={API_KEY}"
            fb_response = requests.post(fallback_url, json=payload, headers=headers)
            fb_res_data = fb_response.json()
            
            if fb_response.status_code == 200:
                try:
                    reply_text = fb_res_data['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError):
                    reply_text = "لم يتم تلقي رد واضح من نموذج الذكاء الاصطناعي."
            else:
                error_msg = res_data.get('error', {}).get('message', 'خطأ غير معروف')
                reply_text = f"عذراً، حدث خطأ في الاتصال بخدمة الذكاء الاصطناعي: {error_msg}"

        return jsonify({'reply': reply_text})
    except Exception as e:
        return jsonify({'reply': f'حدث خطأ في النظام: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)
