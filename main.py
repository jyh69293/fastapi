from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date, datetime
import os

from models import Base, Schedule
from database import engine, SessionLocal
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
Base.metadata.create_all(bind=engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용 전체 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index2.html", {"request": request})

@app.get("/tasks", response_class=HTMLResponse)
async def read_tasks(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    schedules = db.query(Schedule).filter(
        Schedule.start_time >= today_start,
        Schedule.start_time <= today_end
    ).all()

    return templates.TemplateResponse("tasks.html", {
        "request": request,
        "tasks": schedules,
        "today": today.isoformat()
    })

class ScheduleCreate(BaseModel):
    user_id: str
    title: str
    is_todo: bool
    start_time: datetime
    end_date: str  # YYYY-MM-DD

@app.post("/schedule/")
def create_schedule(schedule: ScheduleCreate, db: Session = Depends(get_db)):
    if schedule.is_todo:
        end_time = datetime.strptime(schedule.end_date + " 23:59:00", "%Y-%m-%d %H:%M:%S")
    else:
        end_time = datetime.strptime(schedule.end_date, "%Y-%m-%d %H:%M:%S")

    new_schedule = Schedule(
        user_id=schedule.user_id,
        title=schedule.title,
        is_todo=schedule.is_todo,
        start_time=schedule.start_time,
        end_time=end_time
    )
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    return new_schedule


from fastapi import HTTPException

# 일정 완료 상태 업데이트 (체크박스)
@app.patch("/schedule/{schedule_id}")
def update_schedule_completion(schedule_id: int, is_completed: bool, db: Session = Depends(get_db)):
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    schedule.is_completed = is_completed
    db.commit()
    return {"message": "Updated"}

# 일정 삭제
@app.delete("/schedule/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(schedule)
    db.commit()
    return {"message": "Deleted"}




import socket

app = FastAPI()

@app.get("/get-local-ip")
def get_local_ip():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return {"local_ip": local_ip}
