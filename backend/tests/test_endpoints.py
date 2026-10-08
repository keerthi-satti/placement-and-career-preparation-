from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home():
    assert client.get("/").status_code == 200


def test_auth_endpoints():
    for path in ["signup", "login", "logout", "reset-password"]:
        assert client.post(f"/auth/{path}").status_code == 200


def test_upload_and_list():

    with open("tests/sample_resumes/resume_01_standard.pdf", "rb") as file:
        response = client.post(
            "/resumes",
            files={
                "file": (
                    "resume_01_standard.pdf",
                    file,
                    "application/pdf"
                )
            }
        )

    assert response.status_code == 200

    data = response.json()

    assert "resume_upload_id" in data
    assert data["status"] == "processed"
    assert "skills" in data
    assert "projects" in data

def test_question_set_shape():
    data = client.get("/resumes/r_123/question-set").json()
    assert data["status"] in ["processing", "ready", "needs_input", "failed"]
    q = data["questions"][0]
    for key in ["id", "text", "hint", "type", "difficulty", "project_id", "evidence"]:
        assert key in q


def test_project_details_and_generate_more():
    assert client.post("/resumes/r_123/project-details").status_code == 200
    data = client.post("/resumes/r_123/generate-more").json()
    assert "questions" in data and "exhausted" in data


def test_deletes():
    assert client.delete("/resumes/r_123").status_code == 200
    assert client.delete("/account").status_code == 200