from flask import Flask, render_template, request, jsonify
import os
from google import genai
from google.genai import types

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY else None


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

        if not client:
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

      response = client.models.generate_content(
            model="gemini-1.5-flash",  # أو النموذج المناسب المتاح لديك
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )

        reply_text = response.text

        if not reply_text:
            reply_text = (
                "لم أتمكن من إنشاء إجابة واضحة. "
                "جرّب صياغة سؤالك مرة أخرى."
            )

        return jsonify({"reply": reply_text}), 200

    except Exception as e:
        app.logger.exception("Gemini API error")
        return jsonify({
            "reply": f"نوع الخطأ: {type(e).__name__} - {str(e)}"
        }), 500


if __name__ == "__main__":
    app.run(debug=False)
