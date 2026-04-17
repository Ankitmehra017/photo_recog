import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Data paths
SELFIES_DIR     = os.path.join(PROJECT_ROOT, "data", "selfies")
PHOTOS_DIR      = os.path.join(PROJECT_ROOT, "data", "wedding_photos")
GALLERIES_DIR   = os.path.join(PROJECT_ROOT, "data", "galleries")
DB_PATH         = os.path.join(PROJECT_ROOT, "data", "db", "wedding.db")

# Face matching (insightface / ArcFace)
MATCH_THRESHOLD   = 0.35      # cosine similarity; higher = stricter (range 0–1)
MAX_SELFIE_EDGE   = 800       # px
MAX_PHOTO_EDGE    = 1200      # px

# Server
HOST             = "0.0.0.0"
PORT             = 8000
GALLERY_BASE_URL = os.environ.get("GALLERY_BASE_URL", "http://localhost:8000")
