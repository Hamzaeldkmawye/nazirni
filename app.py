# ====================================================
# Project: Nazirni Platform (منصة ناظرني)
# Developer: Hamza Mohamed Eldkmawye
# Year: 2026
# Copyright (c) 2026 Hamza Eldkmawye. All rights reserved.
# ====================================================
from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import requests
import sqlite3
import time
from supabase import create_client, Client

app = Flask(__name__)
application = app  # ضروري جداً لتعريف نقطة البداية في Vercel

# ----------------------------------------------------
# 1. إعدادات Supabase لربط قاعدة بيانات الكتب
# ----------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://wppcxzceqdytvrukepwt.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_rWYN7qbep0gEnNOkGlAmNw_6wj2q8hW")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    app.logger.error(f"Supabase Init Error: {e}")
    supabase = None

# ----------------------------------------------------
# 2. إعداد مفاتيح Gemini API للنظام التناوبي
# ----------------------------------------------------
API_KEYS = []
for env_name in ["GEMINI_API_KEY", "GEMINI_KEY_1", "GEMINI_KEY"]:
    val = os.environ.get(env_name)
    if val and val.strip():
        API_KEYS.append(val.strip())

for key, value in os.environ.items():
    if key.startswith("GEMINI_KEY_") and value.strip() and value.strip() not in API_KEYS:
        API_KEYS.append(value.strip())

key_index = 0

def get_next_api_key():
    global key_index
    if not API_KEYS:
        return None
    key = API_KEYS[key_index % len(API_KEYS)]
    key_index += 1
    return key

# ----------------------------------------------------
# 3. إعداد قواعد البيانات المحلية (SQLite) لبيانات المستخدمين والزيارات
# ----------------------------------------------------
DB_FILE = os.path.join('/tmp', 'database.db')

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT UNIQUE,
                password TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                category TEXT,
                question TEXT,
                reply TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        app.logger.error(f"DB Init Error: {e}")

init_db()

# ----------------------------------------------------
# 4. مسارات تطبيق Flask
# ----------------------------------------------------
@app.route("/")
def index():
    try:
        client_ip = request.remote_addr or "unknown"
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO visits (ip) VALUES (?)', (client_ip,))
        conn.commit()
        conn.close()
    except Exception as e:
        app.logger.error(f"Visit log error: {e}")
        
    return render_template("index.html")


@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory('.', 'sitemap.xml')


@app.route("/api/auth", methods=["POST"])
def handle_auth():
    try:
        data = request.get_json(silent=True) or {}
        action = data.get("action")
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()
        name = data.get("name", "").strip()

        if not email or not password:
            return jsonify({"success": False, "message": "البريد الإلكتروني وكلمة المرور مطلوبان."}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        if action == "signup":
            try:
                cursor.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name or email.split('@')[0], email, password))
                conn.commit()
                conn.close()
                return jsonify({"success": True, "message": "تم إنشاء الحساب بنجاح", "name": name or email.split('@')[0]})
            except sqlite3.IntegrityError:
                conn.close()
                return jsonify({"success": False, "message": "البريد الإلكتروني مسجل مسبقاً!"}), 400

        elif action == "login":
            cursor.execute('SELECT name FROM users WHERE email = ? AND password = ?', (email, password))
            user = cursor.fetchone()
            conn.close()
            if user:
                return jsonify({"success": True, "message": "تم تسجيل الدخول بنجاح", "name": user[0]})
            else:
                return jsonify({"success": False, "message": "البريد الإلكتروني أو كلمة المرور غير صحيحة!"}), 401

        conn.close()
        return jsonify({"success": False, "message": "إجراء غير معروف"}), 400

    except Exception as e:
        app.logger.exception("Auth error")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/admin/data", methods=["GET"])
