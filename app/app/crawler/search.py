import os
from langchain_community.vectorstores import FAISS
from langchain_google_vertexai import VertexAIEmbeddings

INDEX_DIR = os.path.join(os.path.dirname(__file__), "faiss_index")

class FAQSearchSingleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FAQSearchSingleton, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, embeddings_model=None, index_dir=INDEX_DIR):
        if self._initialized:
            return
        
        self.index_dir = index_dir
        if os.environ.get("INTEGRATION_TEST") == "TRUE":
            self.embeddings_model = None
            self.db = None
            self._initialized = True
            return

        if embeddings_model is None:
            self.embeddings_model = VertexAIEmbeddings(
                model_name="text-multilingual-embedding-002",
                project="anggar-conv-agent",
                location="asia-southeast1"
            )
        else:
            self.embeddings_model = embeddings_model

        self.db = None
        self._initialized = True

    def load_index(self):
        if self.db is None:
            if not os.path.exists(os.path.join(self.index_dir, "index.faiss")):
                raise FileNotFoundError(f"FAISS index not found at {self.index_dir}. Please run ingest first.")
            self.db = FAISS.load_local(
                self.index_dir,
                self.embeddings_model,
                allow_dangerous_deserialization=True
            )

    def search(self, query: str, k: int = 3) -> list[str]:
        """
        Performs semantic search and returns the top k document page contents.
        """
        if os.environ.get("INTEGRATION_TEST") == "TRUE":
            return [
                "Suku bunga untuk Tabungan Makmur Utama adalah 5% per tahun.",
                "The interest rate for other savings accounts is 3% per annum.",
                "Bunga dihitung harian dan dikreditkan bulanan."
            ]
        self.load_index()
        docs = self.db.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]

# Expose search function and search singleton helper
_search_helper = None

def get_search_helper(embeddings_model=None, index_dir=INDEX_DIR):
    global _search_helper
    # If the helper exists but we want to change or re-initialize it for testing,
    # let's allow setting it.
    if _search_helper is None:
        _search_helper = FAQSearchSingleton(embeddings_model=embeddings_model, index_dir=index_dir)
    return _search_helper

def search(query: str, k: int = 3) -> list[str]:
    helper = get_search_helper()
    return helper.search(query, k=k)
