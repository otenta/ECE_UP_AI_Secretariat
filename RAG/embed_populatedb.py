# index_translated.py
import argparse, json
from langchain.schema import Document
from get_embedding_function import get_embedding_function
from langchain_chroma import Chroma

def load_translated_chunks(path):
    docs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            id_ = f"{rec['page']}_{rec['chunk_id']}"
            docs.append(Document(
                page_content=rec["text"],
                metadata={"page":rec["page"], "chunk_id":rec["chunk_id"], "id":id_}
            ))
    return docs

def main(translated_jsonl, chroma_path, reset=False):
    if reset:
        import shutil, os
        if os.path.isdir(chroma_path):
            shutil.rmtree(chroma_path)

    docs = load_translated_chunks(translated_jsonl)
    texts = [d.page_content for d in docs]
    embeddings = get_embedding_function()
    # embs = embeddings.embed_documents(texts)

    db = Chroma(
        collection_name="regulations",
        persist_directory=chroma_path,
        embedding_function=embeddings)
    ids       = [d.metadata["id"] for d in docs]
    metadatas = [{"page":d.metadata["page"], "chunk_id":d.metadata["chunk_id"]} for d in docs]

    # db._collection.upsert(
    #     documents=texts,
    #     embeddings=embs,
    #     metadatas=metadatas,
    #     ids=ids
    # )
    db.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    print(f"Indexed {len(docs)} chunks into {chroma_path}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--jsonl", default ="data/translated_stream.jsonl", help="translated_stream.jsonl")
    p.add_argument("--chroma", default="chroma")
    p.add_argument("--reset", action="store_true")
    args = p.parse_args()
    main(args.jsonl, args.chroma, args.reset)
