import pymupdf


def extract_resume_text(pdf_path):
    """
    Extract text from a PDF resume.
    """

    document = pymupdf.open(pdf_path)

    pages = []

    for page in document:
        text = page.get_text("text")
        pages.append(text)

    document.close()

    return "\n".join(pages)


def extract_resume_links(pdf_path):
    """
    Extract hyperlinks embedded in the resume PDF.
    """

    document = pymupdf.open(pdf_path)

    links = []

    for page in document:
        page_links = page.get_links()

        for link in page_links:
            if "uri" in link:
                links.append(link["uri"])

    document.close()

    return links