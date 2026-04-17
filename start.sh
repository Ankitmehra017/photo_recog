#!/bin/bash
set -e

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env — edit PHOTOS_FOLDER and GALLERY_BASE_URL if needed, then run this script again."
    exit 0
fi

mkdir -p empty_photos

echo "Starting Wedding Photo System..."
docker compose up --build -d

echo ""
echo "✅  App is running at: http://localhost:8000"
echo ""
echo "To stop:  docker compose down"
echo "To reset: docker compose down -v  (clears all data)"
