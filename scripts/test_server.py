from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "Jarvis is ALIVE!", 200

if __name__ == "__main__":
    print("--- 正在啟動緊急測試伺服器 ---")
    app.run(port=8888, host='0.0.0.0')
