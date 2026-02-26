FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성 설치 (필요시 lxml, pykrx 등 지원을 위해)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 종속성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 실행 환경 설정
ENV PORT=8080
ENV PYTHONUNBUFFERED=TRUE

# Cloud Run은 PORT 환경변수로 수신 포트를 전달함.
# uvicorn을 사용하여 0.0.0.0 포트로 서버 안정적 가동.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
