import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from config import HOST, PORT, PROJECT_ROOT
from database import init_db
from face_engine import warm_cache
from routers import guest, photographer, gallery

import os

app = FastAPI(title="Wedding Photo System")

# Static files & templates
app.mount("/static", StaticFiles(directory=os.path.join(PROJECT_ROOT, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "templates"))


@app.on_event("startup")
async def startup():
    init_db()
    warm_cache()


# Landing page
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})


# Routers
app.include_router(guest.router)
app.include_router(photographer.router)
app.include_router(gallery.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
