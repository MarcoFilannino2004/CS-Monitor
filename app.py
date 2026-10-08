from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "CyberSec Monitor - Applicazione avviata correttamente!"

if __name__ == "__main__":
    app.run(debug=True)