@echo off

if not exist .env (
    copy .env.example .env
    echo Created .env — edit PHOTOS_FOLDER and GALLERY_BASE_URL if needed, then run this script again.
    pause
    exit /b
)

if not exist empty_photos mkdir empty_photos

echo Starting Wedding Photo System...
docker compose up --build -d

echo.
echo App is running at: http://localhost:8000
echo.
echo To stop:  docker compose down
echo To reset: docker compose down -v  (clears all data)
pause
