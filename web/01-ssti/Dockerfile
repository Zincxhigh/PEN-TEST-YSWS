FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
# Real flag is injected at deploy time, never baked into this file:
#   docker build --build-arg FLAG=pentest{...} -t ssti .
ARG FLAG=pentest{REDACTED}
RUN echo "$FLAG" > /flag.txt
EXPOSE 5000
CMD ["python", "app.py"]
