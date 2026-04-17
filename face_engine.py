"""
Face detection, encoding, and matching engine.
Uses insightface (ArcFace model via ONNX Runtime) — no compilation required.
"""

import os
import shutil
import threading
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image, ImageOps

# Register HEIC/HEIF support (iPhone photos) if pillow-heif is installed
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

from config import (
    MATCH_THRESHOLD, MAX_SELFIE_EDGE, MAX_PHOTO_EDGE, GALLERIES_DIR
)

# Lazy-init: insightface app is heavy to load, do it once per process
_APP = None

def _get_app():
    global _APP
    if _APP is None:
        from insightface.app import FaceAnalysis
        _APP = FaceAnalysis(providers=["CPUExecutionProvider"])
        _APP.prepare(ctx_id=0, det_size=(640, 640))
    return _APP


# In-memory cache: list of dicts with keys: id, token, embedding (np.ndarray)
_GUEST_CACHE: list[dict] = []

# Processing state
IS_PROCESSING = False
_PROCESSING_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def _load_image(path: str, max_edge: int) -> np.ndarray:
    """Load image, fix EXIF rotation, resize, return as RGB numpy array."""
    img = Image.open(path).convert("RGB")
    img = ImageOps.exif_transpose(img)
    w, h = img.size
    scale = max_edge / max(w, h)
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return np.array(img)


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

def encode_selfie(path: str) -> np.ndarray:
    """
    Encode a guest selfie. Returns 512-d ArcFace embedding (float32).
    Raises ValueError if 0 or more than 1 face is found.
    """
    img = _load_image(path, MAX_SELFIE_EDGE)
    faces = _get_app().get(img)
    if len(faces) == 0:
        raise ValueError("no_face")
    if len(faces) > 1:
        raise ValueError("multiple_faces")
    return faces[0].normed_embedding.astype(np.float32)


def extract_faces(photo_path: str) -> list[np.ndarray]:
    """
    Extract all face embeddings from a wedding photo.
    Returns a list of 512-d float32 arrays (one per face found).
    """
    img = _load_image(photo_path, MAX_PHOTO_EDGE)
    faces = _get_app().get(img)
    return [f.normed_embedding.astype(np.float32) for f in faces]


# ---------------------------------------------------------------------------
# Distance & matching
# ---------------------------------------------------------------------------

