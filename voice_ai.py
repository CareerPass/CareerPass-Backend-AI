# ================================================================
# 🎧 음성 → 텍스트(STT) 전용 서버 
#  - 클라이언트(또는 스프링 백엔드)에서 meta + 음성파일을 보내면
#    텍스트로 변환해서 answerText 하나만 반환
#  - 아직은 Whisper 안 붙이고 mock 텍스트로 동작 (흐름 테스트용)
# ================================================================

import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI(title="Voice STT Server")

# CORS 설정 (백엔드 / 프론트에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------
# ✅ STT 결과 DTO
# --------------------------
class STTResult(BaseModel):
    answerText: str   # 변환된 텍스트만!

# --------------------------
# 헬스체크
# --------------------------
@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

# --------------------------
# 🎯 핵심: 음성 → 텍스트 엔드포인트
# --------------------------
@app.post("/analyze", response_model=STTResult)
async def analyze(
    meta: str = Form(...),         # form-data 필드 "meta" (JSON 문자열)
    file: UploadFile = File(...),  # form-data 필드 "file" (음성 파일)
):
    """
    meta 예시:
        {"interviewId":1,"questionId":"q-1","userId":10}

    - 프론트: 질문별로 녹음 -> 백엔드(/api/interview/voice/analyze)로 전송
    - 스프링: meta + file 그대로 여기(5001/analyze)로 포워딩
    - 이 서버: STT(지금은 mock) 후 answerText만 반환
    """

    # 1) meta JSON 파싱
    try:
        meta_obj = json.loads(meta)
        interview_id = meta_obj.get("interviewId")
        question_id = meta_obj.get("questionId")
        user_id = meta_obj.get("userId")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid meta json: {e}")

    # 2) 파일 체크
    if file is None or file.filename is None:
        raise HTTPException(status_code=400, detail="file missing")

    if not file.filename.lower().endswith((".m4a", ".mp3", ".wav", ".webm", ".ogg")):
        raise HTTPException(status_code=400, detail="unsupported audio type")

    # 3) (임시) STT mock
    #    나중에 여기서 Whisper 붙이면 됨
    text = f"(mock STT) user={user_id}, interview={interview_id}, question={question_id}, file={file.filename}"

    # 4) answerText 하나만 리턴
    return STTResult(answerText=text)