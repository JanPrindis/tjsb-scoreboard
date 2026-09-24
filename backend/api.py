import asyncio
import argparse
import json
import os
import sys
import time
import hmac
import uuid
import uvicorn
from contextlib import asynccontextmanager
from typing import Set, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core.connection import MockConnection, SerialConnection
from core.controller import ScoreboardController
from core.settings import Settings
from core.database import init_db, get_all_rosters, get_full_roster, create_roster, update_roster, delete_roster

class PlayerModel(BaseModel):
    number: int = Field(default=0, ge=0, le=99)
    first_name: str | None = ""
    last_name: str | None = ""
    is_active: bool = True

class RosterProfileModel(BaseModel):
    name: str
    home: list[PlayerModel] = []
    away: list[PlayerModel] = []

class PlayerActionPayload(BaseModel):
    action: str  # "goal", "yellow", "red", "sub"
    team: str | None = None  # "home" nebo "away"
    player_id: int | None = None  # None = Unknown / Fast mode
    player_name: str | None = None
    player_number: int | None = None
    # Extra data required for substitution
    player_out_name: str | None = None
    player_out_number: int | None = None

# ==========================================
# CONFIGURATION
# ==========================================
settings = Settings()

# ==========================================
# GLOBAL STATE
# ==========================================
USE_MOCK: bool = True
SERIAL_PORT: str = "/dev/ttyUSB0"

controller: ScoreboardController | None = None
command_queue: asyncio.Queue = asyncio.Queue()
active_websockets: List[WebSocket] = []
active_tokens: Set[str] = set()
background_tasks: List[asyncio.Task] = []
is_animating: bool = False
is_syncing_roster: bool = False
sync_progress: int = 0

# ==========================================
# AUTH
# ==========================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

FAILED_LOGIN_ATTEMPTS = {}
MAX_LOGIN_ATTEMPTS = 10
LOCKOUT_TIME_SECONDS = 300

def get_real_ip(conn: Request | WebSocket) -> str:
    return conn.headers.get("CF-Connecting-IP") or \
           conn.headers.get("X-Forwarded-For") or \
           (conn.client.host if conn.client else "unknown")


def verify_token(token: str = Depends(oauth2_scheme)) -> str:
    if token not in active_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized, please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


class LoginPayload(BaseModel):
    password: str = Field(..., description="Password from .env file")


# ==========================================
# 4. HARDWARE WORKER & QUEUE
# ==========================================
async def hw_worker():
    while True:
        func, args, future = await command_queue.get()
        try:
            result = await asyncio.to_thread(func, *args)

            print(f"{result}")
            await broadcast_log(result)

            future.set_result(result)
        except Exception as e:
            error_msg = f"[ERROR] HW Worker failed: {e}"
            print(error_msg)
            await broadcast_log(error_msg)
            future.set_exception(e)
            
            await asyncio.sleep(1.0)
        finally:
            command_queue.task_done()
            await broadcast_state()


async def send_to_hw(func, *args):
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    await command_queue.put((func, args, future))
    return await future


# ==========================================
# WEBSOCKET, LOGGING & TIMER
# ==========================================
async def broadcast_state():
    if not controller or not active_websockets:
        return

    state = {
        "type": "state",
        "score_home": controller.score_home,
        "score_away": controller.score_away,
        "minutes": controller.minutes,
        "seconds": controller.seconds,
        "period": controller.period,
        "is_running": controller.is_time_running,
        "team_home": controller.team_home,
        "team_away": controller.team_away,
        "halftime_length": controller.halftime_length,
        "mode": controller.mode,
        "brightness": controller.brightness,
        "active_roster_id": controller.active_roster_id,
        "is_syncing": is_syncing_roster,
        "sync_progress": sync_progress
    }

    for ws in active_websockets:
        try:
            await ws.send_json(state)
        except Exception:
            pass


async def broadcast_log(message: str):
    if not active_websockets or not message:
        return

    for ws in active_websockets:
        try:
            await ws.send_json({"type": "log", "message": message})
        except Exception:
            pass


async def broadcast_roster_update():
    if not active_websockets:
        return

    for ws in active_websockets:
        try:
            await ws.send_json({"type": "roster_update"})
        except Exception:
            pass

auto_stop_in_flight = False