def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two L2-normalized embeddings."""
    return float(np.dot(a, b))


def find_matching_guests(face_embedding: np.ndarray) -> list[tuple[int, str, float]]:
    """
    Compare a face embedding against all cached guests.
    Returns list of (guest_id, token, similarity) sorted by similarity desc.
    """
    results = []
    for g in _GUEST_CACHE:
        sim = _cosine_sim(face_embedding, g["embedding"])
        if sim >= MATCH_THRESHOLD:
            results.append((g["id"], g["token"], sim))
    results.sort(key=lambda x: x[2], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def warm_cache():
    """Load all guest embeddings into memory. Call on app startup."""
    from database import get_conn
    _GUEST_CACHE.clear()
    with get_conn() as conn:
        rows = conn.execute("SELECT id, token, embedding FROM guests").fetchall()
    for row in rows:
        _GUEST_CACHE.append({
            "id": row["id"],
            "token": row["token"],
            "embedding": np.frombuffer(row["embedding"], dtype=np.float32).copy(),
        })


def add_guest_to_cache(guest_id: int, token: str, embedding: np.ndarray):
    """Add a newly registered guest to the in-memory cache."""
    _GUEST_CACHE.append({
        "id": guest_id,
        "token": token,
        "embedding": embedding.copy(),
    })


def clear_cache():
    """Wipe the in-memory guest cache (call after a full data reset)."""
    _GUEST_CACHE.clear()


# ---------------------------------------------------------------------------
# Match recording
# ---------------------------------------------------------------------------

def _record_match(conn, guest_id: int, photo_id: int, similarity: float, token: str, photo_path: str):
    """Insert a match record and copy photo to guest gallery folder."""
    conn.execute(
        "INSERT OR IGNORE INTO guest_photo_matches (guest_id, photo_id, distance) VALUES (?, ?, ?)",
        (guest_id, photo_id, similarity),
    )
    gallery_dir = os.path.join(GALLERIES_DIR, token)
    os.makedirs(gallery_dir, exist_ok=True)
    dest = os.path.join(gallery_dir, os.path.basename(photo_path))
    if not os.path.exists(dest):
        shutil.copy2(photo_path, dest)


# ---------------------------------------------------------------------------
# Worker function (module-level — required for ProcessPoolExecutor pickling)
# ---------------------------------------------------------------------------

def _worker_process_photo(args):
    """
    Runs in a subprocess. Loads its own insightface instance.
    Receives serializable args only (no numpy arrays, no DB connections).
    Returns (photo_id, list_of_match_tuples).
    """
    photo_id, file_path, guest_list = args
    try:
        face_embeddings = extract_faces(file_path)
    except Exception:
        return (photo_id, [])  # unreadable/no-face photo — mark processed, no matches

    matches_out = []
    for face_emb in face_embeddings:
        for guest in guest_list:
            emb = np.frombuffer(guest["embedding_bytes"], dtype=np.float32)
            sim = _cosine_sim(face_emb, emb)
            if sim >= MATCH_THRESHOLD:
                matches_out.append((guest["id"], guest["token"], sim))
    return (photo_id, matches_out)


# ---------------------------------------------------------------------------
# Processing pipelines
# ---------------------------------------------------------------------------

def process_all_unprocessed():
    """
    Match all unprocessed wedding photos against all registered guests.
    Uses ProcessPoolExecutor for parallel CPU-bound face inference.
    All DB writes happen in the main process.
    """
    global IS_PROCESSING
    from database import get_conn

    with _PROCESSING_LOCK:
        if IS_PROCESSING:
            return  # already running — new photos will be caught by the while loop
        IS_PROCESSING = True

    try:
        # Serialize guest embeddings as bytes for safe IPC (no numpy across processes)
        guest_list = [
            {
                "id": g["id"],
                "token": g["token"],
                "embedding_bytes": g["embedding"].astype(np.float32).tobytes(),
            }
            for g in _GUEST_CACHE
        ]

        max_workers = max(1, (os.cpu_count() or 4) - 1)

        # Loop handles photos uploaded while we're already processing
        while True:
            with get_conn() as conn:
                photos = conn.execute(
                    "SELECT id, file_path FROM wedding_photos WHERE processed = 0"
                ).fetchall()

            if not photos:
                break

            args_list = [(p["id"], p["file_path"], guest_list) for p in photos]

            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(_worker_process_photo, a) for a in args_list]
                for future in as_completed(futures):
                    photo_id, matches = future.result()
                    with get_conn() as conn:
                        for guest_id, token, sim in matches:
                            row = conn.execute(
                                "SELECT file_path FROM wedding_photos WHERE id = ?", (photo_id,)
                            ).fetchone()
                            if row:
                                _record_match(conn, guest_id, photo_id, sim, token, row["file_path"])
                        conn.execute(
                            "UPDATE wedding_photos SET processed = 1 WHERE id = ?", (photo_id,)
                        )

    finally:
        with _PROCESSING_LOCK:
            IS_PROCESSING = False


def match_guest_to_existing_photos(guest_id: int, token: str, embedding: np.ndarray):
    """
    When a guest registers after photos are already uploaded,
    retroactively match them against all processed photos.
    """
    from database import get_conn

    with get_conn() as conn:
        photos = conn.execute(
            "SELECT id, file_path FROM wedding_photos WHERE processed = 1"
        ).fetchall()

        for photo in photos:
            try:
                face_embeddings = extract_faces(photo["file_path"])
            except Exception:
                continue
            for face_emb in face_embeddings:
                sim = _cosine_sim(embedding, face_emb)
                if sim >= MATCH_THRESHOLD:
                    _record_match(conn, guest_id, photo["id"], sim, token, photo["file_path"])
