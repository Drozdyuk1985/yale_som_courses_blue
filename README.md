# Yale SOM Course Explorer

React + FastAPI + PydanticAI course explorer for the Yale SOM catalog, with
accounts and saved chat history.

- **Catalog** — browse and search 234 Spring 2026 course sections
- **Chat agent** — answers questions using two tools: `search_courses` (queries the
  local `courses` table) and `web_search` (OpenAI native web search, for anything the
  catalog cannot answer)
- **Accounts** — register / sign in, bcrypt-hashed passwords, JWT sessions
- **History** — every conversation is saved per user and restored on sign-in

## Layout

```
backend/    FastAPI app, PydanticAI agent, SQLAlchemy models
frontend/   React + Vite + TypeScript
data/       yale_som.db (SQLite: courses, users, chats)
output/     agent audit trail
```

## Run locally

Backend:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload --port 8000
```

Frontend (second terminal):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. API docs are at http://127.0.0.1:8000/docs.

## Environment

Copy `.env.example` to `.env` and fill in:

| Variable | Purpose |
| --- | --- |
| `PORTKEY_API_KEY` | Required. Portkey gateway credential for the model. |
| `JWT_SECRET` | Signs session tokens. Falls back to an insecure dev value if unset — **must** be set in production, or every redeploy invalidates all sessions. |
| `DATABASE_URL` | Optional. Defaults to the bundled SQLite file; set to a Postgres URL (e.g. Supabase) in production. |
| `ALLOWED_ORIGINS` | Optional. Comma-separated CORS origins. Defaults to `*` for local development. |

Never commit a real `.env`.

## Notes

- `data/yale_som.db` is committed on purpose so the app runs immediately after cloning.
  It ships with the course catalog and empty `users` / `chats` tables.
- The catalog hides rows where `visible != '1'`, so 206 of 234 sections are shown.
