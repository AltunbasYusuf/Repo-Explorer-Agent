import ollama
import numpy as np

def get_embedding(model, text):
    response = ollama.embeddings(model=model, prompt=text)
    return np.array(response["embedding"])

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Real code snippets from test_sample.py
add_func = """def add(self, a, b):
    return a + b"""

subtract_func = """def subtract(self, a, b):
    return a - b"""

divide_func = """def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b"""

unrelated_code = """import os

def read_config_file(path):
    with open(path, "r") as f:
        return f.read()"""

def run_comparison(model_name):
    print(f"=== Model: {model_name} ===\n")

    ref = get_embedding(model_name, add_func)

    for label, code in [
        ("subtract (similar - both simple arithmetic)", subtract_func),
        ("divide (related - also arithmetic, but has error handling)", divide_func),
        ("unrelated (file reading, no arithmetic)", unrelated_code),
    ]:
        vec = get_embedding(model_name, code)
        sim = cosine_similarity(ref, vec)
        print(f"Similarity to 'add': {sim:.4f}  <-  {label}")

    print()

run_comparison("bge-m3")
run_comparison("qwen3-embedding")