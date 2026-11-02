import os
import json
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import gspread
from google.oauth2.service_account import Credentials

BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "results.json"
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

STATIC_QUESTIONS = [
    {
        "id": "q_1",
        "question": "Which protocol is commonly used to transfer data securely over the web?",
        "options": ["HTTP", "HTTPS", "FTP"],
        "answer": "HTTPS",
    },
    {
        "id": "q_2",
        "question": "What does API stand for?",
        "options": [
            "Application Programming Interface",
            "Automated Program Integration",
            "Application Process Index",
        ],
        "answer": "Application Programming Interface",
    },
    {
        "id": "q_3",
        "question": "Which language is commonly used to style a web page?",
        "options": ["HTML", "CSS", "Python"],
        "answer": "CSS",
    },
    {
        "id": "q_4",
        "question": "What is the name of the Python framework commonly used for lightweight web apps?",
        "options": ["Flask", "Django", "FastAPI"],
        "answer": "Flask",
    },
    {
        "id": "q_5",
        "question": "What does ROI stand for?",
        "options": ["Return on Investment", "Rate of Income", "Revenue over Inventory"],
        "answer": "Return on Investment",
    },
    {
        "id": "q_6",
        "question": "Which operation clears bit 5 in a register?",
        "options": ["reg |= (1 << 5);", "reg ^= (1 << 5);", "reg &= ~(1 << 5);"],
        "answer": "reg &= ~(1 << 5);",
    },
    {
        "id": "q_7",
        "question": "In symmetric encryption, what is used to encrypt and decrypt the data?",
        "options": ["Two completely unrelated passwords.", "The same secret key.", "No key is used."],
        "answer": "The same secret key.",
    },
    {
        "id": "q_8",
        "question": "What does quality mean for a product or service?",
        "options": [
            "To be the most expensive",
            "To fulfill the client's requirements and expectations",
            "To receive low demand",
        ],
        "answer": "To fulfill the client's requirements and expectations",
    },
]

BADGE_TEXTS = [
    "1. SYSTEM REQUIREMENTS",
    "2. SOFTWARE REQUIREMENTS",
    "3. SOFTWARE ARCHITECTURE",
    "4. SOFTWARE INTEGRATION",
    "5. SOFTWARE TEST",
    "6. SYSTEM TEST",
    "7. HARDWARE LAB",
    "8. FINAL CHALLENGE 🚨",
]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "quiz-secret-key")


def build_question_quiz():
    return STATIC_QUESTIONS


def get_quiz_session():
    participant = session.get("participant")
    quiz_state = session.get("quiz_state")
    if not participant or not isinstance(quiz_state, list):
        return None
    return participant, quiz_state


def get_sheet():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        raise FileNotFoundError("GOOGLE_APPLICATION_CREDENTIALS is not set")

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1


def ensure_headers(sheet):
    if not sheet.row_values(1):
        sheet.append_row(["name", "email", "phone", "score", "submitted_at"])
    elif sheet.row_values(1) != ["name", "email", "phone", "score", "submitted_at"]:
        sheet.insert_row(["name", "email", "phone", "score", "submitted_at"], 1)
        sheet.delete_row(2)


def save_quiz_result(name, email, phone, score):
    if not name or not email or not phone or not score:
        raise ValueError("Missing required fields: name, email, phone and score")

    submitted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    results = []
    if RESULTS_FILE.exists():
        try:
            with RESULTS_FILE.open("r", encoding="utf-8") as file:
                existing_results = json.load(file)
            if isinstance(existing_results, list):
                results = existing_results
        except (json.JSONDecodeError, OSError):
            results = []

    results.append({
        "name": name,
        "email": email,
        "phone": phone,
        "score": score,
        "submitted_at": submitted_at,
    })

    with RESULTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)

    if not GOOGLE_SHEET_ID:
        raise ValueError("GOOGLE_SHEET_ID is not set")

    sheet = get_sheet()
    ensure_headers(sheet)
    sheet.append_row([name, email, phone, score, submitted_at])


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/quiz")
def quiz_start():
    name = request.args.get("name", "").strip()
    email = request.args.get("email", "").strip()
    phone = request.args.get("phone", "").strip()

    if not name or not email or not phone:
        return redirect(url_for("index"))

    session["participant"] = {"name": name, "email": email, "phone": phone}
    session["quiz_state"] = build_question_quiz()
    session["scores"] = {}
    session["result_saved"] = False
    session["save_error"] = None
    return redirect(url_for("quiz_category_page", page_num=0))


