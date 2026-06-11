@echo off
title He thong xac thuc SmartFace

echo 1. Dang khoi dong Python FastAPI Backend...
start cmd /k "cd /d D:\AI\SmartFace\database_pdt && python main.py"

echo 2. Dang khoi dong React Frontend...
start cmd /k "cd /d D:\AI\SmartFace\frontend && npm run dev"

echo 3. Dang tu dong mo trinh duyet...
timeout /t 3 >nul
start http://localhost:5174

echo Khoi dong hoan tat!