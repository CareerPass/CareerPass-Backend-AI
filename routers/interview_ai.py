import os
import json
from typing import List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field, ValidationError
from fastapi import FastAPI, HTTPException, APIRouter
import openai
from openai import OpenAI

# ==============================================================================
# 1. 라우터 객체 생성, 환경 설정 및 클라이언트 초기화
# ==============================================================================

interview_router = APIRouter()

# 환경 변수에서 API Key 및 모델 ID 설정
INTERVIEW_KEY = os.environ.get("INTERVIEW_OPENAI_KEY")
CUSTOM_FINETUNED_MODEL_ID = os.environ.get("INTERVIEW_FINEDTUNED_MODEL_ID")

try:
    client = OpenAI(api_key=INTERVIEW_KEY)
    print("Interview Router OpenAI 클라이언트 초기화 완료.")
except Exception:
    print("OpenAI API Key가 설정되지 않았습니다. 분석은 Mock 모드로 작동합니다.")
    client = None

# ==============================================================================
# 2. 데이터 모델 정의 (Pydantic)
# ==============================================================================

class InterviewMeta(BaseModel):
    """A팀 tb_interview Entity를 반영한 세션 레벨 메타데이터"""
    id: int
    userId: int
    jobApplied: str
    questionId: int

class AnswerDispatch(BaseModel):
    """B팀 API가 A팀으로부터 받아야 하는 전체 입력 데이터 구조"""
    answerId: int
    questionText: str
    transcript: str = Field(..., description="A팀 Voice AI의 STT 결과")
    durationMs: int
    resumeContent: str
    meta: InterviewMeta

class AnswerAnalysisResult(BaseModel):
    """B팀 LLM의 최종 출력 스키마 (면접 피드백 항목)"""
    score: int = Field(..., ge=0, le=100)
    timeMs: int
    fluency: int = Field(..., ge=1, le=5)
    contentDepth: int = Field(..., ge=1, le=5)
    structure: int = Field(..., ge=1, le=5)
    fillerCount: int
    improvements: List[str]
    strengths: List[str]
    risks: List[str]

# ==============================================================================
# 3. 유틸리티 함수 (LLM 프롬프트 구성)
# ==============================================================================

def create_fine_tuning_example(dispatch: AnswerDispatch, analysis: AnswerAnalysisResult) -> Dict[str, Any]:
    """답변-분석 쌍을 OpenAI JSONL 형식으로 변환합니다."""

    system_prompt = (
        f"당신은 '{dispatch.meta.jobApplied}' 직무의 면접 평가 전문가입니다. "
        "주어진 질문과 답변, 지원자의 자기소개서 원문을 바탕으로 평가하고, "
        "반드시 JSON 스키마에 맞춰 결과를 출력해야 합니다."
    )
    user_content = (
        f"--- 평가 요청 ---\n자기소개서(원문): {dispatch.resumeContent}\n"
        f"질문: {dispatch.questionText}\n답변(transcript): {dispatch.transcript}\n"
        f"소요 시간(ms): {dispatch.durationMs}\n\n위 답변을 평가하고, JSON 스키마에 맞춰 결과를 출력해주세요."
    )
    assistant_content = analysis.model_dump_json()

    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content}
        ]
    }

# ==============================================================================
# 4. 면접 분석 핵심 로직 (LLM 호출)
# ==============================================================================

def run_analysis_with_finetuned_model(dispatch: AnswerDispatch) -> AnswerAnalysisResult:
    """파인튜닝된 모델을 호출하거나 Mock 데이터를 반환합니다."""

    # 1. 메시지 구성 (프롬프트 구성)
    messages = create_fine_tuning_example(dispatch, analysis=AnswerAnalysisResult.model_construct())['messages']
    raw_llm_output = ""

    # 2. LLM 호출 시도
    if client and CUSTOM_FINETUNED_MODEL_ID and 'ft:' in CUSTOM_FINETUNED_MODEL_ID:
        try:
            print(f"LLM 호출: {CUSTOM_FINETUNED_MODEL_ID} (Session ID: {dispatch.meta.id})")
            response = client.chat.completions.create(
                model=CUSTOM_FINETUNED_MODEL_ID,
                response_format={"type": "json_object", "schema": AnswerAnalysisResult.model_json_schema()},
                messages=messages,
                temperature=0.0
            )
            raw_llm_output = response.choices[0].message.content
        except Exception as e:
            print(f"LLM 호출 실패: {e}")

    # 3. Mock 데이터 또는 대체 로직
    if not client or not raw_llm_output:
        print("Mock 데이터를 사용하여 분석을 실행합니다.")
        raw_llm_output = json.dumps({
            "score": 88, "timeMs": dispatch.durationMs, "fluency": 5, "contentDepth": 4,
            "structure": 4, "fillerCount": 0,
            "improvements": [f"Mock 결과: 답변 시작 시 '음...'과 같은 필러가 없도록 연습하세요."],
            "strengths": ["직무 경험과 답변의 연관성이 높습니다."], "risks": ["답변 길이가 다소 짧았습니다."]
        })

    # 4. JSON 유효성 검증
    try:
        analysis_result = AnswerAnalysisResult.model_validate_json(raw_llm_output)
        return analysis_result
    except ValidationError as e:
        print(f"LLM 출력 JSON 스키마 오류: {e}")
        raise HTTPException(status_code=500, detail="LLM이 유효하지 않은 JSON을 반환했습니다.")


# ==============================================================================
# 5. FastAPI 엔드포인트 정의 (A팀이 호출할 API)
# ==============================================================================

@interview_router.post("/analysis/interview/run", response_model=AnswerAnalysisResult)
async def analyze_interview_answer(dispatch_data: AnswerDispatch):
    """
    HTTP POST 요청을 받아 면접 답변 분석을 실행하는 메인 엔드포인트입니다.
    """
    print(f"[{datetime.now()}] 분석 요청 수신: Answer ID {dispatch_data.answerId} (Session ID: {dispatch_data.meta.id})")

    analysis_result = run_analysis_with_finetuned_model(dispatch_data)

    return analysis_result