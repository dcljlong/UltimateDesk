from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends, Response
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from bson import ObjectId
import json
import math

# Emergent integrations
from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse

ROOT_DIR = Path(__file__).parent

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_ALGORITHM = "HS256"

def get_jwt_secret() -> str:
    return os.environ.get("JWT_SECRET", "default-secret-change-me")

# Create the main app
app = FastAPI(title="UltimateDesk CNC Pro API")

# Create routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
designs_router = APIRouter(prefix="/designs", tags=["Designs"])
chat_router = APIRouter(prefix="/chat", tags=["AI Chat"])
cnc_router = APIRouter(prefix="/cnc", tags=["CNC Generator"])
payments_router = APIRouter(prefix="/payments", tags=["Payments"])

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============== MODELS ==============

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_pro: bool = False
    created_at: datetime

class DesignParams(BaseModel):
    width: int = 1800
    depth: int = 800
    height: int = 750
    desk_type: str = "gaming"
    monitor_count: int = 1
    has_rgb_channels: bool = False
    has_cable_management: bool = True
    has_headset_hook: bool = False
    has_gpu_tray: bool = False
    has_mixer_tray: bool = False
    mixer_tray_width: int = 610
    has_pedal_tilt: bool = False
    has_vesa_mount: bool = False
    leg_style: str = "standard"
    joint_type: str = "finger"
    material_thickness: int = 18
    custom_features: List[str] = []

class DesignCreate(BaseModel):
    name: str
    params: DesignParams

class DesignResponse(BaseModel):
    id: str
    name: str
    user_id: str
    params: DesignParams
    created_at: datetime
    updated_at: datetime
    thumbnail_url: Optional[str] = None

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatRequest(BaseModel):
    message: str
    current_params: Optional[DesignParams] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    updated_params: DesignParams
    session_id: str
    extracted_changes: List[str] = []

class CNCConfig(BaseModel):
    bit_size: int = 6
    cut_depth_per_pass: int = 6
    sheet_width: int = 2400
    sheet_height: int = 1200
    material_thickness: int = 18

class NestingResult(BaseModel):
    sheets_required: int
    waste_percentage: float
    parts: List[Dict[str, Any]]
    total_area: float
    used_area: float

class CNCOutput(BaseModel):
    nesting: NestingResult
    estimated_cut_time_minutes: float
    material_cost_nzd: float
    gcode_preview: str

class SubscriptionTier(BaseModel):
    tier: str
    price: float = 4.99
    currency: str = "nzd"

# ============== PASSWORD HELPERS ==============

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# ============== JWT HELPERS ==============

def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "type": "access"
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh"
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["id"] = str(user["_id"])
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_optional_user(request: Request) -> Optional[dict]:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

# ============== AUTH ROUTES ==============

@auth_router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, response: Response):
    email = user_data.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_doc = {
        "email": email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "role": "user",
        "is_pro": False,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return UserResponse(
        id=user_id,
        email=email,
        name=user_data.name,
        role="user",
        is_pro=False,
        created_at=user_doc["created_at"]
    )

@auth_router.post("/login", response_model=UserResponse)
async def login(user_data: UserLogin, response: Response):
    email = user_data.email.lower()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return UserResponse(
        id=user_id,
        email=user["email"],
        name=user["name"],
        role=user.get("role", "user"),
        is_pro=user.get("is_pro", False),
        created_at=user["created_at"]
    )

@auth_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}

@auth_router.get("/me", response_model=UserResponse)
async def get_me(request: Request):
    user = await get_current_user(request)
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user.get("role", "user"),
        is_pro=user.get("is_pro", False),
        created_at=user["created_at"]
    )

