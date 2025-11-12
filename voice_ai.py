import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai

# ==========================================================
# 1️⃣ 환경 변수 로드 및 OpenAI API 키 설정
# ==========================================================
# .env 파일에서 OPENAI_API_KEY를 읽어옴 (같은 디렉토리에 있어야 함)
# 예시:  OPENAI_API_KEY=sk-xxxxxx
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ==========================================================
# 2️⃣ Flask 앱 설정 및 CORS 허용
# ==========================================================
# Flask 인스턴스 생성
app = Flask(__name__)

# CORS(Cross-Origin Resource Sharing) 허용
# 프론트엔드(React, Vue 등)에서 다른 포트로 접근할 수 있게 해줌
CORS(app)

# ==========================================================
# 3️⃣ 핵심 함수: OpenAI API를 호출해 면접 질문 생성
# ==========================================================
def generate_interview_questions(major, job_title):
    """
    학과(major)와 직무(job_title)를 기반으로 OpenAI API를 호출하여
    면접 질문 5개를 리스트 형태로 반환하는 함수.
    """
    
    # GPT에 보낼 프롬프트(명령문) 구성
    prompt = f"""
    당신은 전문 면접관입니다. 지원자가 **{major}** 학과를 졸업하고 **{job_title}** 직무에 지원한다고 가정합니다.
    이 지원자를 평가하기 위한 전문적인 면접 질문 5가지를 **리스트 형태로** 생성해주세요.
    질문은 한 줄에 하나씩 번호 없이 출력되어야 합니다.
    """

    try:
        # OpenAI ChatGPT API 호출
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # 모델 지정
            messages=[
                {"role": "system", "content": "사용자의 요청에 따라 전문 면접 질문을 생성하는 AI입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7  # 창의성 조절 (낮을수록 보수적, 높을수록 다양)
        )

        # 응답 텍스트 추출
        questions_text = response.choices[0].message.content.strip()

        # 줄 단위로 분리하여 리스트로 반환
        return [q.strip() for q in questions_text.split('\n') if q.strip()]

    except Exception as e:
        # API 호출 실패 시 콘솔에 에러 메시지 출력
        print(f"⚠️ OpenAI API 호출 중 오류 발생: {e}")
        return None

# ==========================================================
# 4️⃣ Flask API 엔드포인트 정의 (프론트 요청 수신)
# ==========================================================
@app.route('/api/questions', methods=['POST'])
def get_questions():
    """
    프론트엔드에서 전달받은 JSON 데이터를 기반으로
    학과와 직무 정보를 추출해 질문을 생성하고 JSON으로 응답.
    """
    # JSON 데이터 받기
    data = request.json
    major = data.get('major')         # 학과 정보
    job_title = data.get('job_title') # 직무 정보

    # 필수 데이터 검증
    if not major or not job_title:
        return jsonify({"error": "학과와 직무 정보를 모두 제공해야 합니다."}), 400

    # OpenAI API 호출
    questions = generate_interview_questions(major, job_title)

    # 성공 시: 질문 리스트 반환 / 실패 시: 에러 메시지 반환
    if questions:
        return jsonify({"questions": questions}), 200
    else:
        return jsonify({"error": "면접 질문 생성에 실패했습니다."}), 500

# ==========================================================
# 5️⃣ Flask 서버 실행
# ==========================================================
if __name__ == "__main__":
    # 0.0.0.0 : 외부 접근 허용 / 포트 5002에서 실행
    app.run(host="0.0.0.0", port=5002, debug=True)