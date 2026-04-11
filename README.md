# Wedding Photo Recognition System

Locally-hosted face recognition system for photographers. Guests register with a selfie, the photographer uploads event photos, and each guest automatically receives an email link to their personal gallery.

---

## Installation (one-time)

```bash
cd "/Users/ankitmehra/Downloads/photo recog"
python3 -m venv venv
source venv/bin/activate
pip install cmake
pip install insightface onnxruntime pillow-heif
pip install fastapi==0.111.0 "uvicorn[standard]==0.29.0" jinja2==3.1.4 \
    python-multipart==0.0.9 Pillow numpy
```

> First run downloads the ArcFace model (~300MB) automatically.

---

## Running Locally (same WiFi only)

**Terminal 1 — fake email server (prints emails to terminal instead of sending):**
```bash
python3 -m smtpd -n -c DebuggingServer localhost:1025
```

**Terminal 2 — app:**
```bash
cd "/Users/ankitmehra/Downloads/photo recog"
source venv/bin/activate
python main.py
```

Open `http://localhost:8000` in your browser.

To share with devices on the same WiFi, find your local IP:
```bash
ipconfig getifaddr en0
```
Then share: `http://192.168.x.x:8000/register`

---

## Running with ngrok (share with anyone over internet)

**Terminal 1 — fake email server:**
```bash
python3 -m smtpd -n -c DebuggingServer localhost:1025
```

**Terminal 2 — ngrok tunnel:**
```bash
ngrok http 8000
```
Copy the public URL shown (e.g. `https://abc123.ngrok-free.dev`).

**Terminal 3 — app with public URL:**
```bash
cd "/Users/ankitmehra/Downloads/photo recog"
source venv/bin/activate
GALLERY_BASE_URL=https://abc123.ngrok-free.dev python main.py
```

Replace `https://abc123.ngrok-free.dev` with your actual ngrok URL every time you restart ngrok.

Share with guests:
- Register: `https://abc123.ngrok-free.dev/register`
- Photographer upload: `https://abc123.ngrok-free.dev/upload`

---

## Workflow

1. **Guests** visit `/register` — upload selfie + name + email
2. **Photographer** visits `/upload` — paste folder path or select photos manually
3. System matches faces in background automatically
4. Each guest gets an email with a link to their private gallery

---

## Cleanup Commands

### Reset everything (start fresh for a new event)
```bash
rm "/Users/ankitmehra/Downloads/photo recog/data/db/wedding.db"
rm -f "/Users/ankitmehra/Downloads/photo recog/data/selfies/"*
rm -f "/Users/ankitmehra/Downloads/photo recog/data/wedding_photos/"*
rm -rf "/Users/ankitmehra/Downloads/photo recog/data/galleries/"*/
```

### Delete only guest registrations (keep photos)
```bash
rm "/Users/ankitmehra/Downloads/photo recog/data/db/wedding.db"
rm -f "/Users/ankitmehra/Downloads/photo recog/data/selfies/"*
rm -rf "/Users/ankitmehra/Downloads/photo recog/data/galleries/"*/
```

### Delete only uploaded photos (keep guest registrations)
```bash
rm -f "/Users/ankitmehra/Downloads/photo recog/data/wedding_photos/"*
rm -rf "/Users/ankitmehra/Downloads/photo recog/data/galleries/"*/
# Then reprocess: visit /upload and re-upload photos
```

### Reprocess all photos (re-run face matching without re-uploading)
```bash
sqlite3 "/Users/ankitmehra/Downloads/photo recog/data/db/wedding.db" \
  "UPDATE wedding_photos SET processed = 0; DELETE FROM guest_photo_matches;"
rm -rf "/Users/ankitmehra/Downloads/photo recog/data/galleries/"*/
# Restart the app — processing runs automatically on startup
```

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
