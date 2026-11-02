import os
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import gspread
from google.oauth2.service_account import Credentials

BASE_DIR = Path(__file__).resolve().parent
RESULTS_FILE = BASE_DIR / "results.json"
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

QUESTION_POOLS = {
    "Hardware": [
        {"id": "hw_1", "question": "Which protocol is commonly used to transfer data securely over the web?", "options": ["HTTP", "HTTPS", "FTP"], "answer": "HTTPS"},
        {"id": "hw_2", "question": "Which language is commonly used to style a web page?", "options": ["HTML", "CSS", "Python"], "answer": "CSS"},
        {"id": "hw_3", "question": "What is the name of the Python framework commonly used for lightweight web apps?", "options": ["Flask", "Django", "FastAPI"], "answer": "Flask"},
        {"id": "hw_4", "question": "Which storage solution is often used for spreadsheet-style data in the cloud?", "options": ["Google Sheets", "MongoDB", "SQLite"], "answer": "Google Sheets"},
        {"id": "hw_5", "question": "What does API stand for?", "options": ["Application Programming Interface", "Automated Program Integration", "Application Process Index"], "answer": "Application Programming Interface"},
        {"id": "hw_6", "question": "Which HTML element is usually used to create a clickable button?", "options": ["<button>", "<link>", "<input>"], "answer": "<button>"},
    ],
    "Software": [
        {"id": "sw_1", "question": 'What is the effect of the "break" statement when it is used inside a "for" loop?', "options": ["It immediately terminates the execution of the for loop and continues the program with the statement that follows it.", "It jumps directly to the next iteration of the loop, ignoring the rest of the current loop body.", "It completely stops the execution of the C program."], "answer": "It immediately terminates the execution of the for loop and continues the program with the statement that follows it."},
        {"id": "sw_2", "question": "Which operator is used to set bit 3 of a register?", "options": ["reg |= (1 << 3);", "reg &= (1 << 3);", "reg ^= (1 << 3);"], "answer": "reg |= (1 << 3);"},
        {"id": "sw_3", "question": "What is the result of the expression below?\n\nuint8_t x = 0x55;\nx ^= 0xFF;", "options": ["0x00", "0xAA", "0x55"], "answer": "0xAA"},
        {"id": "sw_4", "question": "Which statement about stack usage in embedded systems is true?", "options": ["Stack size is unlimited", "Stack overflow cannot occur in C", "Recursion may cause stack overflow"], "answer": "Recursion may cause stack overflow"},
        {"id": "sw_5", "question": "What is the primary purpose of a Watchdog Timer (WDT)?", "options": ["Measure execution time of Watchdog runnables", "Manage the timer used by the Watchdog SW driver", "Reset the system if software becomes unresponsive"], "answer": "Reset the system if software becomes unresponsive"},
        {"id": "sw_6", "question": "What is the value of x after executing the code?\n\nuint8_t x = 0x0F;\nx <<= 2;", "options": ["0x11", "0x3C", "0xF0"], "answer": "0x3C"},
        {"id": "sw_7", "question": "Which operation clears bit 5 in a register?", "options": ["reg |= (1 << 5);", "reg ^= (1 << 5);", "reg &= ~(1 << 5);"], "answer": "reg &= ~(1 << 5);"},
        {"id": "sw_8", "question": 'What is the output?\n\nuint8_t a = 5;\nuint8_t b = 3;\n\nprintf("%d", a & b);', "options": ["1", "7", "8"], "answer": "1"},
        {"id": "sw_9", "question": "What does this code do?\n\nuint32_t timeout = 1000;\n\nwhile(timeout--)\n{\n}", "options": ["Infinite loop", "Busy wait delay loop", "Memory initialization"], "answer": "Busy wait delay loop"},
        {"id": "sw_10", "question": "Which is generally safer for embedded safety-critical systems?", "options": ["Dynamic memory allocation during runtime", "Static memory allocation determined at compile time", "Safe malloc / free functions"], "answer": "Static memory allocation determined at compile time"},
        {"id": "sw_11", "question": 'What is wrong with the following code?\n\nchar *str;\n\nstrcpy(str, "Hello");', "options": ["Nothing - the code is correct", "str does not point to valid memory", "Missing volatile keyword for str"], "answer": "str does not point to valid memory"},
    ],
    "FuSa": [
        {"id": "fusa_1", "question": "What does ROI stand for?", "options": ["Return on Investment", "Rate of Income", "Revenue over Inventory"], "answer": "Return on Investment"},
        {"id": "fusa_2", "question": "What is a budget primarily used for?", "options": ["Planning and controlling spending", "Hiring staff", "Writing emails"], "answer": "Planning and controlling spending"},
        {"id": "fusa_3", "question": "Which term describes the total money coming into a business?", "options": ["Revenue", "Expense", "Liability"], "answer": "Revenue"},
        {"id": "fusa_4", "question": "What is the purpose of operational KPIs?", "options": ["To track performance and efficiency", "To design logos", "To pay suppliers"], "answer": "To track performance and efficiency"},
        {"id": "fusa_5", "question": "Which process helps a business check if its cash inflows cover its outflows?", "options": ["Cash flow analysis", "Market research", "Branding"], "answer": "Cash flow analysis"},
        {"id": "fusa_6", "question": "What is a fixed cost?", "options": ["A cost that stays fairly constant over time", "A one-time sale", "A customer refund"], "answer": "A cost that stays fairly constant over time"},
    ],
    "Cyber Security": [
        {"id": "cyber_1", "question": "What is the main difference between encryption and hashing?", "options": ["Encryption is only used for passwords, while hashing is used for files.", "Encryption is designed to be reversible with the correct key, while hashing is designed to be one-way.", "Hashing is a stronger form of encryption that does not require a key."], "answer": "Encryption is designed to be reversible with the correct key, while hashing is designed to be one-way."},
        {"id": "cyber_2", "question": "In symmetric encryption, what is used to encrypt and decrypt the data?", "options": ["Two completely unrelated passwords.", "The same secret key.", "No key is required."], "answer": "The same secret key."},
        {"id": "cyber_3", "question": "In asymmetric cryptography, which keys are normally used?", "options": ["Two public keys.", "A public key and a private key.", "One password and one username."], "answer": "A public key and a private key."},
        {"id": "cyber_4", "question": "Which statement best describes a cryptographic hash function such as SHA-256?", "options": ["It encrypts information that can later be decrypted.", "It creates a fixed-size digest from input data and is designed to be one-way.", "It generates a public/private key pair."], "answer": "It creates a fixed-size digest from input data and is designed to be one-way."},
        {"id": "cyber_5", "question": "What can a digital signature primarily help verify?", "options": ["That file has been encrypted.", "That nobody is able to copy the file.", "The authenticity and integrity of the signed data."], "answer": "The authenticity and integrity of the signed data."},
    ],
    "System": [
        {"id": "sys_1", "question": "What does NPS stand for?", "options": ["Net Promoter Score", "New Product Survey", "Network Performance Standard"], "answer": "Net Promoter Score"},
        {"id": "sys_2", "question": "What is the main purpose of customer feedback?", "options": ["To understand needs and improve service", "To increase taxes", "To reduce office time"], "answer": "To understand needs and improve service"},
        {"id": "sys_3", "question": "Which metric helps measure how quickly a company responds to customers?", "options": ["Response time", "Inventory count", "Operating margin"], "answer": "Response time"},
        {"id": "sys_4", "question": "What is a common goal of customer support?", "options": ["Resolve problems efficiently and politely", "Train employees for sales", "Increase manufacturing speed"], "answer": "Resolve problems efficiently and politely"},
        {"id": "sys_5", "question": "Which experience element is most directly tied to customer satisfaction?", "options": ["Service quality", "Office layout", "Accounting rules"], "answer": "Service quality"},
        {"id": "sys_6", "question": "What is the benefit of personalization in customer experience?", "options": ["It makes interactions more relevant and effective", "It shortens product lines", "It lowers staff pay"], "answer": "It makes interactions more relevant and effective"},
    ],
    "Quality": [
        {"id": "q_1", "question": 'What does "quality" mean for a product or service?', "options": ["To be the most expensive", "To fulfill the client's requirements and expectations", "To receive no complaints"], "answer": "To fulfill the client's requirements and expectations"},
        {"id": "q_2", "question": "You find a problem in a product. What is the best approach?", "options": ["If the client didn't notice it, you ignore it", "You quickly fix it without looking for the root cause", "You identify the root cause, then take the appropiate measures to prevent it"], "answer": "You identify the root cause, then take the appropiate measures to prevent it"},
        {"id": "q_3", "question": "Who is responsible for quality in an organisation?", "options": ["Only the Quality department", "Managers only", "Everyone involved in developing the product or service"], "answer": "Everyone involved in developing the product or service"},
        {"id": "q_4", "question": "What is more efficient?", "options": ["To detect the defects at the end", "To prevent the appearance of defects", "To repair the product after delivery"], "answer": "To prevent the appearance of defects"},
        {"id": "q_5", "question": "Why it's important to find the cause of a problem?", "options": ["To idenitfy the responsible person", "To prevent it's reoccurence", "To fill in a report"], "answer": "To prevent it's reoccurence"},
        {"id": "q_6", "question": "A client reports a problem that appears very rearly. What should we do?", "options": ["Ignore it because it's rare", "Investigate the problem and the associated risk", "Wait for it to happen again"], "answer": "Investigate the problem and the associated risk"},
        {"id": "q_7", "question": "Which of the following is an example of continuous improvement?", "options": ["Repeating the same method regardless of the results", "Analyse the results and improve the way of work", "Changing the process every week"], "answer": "Analyse the results and improve the way of work"},
        {"id": "q_8", "question": "Why clear requirements are important to have before developing a product?", "options": ["They reduce the risk of misunderstandings and errors", "They completely eliminate the need for testing", "The product will automatically be cheaper"], "answer": "They reduce the risk of misunderstandings and errors"},
        {"id": "q_9", "question": "A product passes all the defined tests. Does this automatically mean it is qualitative?", "options": ["Yes, always", "Not necessarily. Tests must cover all requirements and relevant use cases", "Yes, if testing was fast"], "answer": "Not necessarily. Tests must cover all requirements and relevant use cases"},
        {"id": "q_10", "question": "Which statement best describes quality culture?", "options": ["Quality will find all problems", "If it works, there's no need for quality checks", "Each of us contributes to problem prevention and product improvement"], "answer": "Each of us contributes to problem prevention and product improvement"},
    ],
}

