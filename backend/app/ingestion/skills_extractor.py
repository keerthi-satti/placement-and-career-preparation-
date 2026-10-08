import re


# Common technical skills
KNOWN_SKILLS = [
    "Python",
    "Java",
    "C",
    "C++",
    "C#",
    "HTML",
    "CSS",
    "JavaScript",
    "React",
    "Node.js",
    "SQL",
    "MySQL",
    "MongoDB",
    "PostgreSQL",
    "Git",
    "GitHub",
    "Machine Learning",
    "Deep Learning",
    "TensorFlow",
    "PyTorch",
    "NLP",
    "AWS",
    "Azure",
]


def extract_skills(resume_text):
    """
    Extract known technical skills from resume text.
    """

    found_skills = []

    for skill in KNOWN_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"

        if re.search(pattern, resume_text, re.IGNORECASE):
            found_skills.append(skill)

    return found_skills