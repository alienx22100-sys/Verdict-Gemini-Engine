
@echo off
echo Initializing Git...
git init
git remote add origin https://github.com/alienx22100-sys/Verdict-Gemini-Engine.git
git branch -M main
git add .
git commit -m "Initial commit: Decision Authority Project"
git push -u origin main
pause
