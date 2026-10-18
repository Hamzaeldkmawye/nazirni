from flask import Flask, render_template, request, jsonify
import os
import requests
from pypdf import PdfReader

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")

# دالة لقراءة واستخراج كافة النصوص من ملفات الـ PDF المرفوعة في المشروع
def load_pdf_context():
    pdf_text = ""
    # البحث عن جميع ملفات PDF في المستودع
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                try:
                    reader = PdfReader(pdf_path)
                    pdf_text += f"\n--- بداية المحتوى من الملف: {file} ---\n"
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            pdf_text += text + "\n"
                    pdf_text += f"--- نهاية المحتوى من الملف: {file} ---\n"
                except Exception as e:
                    app.logger.error(f"خطأ في قراءة الملف {file}: {e}")
    return pdf_text

# تحميل نصوص الـ PDF في الذاكرة عند بدء السيرفر
PDF_CONTEXT = load_pdf_context()


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

        # تعليمات صارمة لحصر الإجابة داخل الـ PDFs فقط
        system_instruction = (
            "أنت مساعد ذكي وموثوق في منصة ناظرني للحوار والدراسات الدينية. "
            f"القسم الحالي هو: {category}. "
            "قاعدتك الأساسية والصارمة التي لا تجوز مخالفتها: "
            "أجب فقط وفقط بالاعتماد على محتوى ملفات الـ PDF المرفقة والمزودة لك أسفله. "
            "يُمنع منعاً باتاً البحث في الإنترنت، أو الاستعانة بمعلومات خارجية من خارج النصوص المرفقة، أو اختراع مراجع أو إجابات. "
            "إذا كانت الإجابة موجودة في النصوص المرفقة، اذكر الإجابة بوضوح مع ذكر اسم الكتاب/الملف المأخوذ منه إن أمكن. "
            "إذا لم تجد الإجابة بالنص أو المعنى الصريح داخل ملفات الـ PDF المرفقة، يجب عليك أن تجيب بهذه العبارة فقط: "
            "'عذراً، هذه المعلومة غير متوفرة في الملفات والكتب المعتمدة حالياً في المنصة.'"
        )

        # دمج محتوى الـ PDFs مع السؤال
        full_user_content = (
            f"محتوى الملفات والكتب المعتمدة:\n{PDF_CONTEXT}\n\n"
            f"سؤال المستخدم: {user_message}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={API_KEY}"

        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": [
                {
                    "parts": [{"text": full_user_content}]
                }
            ]
        }

        response = requests.post(url, json=payload, timeout=45)
        res_data = response.json()

        if response.status_code != 200:
            error_msg = res_data.get("error", {}).get("message", "حدث خطأ غير معروف")
            app.logger.error(f"Gemini API Error: {res_data}")
            return jsonify({
                "reply": f"خطأ من جوجل: {error_msg}"
            }), response.status_code

        candidates = res_data.get("candidates", [])
        reply_text = ""
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
