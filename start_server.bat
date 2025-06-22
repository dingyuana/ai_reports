
@echo off
echo Starting FastAPI server on http://0.0.0.0:8000
echo Press CTRL+C to stop the server.
call .venv\Scripts\python.exe -m uvicorn main:report --host 0.0.0.0 --port 8000
pause 