import os
import chromadb
import ollama
from chunker import extract_chunks_from_file

EMBED_MODEL = "qwen3-embedding"
DB_PATH = "chroma_db"
COLLECTION_NAME = "code_index"

INDEXABLE_EXTENSIONS = {".py", ".js", ".jsx", ".md", ".json", ".txt"}

SKIP_DIRS = {
    ".git", "venv", "node_modules", "__pycache__", "chroma_db", ".idea",
}

# Conservative character limit per chunk sent to the embedding model.
# qwen3-embedding's context window is token-based, not character-based,
# but ~4 chars/token is a safe rule of thumb - this keeps us well under the limit.
MAX_CHUNK_CHARS = 6000


def get_embedding(text):
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def looks_like_data_file(text, sample_lines=5):
    """Heuristic: if most sampled lines are just numbers, this is likely a
    data/label file (e.g. YOLO annotations), not documentation - skip it."""
    lines = [l.strip() for l in text.split("\n") if l.strip()][:sample_lines]
    if not lines:
        return False
    numeric_lines = 0
    for l in lines:
        parts = l.split()
        if parts and all(p.replace(".", "").replace("-", "").isdigit() for p in parts):
            numeric_lines += 1
    return numeric_lines / len(lines) > 0.7


def split_large_chunk(chunk, max_chars=MAX_CHUNK_CHARS):
    """Splits an oversized chunk into smaller sub-chunks by lines,
    preserving as much context as possible rather than truncating blindly."""
    code = chunk["code"]
    if len(code) <= max_chars:
        return [chunk]

    lines = code.split("\n")
    sub_chunks = []
    current_lines = []
    current_len = 0
    part_num = 1
    start_line = chunk["start_line"]

    for i, line in enumerate(lines):
        current_lines.append(line)
        current_len += len(line) + 1
        if current_len >= max_chars:
            sub_code = "\n".join(current_lines)
            sub_chunks.append({
                **chunk,
                "name": f"{chunk['name']} (part {part_num})",
                "code": sub_code,
                "start_line": start_line,
                "end_line": start_line + len(current_lines) - 1,
            })
            start_line += len(current_lines)
            current_lines = []
            current_len = 0
            part_num += 1

    if current_lines:
        sub_code = "\n".join(current_lines)
        sub_chunks.append({
            **chunk,
            "name": f"{chunk['name']} (part {part_num})",
            "code": sub_code,
            "start_line": start_line,
            "end_line": start_line + len(current_lines) - 1,
        })

    return sub_chunks


def find_indexable_files(root_dir):
    files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            ext = os.path.splitext(fname)[1]
            if ext in INDEXABLE_EXTENSIONS:
                files.append(os.path.join(dirpath, fname))
    return files


def index_file(filepath, collection):
    try:
        raw_chunks = extract_chunks_from_file(filepath)
    except Exception as e:
        print(f"  Skipped {filepath}: {e}")
        return 0

    indexed_count = 0

    for chunk in raw_chunks:
        code = chunk["code"]
        if not code.strip():
            continue

        # Content-based filter: skip files/chunks that look like numeric data,
        # regardless of extension or folder name (e.g. YOLO label files)
        if looks_like_data_file(code):
            continue

        # Split anything too large for the embedding model's context window,
        # instead of skipping it and losing the content entirely
        for sub_chunk in split_large_chunk(chunk):
            embedding = get_embedding(sub_chunk["code"])
            chunk_id = f"{filepath}::{sub_chunk['name']}::{indexed_count}"

            collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[sub_chunk["code"]],
                metadatas=[{
                    "name": sub_chunk["name"],
                    "type": sub_chunk["type"],
                    "file": sub_chunk["file"],
                    "start_line": sub_chunk["start_line"],
                    "end_line": sub_chunk["end_line"],
                }],
            )
            indexed_count += 1

    return indexed_count


def build_index(root_dir):
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    files = find_indexable_files(root_dir)
    print(f"Found {len(files)} candidate files.\n")

    total_chunks = 0
    skipped_files = 0
    for filepath in files:
        count = index_file(filepath, collection)
        if count == 0:
            skipped_files += 1
        else:
            total_chunks += count
            print(f"  {filepath}: {count} chunks")

    print(f"\nDone. {collection.count()} total chunks indexed. "
          f"{skipped_files} files skipped (empty or data-like content).")
    return collection


if __name__ == "__main__":
    from clone_repo import clone_repo
    repo_path = clone_repo("https://github.com/AltunbasYusuf/SmartVineyard-Analytics")
    build_index(repo_path)