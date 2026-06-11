import os
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_google_vertexai import VertexAIEmbeddings
from crawler.crawl import crawl_faq
from crawler.refactor import refactor_faq

INDEX_DIR = os.path.join(os.path.dirname(__file__), "faiss_index")

def ingest_data(embeddings_model=None):
    """
    Crawls, refactors, chunks, embeds, and indexes the FAQ articles in FAISS.
    """
    # 1. Crawl FAQ
    raw_articles = crawl_faq()
    if not raw_articles:
        print("No articles found to ingest.")
        return

    # 2. Refactor (brand replacement)
    refactored_articles = refactor_faq(raw_articles)

    # 3. Create Documents
    documents = []
    for art in refactored_articles:
        content = f"Question: {art['question']}\nAnswer: {art['answer']}"
        doc = Document(
            page_content=content,
            metadata={"question": art["question"], "answer": art["answer"]}
        )
        documents.append(doc)

    # 4. Embed and Index
    if embeddings_model is None:
        # Default Vertex AI Embeddings
        embeddings_model = VertexAIEmbeddings(
            model_name="text-multilingual-embedding-002",
            project="anggar-conv-agent",
            location="asia-southeast1"
        )

    print(f"Creating FAISS index with {len(documents)} documents...")
    vector_store = FAISS.from_documents(documents, embeddings_model)

    # 5. Save locally
    os.makedirs(INDEX_DIR, exist_ok=True)
    vector_store.save_local(INDEX_DIR)
    print(f"FAISS index successfully saved to {INDEX_DIR}")

if __name__ == "__main__":
    ingest_data()
