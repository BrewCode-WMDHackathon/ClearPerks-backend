---
title: ClearPerks Backend
emoji: 💼
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# ClearPerks Backend

The backend service for the ClearPerks ecosystem. This API powers the "AI Benefits Optimizer" and "Trends Engine", providing intelligent analysis of paystubs and optimization of benefits packages.

## 🚀 Features

-   **Paystub Analysis**: Extracts and analyzes data from paystub documents (PDF/Images) using OCR.
-   **Benefits Optimization**: Recommends personalized benefits packages based on user profiles and paystub data.
-   **Trends Engine**: (In-Progress) Analyzes broader trends in benefits usage.
-   **User Management**: Basic user profile management and preferences.

## 🛠 Tech Stack

-   **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
-   **Database**: PostgreSQL (via SQLAlchemy ORM)
-   **Containerization**: Docker
-   **Authentication**: Custom header-based auth (Hackathon/Stub mode).

## 🏁 Getting Started

### Prerequisites

-   Python 3.10+
-   PostgreSQL database (local or remote)

### 💻 Local Development

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd clearperks-backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    # Windows
    .\.venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration:**
    Create a `.env` file in the root directory. You can copy the example `.env.example` if available.
    ```env
    DATABASE_URL=postgresql://user:password@localhost:5432/clearperks_db
    ```
    *Note: Ensure your database server is running and the database exists.*

5.  **Run the application:**
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```

6.  **Access the API:**
    -   API Docs (Swagger UI): `http://localhost:8000/api/v1/docs`
    -   OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`

### 🐳 Docker & Hugging Face Spaces

This project is configured to run on Hugging Face Spaces or any Docker-compatible environment.

**Build and Run with Docker:**

```bash
docker build -t clearperks-backend .
docker run -p 7860:7860 clearperks-backend
```

*Note: The Dockerfile is configured to expose port `7860`. Adjust `docker run` ports if you want to map to a different local port (e.g., `-p 8000:7860`).*

## 📁 Project Structure

```
clearperks-backend/
├── app/
│   ├── api/            # Route handlers (users, paystubs, benefits)
│   ├── core/           # Config, Database, Auth logic
│   ├── models/         # SQLAlchemy Database models
│   ├── schemas/        # Pydantic Schemas for validation
│   └── main.py         # Application entry point
├── static/             # Static frontend files (served at /static)
├── uploads/            # Temporary storage for uploads
├── Dockerfile          # Docker configuration
└── requirements.txt    # Python dependencies
```

## 🔐 Authentication

Currently, the API uses a stubbed authentication mechanism suitable for development/hackathons.

-   **Headers**:
    -   `X-User-Id`: UUID string (Required) - Identifies the user.
    -   `X-User-Email`: String (Optional) - Sets the email for new profiles.

## 🌐 Frontend Integration

The backend can serve static frontend files for simplified deployment.

1.  Place your build artifacts in a `static/` folder in the root.
2.  Access them at: `http://localhost:8000/static/index.html`

> **Note**: For production, it is recommended to host the frontend separately (e.g., Vercel, Netlify).
