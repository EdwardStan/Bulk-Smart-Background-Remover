@echo off
echo Installing dependencies...
pip install -r requirements.txt > nul

echo Running app...
python bg_remove_app.py
pause