from fastapi import FastAPI, Request, Depends, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date, datetime
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os, socket, json, shutil
from fastapi.responses import JSONResponse

from models import Base, Schedule
from database import engine, SessionLocal

# 기본 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
Base.metadata.create_all(bind=engine)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 의존성 주입
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 루트 페이지
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index2.html", {"request": request})

# 오늘 할 일 및 일정 가져오기
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

# 일정 등록
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

# 일정 완료 상태 업데이트
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

# 클라이언트 IP 반환
@app.get("/get-client-ip")
async def get_client_ip(request: Request):
    client_host = request.client.host
    return {"client_ip": client_host}


#음악 설정
UPLOAD_FOLDER = "static/music"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.post("/upload-music/")
async def upload_music(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"file_path": f"/{UPLOAD_FOLDER}/{file.filename}"}



#음악리스트 제공
@app.get("/list-music/")
async def list_music():
    files = os.listdir(UPLOAD_FOLDER)
    wav_files = [f for f in files if f.endswith(".wav")]
    return JSONResponse(content=wav_files)



