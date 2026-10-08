import re

from .resume_parser import (
    extract_resume_text,
    extract_resume_links
)


from .skills_extractor import extract_skills
from .project_extractor import extract_projects
from .link_extractor import classify_links
from .readme_fetcher import fetch_readme
from .chunker import create_evidence_chunks

def create_student_provided_evidence(project_id, text):
    text = text.strip()

    if not text:
        return []

    return create_evidence_chunks(
        project_id,
        text,
        source="student_provided"
    )

def determine_input_quality(project, readme_text):
    repo_url = project.get("repo_url")
    description = project.get("description_text", "").strip()

    # No useful project information at all
    if not description and not repo_url:
        return "missing", True

    # Project has no repository link
    if not repo_url:
        return "thin", True

    # Repository exists but README could not be fetched
    if not readme_text:
        return "thin", True

    # README exists but contains very little information
    if len(readme_text.strip()) < 100:
        return "thin", True

    # Project has resume description + useful README
    return "ok", False


def process_resume(pdf_path):
    """
    Complete resume ingestion pipeline.
    """

    warnings = []

    # --------------------------------------------------
    # 1. Extract resume text
    # --------------------------------------------------

    try:
        resume_text = extract_resume_text(pdf_path)
    except Exception as error:
        warnings.append(
            f"Could not read resume: {error}"
        )
        resume_text = ""

    # --------------------------------------------------
    # 2. Extract links
    # --------------------------------------------------

    try:
        links = extract_resume_links(pdf_path)
    except Exception as error:
        warnings.append(
            f"Could not extract resume links: {error}"
        )
        links = []

    # --------------------------------------------------
    # 3. Extract skills
    # --------------------------------------------------

    skills = extract_skills(resume_text)

    # --------------------------------------------------
    # 4. Extract projects
    # --------------------------------------------------

    projects = extract_projects(resume_text)

    # --------------------------------------------------
    # 5. Classify links
    # --------------------------------------------------

    classified_links = classify_links(links)

    github_repos = classified_links["github_repos"]

    # --------------------------------------------------
    # 6. Match repositories to projects
    # --------------------------------------------------

    for project in projects:
        project_name = project["name"].lower()

        for repo_url in github_repos:
            repo_name = (
                repo_url.rstrip("/")
                .split("/")[-1]
                .lower()
            )

            normalized_project = re.sub(
                r"[^a-z0-9]",
                "",
                project_name
            )

            normalized_repo = re.sub(
                r"[^a-z0-9]",
                "",
                repo_name
            )

            if (
                normalized_repo
                and normalized_repo in normalized_project
            ):
                project["repo_url"] = repo_url
                break

    # --------------------------------------------------
    # 7. Process each project
    # --------------------------------------------------

    project_contexts = []

    for project in projects:

        project_id = project["project_id"]

        repo_url = project.get("repo_url")

        readme_text = None

        # Fetch README if repository exists
        if repo_url:
            readme_text = fetch_readme(repo_url)

        # Determine quality
        input_quality, needs_student_input = (
            determine_input_quality(
                project,
                readme_text
            )
        )

        # Create evidence chunks
        evidence_chunks = []

        # Resume project description
        description = project.get(
            "description_text",
            ""
        ).strip()

        if description:
            evidence_chunks.extend(
                create_evidence_chunks(
                    project_id,
                    description,
                    source="resume"
                )
            )

        # README evidence
        if readme_text:
            evidence_chunks.extend(
                create_evidence_chunks(
                    project_id,
                    readme_text,
                    source="readme"
                )
            )

        project_contexts.append({
            "project_id": project_id,
            "project_name": project["name"],
            "input_quality": input_quality,
            "needs_student_input": needs_student_input,
            "evidence_chunks": evidence_chunks
        })

    # --------------------------------------------------
    # 8. Final result
    # --------------------------------------------------

    return {
        "skills": skills,
        "projects": projects,
        "project_contexts": project_contexts,
        "warnings": warnings
    }