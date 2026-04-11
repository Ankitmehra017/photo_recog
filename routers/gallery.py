import io
import os
import re
import zipfile

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config import GALLERIES_DIR, PROJECT_ROOT
from database import get_conn

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "templates"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(name: str) -> str:
    """Convert a guest name to a safe filename slug."""
    return re.sub(r"[^\w]", "_", name).strip("_")


def _zip_stream_generator(file_paths: list[str]):
    """
    Yields ZIP bytes one file at a time — peak RAM ≈ one photo.
    Uses ZIP_STORED (no compression) — correct for JPEGs which are already compressed.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_STORED) as zf:
        for path in file_paths:
            zf.write(path, arcname=os.path.basename(path))
            buf.seek(0)
            chunk = buf.read()
            buf.seek(0)
            buf.truncate()
            if chunk:
                yield chunk
    # Yield final ZIP central directory (written on ZipFile close)
    buf.seek(0)
    remaining = buf.read()
    if remaining:
        yield remaining


def _get_validated_paths(guest_id: int, filenames: list[str], token: str) -> list[str]:
    """
    Returns absolute file paths for filenames that belong to this guest.
    Guards against path traversal and cross-guest access.
    """
    paths = []
    with get_conn() as conn:
        for fn in filenames:
            safe = os.path.basename(fn)  # strip any path traversal
            row = conn.execute(
                """
                SELECT wp.filename FROM guest_photo_matches gpm
                JOIN wedding_photos wp ON wp.id = gpm.photo_id
                WHERE gpm.guest_id = ? AND wp.filename = ?
                """,
                (guest_id, safe),
            ).fetchone()
            if row:
                fpath = os.path.join(GALLERIES_DIR, token, safe)
                if os.path.exists(fpath):
                    paths.append(fpath)
    return paths


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/gallery/{token}", response_class=HTMLResponse)
async def guest_gallery(request: Request, token: str):
    with get_conn() as conn:
        guest = conn.execute(
            "SELECT id, name FROM guests WHERE token = ?", (token,)
        ).fetchone()

    if not guest:
        raise HTTPException(status_code=404, detail="Gallery not found")

    with get_conn() as conn:
        photos = conn.execute(
            """
            SELECT wp.filename
            FROM guest_photo_matches gpm
            JOIN wedding_photos wp ON wp.id = gpm.photo_id
            WHERE gpm.guest_id = ?
            ORDER BY gpm.distance ASC
            """,
            (guest["id"],),
        ).fetchall()

    photo_urls = [f"/photos/{token}/{row['filename']}" for row in photos]

    return templates.TemplateResponse(
        "gallery.html",
        {
            "request": request,
            "guest_name": guest["name"],
            "token": token,
            "photos": photo_urls,
            "count": len(photo_urls),
        },
    )


@router.get("/photos/{token}/{filename}")
async def serve_photo(token: str, filename: str):
    with get_conn() as conn:
        guest = conn.execute(
            "SELECT id FROM guests WHERE token = ?", (token,)
        ).fetchone()

    if not guest:
        raise HTTPException(status_code=404, detail="Not found")

    with get_conn() as conn:
        match = conn.execute(
            """
            SELECT gpm.id FROM guest_photo_matches gpm
            JOIN wedding_photos wp ON wp.id = gpm.photo_id
            WHERE gpm.guest_id = ? AND wp.filename = ?
            """,
            (guest["id"], filename),
        ).fetchone()

    if not match:
        raise HTTPException(status_code=403, detail="Forbidden")

    safe_filename = os.path.basename(filename)
    file_path = os.path.join(GALLERIES_DIR, token, safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


@router.get("/download-all/{token}")
async def download_all(token: str):
    with get_conn() as conn:
        guest = conn.execute(
            "SELECT id, name FROM guests WHERE token = ?", (token,)
        ).fetchone()

    if not guest:
        raise HTTPException(status_code=404, detail="Gallery not found")

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT wp.filename FROM guest_photo_matches gpm
            JOIN wedding_photos wp ON wp.id = gpm.photo_id
            WHERE gpm.guest_id = ?
            ORDER BY gpm.distance ASC
            """,
            (guest["id"],),
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=400, detail="No photos to download")

    file_paths = []
    for row in rows:
        fpath = os.path.join(GALLERIES_DIR, token, os.path.basename(row["filename"]))
        if os.path.exists(fpath):
            file_paths.append(fpath)

    if not file_paths:
        raise HTTPException(status_code=400, detail="No photo files found on disk")

    zip_name = f"wedding_photos_{_slug(guest['name'])}.zip"
    return StreamingResponse(
        _zip_stream_generator(file_paths),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


class DownloadRequest(BaseModel):
    filenames: list[str]


@router.post("/download-selected/{token}")
async def download_selected(token: str, body: DownloadRequest):
    if not body.filenames:
        raise HTTPException(status_code=400, detail="No files selected")

    with get_conn() as conn:
        guest = conn.execute(
            "SELECT id, name FROM guests WHERE token = ?", (token,)
        ).fetchone()

    if not guest:
        raise HTTPException(status_code=404, detail="Gallery not found")

    file_paths = _get_validated_paths(guest["id"], body.filenames, token)

    if not file_paths:
        raise HTTPException(status_code=400, detail="No valid files found for the selection")

    zip_name = f"wedding_photos_{_slug(guest['name'])}.zip"
    return StreamingResponse(
        _zip_stream_generator(file_paths),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )
