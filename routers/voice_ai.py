# voice_ai.py
# ================================================================
# 음성 STT 서버 (FastAPI + OpenAI Whisper)
# ================================================================

import os
import json
import logging
from io import BytesIO  # ✅ 파일 데이터를 바이트 스트림으로 처리하기 위해 사용

from fastapi import UploadFile, File, Form, HTTPException, APIRouter
from fastapi.responses import Response
from pydantic import BaseModel
from openai import OpenAI
from openai import OpenAIError # 💡 OpenAI API 관련 예외 처리를 위해 추가

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------
# 0. 환경 변수 / OpenAI 설정
# -----------------------------

voice_router = APIRouter()

# 🚨 주의: 전역 초기화 코드 (VOICE_KEY, client 정의 블록)는 
# 타이밍 문제 해결을 위해 삭제되었습니다.


# -----------------------------
# 2. 응답 DTO (STT 결과)
# -----------------------------
class SttResult(BaseModel):
    answerText: str  # STT 결과 텍스트만 반환

# -----------------------------
# 3. 헬스체크 & 파비콘
# -----------------------------
@voice_router.get("/health")
async def health():
    return {"ok": True}

@voice_router.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

# -----------------------------
# 4. 핵심 API: /analyze
# -----------------------------
@voice_router.post("/analyze", response_model=SttResult)
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
        logger.info(f"STT 요청 수신: Interview ID={meta_obj.get('interviewId')}, 파일명={file.filename}")
    except Exception as e:
        logger.error(f"메타 JSON 파싱 오류: {e}")
        # ⚠️ (추가) 요청을 보내는 클라이언트 측에서 유효한 JSON 문자열("{"interviewId": 0}")을 보내야 합니다.
        raise HTTPException(status_code=400, detail=f"invalid meta json: {e}")

    interview_id = meta_obj.get("interviewId")
    question_id = meta_obj.get("questionId")
    user_id = meta_obj.get("userId")  # 없어도 됨 (null 허용)

    # 2) 파일 기본 검증
    if not file or not file.filename:
        logger.error("파일 누락 오류 발생")
        raise HTTPException(status_code=400, detail="file missing")

    lower_name = file.filename.lower()
    if not lower_name.endswith((".m4a", ".mp3", ".wav", ".webm", ".ogg")):
        logger.error(f"지원하지 않는 오디오 타입: {file.filename}")
        raise HTTPException(status_code=400, detail="unsupported audio type")

    # 3) Whisper 호출 (실제 STT)
    try:
        # 💡 [핵심 해결] 지연 초기화: 함수 호출 시점에 키를 읽어 클라이언트 생성
        local_voice_key = os.environ.get("QUESTION_VOICE_OPENAI_KEY")
        if not local_voice_key:
            logger.error("QUESTION_VOICE_OPENAI_KEY 환경 변수가 설정되지 않았습니다.")
            raise HTTPException(status_code=500, detail="Whisper 호출 실패: OpenAI API Key 설정 누락")
        
        # 🔑 클라이언트 생성 (OpenAI API Key 누락 오류 해결)
        client = OpenAI(api_key=local_voice_key) 
        
        # ✅ 업로드 파일 바이트 읽어서 BytesIO로 감싸기
        contents = await file.read()
        audio_bytes = BytesIO(contents)
        audio_bytes.name = file.filename  # 확장자 포함 이름을 달아줌

        logger.info(f"Whisper API 호출 시도: 모델=whisper-1, 파일 크기={len(contents)} bytes") 

        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_bytes,
            language="ko",
        )

        text = getattr(transcription, "text", None) or str(transcription)

        logger.info(f"Whisper 호출 성공: 텍스트 길이={len(text)}")

    except OpenAIError as e:
        # OpenAI API 호출 자체에서 발생한 오류 처리 (예: 잘못된 키, 모델)
        logger.error(f"Whisper API 오류: {e.status_code} - {e.response.text}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Whisper API 오류: {e}")
    except Exception as e:
        logger.error(f"Whisper 호출 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Whisper 호출 실패: {e}")

    # 4) 최종 응답
    return SttResult(answerText=text)