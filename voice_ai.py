# voice_ai.py
# ================================================================
# 음성 STT 서버 (FastAPI + OpenAI Whisper)
# ================================================================

import os
import json
from io import BytesIO  # ✅ 추가

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import openai

# -----------------------------
# 0. 환경 변수 / OpenAI 설정
# -----------------------------
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY 가 설정되어 있지 않습니다. (.env 확인!)")

# -----------------------------
# 1. FastAPI 앱 & CORS
# -----------------------------
app = FastAPI(title="CareerPass Voice STT")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# 2. 응답 DTO (STT 결과)
# -----------------------------
class SttResult(BaseModel):
    answerText: str  # STT 결과 텍스트만 반환

# -----------------------------
# 3. 헬스체크 & 파비콘
# -----------------------------
@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

# -----------------------------
# 4. 핵심 API: /analyze
# -----------------------------
@app.post("/analyze", response_model=SttResult)
async def analyze(
    meta: str = Form(...),
    file: UploadFile = File(...),
):
    """
    🎧 음성 파일을 Whisper에 보내서 텍스트로 변환
    - meta: 인터뷰 / 질문 정보 (백엔드에서 사용하는 용도)
    - file: .m4a / .mp3 / .wav / .webm / .ogg 등
    """

    # 1) meta JSON 파싱
    try:
        meta_obj = json.loads(meta)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid meta json: {e}")

    interview_id = meta_obj.get("interviewId")
    question_id = meta_obj.get("questionId")
    user_id = meta_obj.get("userId")  # 없어도 됨 (null 허용)

    # 2) 파일 기본 검증
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="file missing")

    lower_name = file.filename.lower()
    if not lower_name.endswith((".m4a", ".mp3", ".wav", ".webm", ".ogg")):
        raise HTTPException(status_code=400, detail="unsupported audio type")

    # 3) Whisper 호출 (실제 STT)
    try:
        # ✅ 업로드 파일 바이트 읽어서 BytesIO로 감싸기
        contents = await file.read()
        audio_bytes = BytesIO(contents)
        audio_bytes.name = file.filename  # 🔥 여기서 확장자 포함 이름을 달아줌

        transcription = openai.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",  # 또는 "whisper-1"
            file=audio_bytes,
            language="ko",
        )

        # SDK 버전에 따라 text 속성이 있거나, 문자열일 수 있음
        text = getattr(transcription, "text", None) or str(transcription)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Whisper 호출 실패: {e}")

    # 4) 최종 응답
    return SttResult(answerText=text)


# 로컬 실행용 엔트리포인트
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("voice_ai:app", host="0.0.0.0", port=5001, reload=True)