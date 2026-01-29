import time
import uuid
import os
from fastapi import FastAPI, Request, HTTPException
from typing import Optional, Dict
from motor.motor_asyncio import AsyncIOMotorClient # 2mlrd+ uchun asinxron ulanish shart
import uvicorn
from functools import lru_cache

app = FastAPI(title="Dragon Global: 2B+ Edition")

# --- 🛰️ HIGH-SCALE DATABASE (MONGODB ASYNC) ---
MONGO_URL = "mongodb+srv://Dragon_admin:<db_password>@islombek.zpglyqc.mongodb.net/?appName=islombek"
client = AsyncIOMotorClient(MONGO_URL, maxPoolSize=100) # Bir vaqtda 100ta ulanish
db = client['dragon_game_db']
accounts_db = db['players_vault']
sessions_db = db['active_sessions']

# --- UC/BC SERVICE INTEGRATION (SO'ROV QABUL QILISH) ---
class UCRequest(BaseModel if 'BaseModel' in globals() else object):
    player_id: str
    amount: int
    secret_key: str

@app.post("/v1/internal/add-bc")
async def add_bc_to_account(request: Request):
    """UC Service dan kelgan so'rovni qabul qilish"""
    data = await request.json()
    player_id = data.get("player_id")
    amount = data.get("amount")
    secret_key = data.get("secret_key")

    if secret_key != "DRAGON_SECRET_99": 
        raise HTTPException(status_code=403, detail="Forbidden")

    # Bazada BC balansi yangilash
    await accounts_db.update_one(
        {"player_id": player_id},
        {"$inc": {"bc_balance": amount},
         "$setOnInsert": {"registered_hwid": "PENDING", "created_at": time.time()}},
        upsert=True
    )
    return {"status": "success", "msg": f"{amount} BC added to {player_id}"}

# --- OPTIMIZATSIYA: 2MLRD+ UCHUN CACHE ---
@lru_cache(maxsize=10000) # Eng faol 10k o'yinchini xotirada saqlaydi
def get_cached_status(player_id: str):
    return "ACTIVE"

# --- DRAGON LOGS ---
@app.post("/log")
async def receive_game_logs(request: Request):
    data = await request.json()
    # 2mlrd odamda 'print' ishlatib bo'lmaydi, lekin hozircha ko'rishing uchun qoldirdim
    print(f"🐉 Log: {data.get('player_id')} is active")
    return {"status": "ok"}

# --- CONNECT & SYNC (HIGH-SPEED) ---
@app.post("/v1/game/connect")
async def connect_player(player_id: str, hwid: str):
    session_id = str(uuid.uuid4())
    # Asinxron yozish - serverni to'xtatib qo'ymaydi
    await sessions_db.update_one(
        {"player_id": player_id},
        {"$set": {"session_id": session_id, "hwid": hwid, "timestamp": time.time()}},
        upsert=True
    )
    return {"status": "connected", "token": session_id}

@app.get("/v1/server/health")
async def health():
    # 2mlrd odam uchun bazani sanash qimmatga tushadi, shuning uchun taxminiy statistik
    return {"status": "GLOBAL_FIRE_READY", "engine": "Dragon_V2_Async"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port, workers=4) # 4ta parallel ishchi (worker)