def admin_data():
    email = request.args.get("email", "").strip().lower()
    if email != "hamzadakma391@gmail.com":
        return jsonify({"success": False, "message": "غير مسموح بالدخول!"}), 403

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM visits')
        total_visits = cursor.fetchone()[0]

        cursor.execute('SELECT name, email, created_at FROM users ORDER BY id DESC')
        users = [{"name": row[0], "email": row[1], "date": row[2]} for row in cursor.fetchall()]

        cursor.execute('SELECT email, category, question, date FROM chats ORDER BY id DESC LIMIT 25')
        chats = [{"email": row[0], "category": row[1], "question": row[2], "date": row[3]} for row in cursor.fetchall()]

        conn.close()
        return jsonify({
            "success": True,
            "total_users": total_users,
            "total_visits": total_visits,
            "users": users,
            "chats": chats
        })
    except Exception as e:
        app.logger.exception("Admin data error")
        return jsonify({"success": False, "message": str(e)}), 500


# ----------------------------------------------------
# 5. دالة الـ Chat
# ----------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()
        category = data.get("category", "سؤال ديني")
        user_email = data.get("email", "guest@nazirni.com")

        if not user_message:
            return jsonify({"reply": "من فضلك اكتب سؤالك الأول."}), 400

        if not API_KEYS:
            return jsonify({"reply": "خطأ تقني: مفاتيح الذكاء الاصطناعي غير مُعدة في Environment Variables."}), 200

        # أ) البحث بالكلمات المفتاحية في قاعدة بيانات الكتب بـ Supabase
        context_text = ""
        if supabase:
            try:
                keywords = user_message.split()[:2]
                search_term = " ".join(keywords) if keywords else user_message
                
                res = supabase.table("book_chunks").select("book_name, page_number, content").ilike("content", f"%{search_term}%").limit(3).execute()
                chunks = res.data or []
                
                for c in chunks:
                    context_text += f"\n- الكتاب: {c.get('book_name')} (صفحة {c.get('page_number')})\nالنص: {c.get('content')}\n---"
            except Exception as search_err:
                app.logger.error(f"Text search failed: {search_err}")

        # ب) صياغة تعليمات النظام
        system_instruction = (
            "أنت مساعد ذكي وموثوق في منصة ناظرني للحوار والدراسات الدينية. "
            f"القسم الحالي هو: {category}. "
            "أجب باللغة العربية بوضوح واحترام وموضوعية وفقاً للمنهج الإسلامي الصحيح والمصادر المعتمدة. "
        )
        
        if context_text:
            system_instruction += (
                "\n\nاستعن بالنصوص التالية المستخرجة من المكتبة للإجابة بدقة موثقة:\n"
                f"{context_text}"
            )

        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"parts": [{"text": user_message}]}]
        }

        reply_text = ""
        success = False
        last_api_error = "Unknown API Error"

        # ج) الاعتماد على Gemini Flash حصرياً وبمحاولات متعددة للمفاتيح المتاحة
        for _ in range(len(API_KEYS) + 2):
            key = get_next_api_key()
            if not key:
                break

            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={key}"
            try:
                response = requests.post(url, json=payload, timeout=20)
                if response.status_code == 200:
                    res_data = response.json()
                    candidates = res_data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            reply_text = parts[0].get("text", "")
                            if reply_text:
                                success = True
                                break
                else:
                    last_api_error = f"API Status {response.status_code}: {response.text}"
            except Exception as api_ex:
                last_api_error = f"API Exception: {str(api_ex)}"
                time.sleep(0.4)

            if success:
                break

        if not success or not reply_text:
            return jsonify({"reply": f"خطأ تقني حقيقي من السيرفر: {last_api_error}"}), 200

        # د) حفظ المحادثة في قاعدة البيانات المحلية
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO chats (email, category, question, reply) VALUES (?, ?, ?, ?)',
                (user_email, category, user_message, reply_text)
            )
            conn.commit()
            conn.close()
        except Exception as db_err:
            app.logger.error(f"Failed to save chat: {db_err}")

        return jsonify({"reply": reply_text}), 200

    except Exception as e:
        app.logger.exception("Gemini API error")
        return jsonify({"reply": f"خطأ برمجى شامل (Exception): {str(e)}"}), 200


if __name__ == "__main__":
    app.run(debug=False)
        
