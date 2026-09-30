FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && python -m playwright install --with-deps chromium
COPY app.py bot.py .
# Real flag/secret are injected at deploy time, never baked into this file:
#   docker build --build-arg FLAG=pentest{...} --build-arg ADMIN_SECRET=... -t xss .
ARG FLAG=pentest{REDACTED}
ARG ADMIN_SECRET=REDACTED
ENV ADMIN_SECRET=$ADMIN_SECRET \
    APP_URL=http://127.0.0.1:5000
RUN echo "$FLAG" > /flag.txt
EXPOSE 5000
CMD ["python", "app.py"]
