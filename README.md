# PaperPilot — AI Research Paper Assistant

Upload research papers as PDFs, ask questions about them in plain English, and get answers that are built only from passages actually retrieved from those papers — with the filename and page number shown for every claim.

---

## Overview

Reading a research paper to find one specific thing — the dataset, the baseline, the stated limitation — means skimming twenty pages. PaperPilot indexes the paper once, then answers questions against it in seconds.

The important part is *how* it answers. It does not send the whole PDF to a language model and hope for the best. It runs a real **Retrieval-Augmented Generation (RAG)** pipeline: the paper is split into passages, each passage is turned into a vector, your question is turned into a vector, and only the handful of passages closest in meaning to your question are given to the model. The model is instructed to answer from those passages, to cite them, and to say when they do not contain the answer.

## Problem statement

Three problems, in order of importance:

1. **Language models invent plausible-sounding detail.** Asked about a paper it has not seen, a model will confidently produce a methodology section that does not exist. Grounding the model in retrieved text and showing the source makes unsupported claims visible and checkable.
2. **Context windows are finite and expensive.** Stuffing several 30-page papers into every request is slow and wasteful, and burying the relevant paragraph in 40,000 tokens of noise measurably degrades answer quality.
3. **Keyword search misses the point.** Ctrl-F for "dataset" does not find "experiments were conducted over CIFAR-100". Semantic search does.

## Features

**Papers**
- Upload one or several PDFs at once, by drag-and-drop or file picker
- File type validated by extension *and* by file signature, so a renamed `.txt` is rejected
- Size limit, empty-file check, password-protected and image-only PDF detection
- Duplicate detection by SHA-256 content hash, so the same paper is not indexed twice
- Per-file results: one bad PDF in a batch of five does not block the other four
- Library view with page count, indexed-passage count, size and upload time
- Delete a paper, which removes its vectors from the index immediately

