# -*- coding: utf-8 -*-
"""
Resume Feedback API
사용자 -> 이력서 입력 -> OpenAI 피드백 생성 -> 반환
"""

import os
from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# FastAPI app
app = FastAPI()
resume_router = APIRouter()

# OpenAI Key 가져오기
RESUME_KEY = os.getenv("RESUME_OPENAI_KEY")

try:
    resume_client = OpenAI(api_key=RESUME_KEY)
    print("Resume Router OpenAI 클라이언트 초기화 완료.")
except Exception as e:
    print("❌ OpenAI API Key 초기화 실패 → Mock 모드로 작동합니다.")
    print(e)
    resume_client = None


# ------------------------------- DTO ---------------------------------

class ResumeInput(BaseModel):
    userId: int
    resumeContent: str

class FeedbackResponse(BaseModel):
    userId: int
    original_resume: str
    feedback: str
    regen_resume: str
    regen_toss_resume: str
    


# ------------------------------- SYSTEM PROMPT ---------------------------------

system_message = """
#이력서를 피드백하는 에이전트 시스템 프롬프트 

##역할 정의
당신은 취업 준비 대학생을 위한 이력서 컨설턴트 전문가입니다.
회사 채용 담당자의 관점에서 이력서를 분석하고, 
서류 전형 통과율을 높이기 위한 구체적이고 실행 가능한 피드백을 제공해야합니다.


##주요 목표
- 이력서 스크리닝(1차 서류 탈락)을 방지하는 것이 최우선적인 목표
-채용 담당자가 6초 이내에 핵심 역량을 파악할 수 있도록 개선 방향 제시
-ATS(Applicant Tracking System) 통과를 위한 최적화 조언

##분석 프레임워크

###1단계 : 전체 구조 평가
다음 항목을 체크리스트로 확인 :
- [ ] 기본 정보(이름, 연락처, 이메일, 링크)
- [ ] 학력 사항
- [ ] 경험 및 활동(인턴, 프로젝트, 수상, 대외활동 등)
- [ ] 기술 스택 및 역량
- [ ] 자격증 및 수상 경력(해당 시)
- [ ] 1~2페이지 분량 준수 여부

###2단계 : 치명적 오류 식별(최우선 개선 사항)
다음 문제가 있다면 **즉시 수정 필요**로 표시 :
- 오타, 맞춤법, 문법 오류
- 연락처 정보 누락 또는 오류
- 비전문적인 이메일 주소
- 과도한 분량 (3페이지 이상)
- 사진 포함 여부 (채용 공고에서 요구하지 않는 경우)
- 주민등록번호 등의 민감 정보 노출

###3단계 : 내용 품질 분석
각 경험/프로젝트 항복에 대해 : 
- **STAR 기법** 적용 여부 (Situation-Task-Action-Result)
- **정량적 성과** 포함 여부 (숫자, 퍼센트, 규모 등)
- **능동적 동사** 사용 여부 (개발했다, 주도했다, 개선했다 등)
- **작무 연관성**: 지원 직무와의 관련도

###4단걔: ATS 최적화
- 직무 관련 키워드 포함 여부
- 표, 이미지, 특수 폰트 사용으로 인한 파싱 문제 가능성
- 명확한 섹션 헤더 사용

##피드백 제공 방식

###구조

1. **종합 평가**(5~6문장)
    - 현재 이력서의 강점 최소 2~3가지 이상, 많은 것은 상관 없음
    - 가장 시급한 개선점 최소 2~3가지 이상, 많은 것은 상관 없음

2. **우선순위별 개선 사항**
    - **즉시 수정 필요** : 치명적 오류
    - **중요 개선** : 통과율에 큰 영향
    - **권장 개선**: 경쟁력 향상

3. **섹션별 상세 피드백**
    각 섹션마다
    - 현재 상태 평가
    - 구체적 개선 방향
    -Before/After 예시(가능한 경우)
    
4. **실행 체크리스트**
    - 수정해야 할 항복을 체크리스트로 요약
    
###피드백 원칙
- **구체적이고 실행 가능하게** : "더 잘 써야합니다" X -> "프로젝트 결과에 사용자 수 증가율을 추가하세요" O
- **교육적으로** : 왜 그렇게 수정해야하는지 이유 설명
- **긍정적이면서 현실적으로** : 개선이 필요한 부분을 솔직하게 지적하되, 격려하는 톤 유지
- **우선순위 명확히** : 모든 것을 다 고칠 필요는 없고 가장 임팩트 있는 개선점부터 제시

##예시 피드백 구조

## [ 종합 평가 ]
현재 이력서는 다양한 프로젝트 경험이 잘 정리되어 있습니다. 특히 기술 스택이 명확하게 제시된 점이 좋습니다. 다만, 각 프로젝트의 **구체적인 성과**가 부족하고, 일부 **오타**가 발견되어 즉시 수정이 필요합니다.

## [ 즉시 수정 필요 ]
1. **오타 수정** (3곳 발견)
    - "웹사이트를 개발하엿습니다" → "개발했습니다"

2. **연락처 정보**
    - 이메일: cutepanda123@naver.com → 전문적인 이메일로 변경 권장
    - 예: your.name@gmail.com 또는 your.name@naver.com

## [ 중요 개선사항 ]
1. **프로젝트 성과 정량화**
    - Before: "쇼핑몰 웹사이트를 개발했습니다"
    - After: "쇼핑몰 웹사이트를 개발하여 월 평균 500명의 사용자 유입 달성"

[... 계속]

## [ 수정 체크리스트 ]
- 오타 3곳 수정
- 이메일 주소 변경
- 프로젝트 3개에 정량적 성과 추가
- 기술 스택을 직무 공고 키워드에 맞춰 재배치


## 추가 지침
- 이력서가 특정 기업/직무에 맞춰진 경우, 해당 직무 요구사항을 고려하여 피드백
- 경력이 부족한 대학생의 경우, 프로젝트/동아리/봉사활동 등으로 보완 가능함을 안내
- 질문이 있으면 언제든 물어보라고 격려
- 1회 피드백으로 끝나지 않고, 수정 후 재검토를 권장

## 톤 가이드라인
- 존댓말 사용 ("~해보세요", "~하시면 좋겠습니다")
- 비판보다는 건설적 제안
- "틀렸다"보다는 "개선하면 더 좋다"는 관점
- 학생의 노력과 경험을 인정하며 시작

각 섹션마다 줄 띄어쓰기를 적용해서 가독성 좋게 출력해야함
가독성 좋게 부탁해

"""


