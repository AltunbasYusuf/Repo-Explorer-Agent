import os
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser

LANGUAGES = {
    ".py": Language(tspython.language()),
    ".js": Language(tsjavascript.language()),
    ".jsx": Language(tsjavascript.language()),
}

# Node types that count as "definitions" per language
DEFINITION_TYPES = {
    ".py": ("function_definition", "class_definition"),
    ".js": ("function_declaration", "class_declaration", "method_definition"),
    ".jsx": ("function_declaration", "class_declaration", "method_definition"),
}


def get_language_for_file(filepath):
    ext = os.path.splitext(filepath)[1]
    return LANGUAGES.get(ext), DEFINITION_TYPES.get(ext), ext


def extract_chunks_from_file(filepath):
    """Extract function/class definitions from a source file as chunk dicts.
    Falls back to whole-file chunking for unsupported languages."""

    language, def_types, ext = get_language_for_file(filepath)

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        source_code = f.read()

    if language is None:
        # Unsupported language - treat the whole file as one chunk
        return [{
            "name": os.path.basename(filepath),
            "type": "file",
            "code": source_code,
            "file": filepath,
            "start_line": 1,
            "end_line": source_code.count("\n") + 1,
        }]

    parser = Parser(language)
    source_bytes = bytes(source_code, "utf-8")
    tree = parser.parse(source_bytes)

    chunks = []

    def walk(node):
        if node.type in def_types:
            name_node = node.child_by_field_name("name")
            name = (
                source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
                if name_node else "<anonymous>"
            )
            code_text = source_bytes[node.start_byte:node.end_byte].decode("utf-8")
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1

            chunks.append({
                "name": name,
                "type": node.type,
                "code": code_text,
                "file": filepath,
                "start_line": start_line,
                "end_line": end_line,
            })
            return

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    # If nothing was found (e.g. a file with no top-level functions/classes),
    # fall back to whole-file chunking so we don't lose the file entirely.
    if not chunks:
        chunks.append({
            "name": os.path.basename(filepath),
            "type": "file",
            "code": source_code,
            "file": filepath,
            "start_line": 1,
            "end_line": source_code.count("\n") + 1,
        })

    return chunks


if __name__ == "__main__":
    chunks = extract_chunks_from_file("experiments/test_sample.py")
    for c in chunks:
        print(f"[{c['type']}] {c['name']} (lines {c['start_line']}-{c['end_line']})")

    print("\n--- JavaScript file ---")
    chunks = extract_chunks_from_file("test_sample.js")
    for c in chunks:
        print(f"[{c['type']}] {c['name']} (lines {c['start_line']}-{c['end_line']})")