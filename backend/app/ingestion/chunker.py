import hashlib


def generate_chunk_id(project_id, source, text):
    """
    Generate a stable ID for an evidence chunk.

    The same project, source, and exact text
    will always produce the same chunk ID.
    """

    content = f"{project_id}|{source}|{text}"

    hash_value = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()[:10]

    return f"{project_id}-{source}-{hash_value}"


def chunk_text(text, chunk_size=500):
    """
    Split text into chunks of approximately chunk_size characters.

    Text is kept exactly as it appears inside each chunk.
    """

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        end = min(
            start + chunk_size,
            len(text)
        )

        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk)

        start = end

    return chunks


def create_evidence_chunks(
    project_id,
    text,
    source="readme",
    chunk_size=500
):
    """
    Create evidence chunks for a project.

    source can be:
        resume
        readme
        student_provided
    """

    if not text:
        return []

    text_chunks = chunk_text(
        text,
        chunk_size
    )

    evidence_chunks = []

    for chunk in text_chunks:

        chunk_id = generate_chunk_id(
            project_id,
            source,
            chunk
        )

        evidence_chunks.append({
            "chunk_id": chunk_id,
            "project_id": project_id,
            "source": source,
            "text": chunk
        })

    return evidence_chunks