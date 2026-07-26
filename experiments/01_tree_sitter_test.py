import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

with open("test_sample.py", "r", encoding="utf-8") as f:
    source_code = f.read()

tree = parser.parse(bytes(source_code, "utf-8"))

def print_node(node, source_bytes, depth=0):
    if node.type in ("function_definition", "class_definition"):
        name_node = node.child_by_field_name("name")
        name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        print(f"{'  ' * depth}[{node.type}] {name} (lines {start_line}-{end_line})")

    for child in node.children:
        print_node(child, source_bytes, depth + 1)

source_bytes = bytes(source_code, "utf-8")
print_node(tree.root_node, source_bytes)