**Asking**
- Chat interface with user turns, answers, loading state and typed error states
- Inline citation markers (`S1`, `S2`) in the answer, linked to expandable footnotes showing the exact retrieved passage, filename, page and match score
- Two explanation modes: plain language (expands jargon, beginner-friendly) and technical (keeps the paper's terminology, numbers and method names)
- Search all papers, or narrow to a selected subset
- Cross-paper questions such as "Compare the methodologies used in these papers"
- Follow-up questions: the last few turns are sent so pronouns resolve, but only retrieved passages are ever treated as facts
- Clear conversation
- Honest "I could not find that in your papers" instead of a guess when retrieval comes back empty

---

## Architecture

```
┌──────────────────────── Browser (React + Vite) ────────────────────────┐
│  Overview   Add papers   Library   Ask                                 │
│                    src/api/client.js  (the only place fetch is called) │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │ JSON / multipart over HTTP
┌────────────────────────────────▼───────────────────────────────────────┐
│                        FastAPI backend                                 │
│                                                                        │
│  api/routes_documents.py        api/routes_chat.py                     │
│           │                              │                             │
│  services/document_service.py            │   (validation, registry)    │
│           │                              │                             │
│           └──────────► rag/pipeline.py ◄─┘                             │
│                          │                                             │
│      ┌───────────────────┼────────────────────┬──────────────┐         │
│      ▼                   ▼                    ▼              ▼         │
│  pdf_loader.py       chunker.py         embeddings.py    prompts.py    │
│  (PyMuPDF)       (size + overlap)     (Gemini / local)  (grounding)    │
│                                              │                         │
│                                              ▼                         │
│                                      vector_store.py                   │
│                                      (ChromaDB, on disk)               │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │ HTTPS (API key stays server-side)
                     Gemini embeddings + Gemini chat model
```

Layers are kept honest: routes only validate and shape HTTP, the service owns document lifecycle, `rag/` owns the pipeline, and nothing in `rag/` knows FastAPI exists. Each RAG stage is its own module so any one of them can be swapped or explained in isolation.

---

## The RAG pipeline in detail

### Ingestion — runs once per uploaded paper

| Stage | Module | What happens |
|---|---|---|
| 1. Extract | `rag/pdf_loader.py` | PyMuPDF reads text page by page. The **page number is captured here** and carried through every later stage — this is what makes "page 7" citations possible. |
| 2. Clean | `rag/pdf_loader.py` | Re-joins words hyphenated across line breaks, collapses the stray single newlines that two-column layouts insert mid-sentence, strips control characters. Dirty text produces dirty embeddings. |
| 3. Chunk | `rag/chunker.py` | Each page is split into ~1,000-character passages with 150 characters of overlap, cut at the nearest paragraph / sentence / clause boundary. Chunks never span two pages. |
| 4. Metadata | `rag/chunker.py` | Every chunk carries `document_id`, `filename`, `page`, `chunk_index`, `chunk_id`. |
| 5. Embed | `rag/embeddings.py` | Chunks are embedded in batches of 64, with retry on transient API failures. |
| 6. Store | `rag/vector_store.py` | Vectors plus metadata plus the original text are upserted into a persistent Chroma collection using cosine distance. |

If any stage fails, partially written vectors for that document are rolled back, so a failed upload never leaves orphan passages in the index.

### Query — runs on every question

| Stage | What happens |
|---|---|
| 1. Embed the question | Same model as ingestion. With the Google provider the question is embedded with `task_type=retrieval_query` while chunks used `retrieval_document` — an asymmetric pairing that is tuned for exactly this "short question, long passage" case. |
| 2. Similarity search | Chroma returns the **top-K** (default 6) nearest chunks, optionally filtered to selected documents via metadata. |
| 3. Relevance cut-off | Anything further than `MAX_DISTANCE` (default 0.85 cosine) is discarded. If nothing survives, the user is told no relevant passage was found — the model is never called. |
| 4. Build context | Surviving chunks are rendered as a numbered block: `[S1] Paper: smith2023.pdf | Page: 4` followed by the passage text. |
| 5. Prompt | Grounding rules + mode-specific style + optional recent-turn transcript + the context block + the question. |
| 6. Generate | Gemini, temperature 0.2 — this is a reading task, not a creative one. |
| 7. Resolve sources | The `[S1]`-style markers the model used are matched back to their chunks, so the footnotes show exactly the passages that supported the answer. |

**An honest note on hallucination.** Grounding does not eliminate it. The model can still misread a passage, over-generalise, or cite loosely, and retrieval can still miss the passage that held the answer. What this design does is make every claim checkable in one click, and make "not in these papers" an available answer rather than a failure mode. That distinction matters more than a guarantee nobody can make.

### Why chunking is necessary

An embedding is a fixed-size summary of its input. Embed an entire 12-page paper and you get one blurred vector that is vaguely near everything and precisely near nothing. Chunking gives retrieval something specific to match against, keeps the prompt small, and keeps citations at a granularity a human can verify.

Chunk size is a trade-off. Too small and a passage loses the context that makes it meaningful ("it improves accuracy by 4%" — what does?). Too large and one chunk covers several topics, so its vector is muddy and the prompt fills with irrelevant text. Around 1,000 characters is roughly one dense paragraph of a paper, which is the natural unit of an argument.

Overlap exists because a hard cut can land in the middle of the one sentence that matters. Repeating the last 150 characters at the start of the next chunk means a fact straddling a boundary still appears intact somewhere.

Chunks never cross page boundaries. That costs a little redundancy and buys precise citations.

### Why embeddings, and why not keyword search

An embedding maps text to a list of numbers positioned so that similar *meanings* land close together. "What data did they train on?" and "experiments were run over CIFAR-100" share almost no words but sit near each other in embedding space. Cosine similarity — the angle between two vectors — is what "close" means here.

Keyword search fails this use case because academic writing is full of synonyms and paraphrase, questions are asked in the reader's vocabulary rather than the author's, and the reader usually does not know the paper's exact terminology yet. Keyword search is better at exact identifiers; a production system often combines both (see Future improvements).

### Why a vector database

Finding the nearest vectors among tens of thousands means an approximate nearest-neighbour index, which a normal relational database does not provide. Chroma gives that, stores metadata alongside each vector so results can be filtered by document and can report their page, keeps the original text for display, and persists to a folder on disk.

**Top-K** means "return the K closest passages". It is the main recall/noise dial: too small and the answering passage may be missing; too large and the prompt fills with distractors that can pull the model off course.

---

## Technology stack

| Technology | What it does | Why it is needed | Why it was chosen | Alternatives |
|---|---|---|---|---|
| **FastAPI** (Python) | HTTP API layer | Something must own file handling, orchestration and secrets | Async, Pydantic validation for free, auto-generated OpenAPI docs at `/docs`. Python is where the PDF and ML ecosystem lives | Flask (no async, no built-in validation), Django (far too heavy), Node/Express (weaker PDF and embedding libraries) |
| **PyMuPDF** | PDF text extraction | Converts PDFs into text with page positions | Fastest of the common options, handles academic two-column layouts well, exposes per-page text so page numbers survive | pdfplumber (better tables, much slower), PyPDF2 (weaker on complex layouts), Unstructured (heavy dependency tree) |
| **Custom chunker** | Splits pages into overlapping passages | Chunking is the core retrieval-quality lever | ~60 readable lines you can fully explain, with the page-boundary rule this project specifically needs | LangChain `RecursiveCharacterTextSplitter` — a large dependency for one function, and the page rule would still need custom code |
| **Gemini `text-embedding-004`** | Text → vector | Semantic search needs vectors | Same API key as the chat model, no local model download, and it supports asymmetric query/document task types which improves retrieval | OpenAI `text-embedding-3-small` (needs a second paid key), local sentence-transformers (offline, but ~90 MB download and slower) — included here as the `local` provider |
| **ChromaDB** | Vector store + metadata + search | Stores embeddings and answers nearest-neighbour queries | Embedded and file-backed, so there is no server to run; metadata filtering and cosine distance out of the box | FAISS (fast, but no metadata layer — you would build one), Pinecone/Weaviate (cloud account and network dependency for a local project), pgvector (needs Postgres) |
| **Gemini 2.0 Flash** | Generates the answer | Turns retrieved passages into readable prose | Usable free tier, fast, long context, and it shares an SDK with the embedding model so there is one key and one client | GPT-4o mini, Claude Haiku — both fine; swapping means editing `_generate` in `rag/pipeline.py` |
| **React + Vite** | Frontend | Chat, upload progress and source expansion are stateful UI | Vite has near-zero config to explain; React is the default vocabulary for component UI | Next.js (SSR and routing this project does not need), plain JS (state handling would get messy fast) |
| **Tailwind CSS** | Styling | Consistent design without a CSS file per component | Styles stay next to markup; shared button/field classes prevent drift | CSS Modules, styled-components |

### Deliberately not used

Adding these would have made the project harder to explain without making it better at its job:

- **LangChain / LlamaIndex** — would replace about 150 lines of clear pipeline code with framework abstractions. When an interviewer asks "how does your retrieval work?", "LangChain does it" is not an answer.
- **LangGraph, agents, multi-agent systems** — there is one linear flow with no branching decisions to orchestrate.
- **Fine-tuning** — teaches a model style, not facts. Retrieval is the correct tool for "answer from this document".
- **GraphRAG** — solves multi-hop reasoning across an entity graph. Overkill for passage lookup within a few papers.
- **Redis, Kafka, Kubernetes, microservices** — infrastructure for scale and throughput this application does not have.
- **A second database** — the document registry is a small JSON file, which is sufficient for a local single-user app and honest about what it is.
- **Authentication** — the app runs on localhost against the user's own files. Adding auth would be ceremony, not security.

---

## Folder structure

```
paperpilot/
├── README.md
├── .gitignore
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py                     FastAPI app, CORS, routers, /api/health
│       ├── config.py                   env-backed settings, path resolution
│       ├── schemas.py                  request/response models (the API contract)
│       ├── errors.py                   typed errors → consistent JSON envelope
│       ├── api/
│       │   ├── routes_documents.py     upload, list, delete, limits
│       │   └── routes_chat.py          ask
│       ├── rag/
│       │   ├── pdf_loader.py           extraction + cleaning, page numbers
│       │   ├── chunker.py              overlapping chunks + metadata
│       │   ├── embeddings.py           Gemini or local sentence-transformers
│       │   ├── vector_store.py         ChromaDB: upsert, filter, top-K search
│       │   ├── prompts.py              grounding rules, modes, context block
│       │   └── pipeline.py             ingest_pdf() and answer_question()
│       └── services/
│           └── document_service.py     validation, dedupe, registry, delete
└── frontend/
    ├── package.json  vite.config.js  tailwind.config.js  postcss.config.js
    ├── index.html   .env.example
    └── src/
        ├── main.jsx  App.jsx  index.css  useApp.js
        ├── api/client.js                every backend call, one error shape
        ├── components/
        │   ├── Sidebar.jsx  DropZone.jsx  DocumentCard.jsx
        │   ├── ChatMessage.jsx  SourceList.jsx  ModeToggle.jsx  Toast.jsx
        └── pages/
            └── Dashboard.jsx  UploadPage.jsx  DocumentsPage.jsx  ChatPage.jsx
```

Runtime data (`backend/data/`) is created on first run and is gitignored.

---

## Installation

Requires Python 3.10+ and Node 18+.

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
```

### 2. Get an API key

Create a free key at <https://aistudio.google.com/app/apikey>, then set it in `backend/.env`:

```
GOOGLE_API_KEY=your_key_here
```

### 3. Frontend

```bash
cd ../frontend
npm install
cp .env.example .env               # Windows: copy .env.example .env
```

## Environment variables

**`backend/.env`** — the only place a secret ever lives.

| Variable | Default | Purpose |
|---|---|---|
| `GOOGLE_API_KEY` | *(empty)* | Gemini key. Required to answer questions. |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Chat model. |
| `EMBEDDING_PROVIDER` | `google` | `google` or `local`. |
| `GOOGLE_EMBEDDING_MODEL` | `models/text-embedding-004` | Embedding model. |
| `LOCAL_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Used when provider is `local`. |
| `CHROMA_DIR` | `./data/chroma` | Vector store location. |
| `UPLOAD_DIR` | `./data/uploads` | Original PDFs. |
| `REGISTRY_PATH` | `./data/documents.json` | Paper-level records. |
| `MAX_UPLOAD_MB` | `25` | Per-file size limit. |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `150` | Chunking. Changing these only affects papers indexed afterwards. |
| `TOP_K` | `6` | Passages retrieved per question. |
| `MAX_DISTANCE` | `0.85` | Cosine distance above which a passage counts as irrelevant. |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed browser origins. |

**`frontend/.env`** — `VITE_API_BASE_URL` only. Anything in a `VITE_` variable is compiled into the browser bundle and readable by anyone, which is exactly why no key goes here.

## Running locally

Two terminals.

```bash
# terminal 1
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

```bash
# terminal 2
cd frontend && npm run dev
```

Open <http://localhost:5173>. Interactive API docs are at <http://localhost:8000/docs>.

---

## API overview

Base URL `http://localhost:8000`. Errors always return `{ "code", "message", "detail?" }`.

| Method | Path | Body | Returns |
|---|---|---|---|
| `GET` | `/api/health` | — | provider, model, whether a key is set, document and chunk counts |
| `POST` | `/api/documents/upload` | multipart, field `files` (repeatable) | `{ uploaded: [{ filename, success, document?, error_code?, error? }], succeeded, failed }` |
| `GET` | `/api/documents` | — | `{ documents: [...], total_documents, total_chunks }` |
| `GET` | `/api/documents/limits` | — | `{ max_upload_mb, max_files_per_request, accepted_types }` |
| `DELETE` | `/api/documents/{id}` | — | `{ id, deleted, chunks_removed }` |
| `POST` | `/api/chat/ask` | `{ question, mode, document_ids?, history? }` | `{ answer, mode, sources: [...], grounded, documents_searched }` |

A source looks like:

```json
{
  "label": "S1",
  "document_id": "9f2c41ab77de",
  "filename": "attention-is-all-you-need.pdf",
  "page": 4,
  "chunk_id": "9f2c41ab77de:37",
  "score": 0.82,
  "excerpt": "The encoder is composed of a stack of N = 6 identical layers..."
}
```

Conversation history is held in the browser, not on the server, so "Clear chat" needs no endpoint and no request.

### Example

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "files=@paper.pdf"

curl -X POST http://localhost:8000/api/chat/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the main findings?","mode":"technical"}'
```

---

## Testing the full RAG workflow

1. **Start both servers.** The sidebar should show the embedding provider and model. If it says "Server unreachable", the backend is not running.
2. **Upload a text-based PDF.** An arXiv paper is ideal. The results panel should report a page count and a passage count — a 10-page paper typically produces 30–60 passages. A passage count of zero means extraction found no text.
3. **Confirm indexing.** `GET /api/health` should show a non-zero `chunks`. The library should list the paper.
4. **Ask a question that the paper answers**, e.g. *"What problem does this paper address?"* You should get an answer with `S1`-style markers, and expanding a footnote should show a passage that genuinely supports the claim, on a page where you can find it in the PDF.
5. **Switch modes.** Ask the same question in plain-language and technical mode; the terminology and depth should visibly differ while the facts stay the same.
6. **Test grounding honestly.** Ask something the paper cannot answer — *"What is the author's phone number?"* The answer should decline rather than invent one. This is the single most important behaviour to demonstrate.
7. **Test multiple papers.** Upload a second paper and ask *"Compare the methodologies used in these papers."* Sources should span both filenames.
8. **Test the scope filter.** Select one paper and ask something only the other covers; retrieval should come up empty.
9. **Test failure handling.** Upload a `.txt` renamed to `.pdf`, an empty file, and the same paper twice. Each should give a specific, different message.
10. **Test deletion.** Delete a paper and re-ask a question it previously answered; its passages should no longer appear.

---

## Common errors and fixes

| What you see | Cause | Fix |
|---|---|---|
| Sidebar says "Server unreachable" | Backend not running, or a different port | Start uvicorn on 8000, or update `VITE_API_BASE_URL` |
| Browser console shows a CORS error | Frontend origin not in the allowlist | Add it to `CORS_ORIGINS` in `backend/.env`, restart the backend |
| "No model API key is set" | `GOOGLE_API_KEY` missing | Add it to `backend/.env` and restart. Editing `.env` needs a restart even with `--reload` |
| "No readable text found in X.pdf" | Scanned or image-only PDF | It has no text layer. Run OCR first (e.g. OCRmyPDF) |
| "has a .pdf extension but its contents are not a PDF" | File signature check failed | The file is not actually a PDF |
| "is already uploaded" | Identical file content | Delete the existing copy to re-index |
| "The embedding service rejected the request" | Bad key, or free-tier quota exhausted | Check the key; wait for quota reset, or set `EMBEDDING_PROVIDER=local` |
| "The model API hit its rate limit" | Too many questions too quickly | Wait a moment and retry |
| "I could not find anything relevant" on a reasonable question | Retrieval genuinely missed | Rephrase using the paper's vocabulary, or raise `TOP_K` / `MAX_DISTANCE` |
| `Failed to send telemetry event ...capture() takes 1 positional argument` | Known harmless bug in Chroma 0.5.x telemetry, already disabled in config | Ignore it |
| `Number of requested results 6 is greater than number of elements in index` | Fewer passages indexed than `TOP_K` | Informational only; Chroma returns what exists |
| `ModuleNotFoundError: sentence_transformers` | `EMBEDDING_PROVIDER=local` without the optional dependency | `pip install sentence-transformers` |

---

## Limitations

- **Text-layer PDFs only.** No OCR, so scanned papers are rejected rather than mangled.
- **Figures, tables and equations are lost.** Extraction produces linear text; a question about a chart is unlikely to be answered well.
- **Grounding reduces but does not remove unsupported claims.** The model can still misread a passage. The sources are there to be checked.
- **Retrieval can miss.** If the answering passage does not rank in the top K, the answer will be incomplete — and the system cannot tell you that it missed.
- **Dense-only retrieval.** Exact identifiers (a specific equation number, an unusual acronym) are a known weakness of pure embedding search.
- **Single user, no auth.** Everyone hitting the server shares one library.
- **Whole-document questions are weak.** "Summarise this entire paper" is not a retrieval problem; only K passages reach the model.
- **JSON registry.** Fine for one user on one machine; it would not survive concurrent writers.

## Future improvements

- **Hybrid retrieval** — combine BM25 keyword scores with vector scores to fix the exact-identifier weakness.
- **Reranking** — retrieve 20 candidates, then rerank with a cross-encoder and keep the best 5. Usually the single largest quality gain per line of code in a RAG system.
- **Section-aware chunking** — detect Abstract / Method / Results headings and attach them as metadata, enabling "what does the Results section say" as a filtered query.
- **Streamed answers** — token-by-token responses so the first sentence appears immediately.
- **Click a citation to open the PDF at that page** — the page number is already stored; only a viewer is missing.
- **Per-paper summaries at ingest time** — a map-reduce pass would make "summarise this paper" work properly.
- **A retrieval evaluation set** — a small file of question/expected-page pairs, so changes to chunk size or K can be measured instead of guessed at.
