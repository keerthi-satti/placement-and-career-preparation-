from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Frame, PageTemplate
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


output = "tests/sample_resumes/resume_09_different_layout.pdf"

styles = getSampleStyleSheet()

left_content = [
    Paragraph("<b>SKILLS</b>", styles["Heading2"]),
    Paragraph("Python, Java, SQL, Git", styles["BodyText"]),
    Paragraph("<b>PROJECTS</b>", styles["Heading2"]),
    Paragraph(
        "<b>Student Management System — Java | OOP</b>",
        styles["BodyText"]
    ),
    Paragraph(
        "Built a console application for managing student records.",
        styles["BodyText"]
    ),
    Paragraph(
        "Implemented add, view, update and delete operations.",
        styles["BodyText"]
    ),
]

right_content = [
    Paragraph("<b>EDUCATION</b>", styles["Heading2"]),
    Paragraph("B.Tech Computer Science", styles["BodyText"]),
    Paragraph("Shri Vishnu Engineering College", styles["BodyText"]),
    Paragraph("<b>PROJECT LINKS</b>", styles["Heading2"]),
    Paragraph(
        "https://github.com/test/student-management-system",
        styles["BodyText"]
    ),
]

doc = SimpleDocTemplate(
    output,
    pagesize=A4,
    rightMargin=40,
    leftMargin=40,
    topMargin=40,
    bottomMargin=40
)

page_width, page_height = A4

left_frame = Frame(
    40,
    40,
    page_width / 2 - 50,
    page_height - 80,
    id="left"
)

right_frame = Frame(
    page_width / 2 + 10,
    40,
    page_width / 2 - 50,
    page_height - 80,
    id="right"
)

doc.addPageTemplates([
    PageTemplate(
        id="TwoColumn",
        frames=[left_frame, right_frame]
    )
])

doc.build(left_content + right_content)

print("Created:", output)