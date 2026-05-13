@echo off
start "inbox-zera backend" cmd /k "cd /d %~dp0backend && uv run uvicorn main:app --reload"
start "inbox-zera frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
