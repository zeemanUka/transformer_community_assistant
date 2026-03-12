from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass(frozen=True)
class RagConfig:
    persist_dir: str = "vector_db"
    embedding_model: str = "text-embedding-3-large"
    chunk_size: int = 500
    chunk_overlap: int = 200


def load_records(path: str | Path) -> list:
    file_path = Path(path)
    raw = file_path.read_text(encoding="utf-8")
    if raw.lstrip().startswith("["):
        import json

        return json.loads(raw)

    records = []
    import json

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def records_to_documents(
    records: Sequence,
    *,
    text_key: str = "description",
    id_key: Optional[str] = "id",
    metadata_keys: Optional[Sequence[str]] = None,
    formatter: Optional[Callable[[dict], str]] = None,
) -> List[Document]:
    documents: List[Document] = []
    for idx, record in enumerate(records):
        if isinstance(record, str):
            text = record
            metadata = {}
        elif isinstance(record, dict):
            if formatter is not None:
                text = formatter(record)
            else:
                text = record.get(text_key)
                if text is None:
                    raise ValueError(f"Record {idx} missing text key '{text_key}'.")
            metadata = {}
            if metadata_keys:
                for key in metadata_keys:
                    if key in record:
                        metadata[key] = record[key]
            if id_key and id_key in record:
                metadata["source_id"] = record[id_key]
        else:
            raise TypeError(f"Unsupported record type at {idx}: {type(record)}")

        documents.append(Document(page_content=str(text), metadata=metadata))

    return documents


def format_event_page_content(data: dict) -> str:
    lines = [
        f"Event: {data.get('name', '') or ''}",
        f"Short Description: {data.get('shortDescription', '') or ''}",
        f"Description: {data.get('description', '') or ''}",
        f"Venue: {data.get('venue', '') or ''}",
        f"Start Date: {data.get('startDate', '') or ''}",
        f"End Date: {data.get('endDate', '') or ''}",
        f"Event Type: {data.get('projectType', '') or ''}",
        f"Status: {data.get('status', '') or ''}",
        f"Organisation Lookup id: {data.get('parentProjectId', '') or ''}",
    ]
    return "\n".join(lines).strip()


def chunk_documents(
    documents: Sequence[Document],
    *,
    chunk_size: int = 500,
    chunk_overlap: int = 200,
) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_documents(documents)


def build_vectorstore(
    documents: Sequence[Document],
    *,
    config: RagConfig,
    reset: bool = False,
) -> Chroma:
    embeddings = OpenAIEmbeddings(model=config.embedding_model)
    persist_dir = Path(config.persist_dir)

    if reset and persist_dir.exists():
        Chroma(persist_directory=str(persist_dir), embedding_function=embeddings).delete_collection()

    return Chroma.from_documents(
        documents=list(documents),
        embedding=embeddings,
        persist_directory=str(persist_dir),
    )


def load_vectorstore(*, config: RagConfig) -> Chroma:
    embeddings = OpenAIEmbeddings(model=config.embedding_model)
    return Chroma(
        persist_directory=str(config.persist_dir),
        embedding_function=embeddings,
    )


def similarity_search(
    vectorstore: Chroma,
    query: str,
    *,
    k: int = 4,
) -> List[Document]:
    return vectorstore.similarity_search(query, k=k)


def build_context(docs: Iterable[Document], *, max_chars: int = 4000) -> str:
    chunks: List[str] = []
    total = 0
    for doc in docs:
        text = doc.page_content.strip()
        if not text:
            continue
        remaining = max_chars - total
        if remaining <= 0:
            break
        if len(text) > remaining:
            text = text[:remaining]
        chunks.append(text)
        total += len(text)
    return "\n\n".join(chunks)
