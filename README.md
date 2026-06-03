# DocMind — PDF Q&A Chatbot

Upload a PDF, ask questions about it in plain English. The app finds the relevant sections and uses Google's Gemini to answer — strictly from your document, not from the model's general knowledge.

---

## What it does

- Extracts text from any uploaded PDF using PyMuPDF
- Splits the text into overlapping chunks and embeds them locally using `all-MiniLM-L6-v2`
- Stores vectors in a FAISS index (in memory, no database needed)
- On each question, retrieves the top 5 matching chunks and sends them to Gemini with a strict grounding prompt
- If the answer isn't in the document, it says so instead of making something up
- Falls back across multiple Gemini models (`gemini-flash-lite-latest` → `gemini-2.0-flash-lite` → `gemini-2.0-flash`) if one hits a quota limit

---

## Stack

**Backend:** Python 3.10+, FastAPI, LangChain, FAISS (CPU), PyMuPDF, Google Generative AI SDK, python-dotenv

**Frontend:** React 18, Vite, plain CSS

---

## Project structure

Rag_chatbot/
├── backend/
│   ├── main.py             # FastAPI endpoints (upload, chat, health)
│   ├── rag_pipeline.py     # Extraction, chunking, embedding, FAISS, generation
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                # Not committed — add your API key here
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   ├── SourceDrawer.jsx
│   │   │   └── UploadZone.jsx
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── index.css
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── .gitignore
└── README.md

---

## Setup

### Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- Gemini API key — get one free at [Google AI Studio](https://aistudio.google.com/app/apikey)

---

### Backend

```bash
cd backend
```

Create and activate a virtual environment:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

> First run will download the `all-MiniLM-L6-v2` model (~90MB) from Hugging Face. It gets cached after that.

Copy the env template and add your key:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and set:
GEMINI_API_KEY=your_actual_gemini_api_key_here
Start the server:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API runs at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

---

### Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`. Vite proxies all `/upload`, `/chat`, and `/health` requests to port 8000, so no CORS config is needed locally.

---

## API

### `GET /health`

```json
{ "status": "ok" }
```

### `POST /upload`

Accepts a PDF via `multipart/form-data` (field name: `file`). Extracts, chunks, embeds, and indexes it.

```json
{
  "status": "ready",
  "chunk_count": 142
}
```

### `POST /chat`

```json
{ "question": "What are the main findings?" }
```

```json
{
  "answer": "According to the document...",
  "sources": [
    { "chunk_index": 12, "text": "The model exhibits..." }
  ]
}
```

---

## Tuning retrieval

These constants are at the top of `backend/rag_pipeline.py`:

| Constant | Default | What it controls |
| :--- | :--- | :--- |
| `CHUNK_SIZE` | `500` | Characters per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between adjacent chunks |
| `TOP_K` | `5` | Chunks retrieved per query |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Local embedding model |

Smaller chunks give more precise retrieval but may lose context within a single idea. Larger chunks preserve context but dilute the semantic signal. 500/50 is a reasonable starting point for most documents.

---

## Pushing to GitHub

```bash
# From the project root
git init
git status  # confirm .env, venv/, and node_modules/ are not listed
git add .
git commit -m "feat: initial commit"
git branch -M main
git remote add origin <your_github_repo_url>
git push -u origin main
```

Never commit your `.env` file. If you accidentally push your API key, revoke it immediately at [Google AI Studio](https://aistudio.google.com/app/apikey).

---

## Deploying

**Backend:** Render, Railway, or Heroku work fine. Use `gunicorn -k uvicorn.workers.UvicornWorker main:app` as the start command and set `GEMINI_API_KEY` as an environment variable in the dashboard.

**Frontend:** Build with `npm run build` inside `frontend/`, then deploy the `dist/` folder to Vercel or Netlify. If the backend is on a separate domain, add that domain to `allow_origins` in `backend/main.py`.