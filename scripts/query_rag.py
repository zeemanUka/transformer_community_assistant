#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from rag import RagConfig, build_context, load_vectorstore, similarity_search


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query a Chroma vector store.")
    parser.add_argument("--query", required=True, help="Question or search query.")
    parser.add_argument("--persist-dir", default="vector_db", help="Chroma persistence directory.")
    parser.add_argument("--embedding-model", default="text-embedding-3-large", help="OpenAI embedding model.")
    parser.add_argument("--k", type=int, default=4, help="Number of chunks to retrieve.")
    parser.add_argument("--max-chars", type=int, default=4000, help="Max characters in context.")
    parser.add_argument("--json", action="store_true", help="Output JSON with docs and context.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = RagConfig(
        persist_dir=args.persist_dir,
        embedding_model=args.embedding_model,
    )

    vectorstore = load_vectorstore(config=config)
    docs = similarity_search(vectorstore, args.query, k=args.k)
    context = build_context(docs, max_chars=args.max_chars)

    if args.json:
        payload = {
            "query": args.query,
            "k": args.k,
            "context": context,
            "documents": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                }
                for doc in docs
            ],
        }
        print(json.dumps(payload, indent=2))
        return

    print("Context:\n")
    print(context)


if __name__ == "__main__":
    main()