@auth_router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        user_id = str(user["_id"])
        access_token = create_access_token(user_id, user["email"])
        response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
        return {"message": "Token refreshed"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============== DESIGNS ROUTES ==============

@designs_router.get("/presets")
async def get_presets():
    return [
        {
            "id": "gaming",
            "name": "Gaming Battlestation",
            "description": "49\" ultrawide ready, RGB channels, headset hook",
            "params": DesignParams(
                width=1800, depth=800, height=750,
                desk_type="gaming", monitor_count=3,
                has_rgb_channels=True, has_headset_hook=True,
                has_cable_management=True, leg_style="angular"
            ).model_dump()
        },
        {
            "id": "studio",
            "name": "Music Production",
            "description": "610mm mixer tray, pedal tilt, isolation dampening",
            "params": DesignParams(
                width=2000, depth=900, height=750,
                desk_type="studio", has_mixer_tray=True,
                mixer_tray_width=610, has_pedal_tilt=True,
                has_cable_management=True, leg_style="solid"
            ).model_dump()
        },
        {
            "id": "office",
            "name": "Professional Office",
            "description": "Clean cable management, VESA mount ready",
            "params": DesignParams(
                width=1600, depth=700, height=750,
                desk_type="office", monitor_count=2,
                has_vesa_mount=True, has_cable_management=True,
                leg_style="standard"
            ).model_dump()
        }
    ]

@designs_router.get("/", response_model=List[DesignResponse])
async def get_user_designs(request: Request):
    user = await get_current_user(request)
    designs = await db.designs.find({"user_id": user["id"]}, {"_id": 1, "name": 1, "user_id": 1, "params": 1, "created_at": 1, "updated_at": 1, "thumbnail_url": 1}).to_list(100)
    return [
        DesignResponse(
            id=str(d["_id"]),
            name=d["name"],
            user_id=d["user_id"],
            params=DesignParams(**d["params"]),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            thumbnail_url=d.get("thumbnail_url")
        ) for d in designs
    ]

@designs_router.post("/", response_model=DesignResponse)
async def create_design(design_data: DesignCreate, request: Request):
    user = await get_current_user(request)
    now = datetime.now(timezone.utc)
    design_doc = {
        "name": design_data.name,
        "user_id": user["id"],
        "params": design_data.params.model_dump(),
        "created_at": now,
        "updated_at": now
    }
    result = await db.designs.insert_one(design_doc)
    return DesignResponse(
        id=str(result.inserted_id),
        name=design_data.name,
        user_id=user["id"],
        params=design_data.params,
        created_at=now,
        updated_at=now
    )

@designs_router.get("/{design_id}", response_model=DesignResponse)
async def get_design(design_id: str, request: Request):
    user = await get_current_user(request)
    design = await db.designs.find_one({"_id": ObjectId(design_id), "user_id": user["id"]})
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    return DesignResponse(
        id=str(design["_id"]),
        name=design["name"],
        user_id=design["user_id"],
        params=DesignParams(**design["params"]),
        created_at=design["created_at"],
        updated_at=design["updated_at"],
        thumbnail_url=design.get("thumbnail_url")
    )

@designs_router.put("/{design_id}", response_model=DesignResponse)
async def update_design(design_id: str, design_data: DesignCreate, request: Request):
    user = await get_current_user(request)
    now = datetime.now(timezone.utc)
    result = await db.designs.find_one_and_update(
        {"_id": ObjectId(design_id), "user_id": user["id"]},
        {"$set": {"name": design_data.name, "params": design_data.params.model_dump(), "updated_at": now}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Design not found")
    return DesignResponse(
        id=str(result["_id"]),
        name=result["name"],
        user_id=result["user_id"],
        params=DesignParams(**result["params"]),
        created_at=result["created_at"],
        updated_at=result["updated_at"]
    )

@designs_router.delete("/{design_id}")
async def delete_design(design_id: str, request: Request):
    user = await get_current_user(request)
    result = await db.designs.delete_one({"_id": ObjectId(design_id), "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Design not found")
    return {"message": "Design deleted"}

# ============== AI CHAT ROUTES ==============

DESK_DESIGNER_SYSTEM_PROMPT = """You are an expert CNC desk designer AI for UltimateDesk CNC Pro. You help Kiwi DIY builders create custom gaming, studio, and office desks from 18mm NZ plywood.

When users describe their desk requirements, extract the parameters and provide helpful suggestions. Always respond in JSON format with two fields:
1. "message": Your friendly response explaining what changes you're making
2. "params": An object with ONLY the parameters that should be CHANGED based on the user's request

Available parameters you can modify:
- width (mm, typically 1200-2400)
- depth (mm, typically 600-1000)  
- height (mm, typically 700-800)
- desk_type: "gaming", "studio", "office"
- monitor_count (1-5)
- has_rgb_channels (true/false)
- has_cable_management (true/false)
- has_headset_hook (true/false)
- has_gpu_tray (true/false)
- has_mixer_tray (true/false)
- mixer_tray_width (mm, typically 610)
- has_pedal_tilt (true/false)
- has_vesa_mount (true/false)
- leg_style: "standard", "angular", "solid", "trestle"
- joint_type: "finger", "dovetail", "box"
- custom_features (array of strings)

Example user: "I want a gaming desk 1800mm wide with RGB and a headset hook"
Example response:
{
  "message": "Great choice! I'm setting up an 1800mm gaming desk with RGB channel routing and a headset hook. The RGB channels will be routed along the back edge for clean cable management.",
  "params": {
    "width": 1800,
    "desk_type": "gaming", 
    "has_rgb_channels": true,
    "has_headset_hook": true
  }
}

Only include parameters that the user explicitly or implicitly requested to change. Be helpful and suggest complementary features when appropriate."""

@chat_router.post("/design", response_model=ChatResponse)
async def chat_design(chat_req: ChatRequest, request: Request):
    session_id = chat_req.session_id or str(uuid.uuid4())
    current_params = chat_req.current_params or DesignParams()
    
    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="LLM API key not configured")
        
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=DESK_DESIGNER_SYSTEM_PROMPT
        ).with_model("gemini", "gemini-3-flash-preview")
        
        context = f"Current desk configuration: {current_params.model_dump_json()}\n\nUser request: {chat_req.message}"
        user_message = UserMessage(text=context)
        
        response_text = await chat.send_message(user_message)
        
        # Parse AI response
        try:
            # Try to extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            elif "{" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]
            else:
                json_str = response_text
            
            ai_response = json.loads(json_str)
            message = ai_response.get("message", response_text)
            param_updates = ai_response.get("params", {})
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            message = response_text
            param_updates = {}
        
        # Apply updates to current params
        updated_dict = current_params.model_dump()
        extracted_changes = []
        for key, value in param_updates.items():
            if key in updated_dict:
                updated_dict[key] = value
                extracted_changes.append(f"{key}: {value}")
        
        updated_params = DesignParams(**updated_dict)
        
        # Store chat message
        await db.chat_sessions.update_one(
            {"session_id": session_id},
            {
                "$push": {
                    "messages": {
                        "role": "user",
                        "content": chat_req.message,
                        "timestamp": datetime.now(timezone.utc)
                    }
                },
                "$set": {"updated_at": datetime.now(timezone.utc)}
            },
            upsert=True
        )
        await db.chat_sessions.update_one(
            {"session_id": session_id},
            {
                "$push": {
                    "messages": {
                        "role": "assistant",
                        "content": message,
                        "timestamp": datetime.now(timezone.utc)
                    }
                }
            }
        )
        
        return ChatResponse(
            response=message,
            updated_params=updated_params,
            session_id=session_id,
            extracted_changes=extracted_changes
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============== CNC GENERATOR ROUTES ==============

def calculate_desk_parts(params: DesignParams) -> List[Dict[str, Any]]:
    """Calculate all parts needed for the desk"""
    parts = []
    t = params.material_thickness
    
    # Main desktop
    parts.append({
        "name": "Desktop",
        "width": params.width,
        "height": params.depth,
        "quantity": 1,
        "type": "panel"
    })
    
    # Side panels (legs)
    leg_depth = params.depth - 50
    parts.append({
        "name": "Left Leg",
        "width": leg_depth,
        "height": params.height - t,
        "quantity": 1,
        "type": "panel"
    })
    parts.append({
        "name": "Right Leg",
        "width": leg_depth,
        "height": params.height - t,
        "quantity": 1,
        "type": "panel"
    })
    
    # Back panel
    parts.append({
        "name": "Back Panel",
        "width": params.width - (2 * t),
        "height": 200,
        "quantity": 1,
        "type": "panel"
    })
    
    # Stretcher
    parts.append({
        "name": "Front Stretcher",
        "width": params.width - (2 * t) - 100,
        "height": 100,
        "quantity": 1,
        "type": "panel"
    })
    
    # Optional features
    if params.has_cable_management:
        parts.append({
            "name": "Cable Tray",
            "width": params.width - 200,
            "height": 150,
            "quantity": 1,
            "type": "panel"
        })
    
    if params.has_headset_hook:
        parts.append({
            "name": "Headset Hook",
            "width": 80,
            "height": 120,
            "quantity": 1,
            "type": "cutout"
        })
    
    if params.has_gpu_tray:
        parts.append({
            "name": "GPU Support Tray",
            "width": 350,
            "height": 200,
            "quantity": 1,
            "type": "panel"
        })
    
    if params.has_mixer_tray:
        parts.append({
            "name": "Mixer Tray",
            "width": params.mixer_tray_width,
            "height": 400,
            "quantity": 1,
            "type": "panel"
        })
        parts.append({
            "name": "Mixer Tray Support L",
            "width": 100,
            "height": 400,
            "quantity": 1,
            "type": "panel"
        })
        parts.append({
            "name": "Mixer Tray Support R",
            "width": 100,
            "height": 400,
            "quantity": 1,
            "type": "panel"
        })
    
    if params.has_vesa_mount:
        parts.append({
            "name": "VESA Mount Plate",
            "width": 200,
            "height": 200,
            "quantity": 1,
            "type": "panel"
        })
    
    return parts

def simple_nesting(parts: List[Dict], sheet_width: int, sheet_height: int) -> NestingResult:
    """Simple bin packing algorithm for sheet nesting"""
    # Add margin for cuts
    margin = 10
    
    # Sort parts by area (largest first)
    sorted_parts = sorted(parts, key=lambda p: p["width"] * p["height"], reverse=True)
    
    sheets = []
    current_sheet = {"parts": [], "spaces": [(0, 0, sheet_width, sheet_height)]}
    
    total_part_area = 0
    
    for part in sorted_parts:
        for _ in range(part.get("quantity", 1)):
            pw, ph = part["width"] + margin, part["height"] + margin
            total_part_area += part["width"] * part["height"]
            
            placed = False
            for sheet in [current_sheet] + sheets:
                for i, (x, y, sw, sh) in enumerate(sheet["spaces"]):
                    # Try normal orientation
                    if pw <= sw and ph <= sh:
                        sheet["parts"].append({
                            "name": part["name"],
                            "x": x,
                            "y": y,
                            "width": part["width"],
                            "height": part["height"],
                            "rotated": False
                        })
                        # Split remaining space
                        sheet["spaces"].pop(i)
                        if sw - pw > 50:
                            sheet["spaces"].append((x + pw, y, sw - pw, ph))
                        if sh - ph > 50:
                            sheet["spaces"].append((x, y + ph, sw, sh - ph))
                        placed = True
                        break
                    # Try rotated
                    elif ph <= sw and pw <= sh:
                        sheet["parts"].append({
                            "name": part["name"],
                            "x": x,
                            "y": y,
                            "width": part["height"],
                            "height": part["width"],
                            "rotated": True
                        })
                        sheet["spaces"].pop(i)
                        if sw - ph > 50:
                            sheet["spaces"].append((x + ph, y, sw - ph, pw))
                        if sh - pw > 50:
                            sheet["spaces"].append((x, y + pw, sw, sh - pw))
                        placed = True
                        break
                if placed:
                    break
            
            if not placed:
                # Need new sheet
                if current_sheet["parts"]:
                    sheets.append(current_sheet)
                current_sheet = {"parts": [], "spaces": [(0, 0, sheet_width, sheet_height)]}
                # Place on new sheet
                current_sheet["parts"].append({
                    "name": part["name"],
                    "x": 0,
                    "y": 0,
                    "width": part["width"],
                    "height": part["height"],
                    "rotated": False
                })
                current_sheet["spaces"] = [(pw, 0, sheet_width - pw, ph), (0, ph, sheet_width, sheet_height - ph)]
    
    if current_sheet["parts"]:
        sheets.append(current_sheet)
    
    total_sheet_area = len(sheets) * sheet_width * sheet_height
    waste = ((total_sheet_area - total_part_area) / total_sheet_area) * 100
    
    all_parts = []
    for i, sheet in enumerate(sheets):
        for p in sheet["parts"]:
            p["sheet"] = i
            all_parts.append(p)
    
    return NestingResult(
        sheets_required=len(sheets),
        waste_percentage=round(waste, 1),
        parts=all_parts,
        total_area=total_sheet_area,
        used_area=total_part_area
    )

def generate_gcode_preview(parts: List[Dict], config: CNCConfig) -> str:
    """Generate a preview of G-code for the parts"""
    lines = [
        "; UltimateDesk CNC Pro - G-Code Preview",
        "; Material: 18mm NZ Plywood",
        f"; Bit Size: {config.bit_size}mm",
        f"; Cut Depth Per Pass: {config.cut_depth_per_pass}mm",
        "",
        "G21 ; Set units to millimeters",
        "G90 ; Absolute positioning",
        "G17 ; XY plane selection",
        "",
        "M3 S18000 ; Spindle on",
        "G4 P2 ; Dwell 2 seconds",
        ""
    ]
    
    feed_rate = 1500 if config.bit_size <= 6 else 1200
    plunge_rate = 300
    
    for i, part in enumerate(parts[:3]):  # Preview first 3 parts
        lines.append(f"; Part: {part['name']}")
        lines.append(f"G0 Z10 ; Safe height")
        lines.append(f"G0 X{part.get('x', 0)} Y{part.get('y', 0)} ; Move to start")
        
        passes = math.ceil(config.material_thickness / config.cut_depth_per_pass)
        for p in range(passes):
            depth = min((p + 1) * config.cut_depth_per_pass, config.material_thickness)
            lines.append(f"G1 Z-{depth} F{plunge_rate} ; Plunge pass {p+1}")
            lines.append(f"G1 X{part.get('x', 0) + part['width']} F{feed_rate}")
            lines.append(f"G1 Y{part.get('y', 0) + part['height']}")
            lines.append(f"G1 X{part.get('x', 0)}")
            lines.append(f"G1 Y{part.get('y', 0)}")
        lines.append("")
    
    lines.extend([
        "; ... (additional parts omitted in preview)",
        "",
        "G0 Z25 ; Raise to safe height",
        "M5 ; Spindle off",
        "G0 X0 Y0 ; Return to origin",
        "M30 ; Program end"
    ])
    
    return "\n".join(lines)

@cnc_router.post("/generate", response_model=CNCOutput)
async def generate_cnc(params: DesignParams):
    config = CNCConfig()
    
    parts = calculate_desk_parts(params)
    nesting = simple_nesting(parts, config.sheet_width, config.sheet_height)
    
    # Calculate cut time (rough estimate)
    total_perimeter = sum(2 * (p["width"] + p["height"]) for p in parts for _ in range(p.get("quantity", 1)))
    passes = math.ceil(config.material_thickness / config.cut_depth_per_pass)
    feed_rate = 1500  # mm/min
    cut_time = (total_perimeter * passes) / feed_rate
    
    # Material cost (NZ plywood ~$80/sheet for 18mm)
    material_cost = nesting.sheets_required * 80.0
    
    gcode = generate_gcode_preview(nesting.parts, config)
    
    return CNCOutput(
        nesting=nesting,
        estimated_cut_time_minutes=round(cut_time, 1),
        material_cost_nzd=material_cost,
        gcode_preview=gcode
    )

@cnc_router.get("/material-estimate")
async def material_estimate(width: int = 1800, depth: int = 800, height: int = 750):
    """Quick material cost estimate"""
    params = DesignParams(width=width, depth=depth, height=height)
    parts = calculate_desk_parts(params)
    nesting = simple_nesting(parts, 2400, 1200)
    
    return {
        "sheets_required": nesting.sheets_required,
        "waste_percentage": nesting.waste_percentage,
        "estimated_cost_nzd": nesting.sheets_required * 80.0,
        "part_count": len(parts)
    }

# ============== PAYMENT ROUTES ==============

# Pricing tiers
SINGLE_EXPORT_PRICE = 4.99
PRO_MONTHLY_PRICE = 19.00

class ExportRequest(BaseModel):
    params: DesignParams
    design_name: str = "UltimateDesk Design"
    export_type: str = "single"  # "single" or "subscription"

class ExportResponse(BaseModel):
    success: bool
    download_urls: Optional[Dict[str, str]] = None
    message: str
    disclaimer: str = ""

# ============== FILE GENERATION FUNCTIONS ==============

def generate_full_gcode(parts: List[Dict], config: CNCConfig, design_name: str) -> str:
    """Generate complete production G-code for all parts"""
    lines = [
        f"; ========================================",
        f"; UltimateDesk CNC Pro - Production G-Code",
        f"; Design: {design_name}",
        f"; Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"; ========================================",
        f";",
        f"; IMPORTANT SAFETY DISCLAIMER:",
        f"; This G-code is a REFERENCE FILE. You MUST verify all toolpaths",
        f"; in your CAM software before cutting. UltimateDesk is not responsible",
        f"; for machine damage, material waste, or injury from unverified toolpaths.",
        f";",
        f"; Material: 18mm NZ Plywood (2400x1200mm sheets)",
        f"; Bit Size: {config.bit_size}mm end mill",
        f"; Cut Depth Per Pass: {config.cut_depth_per_pass}mm",
        f"; Feed Rate: {1500 if config.bit_size <= 6 else 1200} mm/min",
        f"; Plunge Rate: 300 mm/min",
        f"; Safe Height: 10mm",
        f";",
        f"; Total Parts: {len(parts)}",
        f"; ========================================",
        "",
        "G21 ; Set units to millimeters",
        "G90 ; Absolute positioning",
        "G17 ; XY plane selection",
        "G54 ; Work coordinate system",
        "",
        "M3 S18000 ; Spindle on at 18000 RPM",
        "G4 P3 ; Dwell 3 seconds for spindle to reach speed",
        ""
    ]
    
    feed_rate = 1500 if config.bit_size <= 6 else 1200
    plunge_rate = 300
    safe_height = 10
    
    for i, part in enumerate(parts):
        x, y = part.get('x', 0), part.get('y', 0)
        w, h = part['width'], part['height']
        
        lines.append(f"; ----------------------------------------")
        lines.append(f"; Part {i+1}: {part['name']}")
        lines.append(f"; Dimensions: {w}mm x {h}mm")
        lines.append(f"; Position: X{x} Y{y}")
        if part.get('rotated'):
            lines.append(f"; Note: Part is ROTATED 90 degrees")
        lines.append(f"; ----------------------------------------")
        
        lines.append(f"G0 Z{safe_height} ; Safe height")
        lines.append(f"G0 X{x} Y{y} ; Rapid to start position")
        
        passes = math.ceil(config.material_thickness / config.cut_depth_per_pass)
        for p in range(passes):
            depth = min((p + 1) * config.cut_depth_per_pass, config.material_thickness)
            lines.append(f"")
            lines.append(f"; Pass {p+1}/{passes} - Depth: {depth}mm")
            lines.append(f"G1 Z-{depth} F{plunge_rate}")
            lines.append(f"G1 X{x + w} F{feed_rate}")
            lines.append(f"G1 Y{y + h}")
            lines.append(f"G1 X{x}")
            lines.append(f"G1 Y{y}")
        
        lines.append(f"G0 Z{safe_height} ; Retract")
        lines.append("")
    
    lines.extend([
        "; ========================================",
        "; Program End",
        "; ========================================",
        "G0 Z25 ; Final retract to safe height",
        "M5 ; Spindle off",
        "G0 X0 Y0 ; Return to machine origin",
        "M30 ; Program end",
        "",
        "; Thank you for using UltimateDesk CNC Pro!",
        "; Questions? support@ultimatedesk.co.nz"
    ])
    
    return "\n".join(lines)

def generate_dxf(parts: List[Dict], config: CNCConfig, design_name: str) -> str:
    """Generate DXF file for CAD/CAM import"""
    # DXF R12 format (widely compatible)
    dxf_lines = [
        "0", "SECTION",
        "2", "HEADER",
        "9", "$ACADVER",
        "1", "AC1009",
        "9", "$INSBASE",
        "10", "0.0",
        "20", "0.0",
        "30", "0.0",
        "9", "$EXTMIN",
        "10", "0.0",
        "20", "0.0",
        "30", "0.0",
        "9", "$EXTMAX",
        "10", str(config.sheet_width),
        "20", str(config.sheet_height),
        "30", "0.0",
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "ENTITIES"
    ]
    
    for i, part in enumerate(parts):
        x, y = part.get('x', 0), part.get('y', 0)
        w, h = part['width'], part['height']
        
        # Draw rectangle for each part using LINE entities
        # Bottom edge
        dxf_lines.extend([
            "0", "LINE",
            "8", f"PART_{i+1}_{part['name'].replace(' ', '_')}",
            "10", str(x),
            "20", str(y),
            "30", "0.0",
            "11", str(x + w),
            "21", str(y),
            "31", "0.0"
        ])
        # Right edge
        dxf_lines.extend([
            "0", "LINE",
            "8", f"PART_{i+1}_{part['name'].replace(' ', '_')}",
            "10", str(x + w),
            "20", str(y),
            "30", "0.0",
            "11", str(x + w),
            "21", str(y + h),
            "31", "0.0"
        ])
        # Top edge
        dxf_lines.extend([
            "0", "LINE",
            "8", f"PART_{i+1}_{part['name'].replace(' ', '_')}",
            "10", str(x + w),
            "20", str(y + h),
            "30", "0.0",
            "11", str(x),
            "21", str(y + h),
            "31", "0.0"
        ])
        # Left edge
        dxf_lines.extend([
            "0", "LINE",
            "8", f"PART_{i+1}_{part['name'].replace(' ', '_')}",
            "10", str(x),
            "20", str(y + h),
            "30", "0.0",
            "11", str(x),
            "21", str(y),
            "31", "0.0"
        ])
        
        # Add part label as TEXT
        dxf_lines.extend([
            "0", "TEXT",
            "8", f"LABELS",
            "10", str(x + w/2),
            "20", str(y + h/2),
            "30", "0.0",
            "40", "20.0",
            "1", f"{part['name']} ({w}x{h})"
        ])
    
    dxf_lines.extend([
        "0", "ENDSEC",
        "0", "EOF"
    ])
    
    return "\n".join(dxf_lines)

def generate_pdf_html(parts: List[Dict], nesting: NestingResult, params: DesignParams, design_name: str) -> str:
    """Generate HTML that can be converted to PDF cutting sheet"""
    sheet_w, sheet_h = 2400, 1200
    scale = 0.25  # Scale for visualization
    
    # Group parts by sheet
    sheets_parts = {}
    for part in parts:
        sheet_idx = part.get('sheet', 0)
        if sheet_idx not in sheets_parts:
            sheets_parts[sheet_idx] = []
        sheets_parts[sheet_idx].append(part)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{design_name} - Cutting Sheet</title>
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 20px; color: #333; }}
        h1 {{ color: #FF3B30; margin-bottom: 5px; }}
        .header {{ border-bottom: 2px solid #FF3B30; padding-bottom: 15px; margin-bottom: 20px; }}
        .disclaimer {{ background: #FFF3CD; border: 1px solid #FFE69C; padding: 15px; margin: 20px 0; border-radius: 8px; }}
        .disclaimer strong {{ color: #856404; }}
        .specs {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0; }}
        .spec-box {{ background: #f5f5f5; padding: 10px; border-radius: 5px; text-align: center; }}
        .spec-box .value {{ font-size: 24px; font-weight: bold; color: #FF3B30; }}
        .spec-box .label {{ font-size: 12px; color: #666; }}
        .sheet {{ margin: 30px 0; page-break-inside: avoid; }}
        .sheet-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
        .sheet-visual {{ border: 2px solid #333; background: #D4A574; position: relative; }}
        .part {{ position: absolute; border: 2px solid #333; background: rgba(255,255,255,0.9); display: flex; align-items: center; justify-content: center; font-size: 10px; text-align: center; }}
        .parts-list {{ margin-top: 20px; }}
        .parts-list table {{ width: 100%; border-collapse: collapse; }}
        .parts-list th, .parts-list td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .parts-list th {{ background: #f5f5f5; }}
        .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>UltimateDesk CNC Pro</h1>
        <h2>{design_name}</h2>
        <p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>
    
    <div class="disclaimer">
        <strong>⚠️ IMPORTANT SAFETY DISCLAIMER</strong><br>
        This cutting sheet is a REFERENCE DOCUMENT. All measurements should be verified before cutting.
        You are responsible for verifying toolpaths in your CAM software. UltimateDesk is not liable for
        machine damage, material waste, or injury from unverified cuts.
    </div>
    
    <div class="specs">
        <div class="spec-box">
            <div class="value">{params.width}mm</div>
            <div class="label">Width</div>
        </div>
        <div class="spec-box">
            <div class="value">{params.depth}mm</div>
            <div class="label">Depth</div>
        </div>
        <div class="spec-box">
            <div class="value">{params.height}mm</div>
            <div class="label">Height</div>
        </div>
        <div class="spec-box">
            <div class="value">{nesting.sheets_required}</div>
            <div class="label">Sheets Required</div>
        </div>
    </div>
    
    <div class="specs">
        <div class="spec-box">
            <div class="value">{params.material_thickness}mm</div>
            <div class="label">Material Thickness</div>
        </div>
        <div class="spec-box">
            <div class="value">{nesting.waste_percentage}%</div>
            <div class="label">Waste</div>
        </div>
        <div class="spec-box">
            <div class="value">${nesting.sheets_required * 80:.2f}</div>
            <div class="label">Est. Material Cost (NZD)</div>
        </div>
        <div class="spec-box">
            <div class="value">{len(parts)}</div>
            <div class="label">Total Parts</div>
        </div>
    </div>
"""
    
    for sheet_idx, sheet_parts in sheets_parts.items():
        html += f"""
    <div class="sheet">
        <div class="sheet-title">Sheet {sheet_idx + 1} of {nesting.sheets_required} (2400mm x 1200mm)</div>
        <div class="sheet-visual" style="width: {sheet_w * scale}px; height: {sheet_h * scale}px;">
"""
        colors = ['#FFE4E1', '#E0FFE0', '#E0E0FF', '#FFFFE0', '#FFE0FF', '#E0FFFF']
        for i, part in enumerate(sheet_parts):
            color = colors[i % len(colors)]
            html += f"""
            <div class="part" style="left: {part['x'] * scale}px; top: {part['y'] * scale}px; width: {part['width'] * scale - 4}px; height: {part['height'] * scale - 4}px; background: {color};">
                <span>{part['name']}<br>{part['width']}x{part['height']}</span>
            </div>
"""
        html += """
        </div>
    </div>
"""
    
    html += """
    <div class="parts-list">
        <h3>Parts List</h3>
        <table>
            <tr>
                <th>#</th>
                <th>Part Name</th>
                <th>Width (mm)</th>
                <th>Height (mm)</th>
                <th>Sheet</th>
                <th>Rotated</th>
            </tr>
"""
    
    for i, part in enumerate(parts):
        html += f"""
            <tr>
                <td>{i + 1}</td>
                <td>{part['name']}</td>
                <td>{part['width']}</td>
                <td>{part['height']}</td>
                <td>{part.get('sheet', 0) + 1}</td>
                <td>{'Yes' if part.get('rotated') else 'No'}</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
    
    <div class="footer">
        <p><strong>UltimateDesk CNC Pro</strong> - Professional CNC Desk Designer for Kiwi Makers</p>
        <p>Questions? Email support@ultimatedesk.co.nz | Visit ultimatedesk.co.nz</p>
    </div>
</body>
</html>
"""
    return html

# ============== EXPORT ENDPOINTS ==============

exports_router = APIRouter(prefix="/exports", tags=["Pro Exports"])

@exports_router.post("/check-access")
async def check_export_access(request: Request):
    """Check if user has Pro access for exports"""
    user = await get_optional_user(request)
    
    if not user:
        return {
            "has_access": False,
            "reason": "not_authenticated",
            "message": "Please sign in to export files"
        }
    
    if user.get("is_pro"):
        return {
            "has_access": True,
            "plan": "pro_unlimited",
            "message": "You have unlimited Pro exports"
        }
    
    # Check for single export credits
    credits = await db.export_credits.find_one({"user_id": user["id"]})
    if credits and credits.get("remaining", 0) > 0:
        return {
            "has_access": True,
            "plan": "single_export",
            "remaining": credits["remaining"],
            "message": f"You have {credits['remaining']} export(s) remaining"
        }
    
    return {
        "has_access": False,
        "reason": "no_credits",
        "message": "Purchase Pro or single export to download files"
    }

@exports_router.post("/purchase-single")
async def purchase_single_export(request: Request):
    """Create checkout for single export ($4.99)"""
    body = await request.json()
    origin_url = body.get("origin_url", "")
    
    if not origin_url:
        raise HTTPException(status_code=400, detail="Origin URL required")
    
    user = await get_current_user(request)
    
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    
    success_url = f"{origin_url}/export/success?session_id={{CHECKOUT_SESSION_ID}}&type=single"
    cancel_url = f"{origin_url}/designer"
    
    checkout_request = CheckoutSessionRequest(
        amount=SINGLE_EXPORT_PRICE,
        currency="nzd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user["id"],
            "user_email": user["email"],
            "product": "single_export"
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": user["id"],
        "user_email": user["email"],
        "amount": SINGLE_EXPORT_PRICE,
        "currency": "nzd",
        "product": "single_export",
        "status": "pending",
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"url": session.url, "session_id": session.session_id}

@exports_router.post("/purchase-pro")
async def purchase_pro_subscription(request: Request):
    """Create checkout for Pro subscription ($19/mo)"""
    body = await request.json()
    origin_url = body.get("origin_url", "")
    
    if not origin_url:
        raise HTTPException(status_code=400, detail="Origin URL required")
    
    user = await get_current_user(request)
    
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    
    success_url = f"{origin_url}/export/success?session_id={{CHECKOUT_SESSION_ID}}&type=pro"
    cancel_url = f"{origin_url}/pricing"
    
    checkout_request = CheckoutSessionRequest(
        amount=PRO_MONTHLY_PRICE,
        currency="nzd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user["id"],
            "user_email": user["email"],
            "product": "pro_subscription"
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": user["id"],
        "user_email": user["email"],
        "amount": PRO_MONTHLY_PRICE,
        "currency": "nzd",
        "product": "pro_subscription",
        "status": "pending",
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"url": session.url, "session_id": session.session_id}

@exports_router.post("/generate")
async def generate_export_files(export_req: ExportRequest, request: Request):
    """Generate and return export files (DXF, G-code, PDF) - requires Pro or credits"""
    user = await get_current_user(request)
    
    # Check access
    has_pro = user.get("is_pro", False)
    
    if not has_pro:
        credits = await db.export_credits.find_one({"user_id": user["id"]})
        if not credits or credits.get("remaining", 0) <= 0:
            raise HTTPException(
                status_code=403, 
                detail="Pro subscription or export credits required. Purchase at /pricing"
            )
        # Deduct credit
        await db.export_credits.update_one(
            {"user_id": user["id"]},
            {"$inc": {"remaining": -1}}
        )
    
    # Generate files
    config = CNCConfig()
    parts = calculate_desk_parts(export_req.params)
    nesting = simple_nesting(parts, config.sheet_width, config.sheet_height)
    
    # Generate all file contents
    gcode_content = generate_full_gcode(nesting.parts, config, export_req.design_name)
    dxf_content = generate_dxf(nesting.parts, config, export_req.design_name)
    pdf_html = generate_pdf_html(nesting.parts, nesting, export_req.params, export_req.design_name)
    
    # Store export record
    export_id = str(uuid.uuid4())
    await db.exports.insert_one({
        "export_id": export_id,
        "user_id": user["id"],
        "design_name": export_req.design_name,
        "params": export_req.params.model_dump(),
        "gcode": gcode_content,
        "dxf": dxf_content,
        "pdf_html": pdf_html,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=24)
    })
    
    disclaimer = """IMPORTANT: These files are high-quality REFERENCE files. 
You MUST verify all toolpaths in your CAM software (VCarve, Fusion 360, etc.) before cutting. 
UltimateDesk is not responsible for machine damage, material waste, or injury from unverified toolpaths."""
    
    return {
        "success": True,
        "export_id": export_id,
        "files": {
            "gcode": f"/api/exports/download/{export_id}/gcode",
            "dxf": f"/api/exports/download/{export_id}/dxf",
            "pdf": f"/api/exports/download/{export_id}/pdf"
        },
        "disclaimer": disclaimer,
        "message": "Export files generated successfully. Files expire in 24 hours."
    }

@exports_router.get("/download/{export_id}/{file_type}")
async def download_export_file(export_id: str, file_type: str, request: Request):
    """Download a specific export file"""
    user = await get_current_user(request)
    
    export = await db.exports.find_one({
        "export_id": export_id,
        "user_id": user["id"]
    })
    
    if not export:
        raise HTTPException(status_code=404, detail="Export not found or expired")
    
    if export.get("expires_at") and export["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Export has expired. Please generate new files.")
    
    design_name = export.get("design_name", "UltimateDesk").replace(" ", "_")
    
    if file_type == "gcode":
        content = export.get("gcode", "")
        filename = f"{design_name}.nc"
        media_type = "text/plain"
    elif file_type == "dxf":
        content = export.get("dxf", "")
        filename = f"{design_name}.dxf"
        media_type = "application/dxf"
    elif file_type == "pdf":
        content = export.get("pdf_html", "")
        filename = f"{design_name}_cutting_sheet.html"
        media_type = "text/html"
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

# Update webhook to handle new products
@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature")
    
    api_key = os.environ.get("STRIPE_API_KEY")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    
    try:
        event = await stripe_checkout.handle_webhook(body, sig)
        
        if event.payment_status == "paid":
            transaction = await db.payment_transactions.find_one({"session_id": event.session_id})
            
            if transaction:
                await db.payment_transactions.update_one(
                    {"session_id": event.session_id},
                    {"$set": {"status": "complete", "payment_status": "paid", "completed_at": datetime.now(timezone.utc)}}
                )
                
                product = transaction.get("product", "")
                user_id = transaction.get("user_id")
                
                if user_id:
                    if product == "pro_subscription":
                        await db.users.update_one(
                            {"_id": ObjectId(user_id)},
                            {"$set": {"is_pro": True, "pro_since": datetime.now(timezone.utc)}}
                        )
                    elif product == "single_export":
                        # Add 1 export credit
                        await db.export_credits.update_one(
                            {"user_id": user_id},
                            {"$inc": {"remaining": 1}, "$set": {"updated_at": datetime.now(timezone.utc)}},
                            upsert=True
                        )
        
        return {"received": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"received": True, "error": str(e)}

PRO_SUBSCRIPTION_PRICE = PRO_MONTHLY_PRICE  # Keep backward compatibility

# ============== INCLUDE ROUTERS ==============

api_router.include_router(auth_router)
api_router.include_router(designs_router)
api_router.include_router(chat_router)
api_router.include_router(cnc_router)
api_router.include_router(payments_router)
api_router.include_router(exports_router)

@api_router.get("/")
async def root():
    return {"message": "UltimateDesk CNC Pro API", "version": "1.0.0"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[os.environ.get('FRONTEND_URL', '*')],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup events
@app.on_event("startup")
async def startup():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.designs.create_index("user_id")
    await db.chat_sessions.create_index("session_id")
    await db.payment_transactions.create_index("session_id")
    
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@ultimatedesk.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin123!")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "Admin",
            "role": "admin",
            "is_pro": True,
            "created_at": datetime.now(timezone.utc)
        })
        logger.info(f"Admin user created: {admin_email}")
    
    # Write test credentials
    creds_path = Path("/app/memory/test_credentials.md")
    creds_path.parent.mkdir(exist_ok=True)
    creds_path.write_text(f"""# Test Credentials

## Admin Account
- Email: {admin_email}
- Password: {admin_password}
- Role: admin

## Auth Endpoints
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/me
- POST /api/auth/refresh
""")
    logger.info("Test credentials written to /app/memory/test_credentials.md")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
