# OpenShorts Local Development Guide

This guide covers how to set up, run, and develop OpenShorts on your local machine using either **Docker** or **Command Line (Bare-metal)**.

---

## 1. System Architecture

OpenShorts consists of 3 services:
- **Backend (`app.py`, `saasshorts.py`, `main.py`)**: FastAPI REST API handling video downloads (yt-dlp), Whisper transcription, AI moment detection, FFmpeg reframing, and UGC script/video generation.
- **Frontend (`dashboard/`)**: React 18 + Vite dashboard with real-time job status and preview.
- **Renderer (`render-service/`)**: Express + Remotion server for animated templates and overlays.

| Service | Local Port (Docker) | Local Port (Native) |
|---|---|---|
| **Backend API** | `http://localhost:8000` | `http://localhost:8000` |
| **Frontend UI** | `http://localhost:5175` | `http://localhost:5173` |
| **Remotion Renderer** | `http://localhost:3100` | `http://localhost:3100` |

---

## 2. API Keys Preparation

OpenShorts uses a **Bring-Your-Own-Key (BYOK)** model. You only need keys for the features you plan to use:

| Feature | Key Name | Required? | Where to get |
|---|---|---|---|
| **Clip Generator & Analysis** | `GEMINI_API_KEY` | **Yes** | [Google AI Studio](https://aistudio.google.com/app/apikey) (Free tier available) |
| **AI Shorts (Actor / Video)** | `FAL_KEY` | For AI Shorts | [fal.ai](https://fal.ai) (Flux 2, Hailuo 2.3, Lipsync) |
| **Voiceover & Dubbing** | `ELEVENLABS_API_KEY` | For TTS / Dubbing | [elevenlabs.io](https://elevenlabs.io) (Free tier available) |
| **Social Auto-Publishing** | `UPLOAD_POST_API_KEY` | For direct posting | [upload-post.com](https://upload-post.com) (10 free uploads/mo) |
| **Cloud Backup** | `AWS_ACCESS_KEY_ID` / `...` | Optional | AWS S3 or Cloudflare R2 |

### How to configure keys:
- **Option A (Recommended):** Open the Dashboard in your browser (`http://localhost:5175` or `5173`), click **Settings** (gear icon), and paste your keys. They are stored encrypted in your browser's `localStorage` and sent per request.
- **Option B:** Copy `.env.example` to `.env` and configure keys as environment variables:
  ```bash
  cp .env.example .env
  ```

---

## 3. Option 1: Run with Docker (Recommended)

Docker isolates all system dependencies (FFmpeg, OpenCV, Node, Python, fonts).

### Start Services
```bash
docker compose up --build
```
*(Add `-d` to run in the background: `docker compose up --build -d`)*

### Access Dashboard
Open **`http://localhost:5175`** in your browser.

### Working with Code Changes in Docker
Both the backend directory (`.`) and dashboard directory (`./dashboard`) are mounted as live volumes inside the containers:

1. **Frontend Changes (`dashboard/src/...`)**:
   - Updates instantly via Vite Hot Module Replacement (HMR) without restarting.
2. **Backend Changes (`saasshorts.py`, `app.py`, etc.)**:
   - Files update inside the container immediately.
   - Restart the backend process to apply changes (takes ~2 seconds):
     ```bash
     docker compose restart backend
     ```
3. **Dependency Changes (`requirements.txt`, `package.json`, `Dockerfile`)**:
   - Rebuild the containers:
     ```bash
     docker compose up --build
     ```

### Useful Docker Commands
```bash
# View backend logs in real-time
docker compose logs -f backend

# View all container logs
docker compose logs -f

# Restart just the backend
docker compose restart backend

# Stop all containers
docker compose down
```

> **Tip: Auto-reloading in Docker**  
> To have Uvicorn auto-reload on Python file saves without running `restart`, add `command: ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]` to the `backend` service in `docker-compose.yml`.

---

## 4. Option 2: Run via Command Line (Bare-Metal on Mac)

Running directly on your host machine gives fast execution, instant auto-reloading (`--reload`) on file saves, and native debugger support.

### Prerequisites (macOS)
Install required tools via Homebrew:
```bash
brew install ffmpeg node python@3.11
```

---

### Step 1: Backend Server (Terminal 1)

1. Create and activate a Python virtual environment:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

2. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the FastAPI server with **auto-reload**:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```
   *The server runs at `http://localhost:8000`. Any Python code change will trigger an instant reload.*

---

### Step 2: Frontend Dashboard (Terminal 2)

1. Navigate to the dashboard directory:
   ```bash
   cd dashboard
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *The dashboard will be available at `http://localhost:5173` (proxies `/api` requests to backend on port 8000).*

---

### Step 3: Remotion Render Service (Terminal 3, Optional)

*Only needed if rendering animated templates with Remotion:*
```bash
cd render-service
npm install
npm run dev
```
*Runs on `http://localhost:3100`.*

---

## 5. Verifying & Testing Code Changes

### Check Python Syntax
```bash
python3 -m py_compile saasshorts.py app.py
```

### Run Tests
```bash
pytest tests/
```

### Run Frontend Linter
```bash
cd dashboard
npm run lint
```

---

## 6. Troubleshooting

- **`ModuleNotFoundError: No module named '...'`**: Ensure your virtual environment is activated (`source venv/bin/activate`) and run `pip install -r requirements.txt`.
- **`Port 8000 or 5173 already in use`**: Check running processes with `lsof -i :8000` or `lsof -i :5173` and kill the old process (`kill -9 <PID>`).
- **`Failed to parse analysis JSON: Extra data`**: Handled automatically by `_parse_json_from_llm` in `saasshorts.py` using `raw_decode` to bypass any trailing comments from LLMs.
- **Whisper / MediaPipe issues on macOS**: On Apple Silicon, CPU inference is the default (`WHISPER_DEVICE=cpu`, `WHISPER_COMPUTE=int8`).
