<P align="center">
<img width="3780" height="1890" alt="ESCAPE YOUR FATE" src="https://github.com/user-attachments/assets/9aaa356e-a8a3-4cf1-9fa4-55eae4338c55" />
</p>

Welcome to **PEN-TEST**, a youth-driven cybersecurity community where teenagers explore, learn, and innovate in the world of application security.

## What We Do

PEN-TEST is a hackclub dedicated to developing practical cybersecurity projects. Members collaborate on real-world problems, from vulnerability assessments to security tool development, while building expertise in ethical hacking and defensive security practices.

## Why Join?

- **Build Real Skills** - Work on hands-on cybersecurity projects that matter
- **Learn from Peers** - Collaborate with like-minded teenagers passionate about security
- **Get Recognized** - Earn badges, certificates, and rewards for completed projects
- **Make an Impact** - Contribute to securing applications and systems

## Project Categories

We focus on various areas including:
- Web application security 
- penetration testing Tools
- Cryptography Tools
- OSINT Tools
- Infosec Tools
- Forensic Tools
- Security automation tools

## Getting Started

Interested in joining? We meet regularly to brainstorm ideas, share knowledge, and work on our next big project. Whether you're a beginner or experienced, there's a place for you in PEN-TEST.

**Let's secure the future, together.**

## Running locally

Install requirements, set `SECRET_KEY` to a persistent random secret (generate one with
`python -c "import secrets; print(secrets.token_hex(32))"`), then run:

```sh
flask --app main init-db
python main.py
```

`init-db` creates missing tables; it does not alter existing tables or accounts.
Run it before starting `flask run` or a WSGI server against a fresh database.
Keep the same `SECRET_KEY` across restarts/workers and do not commit it.
For HTTPS hosting, set `COOKIE_SECURE=1`. Rate limits use memory per process by
default; multiple workers need a shared `RATELIMIT_STORAGE_URI` and the matching
Flask-Limiter storage dependency. Client IPs come from the direct connection;
proxy deployments must configure trusted forwarding for their actual proxy setup.
