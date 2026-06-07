# DocMind — PDF Q&A Chatbot

Upload a PDF, ask questions about it in plain English. The app finds the relevant sections and uses Google's Gemini to answer — strictly from your document, not from the model's general knowledge.

## 🌐 Live Demo

| Layer | URL |
| :--- | :--- |
| **Frontend** | [https://doc-mind-pdf-q-a-chatbot-6q1m8muzs.vercel.app](https://doc-mind-pdf-q-a-chatbot-6q1m8muzs.vercel.app) |
| **Backend API** | [https://docmind-pdf-q-a-chatbot-production.up.railway.app](https://docmind-pdf-q-a-chatbot-production.up.railway.app) |
| **API Docs (Swagger)** | [https://docmind-pdf-q-a-chatbot-production.up.railway.app/docs](https://docmind-pdf-q-a-chatbot-production.up.railway.app/docs) |

---

## What it does

- Extracts text from any uploaded PDF using PyMuPDF
- Splits the text into overlapping chunks and embeds them locally using `paraphrase-MiniLM-L3-v2`
- Stores vectors in a FAISS index (in memory, no database needed)
- On each question, retrieves the top 5 matching chunks and sends them to Gemini with a strict grounding prompt
- If the answer isn't in the document, it says so instead of making something up
- Falls back across multiple Gemini models (`gemini-flash-lite-latest` → `gemini-2.0-flash-lite` → `gemini-2.0-flash`) if one hits a quota limit
- Chat history and document info persist in `localStorage` so a page refresh doesn't lose your session
- Source chunks for every AI response are viewable through an expandable drawer

---

## Stack

**Backend:** Python 3.10+, FastAPI, LangChain, FAISS (CPU), PyMuPDF, Google Generative AI SDK, Sentence Transformers, python-dotenv

**Frontend:** React 18, Vite 5, plain CSS (Inter font, dark theme)

**Deployment:** Railway (backend) · Vercel (frontend)

---

## Project structure

```text
DocMind-PDF-Q-A-Chatbot/
├── backend/
│   ├── main.py               # FastAPI app — endpoints (upload, chat, health), CORS, Pydantic models
│   ├── rag_pipeline.py        # PDF extraction, chunking, embedding, FAISS indexing, Gemini generation
│   ├── requirements.txt       # Python dependencies
│   ├── build.sh               # Render/Railway build script — installs deps & pre-downloads the embedding model
│   ├── .env.example           # Template for local environment variables
│   └── .env                   # Not committed — add your GEMINI_API_KEY here
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx   # Chat area — message list, typing indicator, textarea input
│   │   │   ├── MessageBubble.jsx# Single message with avatar, bubble, timestamp, and source drawer
│   │   │   ├── SourceDrawer.jsx # Expandable panel showing retrieved source chunks per answer
│   │   │   └── UploadZone.jsx   # Drag-and-drop / click-to-upload PDF zone
│   │   ├── App.jsx              # Root component — sidebar, chat, localStorage persistence, toasts
│   │   ├── App.css              # Full design system — dark theme, variables, animations, responsive
│   │   └── main.jsx             # React 18 entry point — mounts <App /> into #root
│   ├── index.html               # HTML shell with SEO meta, Inter font, emoji favicon
│   ├── vite.config.js           # Vite config — dev proxy for /upload, /chat, /health → port 8000
│   ├── vercel.json              # Vercel SPA rewrite rule — all routes → index.html
│   ├── .env.production          # Production env — VITE_API_URL for the deployed backend
│   └── package.json             # React 18, Vite 5
├── .gitignore
└── README.md
```

---

## Environment variables

### Backend (`backend/.env`)

| Variable | Required | Description |
| :--- | :---: | :--- |
| `GEMINI_API_KEY` | ✅ | Your Google Gemini API key. Get one free at [Google AI Studio](https://aistudio.google.com/app/apikey) |

### Frontend (`frontend/.env.production`)

| Variable | Required | Description |
| :--- | :---: | :--- |
| `VITE_API_URL` | ✅ | Absolute URL of the deployed backend (e.g. `https://docmind-pdf-q-a-chatbot-production.up.railway.app`) |

> **Note:** In the current codebase, the backend URL is hardcoded in `App.jsx` and `UploadZone.jsx` as the `BASE` constant. If you redeploy the backend to a different URL, update `BASE` in both files.

---

## Setup (local development)

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

> First run will download the `paraphrase-MiniLM-L3-v2` model (~60MB) from Hugging Face. It gets cached after that.

Copy the env template and add your key:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and set:

```
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

Start the server:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API runs at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

---

### Frontend

```bash
cd frontend
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
| `EMBEDDING_MODEL` | `paraphrase-MiniLM-L3-v2` | Local embedding model (Sentence Transformers) |

Smaller chunks give more precise retrieval but may lose context within a single idea. Larger chunks preserve context but dilute the semantic signal. 500/50 is a reasonable starting point for most documents.

---

## Deploying

### Backend → Railway

1. Push the repo to GitHub.
2. Create a new Railway project and connect the GitHub repo.
3. Set the **Root Directory** to `backend`.
4. Add the environment variable `GEMINI_API_KEY` in the Railway dashboard.
5. Set the **Build Command** to:
   ```bash
   pip install -r requirements.txt && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
   ```
   (This is what `build.sh` runs — it installs dependencies and pre-downloads the embedding model so the first request doesn't time out.)
6. Set the **Start Command** to:
   ```bash
   gunicorn -k uvicorn.workers.UvicornWorker main:app
   ```
7. After deploy, note the Railway URL (e.g. `https://docmind-pdf-q-a-chatbot-production.up.railway.app`).
8. Add this URL to the `allow_origins` list in `backend/main.py` if your frontend is on a different domain.

### Frontend → Vercel

1. Import the same GitHub repo into Vercel.
2. Set the **Root Directory** to `frontend`.
3. **Framework Preset:** Vite
4. **Build Command:** `npm run build`
5. **Output Directory:** `dist`
6. Add the environment variable:
   ```
   VITE_API_URL=https://docmind-pdf-q-a-chatbot-production.up.railway.app
   ```
7. Deploy. The `vercel.json` SPA rewrite rule handles client-side routing.
8. Copy the Vercel deployment URL and add it to `allow_origins` in `backend/main.py` so the backend accepts requests from the frontend.

### CORS configuration

The backend's CORS whitelist is in `backend/main.py`:

```python
allow_origins=[
    "http://localhost:5173",                                       # local dev
    "https://doc-mind-pdf-q-a-chatbot-6q1m8muzs.vercel.app",      # production frontend
]
```

If you redeploy the frontend and get a new URL, add it here and redeploy the backend.

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