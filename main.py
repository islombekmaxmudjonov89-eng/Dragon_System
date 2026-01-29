import time
import uuid
import os
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
import uvicorn

app = FastAPI(title="Dragon Global: 2B+ Edition")

# --- 🛰️ DATABASE (HIGH-SCALE ASYNC) ---
# Diqqat: <db_password> o'rniga o'z parolingni qo'y!
MONGO_URL = "mongodb+srv://Dragon_admin:<db_password>@islombek.zpglyqc.mongodb.net/?appName=islombek"
client = AsyncIOMotorClient(MONGO_URL, maxPoolSize=100) # Bir vaqtda 100 ulanish
db = client['dragon_game_db']
accounts_db = db['players_vault']
sessions_db = db['active_sessions']

# --- MODELS (VALIDATION) ---
class PlayerConnect(BaseModel):
    player_id: str
    hwid: str

class UCRequest(BaseModel):
    player_id: str
    amount: int
    secret_key: str

# --- 🐉 DRAGON LOGS (O'YINDAN KELADIGAN LOGLAR) ---
@app.post("/log")
async def receive_game_logs(request: Request):
    """Config.json dagi logReportUrl uchun"""
    try:
        data = await request.json()
        # 2mlrd+ odamda loglarni terminalga chiqarish serverni sekinlashtiradi,
        # lekin hozircha tekshirishing uchun qoldirdim
        print(f"🐉 Dragon Log: {data}") 
        return {"status": "ok"}
    except:
        return {"status": "error"}

# --- 💰 UC/BC SERVICE (SYSTEM INTEGRATION) ---
@app.post("/v1/internal/add-bc")
async def add_bc_to_account(data: UCRequest):
    """UC Paneldan kelgan so'rovni bazaga muhrlash"""
    if data.secret_key != "DRAGON_SECRET_99": 
        raise HTTPException(status_code=403, detail="Taqiqlangan kirish!")

    await accounts_db.update_one(
        {"player_id": data.player_id},
        {"$inc": {"bc_balance": data.amount},
         "$setOnInsert": {"registered_hwid": "HWID_PENDING", "created_at": time.time()}},
        upsert=True
    )
    return {"status": "success", "player": data.player_id}

# --- 🚀 CONNECT & SYNC (2MLRD+ SCALE) ---
@app.post("/v1/game/connect")
async def connect_player(data: PlayerConnect):
    """O'yinchi kirganda sessiya ochish"""
    session_id = str(uuid.uuid4())
    
    # Asinxron yozish - 2mlrd odamda server qotib qolmaydi
    await sessions_db.update_one(
        {"player_id": data.player_id},
        {"$set": {
            "session_id": session_id, 
            "hwid": data.hwid, 
            "timestamp": time.time(),
            "x": 0, "y": 0
        }},
        upsert=True
    )
    
    acc = await accounts_db.find_one({"player_id": data.player_id})
    return {
        "status": "connected",
        "session_token": session_id,
        "bc_balance": acc.get("bc_balance", 0) if acc else 0
    }

@app.get("/v1/server/health")
async def health():
    """Server holatini tekshirish"""
    return {"status": "GLOBAL_FIRE_READY", "engine": "Dragon_V2_Async"}

# --- ⚙️ RUNNER (RENDER COMPATIBLE) ---
if __name__ == "__main__":
    # Render avtomatik beradigan portni olish
    port = int(os.environ.get("PORT", 10000))
    # Render Free tierda worker=1 bo'lishi barqarorlikni ta'minlaydi
    uvicorn.run(app, host="0.0.0.0", port=port)