# ------------------------------- OPENAI CALL ---------------------------------

def generate_feedback(resume_text: str) -> str:
    """OpenAI API 호출 → 피드백 생성"""

    # API KEY 없으면 Mock 텍스트 반환
    if resume_client is None:
        return "현재 OpenAI Key가 없어 테스트용 더미 피드백을 반환합니다."

    # system + user 프롬프트를 하나의 문자열로 합쳐서 사용
    prompt = (
        system_message
        + "\n\n"
        + "아래는 사용자가 제출한 이력서(자기소개서) 내용입니다. 위 가이드라인에 따라 한국어로 상세 피드백을 작성해 주세요.\n\n"
        + resume_text
    )

    try:
        response = resume_client.responses.create(
            model="gpt-4o-mini",   # gpt-4o-mini 그대로 사용 가능
            input=prompt           # ⬅️ messages 대신 input 한 줄
        )
        return response.output[0].content[0].text
    except Exception as e:
        print(" OpenAI 호출 중 오류:", e)
        return "AI 분석 중 오류가 발생했습니다. 내용을 다시 입력해 주세요."

# 자기소개서 재생성 함수    
def regenerate_resume(original_resume_text: str, feedback_text: str) -> str:
    """
    주어진 피드백을 바탕으로 이력서 내용을 재생성하고 개선합니다.
    """

    # API KEY 없으면 Mock 텍스트 반환
    if resume_client is None:
        return "현재 OpenAI Key가 없어 테스트용 더미 재생성 이력서를 반환합니다."

    # 재생성 프롬프트 구성: 원본 이력서 + 피드백을 함께 제공하여 개선을 요청합니다.
    prompt = (
        "아래는 **사용자가 제출한 원본 이력서 내용**입니다.\n\n"
        + "--- 원본 이력서 ---\n"
        + original_resume_text
        + "\n\n"
        + "아래는 **AI가 생성한 상세 피드백**입니다. 이 피드백을 100% 반영하여 원본 이력서 내용을 개선해 주세요. 응답은 오직 **개선된 이력서 내용**만 포함해야 합니다. 줄을 띄어쓰지 말고 한 줄로 이어서 작성해주세요. 이름, 전화번호, 이메일, 학력, 학점 등은 작성하지 않습니다. 오로지 이력서에 작성된 경험 및 활동에 해당하는 부분만 개선합니다.\n\n"
        + "--- 피드백 내용 ---\n"
        + feedback_text
    )

    try:
        # OpenAI API 호출 (gpt-4o-mini 그대로 사용)
        response = resume_client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )
        # 응답 구조는 사용하신 OpenAI 라이브러리 버전에 따라 다를 수 있습니다.
        # 기존 코드와 동일한 구조를 따릅니다.
        return response.output[0].content[0].text
    
    except Exception as e:
        print("OpenAI 호출 중 오류:", e)
        return "AI 분석 중 오류가 발생했습니다. 내용을 다시 시도해 주세요."
    
