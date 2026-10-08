from pathlib import Path
from reportlab.pdfgen import canvas


OUTPUT_DIR = Path(__file__).parent


SAMPLES = [
    {
        "filename": "resume_01_standard.pdf",
        "name": "Aarav Kumar",
        "projects": [
            "Expense Tracker — Python | Flask | SQLite",
            "Weather Dashboard — HTML | CSS | JavaScript",
        ],
        "links": [
            "https://github.com/aarav/expense-tracker",
            "https://github.com/aarav/weather-dashboard",
        ],
    },
    {
        "filename": "resume_02_no_repo.pdf",
        "name": "Meera Sharma",
        "projects": [
            "Student Management System — Java | OOP",
            "Library Management System — Java | MySQL",
        ],
        "links": [],
    },
    {
        "filename": "resume_03_single_repo.pdf",
        "name": "Rahul Verma",
        "projects": [
            "Portfolio Website — HTML | CSS | JavaScript",
        ],
        "links": [
            "https://github.com/rahul/portfolio",
        ],
    },
    {
        "filename": "resume_04_three_projects.pdf",
        "name": "Ananya Rao",
        "projects": [
            "Chat Application — Java | Socket Programming",
            "Face Recognition — Python | OpenCV",
            "Task Manager — React | Node.js",
        ],
        "links": [
            "https://github.com/ananya/chat-app",
            "https://github.com/ananya/face-recognition",
            "https://github.com/ananya/task-manager",
        ],
    },
    {
        "filename": "resume_05_github_profile.pdf",
        "name": "Vikram Singh",
        "projects": [
            "AI Study Assistant — Python | NLP",
            "Attendance System — Java",
        ],
        "links": [
            "https://github.com/vikramsingh",
        ],
    },
    {
        "filename": "resume_06_short_project.pdf",
        "name": "Priya Reddy",
        "projects": [
            "Calculator App — Java",
        ],
        "links": [
            "https://github.com/priya/calculator",
        ],
    },
    {
        "filename": "resume_07_web_projects.pdf",
        "name": "Kiran Patel",
        "projects": [
            "E-Commerce Website — React | Node.js | MongoDB",
            "Blog Platform — HTML | CSS | JavaScript",
        ],
        "links": [
            "https://github.com/kiran/ecommerce",
            "https://github.com/kiran/blog",
        ],
    },
    {
        "filename": "resume_08_ml_projects.pdf",
        "name": "Sneha Das",
        "projects": [
            "House Price Prediction — Python | Machine Learning",
            "Spam Detection — Python | NLP",
        ],
        "links": [
            "https://github.com/sneha/house-price",
            "https://github.com/sneha/spam-detection",
        ],
    },
    {
        "filename": "resume_09_different_layout.pdf",
        "name": "Arjun Nair",
        "projects": [
            "Food Delivery App — Java | MySQL",
            "Inventory System — Python | SQLite",
        ],
        "links": [
            "https://github.com/arjun/food-delivery",
            "https://github.com/arjun/inventory",
        ],
    },
    {
        "filename": "resume_10_missing_description.pdf",
        "name": "Divya Menon",
        "projects": [
            "Smart Parking System — Python",
            "College Event Portal — HTML | CSS",
        ],
        "links": [
            "https://github.com/divya/smart-parking",
            "https://github.com/divya/event-portal",
        ],
    },
]


def create_resume(data):
    path = OUTPUT_DIR / data["filename"]

    pdf = canvas.Canvas(str(path))

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 800, data["name"])

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, 775, "Email: student@example.com")
    pdf.drawString(50, 755, "Phone: +91-9000000000")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, 720, "SKILLS")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        50,
        700,
        "Python, Java, HTML, CSS, JavaScript, Git, SQL, Machine Learning"
    )

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, 660, "PROJECTS")

    y = 635

    for project in data["projects"]:
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(50, y, project)
        y -= 20

        if data["filename"] != "resume_10_missing_description.pdf":
            pdf.setFont("Helvetica", 10)
            pdf.drawString(
                65,
                y,
                "Developed and implemented this project as part of academic work."
            )
            y -= 20

            pdf.drawString(
                65,
                y,
                "Applied relevant programming concepts and tested the application."
            )
            y -= 30
        else:
            y -= 20

    if data["links"]:
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, "PROJECT LINKS")

        y -= 25

        for link in data["links"]:
            pdf.setFont("Helvetica", 10)
            pdf.drawString(50, y, link)

            pdf.linkURL(
                link,
                (45, y - 3, 500, y + 10),
                relative=0,
            )

            y -= 20

    pdf.save()

    print(f"Created: {path}")


for sample in SAMPLES:
    create_resume(sample)

print("\nAll sample resumes created successfully.")