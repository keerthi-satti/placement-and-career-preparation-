import re


PROJECT_SECTION_NAMES = [
    "PROJECTS",
    "PROJECT",
    "ACADEMIC PROJECTS",
    "ACADEMIC PROJECT",
    "PERSONAL PROJECTS",
    "PROJECT EXPERIENCE",
]


NEXT_SECTION_NAMES = [
    "EDUCATION",
    "EXPERIENCE",
    "WORK EXPERIENCE",
    "INTERNSHIPS",
    "INTERNSHIP",
    "TECHNICAL SKILLS",
    "SKILLS",
    "CERTIFICATIONS",
    "CERTIFICATES",
    "ACHIEVEMENTS",
    "INTERPERSONAL SKILLS",
    "EXTRACURRICULAR ACTIVITIES",
    "ACTIVITIES",
    "LANGUAGES",
    "PROJECT LINKS",
    "PROJECT LINK",
]


def find_project_section(resume_text):
    """
    Find the lines belonging to the PROJECTS section.
    """

    lines = resume_text.splitlines()

    start_index = None

    for i, line in enumerate(lines):
        if line.strip().upper() in PROJECT_SECTION_NAMES:
            start_index = i + 1
            break

    if start_index is None:
        return []

    project_lines = []

    for line in lines[start_index:]:

        cleaned = line.strip()

        if cleaned.upper() in NEXT_SECTION_NAMES:
            break

        if cleaned:
            project_lines.append(cleaned)

    return project_lines


def is_bullet_line(line):
    """
    Check whether a line is a project description/bullet.
    """

    return line.startswith((
        "•",
        "-",
        "*",
        "▪",
        "◦"
    ))


def is_project_title(line):
    """
    Detect common project-title formats.
    """

    line = line.strip()

    if not line:
        return False

    # Bullet points are descriptions, not titles.
    if is_bullet_line(line):
        return False

    # Common format:
    # Project Name — Java | HTML | CSS
    if "—" in line:
        return True

    # Common format:
    # Project Name - Java | Python
    if " - " in line and "|" in line:
        return True

    # Common format:
    # Project Name | Java | Python
    if "|" in line:
        return True

    # Numbered project titles:
    # 1. Student Management System
    # 2. Resume Scanner
    if re.match(r"^\d+[\.\)]\s+", line):
        return True

    return False


def clean_project_title(line):
    """
    Remove numbering and extra whitespace from a project title.
    """

    line = re.sub(r"^\d+[\.\)]\s*", "", line)

    return line.strip()


def extract_projects(resume_text):
    """
    Extract projects from the PROJECTS section.

    Returns a list containing:
        project_id
        name
        description_text
        repo_url
    """

    lines = find_project_section(resume_text)

    if not lines:
        return []

    projects = []

    current_project = None
    current_description = []

    for line in lines:

        # New project
        if is_project_title(line):

            # Save previous project
            if current_project is not None:

                current_project["description_text"] = " ".join(
                    current_description
                ).strip()

                projects.append(current_project)

            current_project = {
                "project_id": f"p{len(projects) + 1}",
                "name": clean_project_title(line),
                "description_text": "",
                "repo_url": None
            }

            current_description = []

        else:

            # Add description to current project
            if current_project is not None:

                description = line.lstrip(
                    "•-*▪◦"
                ).strip()

                if description:
                    current_description.append(description)

    # Save final project
    if current_project is not None:

        current_project["description_text"] = " ".join(
            current_description
        ).strip()

        projects.append(current_project)

    return projects