#자기소개서 토스 인재상 재생성 함수
def regenerate_toss_resume(original_resume_text: str, feedback_text: str) -> str:
    """
    주어진 피드백을 바탕으로 이력서 내용을 재생성하고 개선합니다.
    """

    # API KEY 없으면 Mock 텍스트 반환
    if resume_client is None:
        return "현재 OpenAI Key가 없어 테스트용 더미 재생성 이력서를 반환합니다."

    # 재생성 프롬프트 구성: 원본 이력서 + 피드백을 함께 제공하여 개선을 요청합니다.
    prompt = (
        "아래는 **사용자가 제출한 원본 이력서 내용**입니다.\n\n"
        + "--- 원본 이력서 ---\n"
        + original_resume_text
        + "\n\n"
        + """아래는 **AI가 생성한 상세 피드백**입니다. 이 피드백을 100% 반영하여 원본 이력서 내용을 개선해 주세요. 
        응답은 오직 **개선된 이력서 내용**만 포함해야 합니다. 줄을 띄어쓰지 말고 한 줄로 이어서 작성해주세요. 
        이름, 전화번호, 이메일, 학력, 학점 등은 작성하지 않습니다. 오로지 이력서에 작성된 경험 및 활동에 해당하는 부분만 개선합니다.
        이 자소서는 토스 기업의 인재상을 반영하여 작성되어야합니다. 토스 인재상 핵심 가치는 다음과 같습니다.
        1) 깊은 몰입 (Deep Focus & Ownership)
        - 각자의 방식으로 문제에 깊게 몰입하고 주도적으로 해결함
        - 맡은 일에 대해 스스로 결정하고 끝까지 책임지는 태도
        - 지시를 기다리지 않고 필요하면 먼저 움직이는 사람
        
        2) DRI 기반 책임감 있는 전문가
        - 맡은 일에 대한 최종 의사결정권(DRI)을 가지고 판단함
        - 결과에 대한 모든 책임을 스스로 짐
        - 필요한 정보를 수집해 전문가로서 합리적 결정을 내릴 수 있는 사람
        
        3) 높은 윤리성과 자율성
        - 자율을 악용하지 않고 스스로 기준을 지킬 줄 아는 사람
        - 불필요한 규칙 없이도 스스로 일을 통제하고 정직하게 수행함
        - 신뢰를 기반으로 협력할 수 있는 도덕성 보유

        4) 투명한 정보 공유
        - 정보 비대칭을 없애기 위해 정보를 모두에게 개방
        - 숨기거나 정치적으로 움직이지 않으며, 모두가 동일한 정보 기반에서 일함
        - 협업을 위해 필요한 정보를 능동적으로 찾아 공유

        5) 빠른 실패와 학습
        - 실패를 두려워하지 않고 빠르게 시도하고 개선하는 사람
        - 실패에서 배운 점을 구조적으로 정리하고 다음 실행에 반영
        - 빠른 시도 → 실패 → 학습 → 재도전의 사이클을 긍정적으로 받아들임

        이 인재상은 자기소개서 개선 시 다음과 같이 활용되어야합니다.
        - 지원자가 맡은 일에 대한 주도성과 책임감을 보여주는 표현 강화
        - 불필요한 장식 대신 '몰입·책임·자율·투명·학습'의 키워드를 반영한 경험 강조
        - 프로젝트나 활동에서의 '결정 경험, 빠른 실험, 실패 복기, 자율적 행동' 등을 구체적으로 서술하도록 유도\n\n"""
        + "--- 피드백 내용 ---\n"
        + feedback_text
    )

    try:
        # OpenAI API 호출 (gpt-4o-mini 그대로 사용)
        response = resume_client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )
        # 응답 구조는 사용하신 OpenAI 라이브러리 버전에 따라 다를 수 있습니다.
        # 기존 코드와 동일한 구조를 따릅니다.
        return response.output[0].content[0].text
    
    except Exception as e:
        print("OpenAI 호출 중 오류:", e)
        return "AI 분석 중 오류가 발생했습니다. 내용을 다시 시도해 주세요."

# ------------------------------- ENDPOINT ---------------------------------

@resume_router.post("/resume/feedback", response_model=FeedbackResponse)
async def resume_feedback(req: ResumeInput):
    """스프링 → 파이썬: 피드백 생성 후 즉시 반환"""

    feedback = generate_feedback(req.resumeContent)
    regenresume = regenerate_resume(req.resumeContent, feedback)
    regentossresume = regenerate_toss_resume(req.resumeContent, feedback)
    
    return FeedbackResponse(
        userId=req.userId,
        original_resume=req.resumeContent,
        feedback=feedback,
        regen_resume=regenresume,
        regen_toss_resume=regentossresume
    )

# FastAPI 라우터 등록
app.include_router(resume_router)
