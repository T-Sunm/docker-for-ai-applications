# Docker for AI Applications

This repository contains a FastAPI backend for local model inference and a Streamlit frontend that calls the backend API.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Internet access for the first model download

## Run locally

### Backend

Run the one-time setup from the repository root:

```powershell
cd backend
uv init --bare --python 3.11
uv add -r requirements.txt
uv run python scripts\prepare_models.py
```

The model artifacts are stored in `backend/model-data/`.

Start the API:

```powershell
uv run uvicorn main:app --app-dir app --port 8000
```

Open <http://127.0.0.1:8000/docs> for the API documentation.

### Frontend

Open another terminal and run:

```powershell
cd frontend
uv init --bare --python 3.11
uv add -r requirements.txt
uv run streamlit run app.py
```

Open <http://localhost:8501> if Streamlit does not open the page automatically.

The `uv init`, `uv add`, and model preparation commands are only needed for the first setup. For later runs, start each service with its `uv run` command.

## Run with Docker Compose

From the repository root:

```powershell
docker compose up --build -d
docker compose ps
```

Compose prepares model artifacts in the named volume `model-artifacts`, starts the API after preparation succeeds, then starts Streamlit after `http://backend:8000/health` responds. The first preparation needs Internet access and may take time. Open <http://localhost:8501> for the UI or <http://localhost:8000/docs> for the API.

The frontend runs `streamlit run app.py --server.address 0.0.0.0 --server.port 8501` and receives `BACKEND_URL=http://backend:8000`. The backend image is `backend:1.0`; the frontend image is `frontend:1.0`. The backend and frontend use `restart: unless-stopped`; the one-time preparation service uses `restart: "no"`.

Stop the stack with `docker compose down`. This keeps the model volume for later runs. To inspect a failed preparation, use `docker compose logs prepare-models`.
