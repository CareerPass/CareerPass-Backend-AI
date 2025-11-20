# main_api.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 1. 모든 라우터 파일 import (✅ 파일명과 라우터 변수명 매칭 완료)
# ----------------------------------------------------------------------
# 라우터 파일 이름 (routers.파일_이름)과 해당 파일 안의 라우터 변수명 (import 변수명)을 매칭합니다.
from routers.interview_ai import interview_router
from routers.question_ai import question_router
from routers.resume_edit import resume_router
from routers.voice_ai import voice_router


# ==============================================================================
# 0. 환경 변수 로드 (중앙 집중 관리)
# ==============================================================================

# 파일 이름이 app_sevice.env였으므로 반영합니다.
load_dotenv('app_sevice.env') 

# 환경 변수에서 서비스 포트 설정 (없으면 기본값 8000 사용)
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", 8000))
SERVICE_HOST = os.environ.get("SERVICE_HOST", "0.0.0.0")

print("환경 변수 로드 완료.")


# ==============================================================================
# 1. FastAPI 앱 인스턴스 생성
# ==============================================================================

app = FastAPI(
    title="통합 AI 백엔드 서비스",
    description="면접 분석, 질문 생성, 이력서 피드백, 음성 STT 기능을 제공하는 단일 API 서버입니다.",
    version="1.0.0"
)

# ==============================================================================
# 2. CORS 미들웨어 설정 (중앙 집중 관리)
# ==============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("CORS 미들웨어 설정 완료.")


# ==============================================================================
# 3. 라우터 통합 (모듈 플러그인)
# ==============================================================================

# 1) 면접 분석 라우터 통합
app.include_router(
    interview_router,
    prefix="/interview", 
    tags=["Interview Analysis"]
)
print("Interview Router 통합 완료 (접두사: /interview)")

# 2) 질문 생성 라우터 통합
app.include_router(
    question_router,
    prefix="/question", 
    tags=["Question Generation"]
)
print("Question Router 통합 완료 (접두사: /question)")

# 3) 이력서 피드백 라우터 통합
app.include_router(
    resume_router,
    prefix="/resume", 
    tags=["Resume Feedback"]
)
print("Resume Router 통합 완료 (접두사: /resume)")

# 4) 음성 STT 라우터 통합
app.include_router(
    voice_router,
    prefix="/voice", 
    tags=["Voice STT"]
)
print("Voice Router 통합 완료 (접두사: /voice)")


# ==============================================================================
# 4. 서버 실행 엔트리포인트 (Uvicorn)
# ==============================================================================

if __name__ == "__main__":
    print("-" * 50)
    print(f"🚀 FastAPI 통합 서버 시작: http://{SERVICE_HOST}:{SERVICE_PORT}")
    print("-" * 50)
    
    uvicorn.run(
        "main_api:app", 
        host=SERVICE_HOST, 
        port=SERVICE_PORT, 
        reload=True 
    )