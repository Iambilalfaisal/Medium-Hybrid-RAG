from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


def split_into_parent_and_child_chunks(text: str) -> list[tuple[str, list[str]]]:
    """Two-level split: parents tile the article contiguously with no overlap between
    them; each parent's children overlap with each other (CHILD_CHUNK_OVERLAP) so a
    concept spanning a child boundary is still findable from either side. Returns
    [(parent_text, [child_text, ...]), ...]."""
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=settings.PARENT_CHUNK_SIZE, chunk_overlap=0)
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHILD_CHUNK_SIZE, chunk_overlap=settings.CHILD_CHUNK_OVERLAP
    )

    parents = parent_splitter.split_text(text)
    return [(parent, child_splitter.split_text(parent)) for parent in parents]
