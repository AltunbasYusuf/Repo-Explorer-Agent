import chromadb
import ollama

EMBED_MODEL = "qwen3-embedding"
DB_PATH = "chroma_db"
COLLECTION_NAME = "code_index"


def get_embedding(text):
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def search(query, n_results=3):
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    print(f'Query: "{query}"\n')

    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )

    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        print(f"  {meta['name']} ({meta['file']}:{meta['start_line']}-{meta['end_line']}) | Distance: {distance:.4f}")
    print()


if __name__ == "__main__":
    search("Where is the vector database index built from a folder of files?")
    search("Which function performs division and handles the divide by zero case?")
    search("How are embeddings compared between two models?")