# ── Stage 1: base image ───────────────────────────────────────────────────────
FROM python:3.11-slim

# Build deps for insightface / onnxruntime native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        cmake \
        build-essential \
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
        fastapi==0.111.0 \
        "uvicorn[standard]==0.29.0" \
        jinja2==3.1.4 \
        python-multipart==0.0.9 \
        Pillow \
        numpy \
        insightface \
        onnxruntime \
        pillow-heif

# ── Copy application code ─────────────────────────────────────────────────────
COPY main.py config.py database.py face_engine.py ./
COPY routers/   routers/
COPY templates/ templates/
COPY static/    static/

# ── Persistent data volumes ───────────────────────────────────────────────────
# These directories hold the SQLite DB, uploaded photos, selfies, and galleries.
# Mount them as Docker volumes so data survives container restarts.
VOLUME ["/app/data"]

# Pre-create the data sub-directories so the app starts cleanly
RUN mkdir -p /app/data/db \
             /app/data/selfies \
             /app/data/wedding_photos \
             /app/data/galleries \
             /app/logs \
             /photos

# ── insightface model cache ───────────────────────────────────────────────────
# insightface downloads ~300 MB of ONNX models to ~/.insightface on first run.
# Mount this as a volume so the download only happens once.
VOLUME ["/root/.insightface"]

# ── Environment defaults (override at runtime) ────────────────────────────────
ENV GALLERY_BASE_URL=http://localhost:8000

# ── Expose port ───────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Start server ──────────────────────────────────────────────────────────────
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
