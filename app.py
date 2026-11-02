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
        "question": "The BMS must protect the battery. What would interest you most?",
        "options": [
            "A. Define how the complete system should work. 🧠",
            "B. Define how the system components should communicate. 🔗",
            "C. Think about how each requirement could be verified. 🧪",
            "D. Test the complete BMS in real-life scenarios. 🚗",
            "E. Work with the battery, sensors and lab equipment. 🔧",
        ],
    },
    {
        "id": "q_2",
        "question": "A cell gets too hot. What would you most like to work on?",
        "options": [
            "A. Define the software architecture for this function. 🧠",
            "B. Define how software modules exchange temperature data. 🔗",
            "C. Create tests to verify the temperature behavior. 🧪",
            "D. Check how the complete BMS reacts to overheating. 🚗",
            "E. Measure and investigate the temperature signal. 🔧",
        ],
    },
    {
        "id": "q_3",
        "question": "How would you approach designing the BMS software?",
        "options": [
            "A. Define the structure and how software components interact. 🧠",
            "B. Make sure interfaces between components work correctly. 🔗",
            "C. Think about how each component can be tested. 🧪",
            "D. Think about complete BMS test scenarios. 🚗",
            "E. Understand how software connects to the hardware. 🔧",
        ],
    },
    {
        "id": "q_4",
        "question": "Two BMS software modules are not communicating correctly. What interests you?",
        "options": [
            "A. Review whether the overall software architecture is correct. 🧠",
            "B. Investigate interfaces, dependencies and configurations. 🔗",
            "C. Create tests to reproduce and investigate the issue. 🧪",
            "D. Check how the issue affects the complete BMS. 🚗",
            "E. Check the related hardware signals and connections. 🔧",
        ],
    },
    {
        "id": "q_5",
        "question": "The BMS software is ready. What would you enjoy doing most?",
        "options": [
            "A. Review whether the design supports the requirements. 🧠",
            "B. Check whether all software components are integrated. 🔗",
            "C. Design and execute software tests. 🧪",
            "D. Test the BMS in complete end-to-end scenarios. 🚗",
            "E. Prepare the hardware setup needed for testing. 🔧",
        ],
    },
    {
        "id": "q_6",
        "question": "The BMS must detect and handle an overheating cell. What interests you most?",
        "options": [
            "A. Analyze the architecture behind this function. 🧠",
            "B. Check how the software components communicate. 🔗",
            "C. Verify the software behavior through testing. 🧪",
            "D. Test the complete scenario from detection to protection. 🚗",
            "E. Monitor the hardware signals during the test. 🔧",
        ],
    },
    {
        "id": "q_7",
        "question": "A temperature signal looks wrong. What would you check first?",
        "options": [
            "A. How the signal is handled by the software architecture. 🧠",
            "B. Whether the interface and configuration are correct. 🔗",
            "C. Whether the software interprets the signal correctly. 🧪",
            "D. How the signal affects the complete BMS. 🚗",
            "E. The signal, connections and measurement equipment. 🔧",
        ],
    },
    {
        "id": "q_8",
        "question": "The BMS detects high temperature, but protection is not activated. What do you do?",
        "options": [
            "A. Analyze the architecture and function flow. 🧠",
            "B. Check communication between the software components. 🔗",
            "C. Reproduce the issue with software tests. 🧪",
            "D. Test the complete BMS scenario end-to-end. 🚗",
            "E. Check the hardware setup and physical signals. 🔧",
        ],
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

RESULT_TEXTS = {
    "A": {
        "title": "🧠 Software Architect",
        "description": "You like seeing the big picture and designing how everything fits together.",
    },
    "B": {
        "title": "🔗 Software Integration Engineer",
        "description": "You like connecting the pieces. You enjoy understanding interfaces, investigating problems and making different components work together.",
    },
    "C": {
        "title": "🧪 Software Test Engineer",
        "description": "You like finding problems and proving that software works as expected.",
    },
    "D": {
        "title": "🚗 System Test Engineer",
        "description": "You like seeing how the complete system behaves in real-life scenarios.",
    },
    "E": {
        "title": "🔧 Hardware Lab Technician",
        "description": "You like working hands-on with hardware, measurements and test equipment.",
    },
}

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


def parse_answer_letter(selected_value):
    if selected_value is None:
        return ""
    value = str(selected_value).strip()
    if not value:
        return ""
    if "." in value:
        value = value.split(".", 1)[0]
    letter = value[0].upper()
    return letter if letter.isalpha() else ""


def get_winner_letter(counts):
    letter_order = ["A", "B", "C", "D", "E"]
    return max(letter_order, key=lambda letter: (counts.get(letter, 0), -letter_order.index(letter)))


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
    selected_answer = request.form.get(f"q_{question['id']}")
    selected_letter = parse_answer_letter(selected_answer)

    session_scores = session.get("scores", {})
    session_scores[str(page_num)] = {
        "letter": selected_letter,
        "total_questions": 1,
    }
    session["scores"] = session_scores

    if page_num < len(quiz_state) - 1:
        return redirect(url_for("quiz_category_page", page_num=page_num + 1))

    counts = {letter: 0 for letter in ["A", "B", "C", "D", "E"]}
    for index, _ in enumerate(quiz_state):
        score_data = session_scores.get(str(index), {})
        letter = score_data.get("letter", "")
        if letter in counts:
            counts[letter] += 1

    winner_letter = get_winner_letter(counts)
    summary = ", ".join(f"{letter}: {counts[letter]}" for letter in ["A", "B", "C", "D", "E"])
    try:
        save_quiz_result(participant["name"], participant["email"], participant["phone"], summary)
        session["result_saved"] = True
        session["save_error"] = None
        session["winner_letter"] = winner_letter
    except Exception as exc:
        session["result_saved"] = False
        session["save_error"] = str(exc)
        session["winner_letter"] = winner_letter

    return redirect(url_for("quiz_results"))


@app.get("/quiz/results")
def quiz_results():
    data = get_quiz_session()
    if data is None:
        return redirect(url_for("index"))

    participant, quiz_state = data
    counts = {letter: 0 for letter in ["A", "B", "C", "D", "E"]}
    session_scores = session.get("scores", {})

    for index, _ in enumerate(quiz_state):
        score_data = session_scores.get(str(index), {})
        letter = score_data.get("letter", "")
        if letter in counts:
            counts[letter] += 1

    winner_letter = session.get("winner_letter") or get_winner_letter(counts)
    winner_info = RESULT_TEXTS.get(winner_letter, RESULT_TEXTS["A"])
    answer_counts = [{"letter": letter, "count": counts[letter]} for letter in ["A", "B", "C", "D", "E"]]

    if not session.get("result_saved"):
        summary = ", ".join(f"{letter}: {counts[letter]}" for letter in ["A", "B", "C", "D", "E"])
        try:
            save_quiz_result(participant["name"], participant["email"], participant["phone"], summary)
            session["result_saved"] = True
            session["save_error"] = None
            session["winner_letter"] = winner_letter
        except Exception as exc:
            session["result_saved"] = False
            session["save_error"] = str(exc)
            session["winner_letter"] = winner_letter

    return render_template(
        "results.html",
        name=participant["name"],
        email=participant["email"],
        phone=participant["phone"],
        answer_counts=answer_counts,
        winner_letter=winner_letter,
        winner_title=winner_info["title"],
        winner_description=winner_info["description"],
        total_questions=len(quiz_state),
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
