# -*- coding: utf-8 -*-
"""
Resume Feedback API
사용자 -> 이력서 입력 -> OpenAI 피드백 생성 -> RDS 저장
"""

import os
import pymysql
from typing import List
from datetime import datetime
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv # 환경 변수 로드를 위해 추가

# 환경 변수 로드
load_dotenv()

# FastAPI 라우터 설정 
resume_router = APIRouter()

# 환경변수 및 OpenAI 클라이언트 초기화 (HEAD 브랜치의 로직 채택)
RESUME_KEY = os.getenv("RESUME_OPENAI_KEY")
try:
    # client 변수를 사용하여 LLM 호출 함수와 통일성을 유지
    client = OpenAI(api_key=RESUME_KEY) 
    print("Resume Router OpenAI 클라이언트 초기화 완료.")
except Exception:
    print("OpenAI API Key가 설정되지 않았습니다. 분석은 Mock 모드로 작동합니다.")
    client = None

# RDS DB 연결 정보 로드 (HEAD 브랜치의 DB 로직 채택)
DB_HOST = os.getenv("RDS_DB_HOST")
DB_USER = os.getenv("RDS_DB_USER")
DB_PASSWORD = os.getenv("RDS_DB_PASSWORD")
DB_NAME = os.getenv("RDS_DB_NAME")

# 실 배포 환경으로 AWS RDS MYSQL 사용
try:
    db = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4"
    )

    cursor = db.cursor()

    # DB 테이블 생성 확인
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resume_feedback (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        resume_text TEXT,
        feedback_text TEXT,
        created_at DATETIME
    );
    """)

    db.commit()
    
except Exception as e:
    print(f"Database Connection Error: {e}")
    db = None
    cursor = None


# 요청 + 응답 모델
class ResumeInput(BaseModel):
    userId: int
    resumeContent: str
    
# 서버가 클라이언트한테로
class FeedbackResponse(BaseModel):
    feedback: str
    userId: int


# 프롬프트
system_message = """
#이력서를 피드백하는 에이전트 시스템 프롬프트 
... (중략: 시스템 프롬프트 내용 유지) ...
"""


# LLM 호출
def generate_feedback(resume_text: str) -> str:
    # client 객체 유무 체크 로직 유지
    if not client:
        return "API 키가 설정되지 않음"
    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"사용자가 제출한 이력서 내용입니다:\n\n{resume_text}"}
            ]
        )
        return response.output[0].content[0].text
    
    except Exception as e:
        print(f"LLM 호출 실패: {e}")
        raise HTTPException(status_code=500, detail="LLM 피드백 생성에 실패했습니다.")


# DB 저장
def save_feedback_to_rds(userId: int, resume_text: str, feedback: str) -> int:
    if not db or not cursor:
        print("DB 연결 오류로 인해 저장 실패.")
        raise HTTPException(status_code=500, detail="데이터베이스 연결 문제로 인해 저장에 실패했습니다.")
    try:
        now = datetime.now()
        sql = """
            INSERT INTO resume_feedback (user_id, resume_text, feedback_text, created_at)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql, (userId, resume_text, feedback, now))
        db.commit()
        return cursor.lastrowid
    except Exception as e:
        db.rollback()
        print(f"Database Save Error: {e}")
        raise HTTPException(status_code=500, detail="피드백 데이터베이스 저장에 실패했습니다.")


# FastAPI 엔드포인트
@resume_router.post("/resume/feedback", response_model=FeedbackResponse)
async def resume_feedback(req: ResumeInput):

    # OpenAI 호출 -> 피드백 생성
    feedback = generate_feedback(req.resumeContent)

    # DB에 저장 로직 추가
    save_feedback_to_rds(req.userId, req.resumeContent, feedback)
    
    # DB 저장 성공 후 피드백과 사용자 ID를 반환
    return FeedbackResponse(
        feedback=feedback,
        userId=req.userId
    )