async def tick_timer_loop():
    global auto_stop_in_flight
    while True:
        if controller and controller.is_time_running and not auto_stop_in_flight:
            auto_stop = controller.tick_local_time()
            if auto_stop:
                auto_stop_in_flight = True
                asyncio.create_task(handle_auto_stop(auto_stop))
            await broadcast_state()
        await asyncio.sleep(0.1)

async def handle_auto_stop(auto_stop: dict):
    global auto_stop_in_flight
    try:
        msgs = []
        msgs.append(f"*** AUTO-STOP: end of period {auto_stop['period']} ***")
        msgs.append(await send_to_hw(controller.stop_time))
        msgs.append(await send_to_hw(controller.set_time, auto_stop["target_minutes"], 0))

        if auto_stop["advance_to_period"]:
            msgs.append(f"*** AUTO-ADVANCE: switching to {auto_stop['advance_to_period']}. period ***")
            msgs.append(await send_to_hw(controller.set_period, auto_stop["advance_to_period"]))

        full_msg = "\n".join(msgs)
        print(f"\n{full_msg}\n")
        await broadcast_log(full_msg)
    except Exception as e:
        print(f"[AUTO-STOP ERROR] {e}")
    finally:
        auto_stop_in_flight = False

# ==========================================
# APPLICATION LIFECYCLE
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global controller
    print("Starting Scoreboard API...")

    init_db()
    print("Database initialized.")

    if USE_MOCK:
        print("MODE: MOCK")
        conn = MockConnection()
    else:
        print(f"MODE: SERIAL ({SERIAL_PORT})")
        try:
            conn = SerialConnection(port=SERIAL_PORT)
        except Exception as e:
            print(f"ERROR: Unable to open port {SERIAL_PORT}: {e}")
            exit(-1)

    controller = ScoreboardController(conn, settings)

    background_tasks.append(asyncio.create_task(hw_worker()))
    background_tasks.append(asyncio.create_task(tick_timer_loop()))

    # Timeout before starting
    await asyncio.sleep(2.0)

    # Sync settings with the scoreboard
    await send_to_hw(controller.set_mode, controller.mode)
    await send_to_hw(controller.set_brightness, controller.brightness)

    yield

    print("Shutting down...")
    for task in background_tasks:
        task.cancel()
    if controller:
        controller.save_state()
        controller.close()


app = FastAPI(
    title="Football Scoreboard API",
    description="Interface for communicating with a football scoreboard",
    version="1.0.0",
    lifespan=lifespan
)

# ==========================================
# GLOBAL EXCEPTION HANDLER
# ==========================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[API ERROR] {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Check server logs."},
    )

# ==========================================
# REST ENDPOINTS
# ==========================================

@app.post("/api/login", tags=["System"], summary="Get access token")
async def login(payload: LoginPayload, request: Request):
    client_ip = get_real_ip(request)
    print(f"[AUTH] Login attempt from IP: {client_ip}")

    now = time.time()

    # Memory attack
    if len(FAILED_LOGIN_ATTEMPTS) > 1000:
        for ip in list(FAILED_LOGIN_ATTEMPTS.keys()):
            FAILED_LOGIN_ATTEMPTS[ip] = [t for t in FAILED_LOGIN_ATTEMPTS[ip] if now - t < LOCKOUT_TIME_SECONDS]
            if not FAILED_LOGIN_ATTEMPTS[ip]:
                del FAILED_LOGIN_ATTEMPTS[ip]

    # Bruteforce protection
    if client_ip in FAILED_LOGIN_ATTEMPTS:
        FAILED_LOGIN_ATTEMPTS[client_ip] = [t for t in FAILED_LOGIN_ATTEMPTS[client_ip] if now - t < LOCKOUT_TIME_SECONDS]
        if len(FAILED_LOGIN_ATTEMPTS[client_ip]) >= MAX_LOGIN_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Příliš mnoho pokusů. Zkuste to za 5 minut.")

    # Time-based attacks
    is_password_correct = hmac.compare_digest(
        payload.password.encode('utf-8'), 
        settings.app_password.encode('utf-8')
    )

    if is_password_correct:
        if client_ip in FAILED_LOGIN_ATTEMPTS:
            del FAILED_LOGIN_ATTEMPTS[client_ip]
            
        new_token = str(uuid.uuid4())
        active_tokens.add(new_token)
        return {"access_token": new_token, "token_type": "bearer"}
        
    FAILED_LOGIN_ATTEMPTS.setdefault(client_ip, []).append(now)
    raise HTTPException(status_code=400, detail="Nesprávné heslo!")


