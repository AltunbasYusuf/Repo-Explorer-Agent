import threading

_repo_lock = threading.Lock()
import os
import chromadb
import ollama
from langchain_core.tools import tool
from clone_repo import clone_repo
from indexer import build_index, EMBED_MODEL, DB_PATH, COLLECTION_NAME

CHAT_MODEL = "qwen2.5:7b"

# Cache of already-loaded repos: github_url -> repo_path.
# Each tool checks/populates this itself, so no tool depends on another
# tool having run first - this removes the race condition entirely.
_repo_cache = {}
_last_loaded_url = {"url": None}


def _get_embedding(text):
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def _ensure_repo_loaded(github_url):
    """Loads and indexes a repo if it hasn't been already. Thread-safe:
    if two tool calls race for the same (or different) repo, the lock
    ensures clone/index operations never overlap."""
    with _repo_lock:
        if github_url in _repo_cache:
            _last_loaded_url["url"] = github_url
            return _repo_cache[github_url]

        repo_path = clone_repo(github_url)
        build_index(repo_path)
        _repo_cache[github_url] = repo_path
        _last_loaded_url["url"] = github_url
        return repo_path


def _resolve_repo_path(github_url):
    """Used by tools that receive an optional github_url. Falls back to
    the last-loaded repo if no URL is given."""
    if github_url:
        return _ensure_repo_loaded(github_url)
    if _last_loaded_url["url"]:
        return _repo_cache[_last_loaded_url["url"]]
    return None


@tool
def load_repo(github_url: str) -> str:
    """Clones a GitHub repository and builds a searchable code index from it."""
    repo_path = _ensure_repo_loaded(github_url)
    return f"Repository loaded and indexed from {github_url}."


@tool
def describe_repo(github_url: str = "") -> str:
    """Gives a high-level description of a repository: what it contains, its
    structure, and what the README says it does. If github_url is omitted,
    describes the most recently loaded repo. If the repo isn't loaded yet,
    this loads it automatically - you don't need to call load_repo first."""

    repo_path = _resolve_repo_path(github_url or None)
    if repo_path is None:
        return "No repository URL given and none has been loaded yet."

    readme_content = ""
    for candidate in ["README.md", "readme.md", "README.txt"]:
        candidate_path = os.path.join(repo_path, candidate)
        if os.path.exists(candidate_path):
            with open(candidate_path, "r", encoding="utf-8", errors="ignore") as f:
                readme_content = f.read()
            break

    top_level_items = [i for i in os.listdir(repo_path) if i != ".git"]

    prompt = f"""Repository top-level contents: {', '.join(top_level_items)}

README content:
{readme_content[:3000] if readme_content else "(no README found)"}

Based on the above, give a concise (3-5 sentence) description of what this project does 
and how it's organized."""

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0},
    )
    return response["message"]["content"]


@tool
def find_code(query: str, github_url: str = "") -> str:
    """Searches a repository's code for something matching the query,
    e.g. 'where is the model loaded'. If github_url is omitted, searches the
    most recently loaded repo. If the repo isn't loaded yet, this loads it
    automatically - you don't need to call load_repo first."""

    repo_path = _resolve_repo_path(github_url or None)
    if repo_path is None:
        return "No repository URL given and none has been loaded yet."

    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    query_embedding = _get_embedding(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=3)

    if not results["ids"][0]:
        return "No matching code found."

    output_parts = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        code = results["documents"][0][i]
        output_parts.append(
            f"--- {meta['name']} ({meta['file']}:{meta['start_line']}-{meta['end_line']}) ---\n{code}"
        )
    return "\n\n".join(output_parts)