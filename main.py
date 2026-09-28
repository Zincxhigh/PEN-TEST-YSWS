from flask import Flask, render_template, request
import os 

app = Flask(__name__)

@app.route('/')
@app.route('/index') 
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route("/signup")
def signup():
    return render_template("signup.html")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


    