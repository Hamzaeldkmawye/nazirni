import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from pypdf import PdfReader

app = Flask(__name__)
CORS(app)

# ضع مفتاح الـ API الخاص بك هنا
API_KEY = "AQ.Ab8RN6KXchXHnodUkJbb6N69PuDvxAMDpvIMzYb8LMKgEN7gjA"
client = genai.Client(api_key=API_KEY)

# دالة لقراءة جميع ملفات الـ PDF واستخراج نصوصها من مجلد ناظرني
def load_all_books_text():
    books_folder = "."  # المجلد الحالي الذي توجد به ملفات الـ PDF
    all_text = ""
    print("جاري قراءة وفهرسة الكتب...")
    for filename in os.listdir(books_folder):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(books_folder, filename)
            try:
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n"
            except Exception as e:
                print(f"خطأ في قراءة الملف {filename}: {e}")
    print("تم الانتهاء من قراءة الفهرس وجاهز للإجابة!")
    return all_text

# نقوم بقراءة الكتب مرة واحدة عند تشغيل السيرفر
BOOKS_CORPUS = load_all_books_text()

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.json
    user_question = data.get('question', '')
    category = data.get('category', 'سؤال ديني')

    # التوجيه الصارم للذكاء الاصطناعي ليلتزم حصرياً بالكتب المرفقة
    system_instruction = f"""
    أنت مساعد ذكي ومحاور شرعي لمنصة "ناظرني". مهمتك المطلقة هي الإجابة عن سؤال المستخدم بناءً حصرياً على نصوص الكتب المرفقة في المرجع أدناه، ويُمنع منعاً باتاً الإتيان بأي معلومة أو هبد من خارجها.
    
    هيكل الإجابة الإلزامي:
    1. الإجابة المباشرة والدقيقة على السؤال.
    2. الدليل أو النص الشرعي (الآيات القرآنية، الأحاديث، أو النصوص الفقهية) مأخوذة حرفياً من المراجع.
    3. عبارة ختمية: "هل تحب أن أساعدك في شيء آخر؟"
    4. إذا كان المستخدم يختار ديانة أخرى (مثل: لو كنت مسيحياً، لو كنت يهودياً، لو كنت ملحداً، ديانة أخرى)، تُختم الإجابة بلطف بعبارة: "بعد عرض هذه الأدلة والبراهين، هل اقتنعت بهذا الحق وهذا الدين؟"

    قسم المستخدم الحالي: {category}
    
    مرجع الكتب (قاعدة البيانات):
    {BOOKS_CORPUS[:100000]}  # يتم تضمين النصوص المتاحة
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"السؤال: {user_question}",
            config={
                'system_instruction': system_instruction,
                'temperature': 0.2  # لتقليل العشوائية ومنع الهبد تماماً
            }
        )
        return jsonify({'answer': response.text})
    except Exception as e:
        return jsonify({'answer': f"حدث خطأ أثناء معالجة الطلب: {str(e)}"})

if __name__ == '__main__':
    app.run(port=5000, debug=True)