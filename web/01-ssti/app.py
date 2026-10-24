import os

from flask import Flask, request, render_template_string

app = Flask(__name__)
BLOCKED = ["__", "os", "popen", "system", "import", "config", "request"]

PAGE = """
<!doctype html><html><body>
<h1>Greeting cards</h1>
<p>Give me your name and I'll make you a card.</p>
<form method=POST><input name=name placeholder="name">
<input type=submit value="make card"></form>
{% if card %}<hr><h2>Your card:</h2><p>{{ card }}</p>{% endif %}
</body></html>
"""

CARD = "Hello, %s! Have a nice day."


@app.route("/", methods=["GET", "POST"])
def index():
    card = None
    if request.method == "POST":
        name = request.form.get("name", "")
        for bad in BLOCKED:
            if bad in name:
                return "blocked! (%s)" % bad, 403
        card = render_template_string(CARD % name)
    return render_template_string(PAGE, card=card)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
