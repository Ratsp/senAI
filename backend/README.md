# SenAI Agentic CRM Intelligence Backend

This directory contains the FastAPI-based backend application for the SenAI Agentic CRM Intelligence Platform.

## Requirements
- Python 3.11+
- Supabase PostgreSQL database with `pgvector` enabled

## How to Run

Follow these steps to configure, seed, and run the backend locally.

### 1. Install Dependencies
Make sure you are in the `backend/` directory and have your virtual environment activated, then install the dependencies:
```bash
uv add -r requirements.txt
# OR if using pip:
pip install -r requirements.txt
```

### 2. Configure Environment
Verify or update the configuration inside `backend/.env`. Ensure your database URL (Supabase with pgvector support) and Groq API keys are properly entered.

### 3. Run Database Migrations
Deploy the database schema using Alembic:
```bash
alembic upgrade head
```

### 4. Seed the Knowledge Base
Populate the pgvector store with vector embeddings derived from the markdown documentation in the global `knowledge_base/` directory:
```bash
python scripts/seed_kb.py
```

### 5. Start the Live Server
Start the development server using uvicorn:
```bash
uvicorn app.main:app --reload --port 8000
```
Interactive API documentation is now live at: **[http://localhost:8000/docs](http://localhost:8000/docs)**.

### 6. Run the Email Simulator
In a separate terminal window, execute the chronological email simulation:
```bash
# Navigate to the backend directory
cd backend

# Run the simulation at 1 email per second (customizable via --speed)
python scripts/simulate_emails.py --speed 1.0
```
