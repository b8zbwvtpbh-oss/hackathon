from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# قائمة المهارات المهمة في سوق العمل مرتبة حسب الأولوية
skills_db = [
    "python",
    "sql",
    "data analysis",
    "machine learning",
    "javascript",
    "html",
    "css",
    "react",
    "flask",
    "django",
    "cloud computing",
    "git",
    "docker",
    "project management",
    "communication",
    "problem solving",
    "critical thinking",
    "data visualization"
]

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/analyze', methods=['POST'])
def analyze():
    text = request.json.get('text', '').lower()

    found_skills = []
    missing_skills = []

    # تحقق من وجود كل مهارة في النص
    for skill in skills_db:
        if skill in text:
            found_skills.append(skill)
        else:
            missing_skills.append(skill)

    # حساب نسبة التطابق
    score = round((len(found_skills) / len(skills_db)) * 100, 2)

    # ترتيب النتائج حسب أهمية المهارات
    found_skills.sort(key=lambda x: skills_db.index(x))
    missing_skills.sort(key=lambda x: skills_db.index(x))

    return jsonify({
        "found_skills": found_skills,
        "missing_skills": missing_skills,
        "match_percentage": score
    })

if __name__ == '__main__':
    app.run(debug=True)