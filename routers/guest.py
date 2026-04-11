import os
import uuid

import numpy as np
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config import SELFIES_DIR, PROJECT_ROOT
from database import get_conn
from face_engine import encode_selfie, add_guest_to_cache, match_guest_to_existing_photos

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "templates"))


@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request, success: int = 0, error: str = ""):
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "success": success, "error": error},
    )


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    selfie: UploadFile = File(...),
):
    # Check duplicate email
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM guests WHERE email = ?", (email,)).fetchone()
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "already_registered", "success": 0},
        )

    # Save selfie to disk
    ext = os.path.splitext(selfie.filename or "selfie.jpg")[1] or ".jpg"
    selfie_filename = f"{uuid.uuid4()}{ext}"
    selfie_path = os.path.join(SELFIES_DIR, selfie_filename)
    contents = await selfie.read()
    with open(selfie_path, "wb") as f:
        f.write(contents)

    # Encode face
    try:
        embedding = encode_selfie(selfie_path)
    except (ValueError, Exception) as e:
        os.remove(selfie_path)
        error_msg = str(e) if str(e) in ("no_face", "multiple_faces") else "bad_image"
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": error_msg, "success": 0},
        )

    # Persist guest
    token = str(uuid.uuid4())
    embedding_bytes = embedding.astype(np.float32).tobytes()

    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO guests (name, email, token, selfie_path, embedding) VALUES (?, ?, ?, ?, ?)",
            (name, email, token, selfie_path, embedding_bytes),
        )
        guest_id = cursor.lastrowid

    # Update in-memory cache
    add_guest_to_cache(guest_id, token, embedding)

    # Retroactively match against already-uploaded photos
    match_guest_to_existing_photos(guest_id, token, embedding)

    return templates.TemplateResponse(
        "register.html",
        {"request": request, "success": 1, "error": "", "gallery_token": token},
    )
