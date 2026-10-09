import os
import jwt
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
SECRET = os.environ.get("JWT_SECRET", "secret123")  # TODO: use a strong secret

USERS = {"guest": "guest", "admin": os.environ.get("ADMIN_PASSWORD", "s3cur3-r4nd0m-p4ss")}

with open(os.environ.get("FLAG_FILE", "/flag.txt")) as f:
    FLAG = f.read().strip()

PAGE = """
<!doctype html><html><body>
<h1>Login</h1>
<form method=POST action=/login>user <input name=user> pass <input name=pass type=password>
<input type=submit value=login></form>
<p>Try guest/guest. The flag is at <a href=/flag>/flag</a> (admins only).</p>
</body></html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/login", methods=["POST"])
def login():
    u = request.form.get("user", "")
    p = request.form.get("pass", "")
    if USERS.get(u) != p:
        return "bad login", 401
    tok = jwt.encode({"user": u, "admin": u == "admin"}, SECRET, algorithm="HS256")
    return jsonify(token=tok)


@app.route("/flag")
def flag():
    tok = request.args.get("token", "") or request.headers.get("Authorization", "")
    if tok.startswith("Bearer "):
        tok = tok[7:]
    try:
        claims = jwt.decode(tok, SECRET, algorithms=["HS256"])
    except Exception as e:
        return "bad token: %s" % e, 401
    if not claims.get("admin"):
        return "admins only", 403
    return jsonify(flag=FLAG)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
