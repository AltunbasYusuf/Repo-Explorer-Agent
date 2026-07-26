# Repo Explorer Agent

A local, language-agnostic code search agent. Give it a GitHub repository URL and it clones, indexes, and lets you ask natural-language questions about the codebase - "what does this repo do", "which function loads the model", "where is X handled" - and get back the actual relevant code with file paths and line numbers. Built as part of AI/agent engineering prep.

## How it works

1. Clone - a given GitHub URL is shallow-cloned (--depth 1) into a local folder.
2. Chunk - source files are parsed with tree-sitter (not regex or naive line-splitting), which understands the actual syntax of each language. Each function or class definition becomes one chunk, so a chunk always corresponds to something semantically complete. Currently supports Python and JavaScript; unsupported file types fall back to whole-file chunking rather than being silently dropped.
3. Filter - files that look like numeric data (e.g. YOLO label files, one line of floats per row) are skipped based on their content, not their extension or folder name, so this works for any dataset structure, not just the one repo it was tested against.
4. Embed - each chunk is embedded with qwen3-embedding, chosen after directly benchmarking it against bge-m3 (the model used in an earlier RAG project) on real code snippets - qwen3-embedding produced a meaningfully larger similarity gap between related and unrelated code.
5. Index - embeddings are stored in a local, persistent Chroma database.
6. Search - a natural-language question is embedded and matched against the index via cosine similarity, returning the most relevant code chunks with file path and line numbers.

The agent (LangGraph, ReAct pattern) exposes three tools - load_repo, describe_repo, find_code - and decides which to call based on the request. Everything runs locally via Ollama (qwen2.5:7b for chat, qwen3-embedding for embeddings).

A Streamlit UI (app.py) sits on top for interactive use - load a repo from the sidebar, then ask questions in a chat interface.

## Cross-language retrieval

Because chunking and embedding are language-agnostic, a natural-language query returns relevant code regardless of which language it's written in. In testing, the same query ("which function performs division and handles the divide-by-zero case") returned the Python and JavaScript versions of an equivalent function as the top two results, at nearly identical similarity scores - the model matched on what the code does, not what language it's in.

## Requirements

- Python 3.11+
- git installed and available on PATH
- Ollama (https://ollama.com) installed and running, with:
  - ollama pull qwen2.5:7b
  - ollama pull qwen3-embedding

## Setup

1. Create and activate a virtual environment:
   - python -m venv venv
   - venv\Scripts\activate (Windows)
2. Install dependencies:
   - pip install -r requirements.txt

## Usage

Web UI (recommended):
- streamlit run app.py
- Paste a GitHub URL in the sidebar, click "Load repo", then ask questions in the chat box.

Script:
- Edit the message in agent.py, then run: python agent.py

## Design notes / lessons learned

- Extension-based file filtering isn't enough for real-world repos. Tested against a real computer-vision repo (YOLO/Roboflow-based), the initial version indexed hundreds of numeric label files as if they were text documentation, because they had a .txt extension like the README. The fix was content-based: sample a file's lines and skip it if most of them are just numbers, regardless of extension or folder name.
- Oversized chunks are split, not dropped or truncated. A function or file that exceeds the embedding model's context window is broken into sequential parts by line count, so no content is silently lost - at the cost of occasionally splitting a chunk mid-logic-block, which is noted as a known limitation below.
- Tools that lazily initialize shared state need explicit thread-safety. Early versions of load_repo, describe_repo, and find_code all read/wrote a shared "currently loaded repo" variable. LangGraph can call multiple tools concurrently, and this caused a real race condition: two tool calls would both see "not loaded yet" and both try to clone the same repo folder at once, corrupting the clone mid-delete. The fix was not a prompt instruction ("call tools in order") but a threading.Lock wrapped around the load/cache logic, making concurrent calls safe by construction rather than by hoping the model behaves. Tools that only read from pre-built state (no lazy initialization) don't have this risk.
- Windows-specific: git leaves some .git files read-only, which crashes shutil.rmtree on Windows (works fine on Linux/Mac). Fixed with an onerror handler that clears the read-only flag and retries.
- Local models are noticeably slower than hosted assistants like Copilot for this kind of workload, mostly because of hardware (consumer GPU vs datacenter GPUs) and because each query involves multiple LLM calls (tool selection, then answer generation) plus a separate embedding call. The tradeoff is zero cost, full data locality, and no internet dependency - relevant for privacy-sensitive contexts.

## Known limitations

- Only Python and JavaScript get real syntax-aware chunking; other languages fall back to whole-file chunking, which is much coarser.
- Splitting oversized chunks by line count can cut through a function's logic rather than a clean boundary.
- Multi-repo support isn't tested end-to-end - the cache keys by URL, but the Streamlit UI currently assumes one active repo per session.
- create_react_agent (LangGraph) is deprecated in favor of langchain.agents.create_agent; not yet migrated.

## Project structure

- chunker.py - tree-sitter based, language-agnostic code chunking
- clone_repo.py - shallow git clone, with a Windows read-only-file fix
- indexer.py - walks a repo, filters data-like files, chunks, embeds, and stores in Chroma
- tools.py - load_repo, describe_repo, find_code (LangGraph tools), with thread-safe shared state
- agent.py - the LangGraph ReAct agent definition
- app.py - Streamlit chat UI
- experiments/ - earlier standalone scripts kept for reference: the first tree-sitter test before chunker.py existed, a manual retrieval test script, the bge-m3 vs qwen3-embedding comparison that motivated the embedding model choice, and the sample Python/JS files used to test chunking
- requirements.txt
- README.md

