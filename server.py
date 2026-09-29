import base64
import html
import json
import os
import re
import secrets
from urllib.parse import urlencode

from flask import Flask, jsonify, make_response, redirect, render_template, request, session

try:
    import requests
except ImportError:
    requests = None

def _load_dotenv(path):
    """Minimal .env loader (stdlib only) so `python server.py` / `make run`
    pick up the same values docker compose uses. Never overrides real env."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                if key and key not in os.environ:
                    os.environ[key] = val.strip().strip("'\"")
    except OSError:
        pass


_load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

app = Flask(__name__)
# Own cookie name: the CTFd handoff sets a cookie literally named "session",
# so ours must not collide with it (last same-name Set-Cookie wins).
app.config["SESSION_COOKIE_NAME"] = "pentest_session"
SECRET_KEY_DEFAULTED = not os.environ.get("SECRET_KEY", "")
app.secret_key = os.environ.get("SECRET_KEY", "") or secrets.token_hex(32)
if SECRET_KEY_DEFAULTED:
    # A random key breaks logins across restarts and across gunicorn workers.
    app.logger.warning("SECRET_KEY is not set: login sessions break across "
                       "restarts/workers. Set a stable SECRET_KEY in .env.")

CTFD_URL_OVERRIDE = os.environ.get("CTFD_URL", "").strip().rstrip("/")
CTFD_PORT = os.environ.get("CTFD_PORT", "8000").strip() or "8000"
CTFD_SCHEME = os.environ.get("CTFD_SCHEME", "http").strip() or "http"
CTFD_INTERNAL_URL = os.environ.get("CTFD_INTERNAL_URL", "http://ctfd:8000").strip().rstrip("/") or "http://ctfd:8000"

# Hack Club Auth (https://auth.hackclub.com/docs). Create an OAuth app to get
# these, and register {APP_BASE_URL}/auth/hackclub/callback as redirect URI.
HACKCLUB_CLIENT_ID = os.environ.get("HACKCLUB_CLIENT_ID", "").strip()
HACKCLUB_CLIENT_SECRET = os.environ.get("HACKCLUB_CLIENT_SECRET", "").strip()
HACKCLUB_AUTHORIZE_URL = "https://auth.hackclub.com/oauth/authorize"
HACKCLUB_TOKEN_URL = "https://auth.hackclub.com/oauth/token"
HACKCLUB_ME_URL = "https://auth.hackclub.com/api/v1/me"
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000").strip().rstrip("/") or "http://localhost:5000"
# Admin API token from the CTFd admin panel, used to provision CTF accounts.
CTFD_API_TOKEN = os.environ.get("CTFD_API_TOKEN", "").strip()
# Initial arena password. Empty = random one-time password shown once instead.
ARENA_DEFAULT_PASSWORD = os.environ.get("ARENA_DEFAULT_PASSWORD", "").strip()


def get_ctfd_url():
    """Public CTFd URL for this request (same server by default)."""
    if CTFD_URL_OVERRIDE:
        return CTFD_URL_OVERRIDE
    try:
        hostname = request.host.split(":")[0] or "localhost"
        scheme = os.environ.get("CTFD_SCHEME", "").strip() or request.scheme
    except RuntimeError:  
        hostname, scheme = "localhost", CTFD_SCHEME
    return f"{scheme}://{hostname}:{CTFD_PORT}"


def ctfd_url(path=""):
    base = get_ctfd_url().rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path if path != '/' else ''}"


@app.context_processor
def inject_ctfd():
    return {"ctfd_url": get_ctfd_url()}


@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html")


@app.route("/play")
@app.route("/ctf")
@app.route("/arena")
def play():
    return redirect(ctfd_url("/"), code=302)


@app.route("/challenges")
@app.route("/scoreboard")
def ctfd_deep_link():
    return redirect(ctfd_url(request.path), code=302)


# --- Hack Club Auth -> CTFd registration ------------------------------------
# /register sends the player to Hack Club; the callback verifies their identity,
# creates their CTFd account via the admin API, logs it in, and hands the CTFd
# session cookie to the browser. Cookie handoff works when site + CTFd share a
# host (cookies ignore ports); otherwise we fall back to CTFd's own /login page.
def hackclub_configured():
    return bool(HACKCLUB_CLIENT_ID and HACKCLUB_CLIENT_SECRET)


def hackclub_redirect_uri():
    return f"{APP_BASE_URL}/auth/hackclub/callback"


def auth_error(message, status=502):
    return (
        "<!doctype html><title>Registration failed</title>"
        f"<h1>Registration failed</h1><p>{message}</p>"
        '<p><a href="/">Back to PEN-TEST</a> · <a href="/register">Try again</a></p>'
    ), status


def hc_name(identity):
    """Pull a display name out of a Hack Club identity dict, tolerating nesting."""
    if not isinstance(identity, dict):
        return ""
    for key in ("name", "preferred_username", "username", "given_name", "display_name", "handle", "login"):
        val = identity.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    for nest in ("data", "user", "profile", "identity"):
        sub = identity.get(nest)
        if isinstance(sub, dict):
            found = hc_name(sub)
            if found:
                return found
    return ""


def ctfd_username_for(identity):
    base = hc_name(identity)
    if "@" in base and " " not in base:  # looks like an email, use the local part
        base = base.split("@")[0]
    email = hc_email(identity)
    if not base and email:
        base = email.split("@")[0]
    return re.sub(r"[^A-Za-z0-9_.-]", "_", base).strip("._-")[:64] or "hacker"


def hc_email(identity):
    """Pull an email out of a Hack Club identity dict, tolerating nesting."""
    if not isinstance(identity, dict):
        return ""
    for key in ("email", "primary_email", "primaryEmail", "mail"):
        direct = identity.get(key)
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
    for nest in ("data", "user", "profile", "identity"):
        sub = identity.get(nest)
        if isinstance(sub, dict):
            found = hc_email(sub)
            if found:
                return found
    emails = identity.get("emails")
    if isinstance(emails, list):
        for entry in emails:
            if isinstance(entry, str) and "@" in entry:
                return entry.strip()
            if isinstance(entry, dict):
                for key in ("address", "email"):
                    val = entry.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
    return ""


def hc_keys(identity):
    """Top-level keys of an identity payload for logs (no PII values)."""
    return sorted(identity.keys()) if isinstance(identity, dict) else type(identity).__name__


def hc_shape(identity):
    """One-level key map of an identity payload for logs (keys only, no PII)."""
    if not isinstance(identity, dict):
        return type(identity).__name__
    shape = {}
    for k, v in identity.items():
        if isinstance(v, dict):
            shape[k] = sorted(v.keys())
        elif isinstance(v, list):
            shape[k] = f"list[{len(v)}]"
        else:
            shape[k] = type(v).__name__
    return shape


def _api_bases():
    """CTFd API bases to try in order: internal (docker DNS) then public.
    The public fallback saves local `make run` setups whose .env still points
    CTFD_INTERNAL_URL at the docker-only `http://ctfd:8000`."""
    bases = [CTFD_INTERNAL_URL]
    try:
        public = get_ctfd_url().rstrip("/")
    except RuntimeError:  # noqa: BLE001 - no request context
        public = ""
    if public and public not in bases:
        bases.append(public)
    return bases


def ctfd_create_user(username, email, password, verified):
    """Create a CTFd account. Returns (status, errors) with status one of
    'created', 'taken' (username clash only -> try a suffix), 'exists'
    (email taken -> account already registered), 'error'."""
    payload = {"name": username, "email": email, "password": password, "type": "user",
               "verified": verified, "hidden": False, "banned": False, "fields": []}
    headers = {"Authorization": f"Token {CTFD_API_TOKEN}", "Content-Type": "application/json"}
    for base in _api_bases():
        try:
            r = requests.post(f"{base}/api/v1/users", headers=headers, json=payload, timeout=10)
        except Exception as e:  # noqa: BLE001 - base unreachable, try next
            app.logger.info("ctfd api create: %s unreachable (%s)", base, type(e).__name__)
            continue
        if r.status_code < 300:
            return "created", {}
        try:
            errors = r.json().get("errors", {}) or {}
        except Exception:  # noqa: BLE001 - non-JSON error body
            errors = {}
        app.logger.info("ctfd api create: %s status=%s errors=%s", base, r.status_code, sorted(errors))
        if r.status_code == 400 and "name" in errors and "email" not in errors:
            return "taken", errors
        if r.status_code == 400 and errors:
            return "exists", errors
        return "error", errors
    return "error", {"connection": "all bases unreachable"}


_NONCE_RE = re.compile(r"""name=["']nonce["']\s+value=["']([^"']+)["']|value=["']([^"']+)["']\s+name=["']nonce["']""")


def ctfd_login_cookies(username, password):
    """Log fresh credentials into CTFd, return its session cookies (or {})."""
    for base in _api_bases():
        s = requests.Session()
        try:
            page = s.get(f"{base}/login", timeout=10)
            m = _NONCE_RE.search(page.text or "")
            data = {"name": username, "password": password}
            if m:
                data["nonce"] = m.group(1) or m.group(2)
            r = s.post(f"{base}/login", data=data, timeout=10, allow_redirects=True)
            logged_in = (any(h.status_code in (301, 302, 303) for h in r.history)
                         or r.url.rstrip("/").endswith("/challenges"))
            if logged_in and s.cookies.get("session"):
                return {"session": s.cookies.get("session")}
            return {}
        except Exception:  # noqa: BLE001 - base unreachable, try next
            app.logger.info("ctfd login: %s unreachable", base)
            continue
    return {}


def id_token_claims(id_token):
    """Decode an OIDC ID token payload (claims only; trust comes from the
    TLS-protected token endpoint + the /me check, name is display-only)."""
    try:
        payload = (id_token or "").split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 - malformed token, fall back to /me
        return {}


def ctfd_find_user(email):
    """Find a CTFd user by email. Returns the user dict or None."""
    headers = {"Authorization": f"Token {CTFD_API_TOKEN}"}
    for base in _api_bases():
        try:
            for page in range(1, 6):
                r = requests.get(f"{base}/api/v1/users", headers=headers,
                                 params={"page": page}, timeout=10)
                if r.status_code >= 300:
                    break
                body = r.json() or {}
                for u in body.get("data") or []:
                    if isinstance(u, dict) and str(u.get("email", "")).lower() == email.lower():
                        app.logger.info("ctfd api find: %s found id=%s", base, u.get("id"))
                        return u
                pagination = (body.get("meta") or {}).get("pagination") or {}
                if pagination.get("page", page) >= pagination.get("pages", page):
                    break
        except Exception:  # noqa: BLE001 - base unreachable, try next
            app.logger.info("ctfd api find: %s unreachable", base)
            continue
        return None
    return None


def ctfd_set_password(user_id, password):
    """Reset a CTFd user's password via the admin API."""
    headers = {"Authorization": f"Token {CTFD_API_TOKEN}", "Content-Type": "application/json"}
    for base in _api_bases():
        try:
            r = requests.patch(f"{base}/api/v1/users/{user_id}", headers=headers,
                               json={"password": password}, timeout=10)
            app.logger.info("ctfd api patch: %s status=%s", base, r.status_code)
            return r.status_code < 300
        except Exception:  # noqa: BLE001 - base unreachable, try next
            app.logger.info("ctfd api patch: %s unreachable", base)
            continue
    return False


def provisioned_page(username, password, pw_note, cookies, outcome):
    """Interstitial after provisioning. Shows credentials + change-password
    prompt only when they were actually applied (created/reset); otherwise
    points the returning player at CTFd login instead of showing a password
    that isn't set."""
    u = html.escape(username)
    arena, settings, login = ctfd_url("/"), ctfd_url("/settings"), ctfd_url("/login")
    if outcome in ("created", "reset"):
        p = html.escape(password)
        kind = "default password" if pw_note == "default" else "one-time password"
        body = ("<h1>Arena account ready</h1>"
                f"<p>Signed in as <b>{u}</b> with this {kind}:</p>"
                f'<p style="font-size:1.4em"><code>{p}</code></p>'
                f'<p>Please change it now in <a href="{settings}">CTFd Settings</a>.</p>'
                f'<p><a href="{arena}">Enter the arena</a> · <a href="/">Back to PEN-TEST</a></p>')
    else:
        body = ("<h1>Arena account exists</h1>"
                f"<p>An arena account already exists for your Hack Club email (<b>{u}</b>), "
                "and its password could not be reset automatically.</p>"
                f'<p>Please log in with your existing arena password at <a href="{login}">CTFd login</a> '
                "(or use Forgot password there).</p>"
                f'<p><a href="/">Back to PEN-TEST</a></p>')
    resp = make_response(f"<!doctype html><title>Arena account</title>{body}", 200)
    for k, v in cookies.items():
        resp.set_cookie(k, v, path="/", httponly=True)
    return resp


@app.route("/register")
def register():
    if not hackclub_configured():
        return auth_error("Hack Club login isn't configured yet "
                          "(missing HACKCLUB_CLIENT_ID / HACKCLUB_CLIENT_SECRET).", 503)
    state = secrets.token_urlsafe(32)
    session["hackclub_oauth_state"] = state
    app.logger.info("hackclub authorize start: state issued")
    params = urlencode({"client_id": HACKCLUB_CLIENT_ID, "redirect_uri": hackclub_redirect_uri(),
                        "response_type": "code", "scope": "openid profile email", "state": state})
    return redirect(f"{HACKCLUB_AUTHORIZE_URL}?{params}", code=302)


@app.route("/auth/hackclub/callback")
def hackclub_callback():
    if requests is None:
        return auth_error("The 'requests' package isn't installed.", 500)
    if request.args.get("error"):
        return auth_error(f"Hack Club said: "
                          f"{request.args.get('error_description') or request.args.get('error')}.", 400)
    state, expected = request.args.get("state", ""), session.pop("hackclub_oauth_state", "")
    # Log booleans only, never secret values.
    app.logger.info("hackclub callback: session_cookie=%s state_param=%s state_match=%s",
                    app.config["SESSION_COOKIE_NAME"] in request.cookies,
                    bool(state), bool(state and state == expected))
    if not state or state != expected:
        return auth_error("Your login session expired or was lost (server restarted, SECRET_KEY "
                          "changed, cookies blocked, or you switched between localhost and 127.0.0.1 "
                          "mid-login). Please try again — if it keeps happening, set a stable SECRET_KEY "
                          "in .env and stick to one address.", 400)
    code = request.args.get("code", "")
    if not code:
        return auth_error("No authorization code returned.", 400)
    try:
        tok = requests.post(HACKCLUB_TOKEN_URL,
                            json={"client_id": HACKCLUB_CLIENT_ID, "client_secret": HACKCLUB_CLIENT_SECRET,
                                  "redirect_uri": hackclub_redirect_uri(), "code": code,
                                  "grant_type": "authorization_code"}, timeout=10)
        tok_body = tok.json() if tok.status_code < 300 else {}
        access = tok_body.get("access_token", "")
        id_token = tok_body.get("id_token", "")
        granted_scope = tok_body.get("scope", "")
    except Exception:  # noqa: BLE001 - token endpoint unreachable
        access, id_token, granted_scope = "", "", ""
    app.logger.info("hackclub token exchange status=%s granted_scope=%s",
                    tok.status_code if "tok" in locals() else "exception", granted_scope)
    if not access:
        return auth_error("Could not exchange the authorization code.", 502)
    try:
        me = requests.get(HACKCLUB_ME_URL, headers={"Authorization": f"Bearer {access}"}, timeout=10)
        identity = me.json() if me.status_code < 300 else {}
        app.logger.info("hackclub /me status=%s keys=%s shape=%s",
                        me.status_code, hc_keys(identity), hc_shape(identity))
    except Exception:  # noqa: BLE001 - identity endpoint unreachable
        identity = {}
        app.logger.info("hackclub /me request failed")
    email = hc_email(identity)
    if not email:
        hint = (f" Granted scopes: {granted_scope}." if granted_scope else "")
        return auth_error("Hack Club didn't return an email address." + hint +
                          " Check that the 'email' scope is enabled for your OAuth app, then revoke "
                          "the app's access in your Hack Club account and try again so it re-asks.", 502)
    if isinstance(identity, dict):
        # /me only carries id + primary_email, so take the name from the
        # OIDC ID token (same trusted token response) when /me has none.
        claims = id_token_claims(id_token)
        if claims and not hc_name(identity):
            for key in ("name", "preferred_username", "username"):
                if claims.get(key):
                    identity["name"] = claims[key]
                    break
            else:
                full = f"{claims.get('given_name', '')} {claims.get('family_name', '')}".strip()
                if full:
                    identity["name"] = full
    if not CTFD_API_TOKEN:
        return redirect(ctfd_url("/register"), code=302)
    username = ctfd_username_for(identity)
    verified = bool(identity.get("email_verified", True))
    if ARENA_DEFAULT_PASSWORD:
        password, pw_note = ARENA_DEFAULT_PASSWORD, "default"
    else:
        password, pw_note = secrets.token_urlsafe(16), "one-time"
    final_name, outcome, last_status = username, "error", "error"
    for attempt in range(4):
        candidate = username if attempt == 0 else f"{username}_{attempt + 1}"
        last_status, _ = ctfd_create_user(candidate, email, password, verified)
        if last_status == "created":
            final_name, outcome = candidate, "created"
            break
        if last_status == "exists":
            # Returning player: reset password to the default so the shown
            # credentials always work, then log them in.
            user = ctfd_find_user(email)
            if user and user.get("id") and ctfd_set_password(user["id"], password):
                final_name, outcome = user.get("name") or candidate, "reset"
            else:
                outcome = "exists"
            break
        if last_status != "taken":
            break
    else:
        outcome = last_status
    app.logger.info("ctfd provision: outcome=%s user=%s", outcome, final_name)
    if outcome == "error":
        return redirect(ctfd_url("/login"), code=302)
    entered = ctfd_login_cookies(final_name, password)
    app.logger.info("ctfd auto-login: %s", "ok" if entered else "failed")
    return provisioned_page(final_name, password, pw_note, entered, outcome)


@app.route("/api/auth/status")
def auth_status():
    return jsonify({"hackclub_configured": hackclub_configured(),
                    "ctfd_provisioning": bool(CTFD_API_TOKEN),
                    "callback": hackclub_redirect_uri(),
                    "ctfd_url": get_ctfd_url()}), 200


@app.route("/api/ctfd/status")
def ctfd_status():
    """Live arena check for the footer badge. Never crashes when CTFd is down."""
    online, detail = False, "unknown"
    if requests is None:
        detail = "requests not installed"
    else:
        for candidate in (CTFD_INTERNAL_URL, get_ctfd_url()):
            try:
                r = requests.get(f"{candidate}/", timeout=3, allow_redirects=True)
                online, detail = r.status_code < 500, f"HTTP {r.status_code}"
                break
            except Exception as e:  
                detail = type(e).__name__
                continue
    return jsonify({"online": online, "ctfd_url": get_ctfd_url(), "detail": detail}), (200 if online else 503)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "ctfd_url": get_ctfd_url()}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
