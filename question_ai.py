import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai

# 1. 환경 변수(.env) 로드 및 API 키 설정 (변화 없음)
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY") 

# 2. Flask 웹 서버 설정 (변화 없음)
app = Flask(__name__)
CORS(app) 

# 3. OpenAI에 질문을 요청하는 핵심 함수 (수정 1: cover_letter 인자 추가)
def generate_interview_questions(major, job_title, cover_letter=""): 
    """학과, 직무, (선택적으로) 자소서 정보를 받아 OpenAI API를 호출하여 질문 리스트를 반환합니다."""
    
    # AI에게 줄 기본 프롬프트(명령)를 구성합니다.
    base_prompt = f"""
    당신은 전문 면접관입니다. 지원자가 **{major}** 학과를 졸업하고 **{job_title}** 직무에 지원한다고 가정합니다.
    """
    
    # 자소서 내용이 있으면 프롬프트에 추가합니다.
    if cover_letter and cover_letter.strip():
        # 자소서 내용이 있을 경우, 자소서를 바탕으로 심층 질문을 포함하여 총 7개의 질문을 생성하도록 지시합니다.
        base_prompt += f"""
        아래 지원자의 자기소개서(자소서) 내용을 참고하여, 자소서에서 파생되는 심층 질문 4가지와 직무 역량 관련 질문 3가지를 포함하여 **총 7가지**의 면접 질문을 **리스트 형태로** 생성해주세요.

        --- 자기소개서 내용 ---
        {cover_letter}
        --- 자기소개서 내용 ---
        """
    else:
        # 자소서 내용이 없을 경우, 기존대로 5가지 질문을 생성하도록 지시합니다.
        base_prompt += f"""
        이 지원자를 평가하기 위한 전문적인 면접 질문 5가지를 **리스트 형태로** 생성해주세요.
        """
        
    # 공통 지시사항 추가
    base_prompt += "\n질문은 한 줄에 하나씩 번호 없이 출력되어야 합니다."
    
    prompt = base_prompt
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": "사용자의 요청과 자소서 내용을 바탕으로 전문 면접 질문을 생성하는 AI입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        questions_text = response.choices[0].message.content.strip()
        return [q.strip() for q in questions_text.split('\n') if q.strip()]

    except Exception as e:
        print(f"API 호출 중 오류 발생: {e}")
        return None

# 4. 프론트엔드와 연결되는 API 엔드포인트 (주소) 설정 (수정 2: cover_letter 데이터 받기)
@app.route('/api/questions', methods=['POST'])
def get_questions():
    data = request.json
    major = data.get('major')
    job_title = data.get('job_title')
    # 자소서 텍스트를 받습니다. 데이터가 없으면 빈 문자열('')을 사용합니다.
    cover_letter = data.get('cover_letter', '') 

    if not major or not job_title:
        return jsonify({"error": "학과와 직무 정보를 모두 제공해야 합니다."}), 400

    # 자소서 인자를 포함하여 함수 호출
    questions = generate_interview_questions(major, job_title, cover_letter) 

    if questions:
        return jsonify({"questions": questions}), 200
    else:
        return jsonify({"error": "면접 질문 생성에 실패했습니다."}), 500