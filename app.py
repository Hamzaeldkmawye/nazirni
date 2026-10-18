from flask import Flask, render_template, request, jsonify
import os
import requests

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}

        user_message = data.get("message", "").strip()
        category = data.get("category", "سؤال ديني")

        if not user_message:
            return jsonify({
                "reply": "من فضلك اكتب سؤالك الأول."
            }), 400

        if not API_KEY:
            app.logger.error("GEMINI_API_KEY is not configured")
            return jsonify({
                "reply": "مفتاح الذكاء الاصطناعي غير مُعد على السيرفر. راجع إعدادات Vercel."
            }), 500

        system_instruction = (
            "أنت مساعد ذكي في منصة ناظرني للحوار والدراسات الدينية. "
            f"القسم الحالي هو: {category}. "
            "أجب باللغة العربية بوضوح واحترام وموضوعية. "
            "اعتمد على معلومات موثوقة، وميّز بين الحقائق والآراء. "
            "لا تخترع مراجع أو تنسب أقوالًا لمصادر دون التأكد منها. "
            "إذا لم تكن متأكدًا من الإجابة، وضّح ذلك للمستخدم."
        )

        # رابط الاتصال المباشر بالنموذج المطلوب حصرياً من جوجل
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={API_KEY}"
        
        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": [
                {
                    "parts": [{"text": user_message}]
                }
            ]
        }

        response = requests.post(url, json=payload, timeout=30)
        res_data = response.json()

        if response.status_code != 200:
            error_msg = res_data.get("error", {}).get("message", "حدث خطأ غير معروف")
            app.logger.error(f"Gemini API Error: {res_data}")
            return jsonify({
                "reply": f"خطأ من جوجل: {error_msg}"
            }), response.status_code

        # استخراج النص من الاستجابة
        candidates = res_data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                reply_text = parts[0].get("text", "")

        if not reply_text:
            reply_text = "لم أتمكن من إنشاء إجابة واضحة. جرّب صياغة سؤالك مرة أخرى."

        return jsonify({"reply": reply_text}), 200

    except Exception as e:
        app.logger.exception("Gemini API error")
        return jsonify({
            "reply": f"نوع الخطأ: {type(e).__name__} - {str(e)}"
        }), 500


if __name__ == "__main__":
    app.run(debug=False)
