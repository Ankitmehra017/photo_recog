import os
import shutil

from fastapi import APIRouter, Request, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from config import PHOTOS_DIR, SELFIES_DIR, GALLERIES_DIR, PROJECT_ROOT
from database import get_conn
from face_engine import process_all_unprocessed, clear_cache

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "templates"))

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".bmp", ".tiff"}


@router.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@router.post("/upload")
async def upload_photos(
    background_tasks: BackgroundTasks,
    photos: list[UploadFile] = File(...),
):
    saved = []
    for photo in photos:
        safe_name = os.path.basename(photo.filename or f"photo_{len(saved)}.jpg")
        dest = os.path.join(PHOTOS_DIR, safe_name)

        if os.path.exists(dest):
            base, ext = os.path.splitext(safe_name)
            import uuid as _uuid
            safe_name = f"{base}_{_uuid.uuid4().hex[:6]}{ext}"
            dest = os.path.join(PHOTOS_DIR, safe_name)

        contents = await photo.read()
        with open(dest, "wb") as f:
            f.write(contents)

        with get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO wedding_photos (filename, file_path) VALUES (?, ?)",
                (safe_name, dest),
            )
        saved.append(safe_name)

    background_tasks.add_task(process_all_unprocessed)
    return JSONResponse(
        {"queued": len(saved), "files": saved, "message": "Processing started in background"}
    )


@router.post("/upload-folder")
async def upload_from_folder(
    background_tasks: BackgroundTasks,
    folder_path: str = Form(...),
):
    folder_path = folder_path.strip()

    if not os.path.isdir(folder_path):
        return JSONResponse({"error": f"Folder not found: {folder_path}"}, status_code=400)

    registered = []
    skipped = []

    for filename in os.listdir(folder_path):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            continue

        src = os.path.join(folder_path, filename)
        dest = os.path.join(PHOTOS_DIR, filename)

        # Handle filename collisions
        if os.path.exists(dest):
            base, e = os.path.splitext(filename)
            import uuid as _uuid
            filename = f"{base}_{_uuid.uuid4().hex[:6]}{e}"
            dest = os.path.join(PHOTOS_DIR, filename)

        # Link or copy into the managed photos dir
        import shutil
        shutil.copy2(src, dest)

        with get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO wedding_photos (filename, file_path) VALUES (?, ?)",
                (filename, dest),
            )
        registered.append(filename)

    if not registered:
        return JSONResponse({"error": "No image files found in that folder."}, status_code=400)

    background_tasks.add_task(process_all_unprocessed)
    return JSONResponse({
        "queued": len(registered),
        "files": registered,
        "message": f"Found {len(registered)} photos. Processing started in background.",
    })


@router.get("/status")
async def processing_status():
    import face_engine  # deferred — reads live IS_PROCESSING module attribute
    with get_conn() as conn:
        total     = conn.execute("SELECT COUNT(*) FROM wedding_photos").fetchone()[0]
        processed = conn.execute("SELECT COUNT(*) FROM wedding_photos WHERE processed = 1").fetchone()[0]
        matches   = conn.execute("SELECT COUNT(*) FROM guest_photo_matches").fetchone()[0]
    pending = total - processed
    percent = round((processed / total) * 100) if total > 0 else 0
    return {
        "total": total,
        "processed": processed,
        "pending": pending,
        "percent": percent,
        "matches_found": matches,
        "is_processing": face_engine.IS_PROCESSING,
    }


@router.post("/reset")
async def reset_all_data():
    """Delete all guests, photos, matches, and uploaded files."""
    with get_conn() as conn:
        conn.executescript("""
            DELETE FROM guest_photo_matches;
            DELETE FROM wedding_photos;
            DELETE FROM guests;
        """)

    for directory in [PHOTOS_DIR, GALLERIES_DIR, SELFIES_DIR]:
        if os.path.isdir(directory):
            shutil.rmtree(directory)
            os.makedirs(directory)

    clear_cache()
    return {"message": "All data cleared."}
