# Wedding Photo Recognition System

Guests register with a selfie, the photographer uploads event photos, and each guest gets a private gallery link showing only their photos.

---

## Prerequisites

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) — one-time setup, just download and open it like any app.

---

## Setup (first time)

1. Download and unzip this project folder
2. Open the folder — you'll see a file called `.env.example`
3. Copy `.env.example` and rename the copy to `.env`
4. If you're sharing the app publicly via ngrok, open `.env` and set:

```
GALLERY_BASE_URL=https://your-url.ngrok-free.app
```

Otherwise leave `.env` as-is — it works out of the box for local use.

---

## Start the app

**Mac:**
```bash
./start.sh
```

**Windows:** Double-click `start.bat`

Then open: **http://localhost:8000**

> The first start takes 5–10 minutes — it downloads the face recognition model (~300 MB). Every start after that is fast. Use the same command every time.

---

## How to use

1. **Guests** visit `/register` — enter name and take a selfie
2. **Photographer** visits `/upload` — click "Select Folder" and pick the photos folder, or select files manually
3. Face matching runs automatically in the background
4. Each guest bookmarks their gallery link shown after registration — photos appear as they're processed

---

## Sharing publicly with ngrok

ngrok gives your app a public URL so guests can register from anywhere (not just your WiFi).

**One-time setup:**

1. Install ngrok from [ngrok.com/download](https://ngrok.com/download) (or `brew install ngrok` on Mac)
2. Sign up for a free account at ngrok.com and copy your auth token
3. Save the token:
```bash
ngrok config add-authtoken YOUR_TOKEN_HERE
```

**Every time you use ngrok:**

1. Start the app first:
```bash
./start.sh
```

2. In a new terminal window, run:
```bash
ngrok http 8000
```

3. Copy the URL from the output, e.g. `https://abc123.ngrok-free.app`

4. Open `.env` and set:
```
GALLERY_BASE_URL=https://abc123.ngrok-free.app
```

5. Restart the app to pick up the new URL:
```bash
docker compose down
./start.sh
```

6. Share `https://abc123.ngrok-free.app/register` with guests.

> Free ngrok gives a new URL every time you restart it. A paid plan gives a fixed URL.

---

## Reset for a new event

Go to `/upload` and click **"Reset All Data"** at the bottom of the page. This clears all photos, guests, and matches.

---

## Stop the app

```bash
docker compose down
```

---

## Configuration

| Setting | Where | Description |
|---------|-------|-------------|
| `GALLERY_BASE_URL` | `.env` | Public URL for gallery links (set to ngrok URL when sharing) |
| `MATCH_THRESHOLD` | `config.py` | Face match sensitivity (0–1). Lower = stricter. Default: 0.35 |
