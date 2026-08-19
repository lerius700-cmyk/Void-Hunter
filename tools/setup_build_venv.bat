@echo off
REM Rebuild the .build-venv from scratch with all the deps the project needs.
REM Use when numpy or another requirements.txt dep is missing.
setlocal
cd /d %~dp0..

if not exist .build-venv (
    uv venv .build-venv --python "%USERPROFILE%\.local\bin\python3.11.exe"
)

uv pip install --python ".build-venv\Scripts\python.exe" -r requirements.txt -r requirements-dev.txt