@app.get("/api/state", tags=["System"], summary="Get current scoreboard state")
async def get_state(token: str = Depends(verify_token)):
    """
    Returns the complete current backend state.
    Ideal for initial app load or manual synchronization (desync check).
    Does not need to wait for hardware, returns immediate state from memory
    """
    if not controller:
        raise HTTPException(status_code=503, detail="Controller not ready yet!")

    return {
        "score_home": controller.score_home,
        "score_away": controller.score_away,
        "minutes": controller.minutes,
        "seconds": controller.seconds,
        "period": controller.period,
        "is_running": controller.is_time_running,
        "team_home": controller.team_home,
        "team_away": controller.team_away,
        "halftime_length": controller.halftime_length,
        "mode": controller.mode,
        "brightness": controller.brightness
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """Websocket for reading live data (requires a valid token)."""
    await websocket.accept()

    client_ip = get_real_ip(websocket)

    if not token or token not in active_tokens:
        print(f"[WS] Connection failed from IP: {client_ip} (missing or expired)")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    print(f"[WS] Connected successfully from IP: {client_ip}")
    active_websockets.append(websocket)
    await broadcast_state()
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except (json.JSONDecodeError, TypeError):
                pass
    except (WebSocketDisconnect, Exception) as e:
        print(f"[WS] Disconnected: {e}")
        if websocket in active_websockets:
            active_websockets.remove(websocket)


# --- SCORE ---
@app.post("/api/score/home", tags=["Score"], summary="Add goal (Home)")
async def add_home_goal(token: str = Depends(verify_token)):
    log = await send_to_hw(controller.goal_home)
    return {"status": "ok", "log": log}


@app.post("/api/score/away", tags=["Score"], summary="Add goal (Away)")
async def add_away_goal(token: str = Depends(verify_token)):
    log = await send_to_hw(controller.goal_away)
    return {"status": "ok", "log": log}


class ScorePayload(BaseModel):
    home: int = Field(..., ge=0, le=99)
    away: int = Field(..., ge=0, le=99)


@app.post("/api/score/set", tags=["Score"], summary="Set exact score")
async def set_score(payload: ScorePayload, token: str = Depends(verify_token)):
    log = await send_to_hw(controller.set_score, payload.home, payload.away)
    return {"status": "ok", "log": log}


@app.post("/api/score/reset", tags=["Score"], summary="Reset score (0:0)")
async def reset_score(token: str = Depends(verify_token)):
    log = await send_to_hw(controller.reset_score)
    return {"status": "ok", "log": log}


# --- ČAS ---
@app.post("/api/time/start", tags=["Time"], summary="Start timer")
async def start_time(token: str = Depends(verify_token)):
    log = await send_to_hw(controller.start_time)
    return {"status": "ok", "log": log}


@app.post("/api/time/stop", tags=["Time"], summary="Stop timer")
async def stop_time(token: str = Depends(verify_token)):
    log = await send_to_hw(controller.stop_time)
    return {"status": "ok", "log": log}


@app.post("/api/time/reset", tags=["Time"], summary="Reset time to period start")
async def reset_time(token: str = Depends(verify_token)):
    log = await send_to_hw(controller.reset_time)
    return {"status": "ok", "log": log}


class TimePayload(BaseModel):
    minutes: int = Field(..., ge=0, le=99)
    seconds: int = Field(..., ge=0, le=59)


@app.post("/api/time/set", tags=["Time"], summary="Set manual time")
async def set_time(payload: TimePayload, token: str = Depends(verify_token)):
    log = await send_to_hw(controller.set_time, payload.minutes, payload.seconds)
    return {"status": "ok", "log": log}


# --- SETTINGS & ANIMATION ---
class TeamPayload(BaseModel):
    is_away: bool
    name: str = Field(..., max_length=30)


@app.post("/api/teams/set", tags=["Settings"], summary="Rename team")
async def set_team_name(payload: TeamPayload, token: str = Depends(verify_token)):
    log = await send_to_hw(controller.set_team_name, payload.is_away, payload.name)
    return {"status": "ok", "log": log}


@app.post("/api/settings/period/{period_id}", tags=["Settings"], summary="Change period (half)")
async def set_period(period_id: int, token: str = Depends(verify_token)):
    log = await send_to_hw(controller.set_period, period_id)
    return {"status": "ok", "log": log}


@app.post("/api/settings/halftime/{minutes}", tags=["Settings"], summary="Change halftime length (in minutes)")
async def set_halftime(minutes: int, token: str = Depends(verify_token)):
    log = await send_to_hw(controller.set_halftime_length, minutes)
    return {"status": "ok", "log": log}


@app.post("/api/settings/mode/{mode_id}", tags=["Settings"], summary="Change board mode")
async def set_mode(mode_id: int, token: str = Depends(verify_token)):
    log = await send_to_hw(controller.set_mode, mode_id)
    return {"status": "ok", "log": log}


@app.post("/api/settings/brightness/{level}", tags=["Settings"], summary="Change board brightness (0-15, 255=Auto)")
async def set_brightness(level: int, token: str = Depends(verify_token)):
    log = await send_to_hw(controller.set_brightness, level)
    return {"status": "ok", "log": log}


async def bg_play_animation(anim_func):
    global is_animating
    is_animating = True
    try:
        await send_to_hw(anim_func)
    except Exception as e:
        print(f"[BG ANIMATION ERROR] {e}")
    finally:
        is_animating = False

@app.post("/api/anim/{anim_type}", tags=["Animations"], summary="Play animation")
async def play_animation(anim_type: str, bg_tasks: BackgroundTasks, token: str = Depends(verify_token)):
    """Available: goal, yellow, red, sub, ball, test"""
    global is_animating
    if is_animating:
        raise HTTPException(status_code=429, detail="Panel právě přehrává jinou animaci. Počkejte.")

    anims = {
        "goal": controller.play_goal_animation,
        "yellow": controller.play_yellow_card_animation,
        "red": controller.play_red_card_animation,
        "sub": controller.play_substitution_animation,
        "ball": controller.play_ball_animation,
        "test": controller.play_test_animation
    }
    if anim_type not in anims:
        raise HTTPException(status_code=400, detail="Unknown animation")

    bg_tasks.add_task(bg_play_animation, anims[anim_type])
    return {"status": "ok"}

async def bg_show_roster(team_id: int):
    global is_animating
    is_animating = True
    try:
        await send_to_hw(controller.show_roster, team_id)
    except Exception as e:
        print(f"[BG ROSTER ERROR] {e}")
    finally:
        is_animating = False

@app.post("/api/anim/roster/{team}", tags=["Animations"], summary="Show team roster on board")
async def show_team_roster(team: str, bg_tasks: BackgroundTasks, token: str = Depends(verify_token)):
    global is_animating
    if is_animating:
        raise HTTPException(status_code=429, detail="Panel právě přehrává jinou animaci. Počkejte.")

    if team not in ["home", "away"]:
        raise HTTPException(status_code=400, detail="Invalid team")
    
    team_id = 0 if team == "home" else 1
    bg_tasks.add_task(bg_show_roster, team_id)
    return {"status": "ok"}

# ==========================================
# ROSTER ENDPOINTS
# ==========================================


async def perform_roster_sync():
    global is_syncing_roster, sync_progress, is_animating
    if not controller:
        return
    if is_syncing_roster:
        return

    wait_start = time.time()
    while is_animating:
        if time.time() - wait_start > 15.0:
            print("[SYNC] Timeout for is_animating is too long, continuing anyways.")
            break
        await asyncio.sleep(0.1)

    is_syncing_roster = True
    is_animating = True
    sync_progress = 0
    await broadcast_state()

    try:
        if not controller.active_roster_id:
            await broadcast_log("Mažu soupisky...")
            await send_to_hw(controller.clear_roster, 0)
            sync_progress = 50
            await broadcast_state()
            await send_to_hw(controller.clear_roster, 1)
            sync_progress = 100
            await broadcast_state()
            await broadcast_log("Soupisky vymazány.")
            return

        roster = get_full_roster(controller.active_roster_id)
        if not roster:
            return

        await broadcast_log("Zahajuji synchronizaci soupisky... to může chvíli trvat.")

        home_active = [p for p in roster["home"] if p.get("is_active", True)]
        away_active = [p for p in roster["away"] if p.get("is_active", True)]

        total_ops = 2 + len(home_active) + len(away_active)
        current_op = 0

        async def _update_progress():
            nonlocal current_op
            global sync_progress
            current_op += 1
            sync_progress = int((current_op / total_ops) * 100)
            await broadcast_state()

        await send_to_hw(controller.clear_roster, 0)
        await _update_progress()
        for p in home_active:
            await send_to_hw(controller.add_player, 0, p)
            await _update_progress()

        await send_to_hw(controller.clear_roster, 1)
        await _update_progress()
        for p in away_active:
            await send_to_hw(controller.add_player, 1, p)
            await _update_progress()

        await broadcast_log("Synchronizace soupisky dokončena.")
    except Exception as e:
        print(f"[SYNC ERROR] {e}")
        await broadcast_log(f"Chyba při synchronizaci.")
    finally:
        is_syncing_roster = False
        is_animating = False
        sync_progress = 0
        await broadcast_state()

@app.get("/api/rosters", tags=["Roster"])
async def api_get_rosters(token: str = Depends(verify_token)):
    return get_all_rosters()


@app.post("/api/rosters", tags=["Roster"])
async def api_create_roster(payload: RosterProfileModel, token: str = Depends(verify_token)):
    new_id = create_roster(payload.name)
    update_roster(new_id, payload.name, [p.model_dump() for p in payload.home], [p.model_dump() for p in payload.away])
    await broadcast_roster_update()
    return {"id": new_id, "status": "ok"}


@app.put("/api/rosters/{roster_id}", tags=["Roster"])
async def api_update_roster(roster_id: int, payload: RosterProfileModel, bg_tasks: BackgroundTasks, token: str = Depends(verify_token)):
    update_roster(roster_id, payload.name, [p.model_dump() for p in payload.home],
                  [p.model_dump() for p in payload.away])
    if controller and controller.active_roster_id == roster_id:
        bg_tasks.add_task(perform_roster_sync)
    await broadcast_roster_update()
    return {"status": "ok"}


@app.delete("/api/rosters/{roster_id}", tags=["Roster"])
async def api_delete_roster(roster_id: int, bg_tasks: BackgroundTasks, token: str = Depends(verify_token)):
    delete_roster(roster_id)
    if controller.active_roster_id == roster_id:
        controller.set_active_roster(None)
        await broadcast_state()
        bg_tasks.add_task(perform_roster_sync)
    await broadcast_roster_update()
    return {"status": "ok"}


@app.get("/api/rosters/active", tags=["Roster"])
async def api_get_active_rosters(token: str = Depends(verify_token)):
    if not controller.active_roster_id:
        return {"home": [], "away": []}

    roster = get_full_roster(controller.active_roster_id)
    return {
        "home": [p for p in roster["home"] if p["is_active"]],
        "away": [p for p in roster["away"] if p["is_active"]]
    }


@app.post("/api/rosters/sync", tags=["Roster"])
async def api_sync_rosters(bg_tasks: BackgroundTasks, token: str = Depends(verify_token)):
    bg_tasks.add_task(perform_roster_sync)
    return {"status": "ok"}


class ActiveRosterPayload(BaseModel):
    roster_id: int | None = None


@app.post("/api/settings/active_roster", tags=["Settings"])
async def api_set_active_roster(payload: ActiveRosterPayload, bg_tasks: BackgroundTasks, token: str = Depends(verify_token)):
    log = controller.set_active_roster(payload.roster_id)
    await broadcast_state()
    bg_tasks.add_task(perform_roster_sync)
    return {"status": "ok", "log": log}


async def process_action_sequence(payload: PlayerActionPayload, team_text: str):
    global is_animating
    action_texts = {
        "goal": "GÓL",
        "yellow": "ŽLUTÁ KARTA",
        "red": "ČERVENÁ KARTA"
    }

    try:
        # --- SUBSTITUTION ---
        if payload.action == "sub" and (payload.player_name or payload.player_out_name):
            # Sub animation
            await send_to_hw(controller.play_substitution_animation)
            await asyncio.sleep(4.0)
            
            # Player out
            if payload.player_out_name:
                p_out_num = payload.player_out_number or 0
                display_text_out = f"STŘÍDÁNÍ - ODCHÁZÍ\n{team_text} - {p_out_num}\n{payload.player_out_name}"
                await send_to_hw(controller.send_custom_text, display_text_out, 2, 3, 2, 0)
                
                # Text animation length calculation, because HW sucks. 3 seconds base + .2 per char
                # Needs more testing
                delay_out = 3.0 + (len(display_text_out) * 0.2)
                print(f"[ANIM LOCK] Text ({len(display_text_out)} chars) -> Waiting {delay_out:.1f}s")
                await asyncio.sleep(delay_out)
                    
            # Player in
            if payload.player_name:
                p_in_num = payload.player_number or 0
                display_text_in = f"STŘÍDÁNÍ - PŘICHÁZÍ\n{team_text} - {p_in_num}\n{payload.player_name}"
                await send_to_hw(controller.send_custom_text, display_text_in, 2, 3, 2, 0)
                
                delay_in = 3.0 + (len(display_text_in) * 0.2)
                print(f"[ANIM LOCK] Text ({len(display_text_in)} chars long) -> Waiting {delay_in:.1f}s")
                await asyncio.sleep(delay_in)

        # --- Goal/Cards ---
        elif payload.player_name and payload.action in action_texts:
            
            # Play animation
            if payload.action == "goal":
                await send_to_hw(controller.play_goal_animation)
            elif payload.action == "yellow":
                await send_to_hw(controller.play_yellow_card_animation)
            elif payload.action == "red":
                await send_to_hw(controller.play_red_card_animation)

            await asyncio.sleep(0.1)

            # Text info
            p_num = payload.player_number or 0
            action_title = action_texts[payload.action]
            display_text = f"{action_title}\n{team_text} - {p_num}\n{payload.player_name}"
            await send_to_hw(controller.send_custom_text, display_text, 2, 3, 2, 0)

            delay_action = 3.0 + (len(display_text) * 0.2)
            if delay_action < 10.0:
                delay_action = 10.0
            print(f"[ANIM LOCK] Text ({len(display_text)} chars long) -> Waiting {delay_action:.1f}s")
            await asyncio.sleep(delay_action)

        else:
            # FALLBACK
            if payload.action == "goal":
                await send_to_hw(controller.play_goal_animation)
            elif payload.action == "yellow":
                await send_to_hw(controller.play_yellow_card_animation)
            elif payload.action == "red":
                await send_to_hw(controller.play_red_card_animation)
            elif payload.action == "sub":
                await send_to_hw(controller.play_substitution_animation)
    except Exception as e:
        print(f"[ACTION SEQUENCE ERROR] {e}")
    finally:
        is_animating = False


@app.post("/api/action/goal_player", tags=["Action"], summary="Execute action with specific player")
async def action_with_player(payload: PlayerActionPayload, bg_tasks: BackgroundTasks, token: str = Depends(verify_token)):
    global is_animating
    if is_animating:
        raise HTTPException(status_code=429, detail="Panel právě přehrává jinou animaci. Počkejte.")

    team_text = "Domácí hráč" if payload.team == "home" else "Hráč hostů"
    
    is_animating = True
    bg_tasks.add_task(process_action_sequence, payload, team_text)
    return {"status": "ok"}

# ==========================================
# FRONTEND (STATIC FILES & SPA FALLBACK)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(BASE_DIR, "..", "frontend", "dist")

if os.path.isdir(FRONTEND_DIST):
    # Serve static assets
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")


    # Catch-all route to serve SPA frontend
    @app.get("/{catchall:path}", tags=["Frontend"], summary="Serve SPA Frontend")
    async def serve_frontend(catchall: str):
        # Path traversal check
        safe_dist_path = os.path.abspath(FRONTEND_DIST)
        file_path = os.path.abspath(os.path.join(safe_dist_path, catchall.lstrip('/')))

        if os.path.commonpath([safe_dist_path, file_path]) != safe_dist_path:
            raise HTTPException(status_code=403, detail="Nice try!")

        # If file exists, serve it
        if catchall and os.path.isfile(file_path):
            return FileResponse(file_path)

        # Else fallback to index.html
        index_path = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)

        return {"detail": "Frontend is built, but index.html is missing"}

# ==========================================
# RUN APPLICATION
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Football Scoreboard API")
    parser.add_argument("--mock", action="store_true", help="Run API in MOCK mode")
    parser.add_argument("--port", type=str, default="/dev/ttyUSB0", help="Serial port")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host IP (127.0.0.1 for CF Tunnel safety)")
    parser.add_argument("--api-port", type=int, default=8000, help="API port")
    args, unknown = parser.parse_known_args()

    USE_MOCK = args.mock
    SERIAL_PORT = args.port

    sys.argv = [sys.argv[0]]
    uvicorn.run(app, host=args.host, port=args.api_port, ws_ping_timeout=None, ws_ping_interval=None)
