# Dockerfile

# 1. Python 공식 이미지를 기반으로 사용합니다. (3.11 버전 권장)
FROM python:3.11-slim

# 2. 작업 디렉토리를 /python_ai으로 설정합니다.
WORKDIR /python_ai

# 3. requirements.txt를 먼저 복사하여 종속성 계층을 캐시합니다.
#    (requirements.txt는 이미 완성된 상태라고 가정합니다.)
COPY requirements.txt .

# 4. 종속성 설치. 배포 환경이므로 --no-cache-dir을 사용합니다.
RUN pip install --no-cache-dir -r requirements.txt

# 5. 모든 소스 코드 파일을 /app으로 복사합니다.
#    (routers 폴더, main_api.py 등 모두 포함)
COPY . .

# 6. 환경 변수 설정 (컨테이너 내부의 기본값)
#    ⚠️ 이 값들은 보안상 민감하지 않은 기본값이며, 실제 민감 정보는
#    EC2 환경 변수 또는 AWS Secrets Manager를 통해 주입하는 것이 좋습니다.
ENV SERVICE_HOST=0.0.0.0
ENV SERVICE_PORT=8000

# 7. 서버가 사용할 포트를 외부에 노출합니다.
EXPOSE 8000

# 8. 컨테이너가 시작될 때 실행할 명령 (Gunicorn + Uvicorn Worker 사용)
#    Gunicorn 워커 4개로 main_api의 app 객체를 구동합니다.
CMD ["gunicorn", "main_api:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--log-file", "-", "--error-logfile", "-"]