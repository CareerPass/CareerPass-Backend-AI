# ================================================================
# 🤖 음성 분석 서버 (FastAPI)
# ================================================================
# - 클라이언트로부터 meta(JSON) + 오디오 파일을 multipart/form-data로 받아
#   AI 모델(Whisper + GPT)을 통해 전사 + 분석 결과를 반환하는 역할
# - 현재는 실제 AI 호출 없이 mock(가짜) 데이터로 테스트 가능
# - Flask(question_ai.py)와는 별개의 FastAPI 서버로 동작
# ================================================================

import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

# ---------------------------------------------------------------
# 1️⃣ FastAPI 앱 생성 및 CORS 설정
# ---------------------------------------------------------------
app = FastAPI(title="Voice AI")

# ✅ CORS(Cross-Origin Resource Sharing) 허용
# - 다른 포트(예: 8080, 3000 등)에서 요청을 받아줄 수 있게 함
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 모든 도메인 허용 (필요 시 수정 가능)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------
# 2️⃣ 응답 DTO 정의 (FastAPI에서는 Pydantic 모델 사용)
# ---------------------------------------------------------------
class AnalysisResult(BaseModel):
    """AI 분석 결과를 반환하는 DTO"""
    questionId: int | None = None    # 분석 대상 질문 ID (없을 수도 있음)
    answerText: str                  # 전사된 텍스트
    score: int                       # AI가 부여한 점수
    feedback: str                    # 피드백 문장

# ---------------------------------------------------------------
# 3️⃣ 헬스체크 엔드포인트 (서버 상태 확인용)
# ---------------------------------------------------------------
@app.get("/health")
async def health():
    """서버가 정상적으로 작동 중인지 확인"""
    return {"ok": True}

@app.get("/favicon.ico")
async def favicon():
    """브라우저에서 자동 요청하는 /favicon.ico 무시"""
    return Response(status_code=204)

# ---------------------------------------------------------------
# 4️⃣ 핵심 API: 음성 파일 분석
# ---------------------------------------------------------------
@app.post("/analyze", response_model=AnalysisResult)
async def analyze(
    meta: str = Form(...),         # 요청의 form-data 중 meta (JSON 문자열)
    file: UploadFile = File(...),  # 업로드된 음성 파일
):
    """
    🎧 클라이언트로부터 meta + file을 받아 분석 결과 반환
    - meta: {"interviewId":1,"questionId":101}
    - file: 오디오(.m4a, .mp3, .wav 등)
    """

    # -----------------------------------------------------------
    # ① meta 파싱 및 유효성 검사
    # -----------------------------------------------------------
    try:
        meta_obj = json.loads(meta)   # 문자열 → JSON 변환
        interview_id = meta_obj.get("interviewId")
        question_id = meta_obj.get("questionId")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid meta json: {e}")

    # -----------------------------------------------------------
    # ② 파일 유효성 검사
    # -----------------------------------------------------------
    if file is None or file.filename is None:
        raise HTTPException(status_code=400, detail="file missing")

    if not file.filename.lower().endswith((".m4a", ".mp3", ".wav", ".webm", ".ogg")):
        raise HTTPException(status_code=400, detail="unsupported audio type")

    # -----------------------------------------------------------
    # ③ (임시) AI 분석 Mock 로직
    # -----------------------------------------------------------
    # 실제 Whisper + GPT 연동 전에 정상 흐름만 검증하는 단계
    text = f"(mock) interview={interview_id}, question={question_id}, file={file.filename}"
    score = 87
    feedback = "발음 명료함, 핵심어 강조 좋음. 말 속도 약간 빠름."

    # -----------------------------------------------------------
    # ④ 결과 DTO로 반환 (FastAPI가 자동 JSON 직렬화)
    # -----------------------------------------------------------
    return AnalysisResult(
        questionId=question_id,
        answerText=text,
        score=score,
        feedback=feedback,
    )