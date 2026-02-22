from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import PyPDF2
import sqlite3
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os
import spacy
from spacy.matcher import PhraseMatcher

app = Flask(__name__)
CORS(app)

DB_FILE = "database.db"

# Initialize NLP
nlp = spacy.load("en_core_web_sm")

# Database setup
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS analysis
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 course_name TEXT,
                 major TEXT,
                 score REAL,
                 matched TEXT,
                 missing TEXT,
                 date TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Market Skills per Major with Levels
market_skills = {
    "IT": {
        "Basic": ["python", "programming", "sql", "data analysis"],
        "Intermediate": ["machine learning", "cloud computing", "database"],
        "Advanced": ["ai", "deep learning"]
    },
    "Business": {
        "Basic": ["communication","teamwork","problem solving","excel"],
        "Intermediate": ["project management","critical thinking","statistics"],
        "Advanced": ["leadership","strategic planning"]
    },
    "Healthcare": {
        "Basic": ["teamwork","communication","statistics"],
        "Intermediate": ["data analysis","critical thinking"],
        "Advanced": ["ai","advanced diagnostics"]
    },
    "Engineering": {
        "Basic": ["programming","problem solving","statistics"],
        "Intermediate": ["project management","database"],
        "Advanced": ["ai","advanced modeling"]
    }
}

# NLP Matcher
def build_matcher(skills):
    matcher = PhraseMatcher(nlp.vocab)
    patterns = [nlp(skill.lower()) for skill in skills]
    matcher.add("SKILLS", patterns)
    return matcher

def extract_skills_nlp(text, major):
    # يجمع كل المهارات بدون تصنيف
    skills = sum(market_skills[major].values(), [])
    matcher = build_matcher(skills)
    doc = nlp(text.lower())
    matches = matcher(doc)
    found = set()
    for match_id, start, end in matches:
        span = doc[start:end]
        found.add(span.text)
    return list(found)

def compute_missing_skills(text, major, expected_levels):
    # جمع المهارات المتوقعة حسب المستوى
    expected_skills = []
    for level in expected_levels:
        expected_skills.extend(market_skills[major].get(level, []))
    
    # استخراج المهارات الموجودة في النص
    matched = extract_skills_nlp(text, major)
    
    # Missing Skills الواقعية
    missing = list(set(expected_skills) - set(matched))
    return matched, missing

# PDF Reader
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

# Recommendations
def generate_recommendation(score, missing_skills):
    if score > 75:
        return "Excellent alignment with market demands."
    elif score > 50:
        return f"Good alignment, consider adding: {', '.join(missing_skills[:3])}"
    else:
        return f"Significant improvement needed, focus on: {', '.join(missing_skills)}"

# Routes
@app.route('/')
def home():
    return render_template("index.html", majors=list(market_skills.keys()))

@app.route('/analyze', methods=['POST'])
def analyze():
    major = request.form.get("major")
    course_name = request.form.get("course_name", "Unnamed Course")
    level = request.form.get("level", "Basic")  # Default Basic
    levels_map = {
        "Basic": ["Basic"],
        "Intermediate": ["Basic","Intermediate"],
        "Advanced": ["Basic","Intermediate","Advanced"]
    }
    expected_levels = levels_map.get(level, ["Basic"])

    text_input = request.form.get("text_input")
    file_input = request.files.get("pdf_file")

    if file_input and file_input.filename != "":
        text = extract_text_from_pdf(file_input)
    elif text_input and text_input.strip() != "":
        text = text_input
    else:
        return jsonify({"error": "No input provided"}), 400

    matched, missing = compute_missing_skills(text, major, expected_levels)
    score = round((len(matched)/len(sum([market_skills[major][lvl] for lvl in expected_levels], [])))*100,2)
    recommendation = generate_recommendation(score, missing)

    # Store in DB
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO analysis (course_name, major, score, matched, missing, date) VALUES (?,?,?,?,?,?)',
              (course_name, major, score, ",".join(matched), ",".join(missing), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return jsonify({
        "score": score,
        "matched": matched,
        "missing": missing,
        "recommendation": recommendation
    })

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM analysis ORDER BY date DESC')
    rows = c.fetchall()
    conn.close()
    return render_template("dashboard.html", analyses=rows)

# PDF Report
@app.route('/download_report/<int:analysis_id>')
def download_report(analysis_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT course_name, major, score, matched, missing, date FROM analysis WHERE id=?', (analysis_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return "Analysis not found", 404

    filename = f"SkillBridge_Report_{row[0].replace(' ','_')}.pdf"
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph(f"SkillBridge AI Report - Qassim University", styles["Title"]))
    elements.append(Spacer(1,12))
    elements.append(Paragraph(f"Course: {row[0]}", styles["Heading2"]))
    elements.append(Paragraph(f"Major: {row[1]}", styles["Normal"]))
    elements.append(Paragraph(f"Alignment Score: {row[2]}%", styles["Normal"]))
    elements.append(Paragraph(f"Matched Skills: {row[3]}", styles["Normal"]))
    elements.append(Paragraph(f"Missing Skills: {row[4]}", styles["Normal"]))
    elements.append(Paragraph(f"Recommendation: {generate_recommendation(row[2], row[4].split(','))}", styles["Normal"]))
    elements.append(Paragraph(f"Analysis Date: {row[5]}", styles["Normal"]))
    doc.build(elements)

    return app.send_static_file(filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))