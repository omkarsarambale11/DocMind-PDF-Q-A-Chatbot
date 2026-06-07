import os
import logging
from typing import Optional

import fitz
from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

load_dotenv()

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 5
EMBEDDING_MODEL = "paraphrase-MiniLM-L3-v2"

SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer ONLY using the provided context. "
    "If the answer is not in the context, say: "
    "'I could not find that in the uploaded document.' "
    "Do not make up information."
)

_vector_store: Optional[FAISS] = None
_chunks: list[str] = []
_embeddings_model: Optional[HuggingFaceEmbeddings] = None
_genai_configured: bool = False
_doc_filename: str = ""
_first_chunk: str = ""

# gemini-flash-lite-latest tends to have quota when flash-2.0 is exhausted
_CANDIDATE_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
]


def _get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings_model
    if _embeddings_model is None:
        logger.info("Loading embedding model '%s' …", EMBEDDING_MODEL)
        _embeddings_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        logger.info("Embedding model loaded.")
    return _embeddings_model


def _configure_genai() -> None:
    global _genai_configured
    if not _genai_configured:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. "
                "Get a free key at: https://aistudio.google.com/app/apikey"
            )
        genai.configure(api_key=api_key)
        _genai_configured = True


def _call_gemini(prompt: str) -> str:
    """Try each candidate model in order, skipping quota-exhausted ones."""
    _configure_genai()
    last_err = None
    for model_name in _CANDIDATE_MODELS:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_PROMPT,
            )
            resp = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=2048,
                ),
                request_options={"timeout": 30},
            )
            logger.info("Gemini ok: %s", model_name)
            return resp.text
        except google_exceptions.ResourceExhausted as e:
            logger.warning("Quota exhausted for %s", model_name)
            last_err = e
        except google_exceptions.InvalidArgument as e:
            logger.warning("Model unavailable %s: %s", model_name, e)
            last_err = e
        except Exception as e:
            raise RuntimeError(f"Gemini error: {e}") from e

    raise RuntimeError(
        f"All models quota-exhausted. Create a new API key at "
        f"https://aistudio.google.com/app/apikey — last error: {last_err}"
    )


def extract_text_from_pdf(file_bytes: bytes) -> str:
    parts: list[str] = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            parts.append(page.get_text("text"))
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError("No extractable text found. The PDF may be scanned/image-only.")
    return text


def build_vector_store(text: str, filename: str = "") -> int:
    global _vector_store, _chunks, _doc_filename, _first_chunk

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    raw_chunks = splitter.split_text(text)
    if not raw_chunks:
        raise ValueError("Text splitting produced zero chunks.")

    _chunks = raw_chunks
    _doc_filename = filename
    _first_chunk = text[:1000].strip()

    docs = [
        Document(page_content=c, metadata={"chunk_index": i})
        for i, c in enumerate(raw_chunks)
    ]

    embeddings = _get_embeddings()
    logger.info("Building FAISS index for %d chunks …", len(docs))
    _vector_store = FAISS.from_documents(docs, embeddings)
    return len(docs)


def answer_question(question: str) -> dict:
    if _vector_store is None:
        raise RuntimeError("No document uploaded yet.")

    retriever = _vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": TOP_K},
    )
    docs = retriever.invoke(question)

    if not docs:
        return {"answer": "I could not find that in the uploaded document.", "sources": []}

    seen = set()
    ctx_parts = []
    sources = []

    if _first_chunk:
        ctx_parts.append(f"[Document opening]:\n{_first_chunk}")

    for doc in docs:
        idx = doc.metadata.get("chunk_index", -1)
        if idx not in seen:
            seen.add(idx)
            ctx_parts.append(doc.page_content)
        sources.append({"chunk_index": idx, "text": doc.page_content})

    filename_hint = f"Document filename: {_doc_filename}\n\n" if _doc_filename else ""
    ctx = filename_hint + "\n\n---\n\n".join(ctx_parts)

    answer = _call_gemini(f"Context:\n{ctx}\n\nQuestion: {question}")
    return {"answer": answer.strip(), "sources": sources}


def reset_state() -> None:
    global _vector_store, _chunks, _doc_filename, _first_chunk
    _vector_store = None
    _chunks = []
    _doc_filename = ""
    _first_chunk = ""
