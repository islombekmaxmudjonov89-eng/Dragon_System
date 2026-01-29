import time
import uuid
import hashlib
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from pymongo import MongoClient # <--- REAL BAZA KUTUBXONASI

app = FastAPI(title="Dragon Game Server Global")

# --- 🛰️ REAL DATABASE CONNECTION (DATABASE INTEGRATION) ---
# Diqqat: Bu yerga MongoDB Atlas'dan olgan ulanish kodingni qo'yasan
# Hozircha lokal bazaga ulangan, lekin Cloud URL qo'yilishi bilan REAL bo'ladi.
MONGO_CONNECTION_STRING = "mongodb+srv://Dragon_admin:<db_password>@islombek.zpglyqc.mongodb.net/?appName=islombek" 
client = MongoClient(MONGO_CONNECTION_STRING)
db = client['dragon_game_db']
accounts_db = db['players_vault'] # Kotta acc'lar ombori
sessions_db = db['active_sessions'] # Onlayn o'yinchilar

# --- DRAGON VAULT: KOTTA ACC HIMOYASI (REALNIY) ---
class DragonVault:
    @staticmethod
    def verify_elite_access(player_id: str, current_hwid: str, behavior: dict):
        """Katta akkauntlarni BAZADAN qidirib tekshirish"""
        # Simulyatsiya emas, real qidiruv:
        acc = accounts_db.find_one({"player_id": player_id})
        
        if acc:
            # 1. Hardware Binding (Qurilmaga mixlash)
            if acc.get("registered_hwid") != current_hwid:
                return "ACCESS_DENIED_WRONG_DEVICE", False
            
            # 2. Behavioral Biometrics
            play_style = acc.get("play_style", {})
            if abs(play_style.get("avg_sensitivity", 0) - behavior.get("sensitivity", 0)) > 1.0:
                return "SUSPICIOUS_BEHAVIOR_LOCKED", False
                
        return "CLEAN", True

# --- DRAGON JUDGEMENT: ANTI-CHEAT ---
class DragonAntiCheat:
    @staticmethod
    def validate_packet(player_id: str, current_data: dict, last_data: Optional[dict]):
        if not last_data:
            return "CLEAN", 0

        time_diff = time.time() - last_data['timestamp']
        dist = ((current_data['x'] - last_data['x'])**2 + (current_data['y'] - last_data['y'])**2)**0.5
        velocity = dist / time_diff if time_diff > 0 else 0

        if velocity > 45.0: 
            return "ULTIMATE_HWID_BAN", 100
        
        if current_data.get('recoil') == 0 and current_data.get('is_shooting'):
            return "CRITICAL_CHEAT_BAN", 90

        return "CLEAN", 0

# --- BC SERVICE DAN KELADIGAN BUYRUQ (REALNIY BAZAGA YOZISH) ---
@app.post("/v1/internal/add-bc")
async def add_bc_to_account(player_id: str, amount: int, secret_key: str):
    """BC tushganda srazu bazaga muhrlaydi"""
    if secret_key != "DRAGON_SECRET_99": 
        raise HTTPException(status_code=403, detail="Taqiqlangan kirish!")

    # BAZADA YANGILASH (Upsert: Yo'q bo'lsa ochadi, bor bo'lsa qo'shadi)
    accounts_db.update_one(
        {"player_id": player_id},
        {
            "$inc": {"bc_balance": amount}, # Balansni qo'shish
            "$setOnInsert": {
                "registered_hwid": "HWID_PENDING",
                "play_style": {"avg_sensitivity": 0, "tap_speed": 0},
                "status": "ACTIVE",
                "created_at": time.time()
            }
        },
        upsert=True
    )
    
    updated_acc = accounts_db.find_one({"player_id": player_id})
    return {"status": "success", "new_balance": updated_acc["bc_balance"]}

# --- SERVER ENDPOINTLARI ---

@app.post("/v1/game/connect")
async def connect_player(player_id: str, hwid: str, behavior: dict):
    # Vault tekshiruvi bazadan olinadi
    vault_status, is_allowed = DragonVault.verify_elite_access(player_id, hwid, behavior)
    if not is_allowed:
        return {"status": "LOCKED", "reason": vault_status}

    session_id = str(uuid.uuid4())
    # Sessiyani ham vaqtinchalik bazaga yozamiz
    sessions_db.update_one(
        {"player_id": player_id},
        {"$set": {
            "session_id": session_id, "hwid": hwid,
            "x": 0, "y": 0, "timestamp": time.time()
        }},
        upsert=True
    )
    
    acc = accounts_db.find_one({"player_id": player_id})
    return {
        "status": "connected",
        "session_token": session_id,
        "vault_protection": "MAXIMUM" if acc and acc.get("bc_balance", 0) > 50000 else "STANDARD"
    }

@app.post("/v1/game/sync")
async def game_sync(player_id: str, packet: dict):
    # Sessiyani bazadan tekshirish
    last_session = sessions_db.find_one({"player_id": player_id})
    if not last_session:
        raise HTTPException(status_code=403, detail="Unauthorized")

    verdict, score = DragonAntiCheat.validate_packet(player_id, packet, last_session)
    if verdict != "CLEAN":
        sessions_db.delete_one({"player_id": player_id})
        return {"action": "TERMINATE_AND_BAN", "reason": verdict}

    # Bazadagi koordinatalarni yangilash
    sessions_db.update_one(
        {"player_id": player_id},
        {"$set": {"x": packet['x'], "y": packet['y'], "timestamp": time.time()}}
    )

    # O'yinchining REAL balansini bazadan olib yuborish
    acc = accounts_db.find_one({"player_id": player_id})
    return {
        "status": "SYNCED",
        "bc_balance": acc.get("bc_balance", 0) if acc else 0
    }

@app.get("/v1/server/health")
async def health():
    return {
        "total_active": sessions_db.count_documents({}),
        "vault_secured_accounts": accounts_db.count_documents({}),
        "dragon_status": "FIRE_READY"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)