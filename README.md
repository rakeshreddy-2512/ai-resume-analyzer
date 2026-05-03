# AI Resume Analyzer (Full-Stack)

A production-style **full-stack AI Resume Analyzer** that supports:
- PDF resume upload
- ATS score calculation
- Skill extraction
- Personal analytics dashboard
- JWT authentication

---

## Tech Stack

### Backend
- **FastAPI** (REST API)
- **SQLite + SQLAlchemy** (persistence)
- **JWT auth** with OAuth2 password flow
- **PyPDF** for resume text extraction

### Frontend
- **React + Vite**
- **Axios** for API integration
- Responsive dashboard UI

---

## Features

1. **Authentication**
   - Register user
   - Login user
   - JWT-protected endpoints

2. **Resume Analyzer**
   - Upload PDF resumes
   - Extract text from PDF
   - Identify known technical skills
   - Compute ATS score using:
     - resume length
     - skill coverage
     - bullet-point usage
     - action verbs
     - target keyword alignment

3. **Analytics Dashboard**
   - Total resumes analyzed
   - Average ATS score
   - Top extracted skills
   - Recent/past analyses table

---

## Project Structure

```
ai-resume-analyzer/
├── backend/
│   ├── main.py
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── main.jsx
    │   └── styles.css
    ├── index.html
    ├── package.json
    └── vite.config.js
```

---

## Setup & Run

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at: `http://localhost:8000`

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## API Endpoints

### Auth
- `POST /auth/register`
- `POST /auth/login`

### Resume Analysis
- `POST /analyze` (multipart form: `file`, optional `target_keywords`)

### Dashboard
- `GET /dashboard`
- `GET /analyses`

---

## ATS Scoring Logic (Simplified)

The score is capped at **100** and combines:
- Baseline quality points
- Recommended word-count range check
- Number of extracted skills
- Bullet structure signal
- Action-verb signal
- Optional keyword-match boost from job-specific keywords

---

## Notes for Production

- Replace static `SECRET_KEY` with an environment variable.
- Use PostgreSQL instead of SQLite for scale.
- Add background job queue for heavy parsing/LLM enrichment.
- Add virus scanning and strict file-size limits for uploads.
- Add rate limiting, audit logs, and RBAC if needed.

---

## License

MIT
