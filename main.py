import os
import tempfile
import json
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
import database
from pydantic import BaseModel

# ==========================================
# 🔑 นำ API Key ใหม่มาใส่ในเครื่องหมายคำพูดด้านล่าง
# ==========================================
client = genai.Client(api_key="AQ.Ab8RN6JQ1rvocDQyRp1gTe2QgWIUsFl7hgS1mYWzR9EodchwnQ")

app = FastAPI(title="AI Quiz Generator API")
database.init_db()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- ระบบ Login/Register ---
@app.post("/api/register")
def register(username: str = Form(...), password: str = Form(...)):
    result = database.create_user(username, password)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/api/login")
def login(username: str = Form(...), password: str = Form(...)):
    result = database.verify_user(username, password)
    if result["status"] == "error":
        raise HTTPException(status_code=401, detail=result["message"])
    return result

# --- ระบบ Quiz ---
@app.post("/api/generate-quiz")
async def generate_quiz(
    file: UploadFile = File(...),
    num_questions: int = Form(...),
    user_id: int = Form(...) # รับ user_id เพื่อบันทึกว่าของใคร
):
    temp_file_path = None
    try:
        file_extension = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        uploaded_file = client.files.upload(file=temp_file_path)
        prompt = f"จงสร้างแบบทดสอบ {num_questions} ข้อ 5 ตัวเลือกพร้อมเฉลยในรูปแบบ JSON โดยให้โครงสร้างประกอบด้วย id, question, options (a, b, c, d, e) และ correctAnswer"
        
        response = client.models.generate_content(
           model='gemini-3.6-flash',
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )

        client.files.delete(name=uploaded_file.name)
        quiz_data = json.loads(response.text)
        
        # บันทึกลงฐานข้อมูลพร้อมผูก user_id
        quiz_set_id = database.save_quiz_to_db(user_id, file.filename, quiz_data)

        return {"status": "success", "quiz_set_id": quiz_set_id, "data": quiz_data}

    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/api/history/{user_id}")
def get_history(user_id: int):
    try:
        history = database.get_all_quiz_sets(user_id)
        return {"status": "success", "data": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/quiz/{quiz_id}")
def get_quiz(quiz_id: int):
    try:
        quiz_data = database.get_quiz_by_id(quiz_id)
        if not quiz_data:
            raise HTTPException(status_code=404, detail="ไม่พบชุดข้อสอบนี้")
        return {"status": "success", "data": quiz_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save-score/{quiz_id}")
def save_score(quiz_id: int, score: int = Form(...)):
    try:
        database.update_score(quiz_id, score)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))