from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
# from dotenv import load_dotenv
# from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer

# import os

# load_dotenv()

# client = ChatGroq(
    # model = "llama-3.1-8b-instant",
    # api_key = os.getenv("GROQ_API_KEY")
# )

embed_model = SentenceTransformer('all-MiniLM-L6-v2')
# EMBED_MODEL = "groq-embed-4k"
EMBED_DIM = 3072

splitter = SentenceSplitter(chunk_size = 1_000, chunk_overlap = 200)

def load_and_split_pdf(path: str):
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks

def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings = embed_model.encode(texts)
    return embeddings.tolist()
