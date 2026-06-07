import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import rag_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Pre-loading embedding model …")
    try:
        rag_pipeline._get_embeddings()
    except Exception as e:
        logger.warning("Could not pre-load embeddings: %s", e)
    yield


app = FastAPI(
    title="RAG Chatbot API",
    description="PDF Q&A powered by LangChain, FAISS, and Google Gemini.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://doc-mind-pdf-q-a-chatbot-6q1m8muzs.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


class SourceChunk(BaseModel):
    chunk_index: int
    text: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


class UploadResponse(BaseModel):
    status: str
    chunk_count: int


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse, tags=["Utility"])
async def health():
    return {"status": "ok"}


@app.post("/upload", response_model=UploadResponse, tags=["RAG"])
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    logger.info("Received: %s (%d bytes)", file.filename, len(raw))
    rag_pipeline.reset_state()

    try:
        text = rag_pipeline.extract_text_from_pdf(raw)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("PDF extraction failed.")
        raise HTTPException(status_code=500, detail=f"PDF extraction error: {e}")

    try:
        count = rag_pipeline.build_vector_store(text, filename=file.filename)
    except Exception as e:
        logger.exception("Vector store build failed.")
        raise HTTPException(status_code=500, detail=f"Indexing error: {e}")

    logger.info("Indexed %d chunks from '%s'.", count, file.filename)
    return {"status": "ready", "chunk_count": count}


@app.post("/chat", response_model=ChatResponse, tags=["RAG"])
async def chat(request: ChatRequest):
    q = request.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    try:
        result = rag_pipeline.answer_question(q)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EnvironmentError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Chat pipeline failed.")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    return {"answer": result["answer"], "sources": result["sources"]}
