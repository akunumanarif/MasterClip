# Start Backend
Start-Process -NoNewWindow -FilePath "C:\Users\numan\Documents\Projects\YoutubeVideoClipper\venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--app-dir", "backend"

# Start Frontend
Set-Location frontend
npm run dev
