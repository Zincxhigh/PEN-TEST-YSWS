import os
import subprocess
import sys
import urllib.parse
from flask import Flask, request, redirect, render_template_string

app = Flask(__name__)
SECRET = os.environ.get("ADMIN_SECRET", "dev-secret")
APP_URL = os.environ.get("APP_URL", "http://127.0.0.1:5000")


def _load_flag():
    try:
        with open(os.environ.get("FLAG_FILE", "/flag.txt")) as f:
            return f.read().strip()
    except OSError:
        return "pentest{REDACTED}"


FLAG = _load_flag()

NOTES = []
PAGE = """
<!doctype html><html><body>
<h1>Guestbook</h1>
<form method=POST action=/add>name <input name=author>
message <input name=content size=60><input type=submit value=post></form>
<hr>
{% for i, n in notes %}
<div><b>{{ n.author }}</b>: {{ n.content|safe }}
<a href=/note/{{ i }}>[link]</a></div>
{% endfor %}
<hr>
<form method=GET action=/report>Report a note to the admin:
<input name=url size=60 placeholder="http://127.0.0.1:5000/note/1">
<input type=submit value=report></form>
</body></html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE, notes=list(enumerate(NOTES)))


@app.route("/add", methods=["POST"])
def add():
    NOTES.append({
        "author": request.form.get("author", "anon")[:40],
        "content": request.form.get("content", "")[:2000],
    })
    return redirect("/note/%d" % (len(NOTES) - 1))


@app.route("/note/<int:i>")
def note(i):
    if i >= len(NOTES):
        return "no such note", 404
    n = NOTES[i]
    return "<b>%s</b>: %s" % (n["author"], n["content"])


@app.route("/admin")
def admin():
    if request.cookies.get("session") != SECRET:
        return "admins only", 403
    return "hello admin. flag: %s" % FLAG


@app.route("/report")
def report():
    url = request.args.get("url", "")
    u = urllib.parse.urlparse(url)
    base = urllib.parse.urlparse(APP_URL)
    if u.scheme not in ("http", "https") or u.hostname != base.hostname:
        return "the admin only visits this site", 400
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.py"), url], capture_output=True, timeout=25
        )
        if r.returncode != 0:
            return "bot error: %s" % (r.stderr.decode()[-200:]), 500
    except subprocess.TimeoutExpired:
        return "bot timed out", 500
    return "admin visited. thanks for the report!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
