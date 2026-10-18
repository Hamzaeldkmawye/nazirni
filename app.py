from flask import Flask, render_template, request, jsonify
import os
import requests
import sqlite3

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")

# الحل هنا: استخدام مجلد tmp المؤقت المسموح بالكتابة عليه في Vercel
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
    if email != "hamza.dokmah391@gmail.com":
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


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()
        category = data.get("category", "سؤال ديني")
        user_email = data.get("email", "guest@nazirni.com")

        if not user_message:
            return jsonify({"reply": "من فضلك اكتب سؤالك الأول."}), 400

        if not API_KEY:
            return jsonify({"reply": "مفتاح الذكاء الاصطناعي غير مُعد على السيرفر."}), 500

        system_instruction = (
            "أنت مساعد ذكي في منصة ناظرني للحوار والدراسات الدينية. "
            f"القسم الحالي هو: {category}. "
            "أجب باللغة العربية بوضوح واحترام وموضوعية وفقاً للمنهج الإسلامي الصحيح والمصادر المعتمدة."
        )

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={API_KEY}"

        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"parts": [{"text": user_message}]}]
        }

        response = requests.post(url, json=payload, timeout=30)
        res_data = response.json()

        if response.status_code != 200:
            error_msg = res_data.get("error", {}).get("message", "حدث خطأ غير معروف")
            return jsonify({"reply": f"خطأ من جوجل: {error_msg}"}), response.status_code

        candidates = res_data.get("candidates", [])
        reply_text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                reply_text = parts[0].get("text", "")

        if not reply_text:
            reply_text = "لم أتمكن من إنشاء إجابة واضحة. جرّب صياغة سؤالك مرة أخرى."

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
        return jsonify({"reply": f"خطأ: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=False)
