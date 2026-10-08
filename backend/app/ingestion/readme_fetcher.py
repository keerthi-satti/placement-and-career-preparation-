import requests


def fetch_readme(repo_url):
    """
    Fetch README content from a public GitHub repository.

    Returns:
        README text if available.
        None if README cannot be fetched.
    """

    if not repo_url:
        return None

    if "github.com" not in repo_url.lower():
        return None

    parts = repo_url.rstrip("/").split("/")

    # Expected:
    # https://github.com/username/repository
    if len(parts) < 5:
        return None

    username = parts[-2]
    repository = parts[-1]

    # Remove .git if present
    repository = repository.removesuffix(".git")

    api_url = (
        f"https://api.github.com/repos/"
        f"{username}/{repository}/readme"
    )

    try:
        response = requests.get(
            api_url,
            headers={
                "Accept": "application/vnd.github.raw+json"
            },
            timeout=10
        )

        # README successfully found
        if response.status_code == 200:
            readme_text = response.text.strip()

            if not readme_text:
                return None

            return readme_text

        # 404 → repository or README doesn't exist
        # 403 → private repository / access denied / rate limit
        # Other errors → don't crash the pipeline
        return None

    except requests.RequestException:
        # Network/API failure should not crash ingestion
        return None