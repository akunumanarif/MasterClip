# Start Backend
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--app-dir", "backend"

# Start Frontend
Set-Location frontend
npm run dev
