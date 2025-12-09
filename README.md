---
title: ClearPerks Backend
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# clearperks-backend

Quick run and frontend guidance for local development.

Run the FastAPI server (from project root):

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open the API docs at:

```
http://localhost:8000/api/v1/docs
```

Serving frontend files

- Avoid opening frontend files via `file://` (browsers treat that origin as `null` and block CORS requests).
- Put your static frontend files into a `static/` directory in the project root and access them via HTTP, e.g.:

```
http://localhost:8000/static/index.html
```

This backend mounts `/static` to serve local frontend files and also enables CORS for development. In production, lock down `allow_origins` in `app/main.py`.