@app.get("/quiz/page/<int:page_num>")
def quiz_category_page(page_num):
    data = get_quiz_session()
    if data is None:
        return redirect(url_for("index"))

    participant, quiz_state = data
    if page_num < 0 or page_num >= len(quiz_state):
        return redirect(url_for("quiz_results"))

    question = quiz_state[page_num]
    badge_text = BADGE_TEXTS[page_num] if page_num < len(BADGE_TEXTS) else f"Page {page_num + 1}"
    return render_template(
        "quiz.html",
        name=participant["name"],
        email=participant["email"],
        phone=participant["phone"],
        page_num=page_num,
        total_pages=len(quiz_state),
        is_last_page=(page_num == len(quiz_state) - 1),
        question=question,
        badge_text=badge_text,
    )


@app.post("/quiz/page")
def submit_quiz_page():
    data = get_quiz_session()
    if data is None:
        return redirect(url_for("index"))

    participant, quiz_state = data
    page_num = int(request.form.get("page_num", 0))
    if page_num < 0 or page_num >= len(quiz_state):
        return redirect(url_for("index"))

    question = quiz_state[page_num]
    score = 0
    selected_answer = request.form.get(f"q_{question['id']}")
    if selected_answer == question["answer"]:
        score = 1

    session_scores = session.get("scores", {})
    session_scores[str(page_num)] = {
        "score": score,
        "total_questions": 1,
    }
    session["scores"] = session_scores

    if page_num < len(quiz_state) - 1:
        return redirect(url_for("quiz_category_page", page_num=page_num + 1))

    total_score = 0
    total_questions = 0
    for index, _ in enumerate(quiz_state):
        score_data = session_scores.get(str(index), {})
        total_score += score_data.get("score", 0)
        total_questions += score_data.get("total_questions", 1)

    final_score = f"{total_score} / {total_questions}"
    try:
        save_quiz_result(participant["name"], participant["email"], participant["phone"], final_score)
        session["result_saved"] = True
        session["save_error"] = None
    except Exception as exc:
        session["result_saved"] = False
        session["save_error"] = str(exc)

    return redirect(url_for("quiz_results"))


@app.get("/quiz/results")
def quiz_results():
    data = get_quiz_session()
    if data is None:
        return redirect(url_for("index"))

    participant, quiz_state = data
    question_scores = []
    total_score = 0
    total_questions = 0
    session_scores = session.get("scores", {})

    for index, question in enumerate(quiz_state):
        score_data = session_scores.get(str(index), {})
        score = score_data.get("score", 0)
        page_total = score_data.get("total_questions", 1)
        question_scores.append({
            "label": f"Question {index + 1}",
            "score": score,
            "total": page_total,
        })
        total_score += score
        total_questions += page_total

    if not session.get("result_saved"):
        final_score = f"{total_score} / {total_questions}"
        try:
            save_quiz_result(participant["name"], participant["email"], participant["phone"], final_score)
            session["result_saved"] = True
            session["save_error"] = None
        except Exception as exc:
            session["result_saved"] = False
            session["save_error"] = str(exc)

    return render_template(
        "results.html",
        name=participant["name"],
        email=participant["email"],
        phone=participant["phone"],
        question_scores=question_scores,
        total_score=total_score,
        total_questions=total_questions,
        save_error=session.get("save_error"),
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/submit")
def submit_score():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    email = str(payload.get("email") or "").strip()
    phone = str(payload.get("phone") or "").strip()
    score = str(payload.get("score") or "").strip()

    try:
        save_quiz_result(name, email, phone, score)
    except Exception as exc:
        return jsonify({"error": f"Failed to save to Google Sheet: {exc}"}), 500

    return jsonify({
        "message": "Score saved successfully",
        "name": name,
        "score": score,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
