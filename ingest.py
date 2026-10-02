from loaders import load_file
from shared import model, collection
import uuid


def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def ingest_file(file_path, source_name):
    text = load_file(file_path)
    chunks = chunk_text(text)
    embeddings = model.encode(chunks).tolist()
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"source": source_name} for _ in chunks]

    collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    return len(chunks)


if __name__ == "__main__":
    ingest_file("data/attention_is_all_you_need.pdf", "attention_paper")