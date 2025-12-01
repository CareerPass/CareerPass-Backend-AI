import os
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import openai
from openai import OpenAI

question_router = APIRouter()

QUESTION_KEY = os.environ.get("QUESTION_VOICE_OPENAI_KEY")

try:
    question_client = OpenAI(api_key=QUESTION_KEY)
    print("Question Router OpenAI 클라이언트 초기화 완료.")
except Exception:
    print("OpenAI API Key가 설정되지 않았습니다. 분석은 Mock 모드로 작동합니다.")
    client = None

class QuestionRequest(BaseModel):
    """클라이언트로부터 받아야 하는 요청 데이터 구조"""
    major: str = Field(..., description="지원자의 전공")
    job_title: str = Field(..., description="지원 직무")
    cover_letter: str = Field("", description="자기소개서 내용")

class QuestionResponse(BaseModel):
    """클라이언트에게 응답할 데이터 구조"""
    question: List[str]

# 3. 질문 생성 함수
def generate_interview_questions(major, job_title, cover_letter=""):
    base_prompt = f"""
    당신은 전문 면접관입니다. 지원자가 **{major}** 학과를 졸업하고 **{job_title}** 직무에 지원한다고 가정합니다.
    """
    if cover_letter and cover_letter.strip():
        base_prompt += f"""
        아래 자기소개서를 참고하여, 자소서 심층 질문 4개 + 직무 역량 질문 3개로 총 7개 질문을 리스트 형태로 생성해주세요.

        --- 자기소개서 ---
        {cover_letter}
        --- 자기소개서 ---
        """
    else:
        base_prompt += """
        이 지원자를 평가하기 위한 전문적인 면접 질문 5가지를 리스트 형태로 생성해주세요.
        """
    base_prompt += "\n질문은 한 줄에 하나씩 번호 없이 출력."

    try:
        resp = question_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "사용자의 전공/직무/자소서를 바탕으로 면접 질문을 생성하는 AI"},
                {"role": "user", "content": base_prompt}
            ],
            temperature=0.7
        )
        questions_text = resp.choices[0].message.content.strip()
        return [q.strip() for q in questions_text.split("\n") if q.strip()]
    except Exception as e:
        print(f"API 호출 오류: {e}")
        return None

# 4. 엔드포인트
@question_router.post("/api/questions", response_model=QuestionResponse)
def get_questions(data: QuestionRequest):
    major = data.major
    job_title = data.job_title
    cover_letter = data.cover_letter

    if not major or not job_title:
        raise HTTPException(status_code=400, detail="학과(major)와 직무(job_title)를 모두 제공해야 합니다.")

    qs = generate_interview_questions(major, job_title, cover_letter)
    if qs:
        return {"question": qs}
    raise HTTPException(status_code=500, detail="면접 질문 생성에 실패했습니다.")
# 5. 서버 실행 (여기 없으면 python question_ai.py 실행 시 바로 종료됨)
#if __name__ == "__main__":
#    print("✅ Flask question_ai 서버 시작: http://localhost:5002")
#    app.run(host="0.0.0.0", port=5002, debug=True)