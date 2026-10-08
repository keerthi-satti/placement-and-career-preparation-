from urllib.parse import urlparse


def classify_links(links):
    """
    Classify links extracted from a resume.

    Separates:
    - GitHub repository links
    - GitHub profile links
    - Other links
    """

    github_repos = []
    github_profiles = []
    other_links = []

    for link in links:

        clean_link = link.strip()

        if not clean_link:
            continue

        parsed = urlparse(clean_link)

        # Check GitHub links
        if parsed.netloc.lower() in ["github.com", "www.github.com"]:

            # Remove empty parts caused by leading/trailing /
            parts = [
                part for part in parsed.path.strip("/").split("/")
                if part
            ]

            # GitHub repository:
            # github.com/username/repository
            if len(parts) >= 2:

                username = parts[0]
                repository = parts[1]

                repo_url = (
                    f"https://github.com/"
                    f"{username}/{repository}"
                )

                github_repos.append(repo_url)

            # GitHub profile:
            # github.com/username
            elif len(parts) == 1:

                profile_url = (
                    f"https://github.com/{parts[0]}"
                )

                github_profiles.append(profile_url)

            else:
                other_links.append(clean_link)

        else:
            other_links.append(clean_link)

    return {
        "github_repos": github_repos,
        "github_profiles": github_profiles,
        "other_links": other_links
    }