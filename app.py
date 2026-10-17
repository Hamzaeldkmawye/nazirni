from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

# هذا السطر مهم جداً لـ Vercel
app_handler = app

if __name__ == '__main__':
    app.run()
