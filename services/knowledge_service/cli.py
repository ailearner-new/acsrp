"""CLI commands for knowledge service ingestion."""

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from services.knowledge_service.retrieval import (
    FakeVectorStore,
    FakeEmbeddings,
)


async def ingest_documents(
    input_path: str,
    tenant_id: str,
    batch_size: int = 100,
    chunk_size: int = 1000,
    overwrite: bool = False,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Ingest documents from a file or directory into the knowledge base.

    Supports JSON, JSONL, and newline-delimited JSON formats.

    Args:
        input_path: Path to JSON/JSONL file or directory containing documents
        tenant_id: Tenant ID for filtering
        batch_size: Number of documents to process per batch
        chunk_size: Characters per chunk when splitting documents
        overwrite: Whether to overwrite existing documents
        category: Default category for all documents

    Returns:
        Dictionary with ingestion statistics
    """
    store = FakeVectorStore()
    embedder = FakeEmbeddings()

    # Load documents from input
    documents = []

    input_path_obj = Path(input_path)

    if input_path_obj.is_file():
        if input_path.endswith('.jsonl'):
            with open(input_path, 'r') as f:
                for line in f:
                    if line.strip():
                        doc = json.loads(line)
                        documents.append(doc)
        else:
            with open(input_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    documents = data
                else:
                    documents = [data]
    elif input_path_obj.is_dir():
        for json_file in input_path.rglob('*.json'):
            if json_file.suffix == '.jsonl':
                continue  # Skip newline-delimited files in directory scan
            with open(json_file, 'r') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        documents.extend(data)
                    else:
                        documents.append(data)
                except json.JSONDecodeError:
                    continue

    print(f"Loaded {len(documents)} documents from {input_path}")

    # Process and chunk documents
    processed_docs = []
    for doc in documents:
        content = doc.get('content', doc.get('body', ''))
        title = doc.get('title', doc.get('name', 'Untitled'))

        # Split into chunks if content is large
        if len(content) > chunk_size:
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            for i, chunk in enumerate(chunks):
                doc_id = f"{doc.get('doc_id', str(uuid.uuid4()))}_chunk_{i+1}"
                processed_docs.append({
                    'id': doc_id,
                    'content': chunk,
                    'metadata': {
                        'title': title,
                        'chunk_index': i + 1,
                        'total_chunks': len(chunks),
                        'tenant_id': tenant_id,
                        'category': category or doc.get('category'),
                        'source_url': doc.get('source_url'),
                    }
                })
        else:
            doc_id = doc.get('doc_id', str(uuid.uuid4()))
            processed_docs.append({
                'id': doc_id,
                'content': content,
                'metadata': {
                    'title': title,
                    'tenant_id': tenant_id,
                    'category': category or doc.get('category'),
                    'source_url': doc.get('source_url'),
                }
            })

    # Generate embeddings and upsert
    total_inserted = 0
    for i in range(0, len(processed_docs), batch_size):
        batch = processed_docs[i:i+batch_size]

        # Generate embeddings for batch
        contents = [doc['content'] for doc in batch]
        embeddings = await embedder.aembed_texts(contents)

        # Add embeddings to documents
        for doc, embedding in zip(batch, embeddings):
            doc['embedding'] = embedding

        # Upsert to vector store
        ids = await store.upsert(batch)
        total_inserted += len(ids)

        print(f"Processed batch {i//batch_size + 1}: {len(ids)} documents")

    return {
        'total_documents': len(documents),
        'total_chunks': len(processed_docs),
        'inserted': total_inserted,
        'tenant_id': tenant_id,
    }


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Knowledge Service Ingestion CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('input_path', help='Path to JSON/JSONL file or directory')
    parser.add_argument('--tenant-id', required=True, help='Tenant ID for filtering')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    parser.add_argument('--chunk-size', type=int, default=1000, help='Characters per chunk')
    parser.add_argument('--category', default=None, help='Default category for documents')
    parser.add_argument('--output', default=None, help='Output JSON file for results')

    args = parser.parse_args()

    print(f"Starting ingestion for tenant: {args.tenant_id}")
    print(f"Input: {args.input_path}")

    result = await ingest_documents(
        input_path=args.input_path,
        tenant_id=args.tenant_id,
        batch_size=args.batch_size,
        chunk_size=args.chunk_size,
        category=args.category,
    )

    print(f"\nIngestion complete!")
    print(f"  Total documents: {result['total_documents']}")
    print(f"  Total chunks: {result['total_chunks']}")
    print(f"  Inserted: {result['inserted']}")

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"  Results written to: {args.output}")

    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))