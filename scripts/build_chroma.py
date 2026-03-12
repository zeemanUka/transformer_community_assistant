#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from rag import (
    RagConfig,
    build_vectorstore,
    chunk_documents,
    format_event_page_content,
    load_records,
    records_to_documents,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Chroma vector store from JSON records.")
    parser.add_argument("--input", required=True, help="Path to JSON or JSONL file.")
    parser.add_argument(
        "--config",
        default="rag_config.json",
        help="Path to a JSON config file with defaults.",
    )
    parser.add_argument("--persist-dir", default="vector_db", help="Chroma persistence directory.")
    parser.add_argument("--embedding-model", default="text-embedding-3-large", help="OpenAI embedding model.")
    parser.add_argument("--chunk-size", type=int, default=500, help="Chunk size in characters.")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Chunk overlap in characters.")
    parser.add_argument("--text-key", default="description", help="Field to use as document text.")
    parser.add_argument("--id-key", default="id", help="Field to use as document id in metadata.")
    parser.add_argument(
        "--metadata-keys",
        default="",
        help="Comma-separated list of extra metadata keys to include.",
    )
    parser.add_argument(
        "--format",
        default="event",
        choices=["event", "raw"],
        help="Record formatting preset. Use 'event' to match PR-2 formatting.",
    )
    parser.add_argument(
        "--project-types",
        default="COMMUNITY,CONFERENCE",
        help="Comma-separated list of projectType values to include (e.g. COMMUNITY,CONFERENCE).",
    )
    parser.add_argument("--reset", action="store_true", help="Delete any existing collection first.")
    return parser.parse_args()


def load_config(path: str) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def apply_config(args: argparse.Namespace, config: dict) -> argparse.Namespace:
    # Only apply config values if the user didn't explicitly override via CLI.
    if args.persist_dir == "vector_db" and "persist_dir" in config:
        args.persist_dir = config["persist_dir"]
    if args.embedding_model == "text-embedding-3-large" and "embedding_model" in config:
        args.embedding_model = config["embedding_model"]
    if args.chunk_size == 500 and "chunk_size" in config:
        args.chunk_size = int(config["chunk_size"])
    if args.chunk_overlap == 200 and "chunk_overlap" in config:
        args.chunk_overlap = int(config["chunk_overlap"])
    if args.text_key == "description" and "text_key" in config:
        args.text_key = config["text_key"]
    if args.id_key == "id" and "id_key" in config:
        args.id_key = config["id_key"]
    if args.metadata_keys == "" and "metadata_keys" in config:
        args.metadata_keys = ",".join(config["metadata_keys"])
    if args.format == "event" and "format" in config:
        args.format = config["format"]
    if args.project_types == "COMMUNITY,CONFERENCE" and "project_types" in config:
        args.project_types = ",".join(config["project_types"])
    return args


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    args = apply_config(args, config)
    metadata_keys = [k.strip() for k in args.metadata_keys.split(",") if k.strip()]

    records = load_records(args.input)

    if args.project_types:
        allowed = {item.strip() for item in args.project_types.split(",") if item.strip()}
        records = [
            record
            for record in records
            if isinstance(record, dict) and record.get("projectType") in allowed
        ]
    formatter = format_event_page_content if args.format == "event" else None
    docs = records_to_documents(
        records,
        text_key=args.text_key,
        id_key=args.id_key or None,
        metadata_keys=metadata_keys or None,
        formatter=formatter,
    )

    chunks = chunk_documents(
        docs,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    config = RagConfig(
        persist_dir=args.persist_dir,
        embedding_model=args.embedding_model,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    build_vectorstore(chunks, config=config, reset=args.reset)

    print(f"Records loaded: {len(records)}")
    print(f"Documents created: {len(docs)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Chroma persisted to: {args.persist_dir}")


if __name__ == "__main__":
    main()
