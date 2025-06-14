from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index2.html", {"request": request})

@app.get("/tasks", response_class=HTMLResponse)
async def read_tasks(request: Request):
    # 예시 일정 (DB 연동 시 여기서 조회)
    today = date.today().isoformat()
    tasks = [
        {"title": "회의 준비", "date": today},
        {"title": "팀 미팅", "date": today},
        {"title": "과제 제출", "date": "2025-06-15"},
    ]
    today_tasks = [task for task in tasks if task["date"] == today]
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": today_tasks, "today": today})
