# Wedding Photo Recognition System

Locally-hosted face recognition system for photographers. Guests register with a selfie, the photographer uploads event photos, and each guest automatically receives an email link to their personal gallery.

---

## Option A: Run with Docker (recommended)

No Python setup needed — Docker handles everything.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 1. Build the image (one-time)
```bash
cd ~/Downloads/photo_recog
docker build -t wedding-photos .
```
> First build takes ~5 minutes. Subsequent builds are fast.

### 2. Run the container

**Basic (local only):**
```bash
docker run -p 8000:8000 \
  -v "$HOME/.insightface:/root/.insightface" \
  -v "$(pwd)/data:/app/data" \
  -e GALLERY_BASE_URL=http://localhost:8000 \
  wedding-photos
```

**With a photos folder mounted** (use folder path feature):
```bash
docker run -p 8000:8000 \
  -v "$HOME/.insightface:/root/.insightface" \
  -v "$(pwd)/data:/app/data" \
  -v "/path/to/your/photos:/photos" \
  -e GALLERY_BASE_URL=http://localhost:8000 \
  wedding-photos
```
Then in the Upload page, enter `/photos` as the folder path (not the Mac path).

**With ngrok (share publicly):**
```bash
# Terminal 1 — start ngrok first, copy the URL
ngrok http 8000

# Terminal 2 — run container with the ngrok URL
docker run -p 8000:8000 \
  -v "$HOME/.insightface:/root/.insightface" \
  -v "$(pwd)/data:/app/data" \
  -v "/path/to/your/photos:/photos" \
  -e GALLERY_BASE_URL=https://your-url.ngrok-free.app \
  wedding-photos
```

### Docker notes
| Volume | Purpose |
|--------|---------|
| `$HOME/.insightface:/root/.insightface` | ArcFace model cache (~300MB, downloaded once) |
| `$(pwd)/data:/app/data` | DB, selfies, wedding photos, galleries — persists across restarts |
| `/path/to/photos:/photos` | Your photos folder, accessible inside container as `/photos` |

### Cleanup (Docker)
```bash
# Reset all data (new event)
rm -rf ~/Downloads/photo_recog/data/db/wedding.db
rm -f ~/Downloads/photo_recog/data/selfies/*
rm -f ~/Downloads/photo_recog/data/wedding_photos/*
rm -rf ~/Downloads/photo_recog/data/galleries/*/

# Remove the Docker image (to rebuild fresh)
docker rmi wedding-photos
```

---

## Option B: Run without Docker (Python virtualenv)

### Installation (one-time)
```bash
cd ~/Downloads/photo_recog
python3 -m venv venv
source venv/bin/activate
pip install cmake
pip install insightface onnxruntime pillow-heif
pip install fastapi==0.111.0 "uvicorn[standard]==0.29.0" jinja2==3.1.4 \
    python-multipart==0.0.9 Pillow numpy
```

> First run downloads the ArcFace model (~300MB) automatically.

### Running locally (same WiFi only)

**Terminal 1 — fake email server:**
```bash
python3 -m smtpd -n -c DebuggingServer localhost:1025
```

**Terminal 2 — app:**
```bash
cd ~/Downloads/photo_recog
source venv/bin/activate
python main.py
```

Open `http://localhost:8000`. To share on same WiFi:
```bash
ipconfig getifaddr en0   # find your local IP
```
Share: `http://192.168.x.x:8000/register`

### Running with ngrok (share publicly)

**Terminal 1 — fake email server:**
```bash
python3 -m smtpd -n -c DebuggingServer localhost:1025
```

**Terminal 2 — ngrok:**
```bash
ngrok http 8000
```
Copy the public URL (e.g. `https://abc123.ngrok-free.app`).

**Terminal 3 — app:**
```bash
cd ~/Downloads/photo_recog
source venv/bin/activate
GALLERY_BASE_URL=https://abc123.ngrok-free.app python main.py
```

### Cleanup (without Docker)
```bash
# Reset everything (new event)
rm ~/Downloads/photo_recog/data/db/wedding.db
rm -f ~/Downloads/photo_recog/data/selfies/*
rm -f ~/Downloads/photo_recog/data/wedding_photos/*
rm -rf ~/Downloads/photo_recog/data/galleries/*/

# Delete only guest registrations (keep photos)
rm ~/Downloads/photo_recog/data/db/wedding.db
rm -f ~/Downloads/photo_recog/data/selfies/*
rm -rf ~/Downloads/photo_recog/data/galleries/*/

# Delete only uploaded photos (keep guest registrations)
rm -f ~/Downloads/photo_recog/data/wedding_photos/*
rm -rf ~/Downloads/photo_recog/data/galleries/*/

# Reprocess all photos (re-run face matching without re-uploading)
sqlite3 ~/Downloads/photo_recog/data/db/wedding.db \
  "UPDATE wedding_photos SET processed = 0; DELETE FROM guest_photo_matches;"
rm -rf ~/Downloads/photo_recog/data/galleries/*/
# Then restart the app
```

---

## Workflow

1. **Guests** visit `/register` — upload selfie + name + email
2. **Photographer** visits `/upload` — paste folder path or select photos manually
3. System matches faces in the background automatically
4. Each guest gets an email with a link to their private gallery
5. Guests can select and download individual photos from their gallery

---

## Configuration

Edit `config.py` to change:

| Setting | Default | Description |
|---------|---------|-------------|
| `MATCH_THRESHOLD` | `0.35` | Face match sensitivity (0–1). Lower = stricter, fewer false matches. |
| `MAX_SELFIE_EDGE` | `800` | Max px for selfie before encoding |
| `MAX_PHOTO_EDGE` | `1200` | Max px for wedding photos before encoding |
| `SMTP_HOST/PORT` | `localhost:1025` | Email server settings |
| `GALLERY_BASE_URL` | `http://localhost:8000` | Base URL used in email links (override with env var) |
