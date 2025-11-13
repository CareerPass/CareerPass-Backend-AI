import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai

# 1. 환경 변수(.env) 로드 및 API 키 설정
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 2. Flask 앱 & CORS
app = Flask(__name__)

# ✅ JSON을 UTF-8 한글 그대로 내보내기 (이스케이프 방지용)
app.config["JSON_AS_ASCII"] = False          # 예전 방식
app.json.ensure_ascii = False                # Flask 2.x에서 확실하게 적용

CORS(app)

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
        resp = openai.chat.completions.create(
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
@app.route("/api/questions", methods=["POST"])
def get_questions():
    data = request.json or {}
    major = data.get("major")
    job_title = data.get("job_title")
    cover_letter = data.get("cover_letter", "")

    if not major or not job_title:
        return jsonify({"error": "학과(major)와 직무(job_title)를 모두 제공해야 합니다."}), 400

    qs = generate_interview_questions(major, job_title, cover_letter)
    if qs:
        return jsonify({"questions": qs}), 200
    return jsonify({"error": "면접 질문 생성에 실패했습니다."}), 500

# 5. 서버 실행 (여기 없으면 python question_ai.py 실행 시 바로 종료됨)
if __name__ == "__main__":
    print("✅ Flask question_ai 서버 시작: http://localhost:5002")
    app.run(host="0.0.0.0", port=5002, debug=True)