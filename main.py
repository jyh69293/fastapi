from fastapi import FastAPI, Request, Depends, HTTPException, File, UploadFile, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date, datetime
import os, socket, json, shutil

from models import Base, Schedule, Setting, Alarm
from database import engine, SessionLocal
router = APIRouter()


# --- 기본 설정 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = "static/music"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- JSON 저장 폴더 경로 ---
JSON_FOLDER = os.path.join(BASE_DIR, "Json")
os.makedirs(JSON_FOLDER, exist_ok=True)
JSON_EXPORT_PATH = os.path.join(JSON_FOLDER, "tasks_export.json")

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
Base.metadata.create_all(bind=engine)

# --- CORS 설정 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB 세션 의존성 주입 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- JSON 파일 저장 함수 ---
def export_schedules_to_json(db: Session):
    schedules = db.query(Schedule).all()
    task_data = [
        {
            "id": s.id,
            "title": s.title,
            "is_todo": s.is_todo,
            "is_completed": s.is_completed,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "user_id": s.user_id
        }
        for s in schedules
    ]
    with open(JSON_EXPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(task_data, f, ensure_ascii=False, indent=2)

# --- 루트 페이지 ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index2.html", {"request": request})

# --- HTML 페이지에 오늘의 일정 표시 (JSON 기반) ---
@app.get("/tasks", response_class=HTMLResponse)
async def read_tasks(request: Request):
    try:
        with open(JSON_EXPORT_PATH, "r", encoding="utf-8") as f:
            all_tasks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        all_tasks = []

    today_str = date.today().isoformat()
    today_tasks = [task for task in all_tasks if task["start_time"].startswith(today_str)]

    return templates.TemplateResponse("tasks.html", {
        "request": request,
        "tasks": today_tasks,
        "today": today_str
    })

# --- 일정 등록 ---
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

    export_schedules_to_json(db)
    return new_schedule

# --- 일정 완료 상태 업데이트 ---
@app.patch("/schedule/{schedule_id}")
def update_schedule_completion(schedule_id: int, is_completed: bool, db: Session = Depends(get_db)):
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    schedule.is_completed = is_completed
    db.commit()
    export_schedules_to_json(db)
    return {"message": "Updated"}

# --- 일정 삭제 ---
@app.delete("/schedule/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(schedule)
    db.commit()
    export_schedules_to_json(db)
    return {"message": "Deleted"}

# --- JSON API: 오늘의 일정 반환 ---
@app.get("/api/tasks/today", response_class=JSONResponse)
def get_today_tasks_from_json():
    try:
        with open(JSON_EXPORT_PATH, "r", encoding="utf-8") as f:
            all_tasks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="JSON 파일 오류")

    today_str = date.today().isoformat()
    today_tasks = [task for task in all_tasks if task["start_time"].startswith(today_str)]
    return today_tasks

# --- JSON API: 전체 스케줄 ID 반환 ---
@app.get("/api/schedule-ids")
def get_schedule_ids(db: Session = Depends(get_db)):
    schedules = db.query(Schedule.id).all()
    id_list = [s.id for s in schedules]
    return {"ids": id_list}

# --- 클라이언트 IP 확인 ---
@app.get("/get-client-ip")
async def get_client_ip(request: Request):
    return {"client_ip": request.client.host}

# --- 음악 업로드 ---
@app.post("/upload-music/")
async def upload_music(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"file_path": f"/{UPLOAD_FOLDER}/{file.filename}"}

# --- 음악 파일 목록 조회 ---
@app.get("/list-music/")
async def list_music():
    files = os.listdir(UPLOAD_FOLDER)
    wav_files = [f for f in files if f.endswith(".wav")]
    return JSONResponse(content=wav_files)

# --- 설정 모델 ---
class SettingSchema(BaseModel):
    key: str
    value: str
    user_id: str = None
    type: str = "string"
    category: str = None

# --- 설정 저장 ---
@app.post("/settings")
def set_setting(setting: SettingSchema, db: Session = Depends(get_db)):
    db_setting = db.query(Setting).filter(Setting.key == setting.key).first()
    if db_setting:
        db_setting.value = setting.value
        db_setting.user_id = setting.user_id
        db_setting.type = setting.type
        db_setting.category = setting.category
    else:
        db_setting = Setting(**setting.dict())
        db.add(db_setting)
    db.commit()
    return {"message": "설정이 저장되었습니다."}

# --- 특정 설정 가져오기 ---
@app.get("/settings/{key}")
def get_setting(key: str, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        return {
            "key": setting.key,
            "value": setting.value,
            "type": setting.type,
            "category": setting.category,
            "user_id": setting.user_id
        }
    raise HTTPException(status_code=404, detail="해당 설정이 없습니다.")

# --- 모든 설정 가져오기 ---
@app.get("/settings")
def get_all_settings(db: Session = Depends(get_db)):
    settings = db.query(Setting).all()
    return [{"key": s.key, "value": s.value} for s in settings]


#------------- 알람 관련 api------------------------
@router.post("/api/alarms")
def create_alarm(alarm: AlarmCreate, db: Session = Depends(get_db)):
    if not alarm.music_path:
        alarm.music_path = "static/music/default.mp3"

    db_alarm = Alarm(**alarm.dict())
    db.add(db_alarm)
    db.commit()
    db.refresh(db_alarm)
    return {"id": db_alarm.id}

@router.delete("/api/alarms/{alarm_id}")
def delete_alarm(alarm_id: int, db: Session = Depends(get_db)):
    alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    db.delete(alarm)
    db.commit()
    return {"message": "Alarm deleted"}

@router.get("/api/alarms")
def get_alarms(user_id: str, db: Session = Depends(get_db)):
    alarms = db.query(Alarm).filter(Alarm.user_id == user_id).all()
    return alarms