QUESTION_COUNT_PER_CATEGORY = 3
CATEGORY_ORDER = list(QUESTION_POOLS.keys())

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "quiz-secret-key")


def build_category_quiz():
    selected_questions = []
    for category_name in CATEGORY_ORDER:
        pool = QUESTION_POOLS[category_name]
        picked = random.sample(pool, k=min(len(pool), QUESTION_COUNT_PER_CATEGORY))
        selected_questions.append({
            "category": category_name,
            "questions": picked,
        })
    return selected_questions


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
    session["quiz_state"] = build_category_quiz()
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

    page = quiz_state[page_num]
    return render_template(
        "quiz.html",
        name=participant["name"],
        email=participant["email"],
        phone=participant["phone"],
        category=page["category"],
        page_num=page_num,
        total_pages=len(quiz_state),
        is_last_page=(page_num == len(quiz_state) - 1),
        questions=page["questions"],
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

    page = quiz_state[page_num]
    score = 0
    for question in page["questions"]:
        selected_answer = request.form.get(f"q_{question['id']}")
        if selected_answer == question["answer"]:
            score += 1

    session_scores = session.get("scores", {})
    session_scores[str(page_num)] = {
        "category": page["category"],
        "score": score,
        "total_questions": len(page["questions"]),
    }
    session["scores"] = session_scores

    if page_num < len(quiz_state) - 1:
        return redirect(url_for("quiz_category_page", page_num=page_num + 1))

    total_score = 0
    total_questions = 0
    for index, category_page in enumerate(quiz_state):
        score_data = session_scores.get(str(index), {})
        total_score += score_data.get("score", 0)
        total_questions += score_data.get("total_questions", len(category_page["questions"]))

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
    category_scores = []
    total_score = 0
    total_questions = 0
    session_scores = session.get("scores", {})

    for index, page in enumerate(quiz_state):
        score_data = session_scores.get(str(index), {})
        score = score_data.get("score", 0)
        page_total = score_data.get("total_questions", len(page["questions"]))
        category_scores.append({
            "category": page["category"],
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
        category_scores=category_scores,
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
