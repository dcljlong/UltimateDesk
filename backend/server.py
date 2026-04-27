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
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse
    HAS_EMERGENT_INTEGRATIONS = True
except ImportError:
    LlmChat = None
    UserMessage = None
    StripeCheckout = None
    CheckoutSessionRequest = None
    CheckoutSessionResponse = None
    CheckoutStatusResponse = None
    HAS_EMERGENT_INTEGRATIONS = False

# Pricing engine
from pricing import (
    calculate_quote,
    get_bundle_catalog,
    BUNDLE_OPTIONS,
    QuoteBreakdown,
)

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
pricing_router = APIRouter(prefix="/pricing", tags=["Pricing"])

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
    is_oversize: bool = False
    desktop_split_count: int = 1
    requires_centre_support: bool = False
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
    advice: List[str] = []
    warnings: List[str] = []

class CNCConfig(BaseModel):
    bit_size: float = 6
    cut_depth_per_pass: float = 3
    sheet_width: float = 2400
    sheet_height: float = 1200
    material_thickness: float = 18

    # Production CNC controls
    material: str = "18mm NZ Plywood"
    material_name: str = "18mm NZ Plywood"
    feed_rate: int = 1500
    plunge_rate: int = 300
    spindle_speed: int = 18000
    machine_post: str = "generic_grbl_metric"
    post_processor: str = "generic_grbl_metric"
    tool_number: int = 1
    tool_name: str = ""
    spindle_rotation: str = "CW"
    cut_strategy: str = "climb"

    # Safe motion / machining strategy
    safe_height: float = 10
    retract_height: float = 3
    stock_margin: float = 0
    lead_in_length: float = 0
    lead_out_length: float = 0
    tab_length: float = 0
    tab_skin: float = 0
    pocket_stepover: float = 0
    pocket_finish_allowance: float = 0

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

    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")

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

    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")

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
        response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=900, path="/")
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
                has_rgb_channels=False, has_headset_hook=True,
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
                mixer_tray_width=610, has_pedal_tilt=False,
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
- width (mm, standard 1000-2400; oversize mode 2401-3000)
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
- is_oversize (true/false)
- desktop_split_count (1 for standard, 2 for oversize split desktop)
- requires_centre_support (true/false)
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

AI_BOOLEAN_KEYS = {
    "has_rgb_channels",
    "has_cable_management",
    "has_headset_hook",
    "has_gpu_tray",
    "has_mixer_tray",
    "has_pedal_tilt",
    "has_vesa_mount",
    "is_oversize",
    "requires_centre_support",
}

AI_NUMERIC_LIMITS = {
    "width": (1000, 3000),
    "depth": (600, 1000),
    "height": (680, 820),
    "monitor_count": (1, 5),
    "mixer_tray_width": (280, 1000),
    "material_thickness": (15, 25),
    "desktop_split_count": (1, 2),
}

AI_ENUM_LIMITS = {
    "desk_type": {"gaming", "studio", "office"},
    "leg_style": {"standard", "angular", "solid", "trestle"},
    "joint_type": {"finger", "dovetail", "box"},
}

ALLOWED_AI_PARAM_KEYS = set(AI_BOOLEAN_KEYS) | set(AI_NUMERIC_LIMITS) | set(AI_ENUM_LIMITS) | {"custom_features"}


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "y", "1", "on", "add", "include", "enabled"}:
            return True
        if normalized in {"false", "no", "n", "0", "off", "remove", "exclude", "disabled"}:
            return False
    return None


def _coerce_int(value):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _clean_text_list(value, max_items: int = 5, max_len: int = 80) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = [value]
    elif isinstance(value, list):
        raw_items = value
    else:
        return []

    cleaned = []
    for item in raw_items:
        text = str(item).strip()
        if not text:
            continue
        cleaned.append(text[:max_len])
        if len(cleaned) >= max_items:
            break
    return cleaned


def clean_ai_list(value: Any) -> List[str]:
    return _clean_text_list(value, max_items=6, max_len=140)


def sanitize_ai_param_updates(param_updates: Dict[str, Any]):
    safe_updates: Dict[str, Any] = {}
    validation_warnings: List[str] = []

    if not isinstance(param_updates, dict):
        return safe_updates, ["AI did not return a valid params object."]

    for key, value in param_updates.items():
        if key not in ALLOWED_AI_PARAM_KEYS:
            validation_warnings.append(f"Ignored unsupported design field: {key}")
            continue

        if key in AI_BOOLEAN_KEYS:
            bool_value = _coerce_bool(value)
            if bool_value is None:
                validation_warnings.append(f"Ignored invalid true/false value for {key}.")
                continue
            safe_updates[key] = bool_value
            continue

        if key in AI_NUMERIC_LIMITS:
            number_value = _coerce_int(value)
            if number_value is None:
                validation_warnings.append(f"Ignored invalid number for {key}.")
                continue

            min_value, max_value = AI_NUMERIC_LIMITS[key]
            clamped_value = max(min_value, min(max_value, number_value))
            if clamped_value != number_value:
                validation_warnings.append(
                    f"Adjusted {key} from {number_value} to {clamped_value} to stay inside current product limits."
                )
            safe_updates[key] = clamped_value
            continue

        if key in AI_ENUM_LIMITS:
            enum_value = str(value).strip().lower()
            if enum_value not in AI_ENUM_LIMITS[key]:
                validation_warnings.append(f"Ignored unsupported {key}: {value}")
                continue
            safe_updates[key] = enum_value
            continue

        if key == "custom_features":
            safe_updates[key] = _clean_text_list(value)

    requested_width = safe_updates.get("width")
    if isinstance(requested_width, int) and requested_width > 2400:
        safe_updates["is_oversize"] = True
        safe_updates["desktop_split_count"] = 2
        safe_updates["requires_centre_support"] = True
        validation_warnings.append(
            "Oversize desk mode enabled: desktop will be split into two panels with centre support."
        )

    return safe_updates, validation_warnings


@chat_router.post("/design", response_model=ChatResponse)
async def chat_design(chat_req: ChatRequest, request: Request):
    session_id = chat_req.session_id or str(uuid.uuid4())
    current_params = chat_req.current_params or DesignParams()

    try:
        import google.generativeai as genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")

        genai.configure(api_key=api_key)

        model = genai.GenerativeModel("gemini-2.5-flash-lite")

        prompt = f"""
{DESK_DESIGNER_SYSTEM_PROMPT}

Current desk configuration:
{current_params.model_dump_json()}

User request:
{chat_req.message}

Respond ONLY in strict JSON with this exact shape:
{{
  "message": "short helpful explanation of the proposed desk changes",
  "params": {{
    "width": 1800
  }},
  "advice": [
    "short practical design advice"
  ],
  "warnings": [
    "short honest limitation or safety warning if needed"
  ]
}}

Rules:
- params must only contain fields from the allowed parameter list.
- Only include params the user requested or clearly implied.
- Do not claim structural certification, engineering approval, or guaranteed machine-ready outputs.
- Keep advice practical and relevant.
- Put limitations, safety notes, CAM verification notes, or unsupported requests in warnings.
"""

        response = model.generate_content(prompt)
        response_text = response.text
        advice = []
        warnings = []
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
            advice = clean_ai_list(ai_response.get("advice", []))
            warnings = clean_ai_list(ai_response.get("warnings", []))
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            message = response_text
            param_updates = {}
            warnings.append("AI response could not be parsed as structured JSON.")

        # Apply only validated AI updates to current params
        safe_updates, validation_warnings = sanitize_ai_param_updates(param_updates)
        warnings.extend(validation_warnings)

        if validation_warnings:
            message = message.rstrip()
            if not message.endswith((".", "!", "?")):
                message += "."
            message += " I have adjusted the final applied design to stay within UltimateDesk product limits."

        updated_dict = current_params.model_dump()
        extracted_changes = []
        for key, value in safe_updates.items():
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
            extracted_changes=extracted_changes,
            advice=advice,
            warnings=warnings
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============== CNC GENERATOR ROUTES ==============


def calculate_desk_parts(params: DesignParams) -> List[Dict[str, Any]]:
    """Generate export parts with CNC feature metadata: drill points, pockets, and cutouts."""
    parts: List[Dict[str, Any]] = []

    width = max(1000, int(params.width))
    depth = max(600, int(params.depth))
    height = max(680, int(params.height))
    t = max(15, int(params.material_thickness))

    leg_size = max(44, int(round(t * 2.4)))
    leg_inset_x = max(70, int(round(width * 0.08)))
    leg_inset_y = max(55, int(round(depth * 0.08)))

    clear_span_x = max(300, width - ((leg_inset_x + leg_size) * 2))
    clear_span_y = max(220, depth - ((leg_inset_y + leg_size) * 2))

    def add_part(
        name: str,
        part_w: float,
        part_h: float,
        qty: int = 1,
        kind: str = "panel",
        drill_points: Optional[List[Dict[str, Any]]] = None,
        cutouts: Optional[List[Dict[str, Any]]] = None,
        pockets: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        part_w = int(round(part_w))
        part_h = int(round(part_h))
        if part_w <= 0 or part_h <= 0 or qty <= 0:
            return

        part = {
            "name": name,
            "width": part_w,
            "height": part_h,
            "quantity": qty,
            "type": kind,
        }

        if drill_points:
            part["drill_points"] = drill_points
        if cutouts:
            part["cutouts"] = cutouts
        if pockets:
            part["pockets"] = pockets

        parts.append(part)

    def clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def drill(name: str, x: float, y: float, diameter: float = 5, depth_value: float = 10) -> Dict[str, Any]:
        return {
            "name": name,
            "x": round(float(x), 2),
            "y": round(float(y), 2),
            "diameter": diameter,
            "depth": min(float(depth_value), t),
        }

    def rect_cutout(name: str, x: float, y: float, w: float, h: float) -> Dict[str, Any]:
        return {
            "name": name,
            "type": "cutout",
            "shape": "rectangle",
            "x": round(float(x), 2),
            "y": round(float(y), 2),
            "width": round(float(w), 2),
            "height": round(float(h), 2),
        }

    def rect_pocket(name: str, x: float, y: float, w: float, h: float, depth_value: float = 6) -> Dict[str, Any]:
        return {
            "name": name,
            "type": "pocket",
            "shape": "rectangle",
            "x": round(float(x), 2),
            "y": round(float(y), 2),
            "width": round(float(w), 2),
            "height": round(float(h), 2),
            "depth": min(float(depth_value), max(1, t - 1)),
        }

    def line_drills(prefix: str, part_w: float, y: float, count: int, edge: float = 45, diameter: float = 5, depth_value: float = 10) -> List[Dict[str, Any]]:
        if count <= 1:
            return [drill(f"{prefix} 1", part_w / 2, y, diameter, depth_value)]

        span = max(1, part_w - edge * 2)
        return [
            drill(
                f"{prefix} {i + 1}",
                edge + (span * i / (count - 1)),
                y,
                diameter,
                depth_value,
            )
            for i in range(count)
        ]

    def corner_drills(prefix: str, part_w: float, part_h: float, inset: float = 24, diameter: float = 5, depth_value: float = 10) -> List[Dict[str, Any]]:
        return [
            drill(f"{prefix} FL", inset, inset, diameter, depth_value),
            drill(f"{prefix} FR", part_w - inset, inset, diameter, depth_value),
            drill(f"{prefix} RL", inset, part_h - inset, diameter, depth_value),
            drill(f"{prefix} RR", part_w - inset, part_h - inset, diameter, depth_value),
        ]

    def desktop_features(part_w: float, part_h: float, panel_name: str) -> Dict[str, List[Dict[str, Any]]]:
        drill_points: List[Dict[str, Any]] = []
        cutouts: List[Dict[str, Any]] = []
        pockets: List[Dict[str, Any]] = []

        rail_fix_count = 7 if part_w >= 1800 else 5
        drill_points.extend(line_drills("rear rail fixing", part_w, clamp(part_h - 55, 35, part_h - 25), rail_fix_count, edge=75, diameter=4, depth_value=10))
        drill_points.extend(line_drills("front rail fixing", part_w, 55, rail_fix_count, edge=75, diameter=4, depth_value=10))

        if params.has_cable_management:
            cable_w = min(180, max(90, part_w * 0.10))
            cable_h = 42
            cutouts.append(rect_cutout("rear cable pass-through", (part_w - cable_w) / 2, clamp(part_h - 115, 70, part_h - 70), cable_w, cable_h))

        if params.has_vesa_mount:
            cx = part_w / 2
            cy = clamp(part_h - 145, 110, part_h - 90)
            for dx in (-50, 50):
                for dy in (-50, 50):
                    drill_points.append(drill("VESA/top mounting pilot", cx + dx, cy + dy, 5, 12))

        if params.has_mixer_tray and "Right" not in panel_name:
            pocket_w = min(max(int(params.mixer_tray_width or 520), 280), max(280, part_w - 180))
            pocket_h = min(210, max(120, part_h * 0.28))
            pockets.append(rect_pocket("mixer tray underside rebate", (part_w - pocket_w) / 2, 95, pocket_w, pocket_h, 6))

        return {
            "drill_points": drill_points,
            "cutouts": cutouts,
            "pockets": pockets,
        }

    is_oversize = bool(getattr(params, "is_oversize", False)) or width > 2400
    desktop_split_count = 2 if is_oversize else 1
    requires_centre_support = bool(getattr(params, "requires_centre_support", False)) or is_oversize

    if desktop_split_count > 1:
        left_top_w = int(math.ceil(width / 2))
        right_top_w = width - left_top_w
        left_features = desktop_features(left_top_w, depth, "Desktop Top Left Panel")
        right_features = desktop_features(right_top_w, depth, "Desktop Top Right Panel")
        add_part("Desktop Top Left Panel", left_top_w, depth, drill_points=left_features["drill_points"], cutouts=left_features["cutouts"], pockets=left_features["pockets"])
        add_part("Desktop Top Right Panel", right_top_w, depth, drill_points=right_features["drill_points"], cutouts=right_features["cutouts"], pockets=right_features["pockets"])
        add_part(
            "Desktop Centre Join Plate",
            180,
            max(300, min(depth - 120, 650)),
            drill_points=corner_drills("centre join plate fixing", 180, max(300, min(depth - 120, 650)), inset=32, diameter=5, depth_value=12),
        )
    else:
        top_features = desktop_features(width, depth, "Desktop Top")
        add_part("Desktop Top", width, depth, drill_points=top_features["drill_points"], cutouts=top_features["cutouts"], pockets=top_features["pockets"])

    leg_h = height - t
    leg_holes = lambda label: [
        drill(f"{label} upper rail fixing A", leg_size / 2, clamp(leg_h - 80, 40, leg_h - 20), 5, 12),
        drill(f"{label} upper rail fixing B", leg_size / 2, clamp(leg_h - 145, 40, leg_h - 20), 5, 12),
        drill(f"{label} lower rail fixing A", leg_size / 2, 85, 5, 12),
        drill(f"{label} lower rail fixing B", leg_size / 2, 145, 5, 12),
    ]
    add_part("Leg Post FL", leg_size, leg_h, drill_points=leg_holes("FL leg"))
    add_part("Leg Post FR", leg_size, leg_h, drill_points=leg_holes("FR leg"))
    add_part("Leg Post RL", leg_size, leg_h, drill_points=leg_holes("RL leg"))
    add_part("Leg Post RR", leg_size, leg_h, drill_points=leg_holes("RR leg"))

    rail_count = 7 if clear_span_x >= 1800 else 5
    rear_rail_holes = lambda rail_w, label: line_drills(f"{label} rail top fixing", rail_w, 21, rail_count, edge=55, diameter=5, depth_value=12)
    lower_rail_holes = lambda rail_w, label: line_drills(f"{label} rail fixing", rail_w, 15, rail_count, edge=55, diameter=5, depth_value=12)

    if is_oversize:
        rear_left = int(math.ceil(clear_span_x / 2))
        rear_right = clear_span_x - rear_left
        add_part("Rear Upper Rail Left", rear_left, 42, drill_points=rear_rail_holes(rear_left, "rear left"))
        add_part("Rear Upper Rail Right", rear_right, 42, drill_points=rear_rail_holes(rear_right, "rear right"))
        add_part("Front Lower Rail Left", rear_left, 30, drill_points=lower_rail_holes(rear_left, "front left"))
        add_part("Front Lower Rail Right", rear_right, 30, drill_points=lower_rail_holes(rear_right, "front right"))
    else:
        add_part("Rear Upper Rail", clear_span_x, 42, drill_points=rear_rail_holes(clear_span_x, "rear"))
        add_part("Front Lower Rail", clear_span_x, 30, drill_points=lower_rail_holes(clear_span_x, "front"))

    add_part("Left Side Rail", clear_span_y, 30, drill_points=lower_rail_holes(clear_span_y, "left side"))
    add_part("Right Side Rail", clear_span_y, 30, drill_points=lower_rail_holes(clear_span_y, "right side"))

    if requires_centre_support:
        add_part("Centre Support Post", leg_size, leg_h, drill_points=leg_holes("centre support"))
        add_part("Centre Support Foot", 320, 90, drill_points=corner_drills("centre support foot", 320, 90, inset=25, diameter=5, depth_value=12))
        add_part(
            "Centre Under-Top Support Rail",
            max(420, min(int(width * 0.32), 900)),
            55,
            drill_points=line_drills("centre under-top support fixing", max(420, min(int(width * 0.32), 900)), 27.5, 4, edge=45, diameter=5, depth_value=12),
        )

    back_panel_w = max(600, clear_span_x - 40)
    back_panel_h = 180 if params.desk_type == "office" else 220
    back_panel_cutouts = []
    if params.has_cable_management:
        back_panel_cutouts.append(rect_cutout("modesty cable slot", (back_panel_w - 220) / 2, clamp(back_panel_h - 70, 45, back_panel_h - 45), 220, 36))
    add_part(
        "Back Modesty Panel",
        back_panel_w,
        back_panel_h,
        drill_points=line_drills("modesty panel top fixing", back_panel_w, back_panel_h - 28, 5, edge=55, diameter=5, depth_value=12),
        cutouts=back_panel_cutouts,
    )

    if params.has_cable_management:
        tray_w = max(500, min(width - (leg_inset_x * 2) - 120, int(width * 0.60)))
        add_part(
            "Cable Tray Base",
            tray_w,
            85,
            drill_points=corner_drills("cable tray base fixing", tray_w, 85, inset=22, diameter=5, depth_value=12),
            cutouts=[rect_cutout("cable tray tie slot", tray_w / 2 - 45, 24, 90, 28)],
        )
        add_part("Cable Tray Front", tray_w, 50, drill_points=line_drills("cable tray front fixing", tray_w, 25, 4, edge=45, diameter=4, depth_value=10))
        add_part("Cable Tray Back", tray_w, 50, drill_points=line_drills("cable tray back fixing", tray_w, 25, 4, edge=45, diameter=4, depth_value=10))
        add_part("Cable Tray End Left", 85, 50, drill_points=corner_drills("cable tray left end fixing", 85, 50, inset=18, diameter=4, depth_value=10))
        add_part("Cable Tray End Right", 85, 50, drill_points=corner_drills("cable tray right end fixing", 85, 50, inset=18, diameter=4, depth_value=10))

    if params.has_headset_hook:
        add_part("Headset Hook Backplate", 90, 30, drill_points=[drill("headset hook fixing A", 24, 15, 5, 12), drill("headset hook fixing B", 66, 15, 5, 12)])
        add_part("Headset Hook Arm", 60, 30, drill_points=[drill("headset hook arm fixing", 18, 15, 5, 12)])

    if params.has_gpu_tray:
        add_part("GPU Tray Base", 150, 70, drill_points=corner_drills("gpu tray base fixing", 150, 70, inset=18, diameter=4, depth_value=10))
        add_part("GPU Tray Side Left", 70, 70, drill_points=corner_drills("gpu tray side left fixing", 70, 70, inset=18, diameter=4, depth_value=10))
        add_part("GPU Tray Side Right", 70, 70, drill_points=corner_drills("gpu tray side right fixing", 70, 70, inset=18, diameter=4, depth_value=10))
        add_part("GPU Tray Front Stop", 150, 25, drill_points=line_drills("gpu tray front stop fixing", 150, 12.5, 3, edge=25, diameter=4, depth_value=10))

    if params.has_mixer_tray:
        tray_w = max(280, min(int(params.mixer_tray_width or 520), clear_span_x))
        add_part("Mixer Tray", tray_w, 170, pockets=[rect_pocket("mixer anti-slip rebate", 35, 30, tray_w - 70, 110, 4)], drill_points=corner_drills("mixer tray fixing", tray_w, 170, inset=24, diameter=5, depth_value=12))
        add_part("Mixer Tray Support Left", 170, 120, drill_points=corner_drills("mixer left support fixing", 170, 120, inset=24, diameter=5, depth_value=12))
        add_part("Mixer Tray Support Right", 170, 120, drill_points=corner_drills("mixer right support fixing", 170, 120, inset=24, diameter=5, depth_value=12))
        add_part("Mixer Tray Front Lip", tray_w, 40, drill_points=line_drills("mixer tray front lip fixing", tray_w, 20, 4, edge=45, diameter=4, depth_value=10))

    if getattr(params, "has_pedal_tilt", False):
        add_part("Pedal Platform", 500, 240, drill_points=corner_drills("pedal platform fixing", 500, 240, inset=28, diameter=5, depth_value=12))
        add_part("Pedal Support Left", 240, 120, drill_points=corner_drills("pedal left support fixing", 240, 120, inset=24, diameter=5, depth_value=12))
        add_part("Pedal Support Right", 240, 120, drill_points=corner_drills("pedal right support fixing", 240, 120, inset=24, diameter=5, depth_value=12))

    if params.has_vesa_mount:
        add_part("VESA Upright", 180, 100, drill_points=corner_drills("vesa upright fixing", 180, 100, inset=24, diameter=5, depth_value=12))
        vesa_holes = []
        for dx in (-50, 50):
            for dy in (-50, 50):
                vesa_holes.append(drill("VESA 100 mount hole", 100 + dx, 100 + dy, 5, 12))
        add_part("VESA Mount Plate", 200, 200, drill_points=vesa_holes + corner_drills("vesa plate fixing", 200, 200, inset=24, diameter=5, depth_value=12))
        add_part("VESA Gusset Left", 120, 120, drill_points=corner_drills("vesa left gusset fixing", 120, 120, inset=24, diameter=5, depth_value=12))
        add_part("VESA Gusset Right", 120, 120, drill_points=corner_drills("vesa right gusset fixing", 120, 120, inset=24, diameter=5, depth_value=12))

    return parts





class PartConnection:
    def __init__(self, part_a, part_b, connection_type, axis, offset=0):
        self.part_a = part_a
        self.part_b = part_b
        self.connection_type = connection_type  # rail_to_leg, top_to_rail, etc
        self.axis = axis  # x, y
        self.offset = offset


def build_part_connections(parts):
    connections = []

    for p in parts:
        name = p.get("name", "").lower()

        # Rail to leg connections
        if "rail" in name:
            for leg in parts:
                if "leg" in leg.get("name", "").lower():
                    connections.append(
                        PartConnection(p, leg, "rail_to_leg", axis="x")
                    )

        # Top to rail
        if "top" in name:
            for rail in parts:
                if "rail" in rail.get("name", "").lower():
                    connections.append(
                        PartConnection(p, rail, "top_to_rail", axis="x")
                    )

    return connections

def generate_joinery_holes(parts, params):
    width = params.width
    holes = []

    rail_fixing_count = 7 if width >= 2400 else 5 if width >= 1800 else 4
    edge_offset = 30
    span = width - 120
    spacing = span / max(1, rail_fixing_count - 1)

    for i in range(rail_fixing_count):
        x = edge_offset + i * spacing
        holes.append({
            "x": round(x, 2),
            "y": 20,
            "diameter": 5
        })

    return holes

def simple_nesting(parts: List[Dict], sheet_width: int, sheet_height: int) -> NestingResult:
    """Simple bin packing algorithm for sheet nesting while preserving CNC feature metadata."""
    margin = 18
    feature_keys = (
        "drill_points",
        "holes",
        "joinery_holes",
        "connector_holes",
        "cutouts",
        "inside_profiles",
        "internal_profiles",
        "internal_cutouts",
        "pockets",
        "rebates",
        "trays",
        "pocket_features",
        "recesses",
    )

    def clone_feature_item(item: Dict[str, Any], source_w: float, source_h: float, rotated: bool) -> Dict[str, Any]:
        cloned = dict(item)
        if not rotated:
            return cloned

        # Rotation used by nesting is 90 degrees: original local X/Y maps into rotated panel space.
        x = float(cloned.get("x", cloned.get("left", cloned.get("center_x", cloned.get("cx", 0))) or 0))
        y = float(cloned.get("y", cloned.get("bottom", cloned.get("top", cloned.get("center_y", cloned.get("cy", 0)))) or 0))
        w = float(cloned.get("width", cloned.get("w", 0)) or 0)
        h = float(cloned.get("height", cloned.get("h", 0)) or 0)

        if w > 0 and h > 0:
            cloned["x"] = round(y, 2)
            cloned["y"] = round(source_w - x - w, 2)
            cloned["width"] = round(h, 2)
            cloned["height"] = round(w, 2)
        else:
            cloned["x"] = round(y, 2)
            cloned["y"] = round(source_w - x, 2)

        return cloned

    def copy_feature_list(items, source_w: float, source_h: float, rotated: bool):
        if isinstance(items, dict):
            items = list(items.values())
        if not isinstance(items, list):
            return []
        return [
            clone_feature_item(item, source_w, source_h, rotated)
            for item in items
            if isinstance(item, dict)
        ]

    def placed_part(part: Dict[str, Any], x: float, y: float, rotated: bool) -> Dict[str, Any]:
        source_w = part["width"]
        source_h = part["height"]

        placed = {
            "name": part["name"],
            "x": x,
            "y": y,
            "width": source_h if rotated else source_w,
            "height": source_w if rotated else source_h,
            "rotated": rotated,
            "type": part.get("type", "panel"),
        }

        for key in feature_keys:
            if key in part:
                values = copy_feature_list(part.get(key), source_w, source_h, rotated)
                if values:
                    placed[key] = values

        return placed

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
                    if pw <= sw and ph <= sh:
                        sheet["parts"].append(placed_part(part, x, y, rotated=False))
                        sheet["spaces"].pop(i)
                        if sw - pw > 50:
                            sheet["spaces"].append((x + pw, y, sw - pw, ph))
                        if sh - ph > 50:
                            sheet["spaces"].append((x, y + ph, sw, sh - ph))
                        placed = True
                        break

                    elif ph <= sw and pw <= sh:
                        sheet["parts"].append(placed_part(part, x, y, rotated=True))
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
                if current_sheet["parts"]:
                    sheets.append(current_sheet)
                current_sheet = {"parts": [], "spaces": [(0, 0, sheet_width, sheet_height)]}
                current_sheet["parts"].append(placed_part(part, 0, 0, rotated=False))
                current_sheet["spaces"] = [(pw, 0, sheet_width - pw, ph), (0, ph, sheet_width, sheet_height - ph)]

    if current_sheet["parts"]:
        sheets.append(current_sheet)

    total_sheet_area = len(sheets) * sheet_width * sheet_height
    waste = ((total_sheet_area - total_part_area) / total_sheet_area) * 100 if total_sheet_area else 0

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
        "; UltimateDesk - G-Code Preview",
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

    for i, part in enumerate(parts):
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

    gcode = "(BEGIN CNC PROGRAM)\nG21\nG90\nG17\n" +  generate_gcode_preview(nesting.parts, config)

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
    bundle: str = "dxf"  # dxf | dxf_svg | dxf_gcode | full_pack
    cnc_config: dict = {}

class ExportResponse(BaseModel):
    success: bool
    download_urls: Optional[Dict[str, str]] = None
    message: str
    disclaimer: str = ""

# ============== FILE GENERATION FUNCTIONS ==============

def generate_full_gcode(parts: List[Dict], config: CNCConfig, design_name: str) -> str:
    """Generate complete production G-code with explicit cut classification, lead-ins, and multi-pass profiles."""
    bit_size = float(getattr(config, "bit_size", 6) or 6)
    tool_radius = bit_size / 2
    material_thickness = float(getattr(config, "material_thickness", 18) or 18)
    cut_depth_per_pass = float(getattr(config, "cut_depth_per_pass", 3) or 3)

    feed_rate = int(getattr(config, "feed_rate", 0) or (1500 if bit_size <= 6 else 1200))
    plunge_rate = int(getattr(config, "plunge_rate", 0) or 300)
    spindle_speed = int(getattr(config, "spindle_speed", 0) or 18000)

    material_name = str(
        getattr(config, "material", None)
        or getattr(config, "material_name", None)
        or "18mm NZ Plywood"
    )
    machine_post = str(
        getattr(config, "machine_post", None)
        or getattr(config, "post_processor", None)
        or "generic_grbl_metric"
    )
    tool_number = int(getattr(config, "tool_number", 0) or 1)
    tool_name = str(getattr(config, "tool_name", None) or f"{bit_size:g}mm flat end mill")
    spindle_rotation = str(getattr(config, "spindle_rotation", None) or "CW").upper()
    cut_strategy = str(getattr(config, "cut_strategy", None) or "climb").lower()

    safe_height = float(getattr(config, "safe_height", 10) or 10)
    clearance_height = max(safe_height, 25)
    retract_height = float(getattr(config, "retract_height", 3) or 3)
    lead_in_length = float(getattr(config, "lead_in_length", 0) or max(bit_size * 1.5, 8))
    lead_out_length = float(getattr(config, "lead_out_length", 0) or lead_in_length)
    sheet_width = float(getattr(config, "sheet_width", 2400) or 2400)
    sheet_height = float(getattr(config, "sheet_height", 1200) or 1200)
    stock_margin = float(getattr(config, "stock_margin", 0) or max(lead_in_length + tool_radius, bit_size * 2))
    tab_length = float(getattr(config, "tab_length", 0) or max(bit_size * 3, 18))
    tab_skin = float(getattr(config, "tab_skin", 0) or min(3, max(material_thickness * 0.2, 1.5)))
    tab_z_depth = max(material_thickness - tab_skin, 0)
    pocket_stepover = float(getattr(config, "pocket_stepover", 0) or max(bit_size * 0.45, 1))
    pocket_finish_allowance = float(getattr(config, "pocket_finish_allowance", 0) or max(tool_radius * 0.15, 0.3))

    passes = max(1, math.ceil(material_thickness / cut_depth_per_pass))

    def fmt(value):
        value = round(float(value), 3)
        return f"{value:.3f}".rstrip("0").rstrip(".")

    def resolve_tool_recommendation():
        material_key = material_name.lower()
        if "ply" in material_key or "plywood" in material_key:
            if bit_size <= 3:
                return {
                    "feed": 900,
                    "plunge": 180,
                    "rpm": 18000,
                    "max_pass": 2,
                    "notes": "Small-tool plywood profile: conservative pass depth recommended.",
                }
            if bit_size <= 6:
                return {
                    "feed": 1500,
                    "plunge": 300,
                    "rpm": 18000,
                    "max_pass": 3,
                    "notes": "Standard plywood profile strategy.",
                }
            return {
                "feed": 1200,
                "plunge": 250,
                "rpm": 16000,
                "max_pass": 4,
                "notes": "Large-tool plywood profile: verify chip load and machine rigidity.",
            }

        if "mdf" in material_key:
            return {
                "feed": 1600 if bit_size <= 6 else 1300,
                "plunge": 300,
                "rpm": 18000,
                "max_pass": 3,
                "notes": "MDF profile strategy: manage dust extraction and heat.",
            }

        return {
            "feed": 1200 if bit_size <= 6 else 1000,
            "plunge": 250,
            "rpm": 16000,
            "max_pass": min(3, max(1, bit_size * 0.5)),
            "notes": "Generic material strategy: verify with CAM/tool supplier.",
        }

    tool_recommendation = resolve_tool_recommendation()
    machine_warnings = []

    if feed_rate > tool_recommendation["feed"] * 1.35:
        machine_warnings.append(
            f"Feed rate {feed_rate} mm/min is above recommended baseline {tool_recommendation['feed']} mm/min for {material_name}."
        )

    if plunge_rate > tool_recommendation["plunge"] * 1.35:
        machine_warnings.append(
            f"Plunge rate {plunge_rate} mm/min is above recommended baseline {tool_recommendation['plunge']} mm/min for {material_name}."
        )

    if cut_depth_per_pass > tool_recommendation["max_pass"]:
        machine_warnings.append(
            f"Cut depth per pass {fmt(cut_depth_per_pass)}mm exceeds recommended baseline {fmt(tool_recommendation['max_pass'])}mm for {tool_name} in {material_name}."
        )

    if spindle_rotation != "CW":
        machine_warnings.append(
            f"Spindle rotation is set to {spindle_rotation}; verify profile directions before cutting."
        )

    if cut_strategy not in ("climb", "conventional"):
        machine_warnings.append(
            f"Unknown cut strategy '{cut_strategy}'. Default geometry assumes climb strategy."
        )

    def supports_canned_drill_cycle():
        post_key = machine_post.lower().strip()
        return post_key in ("mach3", "mach4", "linuxcnc", "fanuc_metric", "haas_metric")

    drill_strategy = "G81 canned drill cycle" if supports_canned_drill_cycle() else "explicit plunge/retract drill moves"

    def local_number(source, *names, default=0):
        for name in names:
            if isinstance(source, dict) and source.get(name) is not None:
                try:
                    return float(source.get(name))
                except (TypeError, ValueError):
                    return float(default)
        return float(default)

    def is_absolute_feature(feature):
        return bool(feature.get("absolute") or feature.get("is_absolute") or feature.get("global"))

    def collect_drill_points(part, part_x, part_y):
        drill_points = []
        for key in ("drill_points", "holes", "joinery_holes", "connector_holes"):
            items = part.get(key) or []
            if isinstance(items, dict):
                items = items.values()
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("type") in ("slot", "pocket", "rebate", "cutout"):
                    continue
                hx = local_number(item, "x", "center_x", "cx", default=0)
                hy = local_number(item, "y", "center_y", "cy", default=0)
                if not is_absolute_feature(item):
                    hx += part_x
                    hy += part_y

                hx += origin_shift_x
                hy += origin_shift_y

                diameter = local_number(item, "diameter", "dia", "d", default=bit_size)
                drill_points.append({
                    "name": item.get("name") or item.get("label") or key,
                    "x": hx,
                    "y": hy,
                    "diameter": diameter,
                    "depth": local_number(item, "depth", default=material_thickness),
                })
        return drill_points

    def collect_inside_rect_profiles(part, part_x, part_y):
        profiles = []
        for key in ("inside_profiles", "internal_profiles", "cutouts", "internal_cutouts"):
            items = part.get(key) or []
            if isinstance(items, dict):
                items = items.values()
            for item in items:
                if not isinstance(item, dict):
                    continue
                shape = (item.get("shape") or item.get("type") or "rectangle").lower()
                if shape not in ("rect", "rectangle", "cutout", "inside_profile", "internal_profile"):
                    continue

                ix = local_number(item, "x", "left", default=0)
                iy = local_number(item, "y", "bottom", "top", default=0)
                iw = local_number(item, "width", "w", default=0)
                ih = local_number(item, "height", "h", default=0)

                if iw <= 0 or ih <= 0:
                    continue

                if not is_absolute_feature(item):
                    ix += part_x
                    iy += part_y

                ix += origin_shift_x
                iy += origin_shift_y

                profiles.append({
                    "name": item.get("name") or item.get("label") or key,
                    "left": ix,
                    "bottom": iy,
                    "right": ix + iw,
                    "top": iy + ih,
                })
        return profiles

    def collect_rect_pockets(part, part_x, part_y):
        pockets = []
        for key in ("pockets", "rebates", "trays", "pocket_features", "recesses"):
            items = part.get(key) or []
            if isinstance(items, dict):
                items = items.values()
            for item in items:
                if not isinstance(item, dict):
                    continue

                feature_type = (item.get("type") or item.get("shape") or "pocket").lower()
                if feature_type not in ("pocket", "rebate", "tray", "recess", "rect", "rectangle"):
                    continue

                px = local_number(item, "x", "left", default=0)
                py = local_number(item, "y", "bottom", "top", default=0)
                pw = local_number(item, "width", "w", default=0)
                ph = local_number(item, "height", "h", default=0)
                depth = local_number(item, "depth", "pocket_depth", "rebate_depth", default=min(6, material_thickness * 0.33))

                if pw <= bit_size or ph <= bit_size or depth <= 0:
                    continue

                if not is_absolute_feature(item):
                    px += part_x
                    py += part_y

                px += origin_shift_x
                py += origin_shift_y

                pockets.append({
                    "name": item.get("name") or item.get("label") or key,
                    "left": px,
                    "bottom": py,
                    "right": px + pw,
                    "top": py + ph,
                    "depth": min(depth, material_thickness),
                })
        return pockets

    def calculate_origin_shift():
        min_toolpath_x = 0
        min_toolpath_y = 0
        max_toolpath_x = 0
        max_toolpath_y = 0

        for part in parts:
            px = float(part.get("x", 0) or 0)
            py = float(part.get("y", 0) or 0)
            pw = float(part.get("width", 0) or 0)
            ph = float(part.get("height", 0) or 0)

            # Outside profile is offset outward by tool radius.
            # Lead-in/out extends further left of profile start.
            min_toolpath_x = min(min_toolpath_x, px - tool_radius - lead_in_length)
            min_toolpath_y = min(min_toolpath_y, py - tool_radius)
            max_toolpath_x = max(max_toolpath_x, px + pw + tool_radius)
            max_toolpath_y = max(max_toolpath_y, py + ph + tool_radius)

        shift_x = max(0, stock_margin - min_toolpath_x)
        shift_y = max(0, stock_margin - min_toolpath_y)

        shifted_max_x = max_toolpath_x + shift_x
        shifted_max_y = max_toolpath_y + shift_y

        return shift_x, shift_y, shifted_max_x, shifted_max_y

    origin_shift_x, origin_shift_y, shifted_max_x, shifted_max_y = calculate_origin_shift()

    if origin_shift_x > 0 or origin_shift_y > 0:
        machine_warnings.append(
            f"Toolpaths shifted by X{fmt(origin_shift_x)} Y{fmt(origin_shift_y)} to preserve stock margin and avoid negative machine coordinates."
        )

    if shifted_max_x > sheet_width or shifted_max_y > sheet_height:
        machine_warnings.append(
            f"Shifted toolpath envelope X{fmt(shifted_max_x)} Y{fmt(shifted_max_y)} exceeds sheet size {fmt(sheet_width)} x {fmt(sheet_height)}mm."
        )

    sheet_count = len({int(part.get("sheet", 0) or 0) for part in parts}) if parts else 0

    operation_audit = {
        "parts": len(parts),
        "sheets": sheet_count,
        "drills": 0,
        "pockets": 0,
        "inside_profiles": 0,
        "outside_profiles": 0,
        "profile_passes": 0,
        "pocket_passes": 0,
        "tabs": 0,
        "warnings": len(machine_warnings),
    }

    lines = [
        "; ========================================",
        "; UltimateDesk - Production G-Code",
        f"; Design: {design_name}",
        f"; Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "; ========================================",
        ";",
        "; IMPORTANT SAFETY DISCLAIMER:",
        "; This G-code must be verified in machine-specific CAM/control software before cutting.",
        "; Confirm work origin, stock margin, clamps, vacuum hold-down, tool length, and post compatibility.",
        ";",
        f"; Machine Post: {machine_post}",
        f"; Sheet Size: {fmt(sheet_width)}mm x {fmt(sheet_height)}mm",
        f"; Sheets In Job: {operation_audit['sheets']}",
        "; Sheet Output Mode: one machine setup per sheet with M0 pause between sheets.",
        f"; Stock Margin: {fmt(stock_margin)}mm",
        f"; Origin Shift Applied: X{fmt(origin_shift_x)} Y{fmt(origin_shift_y)}",
        f"; Toolpath Envelope After Shift: X{fmt(shifted_max_x)} Y{fmt(shifted_max_y)}",
        f"; Material: {material_name}",
        f"; Material Thickness: {fmt(material_thickness)}mm",
        f"; Tool Number: T{tool_number}",
        f"; Tool: {tool_name}",
        f"; Bit Size: {fmt(bit_size)}mm",
        f"; Tool Radius / Kerf Offset: {fmt(tool_radius)}mm",
        f"; Cut Depth Per Pass: {fmt(cut_depth_per_pass)}mm",
        f"; Calculated Passes: {passes}",
        f"; Feed Rate: {feed_rate} mm/min",
        f"; Plunge Rate: {plunge_rate} mm/min",
        f"; Spindle Speed: {spindle_speed} RPM",
        f"; Spindle Rotation: {spindle_rotation}",
        f"; Safe Height: {fmt(safe_height)}mm",
        f"; Lead-in / Lead-out: {fmt(lead_in_length)}mm",
        f"; Pocket Stepover: {fmt(pocket_stepover)}mm",
        f"; Pocket Finish Allowance: {fmt(pocket_finish_allowance)}mm",
        f"; Tool Recommendation: feed {tool_recommendation['feed']} mm/min, plunge {tool_recommendation['plunge']} mm/min, rpm {tool_recommendation['rpm']}, max pass {fmt(tool_recommendation['max_pass'])}mm",
        f"; Tool Note: {tool_recommendation['notes']}",
        f"; Cut Strategy: {cut_strategy.upper()}",
        f"; Drill Strategy: {drill_strategy}",
        "; Cut Classification: drill operations first, inside profiles before outside profiles.",
        "; Offset Strategy: generated XY geometry is tool-centreline offset; G41/G42 not used.",
        "; Outside profiles: offset outward by tool radius.",
        "; Inside profiles: offset inward by tool radius.",
        "; Direction Strategy: for CW spindle, outside=CW and inside=CCW represents climb routing.",
        "; Toolpath Direction: outside profiles clockwise, inside profiles counter-clockwise.",
        "; Audit Summary: emitted at program end after operations are generated.",
        "; ========================================",
        "",
        "G21 ; Set units to millimeters",
        "G90 ; Absolute positioning",
        "G17 ; XY plane selection",
        "G54 ; Work coordinate system",
        "G40 ; Cancel cutter compensation",
        "G49 ; Cancel tool length compensation",
        "G80 ; Cancel canned cycles",
        f"M3 S{spindle_speed} ; Spindle on",
        "G4 P3 ; Dwell 3 seconds for spindle to reach speed",
        f"G0 Z{fmt(clearance_height)} ; Initial safe retract",
        "",
    ]

    if machine_warnings:
        lines.append("; MACHINE / TOOLING WARNINGS:")
        for warning in machine_warnings:
            lines.append(f"; WARNING: {warning}")
        lines.append("")

    if machine_post == "generic_grbl_metric":
        lines.append("; POST NOTE: Generic GRBL-style metric output. Canned drill cycles are not emitted for this post.")
        lines.append("; POST NOTE: Drilling uses explicit Z plunge/retract moves for broader GRBL compatibility.")
        lines.append("")
    elif machine_post.lower() in ("mach3", "mach4"):
        lines.append("; POST NOTE: Mach-style controller selected. Verify arc, drilling cycle, and safe-Z behaviour.")
        lines.append("")
    else:
        lines.append(f"; POST NOTE: Custom/unknown post '{machine_post}'. Verify all modal commands before cutting.")
        lines.append("")

    def add_drill_cycle(point):
        operation_audit["drills"] += 1
        drill_depth = min(float(point.get("depth", material_thickness) or material_thickness), material_thickness)

        lines.append(f"; DRILL: {point['name']} diameter {fmt(point['diameter'])}mm")
        if point["diameter"] > bit_size * 1.25:
            lines.append(f"; WARNING: drill diameter {fmt(point['diameter'])}mm exceeds tool size {fmt(bit_size)}mm - verify boring strategy")

        lines.append(f"G0 Z{fmt(safe_height)}")
        lines.append(f"G0 X{fmt(point['x'])} Y{fmt(point['y'])}")

        if supports_canned_drill_cycle():
            lines.append(f"G81 Z-{fmt(drill_depth)} R{fmt(retract_height)} F{plunge_rate} ; canned drill cycle")
            lines.append("G80 ; cancel drill cycle")
        else:
            lines.append(f"G1 Z-{fmt(drill_depth)} F{plunge_rate} ; explicit drill plunge")
            lines.append(f"G0 Z{fmt(retract_height)} ; explicit drill retract")
            lines.append(f"G0 Z{fmt(safe_height)} ; safe drill clearance")

        lines.append("")

    def add_linear_move_with_optional_tab(end_x, end_y, depth, use_tab=False):
        start_x = add_linear_move_with_optional_tab.current_x
        start_y = add_linear_move_with_optional_tab.current_y
        dx = end_x - start_x
        dy = end_y - start_y
        length = math.hypot(dx, dy)

        if use_tab and length >= max(180, tab_length * 4) and depth >= material_thickness:
            ux = dx / length
            uy = dy / length
            mid_x = start_x + dx * 0.5
            mid_y = start_y + dy * 0.5
            pre_x = mid_x - ux * (tab_length / 2)
            pre_y = mid_y - uy * (tab_length / 2)
            post_x = mid_x + ux * (tab_length / 2)
            post_y = mid_y + uy * (tab_length / 2)

            lines.append(f"G1 X{fmt(pre_x)} Y{fmt(pre_y)} F{feed_rate}")
            operation_audit["tabs"] += 1
            lines.append(f"G1 Z-{fmt(tab_z_depth)} F{plunge_rate} ; holding tab lift leaves {fmt(tab_skin)}mm skin")
            lines.append(f"G1 X{fmt(post_x)} Y{fmt(post_y)} F{feed_rate} ; cross holding tab")
            lines.append(f"G1 Z-{fmt(depth)} F{plunge_rate} ; resume profile depth")
            lines.append(f"G1 X{fmt(end_x)} Y{fmt(end_y)} F{feed_rate}")
        else:
            lines.append(f"G1 X{fmt(end_x)} Y{fmt(end_y)} F{feed_rate}")

        add_linear_move_with_optional_tab.current_x = end_x
        add_linear_move_with_optional_tab.current_y = end_y

    add_linear_move_with_optional_tab.current_x = 0
    add_linear_move_with_optional_tab.current_y = 0

    def add_rect_pocket(pocket_name, left, bottom, right, top, pocket_depth):
        operation_audit["pockets"] += 1
        cut_left = left + tool_radius
        cut_bottom = bottom + tool_radius
        cut_right = right - tool_radius
        cut_top = top - tool_radius

        if cut_right <= cut_left or cut_top <= cut_bottom:
            lines.append(f"; WARNING: skipped pocket {pocket_name} - pocket is smaller than tool diameter")
            return

        pocket_passes = max(1, math.ceil(pocket_depth / cut_depth_per_pass))
        operation_audit["pocket_passes"] += pocket_passes
        start_x = (cut_left + cut_right) / 2
        start_y = (cut_bottom + cut_top) / 2

        lines.append("; ----------------------------------------")
        lines.append(f"; POCKET: {pocket_name}")
        lines.append(f"; Pocket Depth: {fmt(pocket_depth)}mm")
        lines.append(f"; Pocket Strategy: rectangular offset clearing, centre-out, finish allowance {fmt(pocket_finish_allowance)}mm")
        lines.append(f"; Pocket Stepover: {fmt(pocket_stepover)}mm")
        lines.append("; ----------------------------------------")

        max_radius_x = max((cut_right - cut_left) / 2 - pocket_finish_allowance, 0)
        max_radius_y = max((cut_top - cut_bottom) / 2 - pocket_finish_allowance, 0)
        loop_count = max(1, math.ceil(max(max_radius_x, max_radius_y) / pocket_stepover))

        for p in range(pocket_passes):
            depth = min((p + 1) * cut_depth_per_pass, pocket_depth)
            lines.append("")
            lines.append(f"; POCKET pass {p + 1}/{pocket_passes} depth {fmt(depth)}mm")
            lines.append(f"G0 Z{fmt(safe_height)}")
            lines.append(f"G0 X{fmt(start_x)} Y{fmt(start_y)} ; rapid to pocket centre")
            lines.append(f"G1 Z-{fmt(depth)} F{plunge_rate} ; pocket plunge")

            for loop_index in range(1, loop_count + 1):
                rx = min(loop_index * pocket_stepover, max_radius_x)
                ry = min(loop_index * pocket_stepover, max_radius_y)

                lx = start_x - rx
                by = start_y - ry
                rxp = start_x + rx
                typ = start_y + ry

                if rx <= 0 or ry <= 0:
                    continue

                lines.append(f"; Pocket clearing loop {loop_index}/{loop_count}")
                lines.append(f"G1 X{fmt(lx)} Y{fmt(by)} F{feed_rate}")
                lines.append(f"G1 X{fmt(rxp)} Y{fmt(by)} F{feed_rate}")
                lines.append(f"G1 X{fmt(rxp)} Y{fmt(typ)} F{feed_rate}")
                lines.append(f"G1 X{fmt(lx)} Y{fmt(typ)} F{feed_rate}")
                lines.append(f"G1 X{fmt(lx)} Y{fmt(by)} F{feed_rate}")

            finish_left = cut_left
            finish_bottom = cut_bottom
            finish_right = cut_right
            finish_top = cut_top

            lines.append("; Pocket finish pass")
            lines.append(f"G1 X{fmt(finish_left)} Y{fmt(finish_bottom)} F{feed_rate}")
            lines.append(f"G1 X{fmt(finish_right)} Y{fmt(finish_bottom)} F{feed_rate}")
            lines.append(f"G1 X{fmt(finish_right)} Y{fmt(finish_top)} F{feed_rate}")
            lines.append(f"G1 X{fmt(finish_left)} Y{fmt(finish_top)} F{feed_rate}")
            lines.append(f"G1 X{fmt(finish_left)} Y{fmt(finish_bottom)} F{feed_rate}")
            lines.append(f"G0 Z{fmt(safe_height)} ; retract after pocket pass")

        lines.append("")

    def add_rect_profile(profile_name, left, bottom, right, top, cut_class):
        if cut_class == "OUTSIDE_PROFILE":
            operation_audit["outside_profiles"] += 1
        else:
            operation_audit["inside_profiles"] += 1
        operation_audit["profile_passes"] += passes

        if right <= left or top <= bottom:
            lines.append(f"; WARNING: skipped invalid profile {profile_name}")
            return

        if cut_class == "OUTSIDE_PROFILE":
            offset_left = left - tool_radius
            offset_bottom = bottom - tool_radius
            offset_right = right + tool_radius
            offset_top = top + tool_radius
            points = [
                (offset_left, offset_bottom),
                (offset_left, offset_top),
                (offset_right, offset_top),
                (offset_right, offset_bottom),
                (offset_left, offset_bottom),
            ]
            lead_start = (points[0][0] - lead_in_length, points[0][1])
            lead_out = (points[-1][0] - lead_out_length, points[-1][1])
            direction = "CLOCKWISE"
            tab_edges = {1, 3}
        else:
            offset_left = left + tool_radius
            offset_bottom = bottom + tool_radius
            offset_right = right - tool_radius
            offset_top = top - tool_radius
            if offset_right <= offset_left or offset_top <= offset_bottom:
                lines.append(f"; WARNING: skipped inside profile {profile_name} - smaller than tool diameter")
                return
            inside_lead = min(lead_in_length, max((offset_right - offset_left) * 0.25, 1), max((offset_top - offset_bottom) * 0.25, 1))
            points = [
                (offset_left, offset_bottom),
                (offset_right, offset_bottom),
                (offset_right, offset_top),
                (offset_left, offset_top),
                (offset_left, offset_bottom),
            ]
            lead_start = (points[0][0] + inside_lead, points[0][1] + inside_lead)
            lead_out = lead_start
            direction = "COUNTER-CLOCKWISE"
            tab_edges = set()

        lines.append(f"; ----------------------------------------")
        lines.append(f"; {cut_class}: {profile_name}")
        lines.append(f"; Direction: {direction}")
        lines.append(f"; Offset Applied: {fmt(tool_radius)}mm")
        lines.append(f"; Lead Start: X{fmt(lead_start[0])} Y{fmt(lead_start[1])}")
        lines.append(f"; Profile Start: X{fmt(points[0][0])} Y{fmt(points[0][1])}")
        if min(p[0] for p in points) < 0 or min(p[1] for p in points) < 0:
            lines.append("; WARNING: offset toolpath goes below X0/Y0. Add nesting margin or reset work origin before cutting.")
        lines.append(f"; ----------------------------------------")

        for p in range(passes):
            depth = min((p + 1) * cut_depth_per_pass, material_thickness)
            is_final_pass = p == passes - 1

            lines.append("")
            lines.append(f"; {cut_class} pass {p + 1}/{passes} depth {fmt(depth)}mm")
            lines.append(f"G0 Z{fmt(safe_height)}")
            lines.append(f"G0 X{fmt(lead_start[0])} Y{fmt(lead_start[1])} ; rapid to lead-in start")
            lines.append(f"G1 Z-{fmt(depth)} F{plunge_rate} ; plunge")
            lines.append(f"G1 X{fmt(points[0][0])} Y{fmt(points[0][1])} F{feed_rate} ; lead-in")

            add_linear_move_with_optional_tab.current_x = points[0][0]
            add_linear_move_with_optional_tab.current_y = points[0][1]

            for edge_index, point in enumerate(points[1:], start=1):
                add_linear_move_with_optional_tab(
                    point[0],
                    point[1],
                    depth,
                    use_tab=(cut_class == "OUTSIDE_PROFILE" and is_final_pass and edge_index in tab_edges),
                )

            lines.append(f"G1 X{fmt(lead_out[0])} Y{fmt(lead_out[1])} F{feed_rate} ; lead-out")
            lines.append(f"G0 Z{fmt(safe_height)} ; retract after pass")

        lines.append("")

    sorted_parts = sorted(
        enumerate(parts),
        key=lambda item: (int(item[1].get("sheet", 0) or 0), item[0])
    )

    current_sheet_idx = None

    for i, (original_part_index, part) in enumerate(sorted_parts):
        sheet_idx = int(part.get("sheet", 0) or 0)

        if sheet_idx != current_sheet_idx:
            if current_sheet_idx is not None:
                lines.extend([
                    "",
                    "; ========================================",
                    f"; SHEET CHANGE: completed Sheet {current_sheet_idx + 1}",
                    "; ========================================",
                    f"G0 Z{fmt(clearance_height)} ; retract before sheet change",
                    "M5 ; spindle off before sheet change",
                    f"M0 ; Load Sheet {sheet_idx + 1}, reset/confirm work origin, clamps, vacuum, and tool clearance",
                    f"M3 S{spindle_speed} ; spindle on after sheet change",
                    "G4 P3 ; dwell after spindle restart",
                    f"G0 Z{fmt(clearance_height)} ; safe height after sheet change",
                    "",
                ])

            current_sheet_idx = sheet_idx
            lines.extend([
                "",
                "; ========================================",
                f"; SHEET {sheet_idx + 1} SETUP",
                "; ========================================",
                f"; Load Sheet {sheet_idx + 1} at the same machine work origin.",
                "; Verify clamps, hold-down, material thickness, and clear toolpath before cycle start.",
                "; Parts below are for this sheet only.",
                "; ========================================",
                "",
            ])

        raw_part_x = float(part.get("x", 0) or 0)
        raw_part_y = float(part.get("y", 0) or 0)
        part_x = raw_part_x + origin_shift_x
        part_y = raw_part_y + origin_shift_y
        width = float(part["width"])
        height = float(part["height"])
        part_name = part.get("name") or f"Part {original_part_index + 1}"

        lines.append("; ========================================")
        lines.append(f"; PART {i + 1}: {part_name}")
        lines.append(f"; Source Part Index: {original_part_index + 1}")
        lines.append(f"; Sheet: {sheet_idx + 1}")
        lines.append(f"; Raw Size: {fmt(width)}mm x {fmt(height)}mm")
        lines.append(f"; Raw Position: X{fmt(raw_part_x)} Y{fmt(raw_part_y)}")
        lines.append(f"; Machine Position After Origin Shift: X{fmt(part_x)} Y{fmt(part_y)}")
        if part.get("rotated"):
            lines.append("; Note: Part is ROTATED 90 degrees in nesting")
        lines.append("; Operation order: drilling -> pocketing -> inside profiles -> outside profile")
        lines.append("; ========================================")

        for point in collect_drill_points(part, part_x, part_y):
            add_drill_cycle(point)

        for pocket in collect_rect_pockets(part, part_x, part_y):
            add_rect_pocket(
                pocket["name"],
                pocket["left"],
                pocket["bottom"],
                pocket["right"],
                pocket["top"],
                pocket["depth"],
            )

        for profile in collect_inside_rect_profiles(part, part_x, part_y):
            add_rect_profile(
                profile["name"],
                profile["left"],
                profile["bottom"],
                profile["right"],
                profile["top"],
                "INSIDE_PROFILE",
            )

        add_rect_profile(
            part_name,
            part_x,
            part_y,
            part_x + width,
            part_y + height,
            "OUTSIDE_PROFILE",
        )

    operation_audit["warnings"] = len(machine_warnings)

    lines.extend([
        "",
        "; ========================================",
        "; OPERATION AUDIT SUMMARY",
        "; ========================================",
        f"; Sheets: {operation_audit['sheets']}",
        f"; Parts: {operation_audit['parts']}",
        f"; Drill Operations: {operation_audit['drills']}",
        f"; Pocket Operations: {operation_audit['pockets']}",
        f"; Pocket Depth Passes: {operation_audit['pocket_passes']}",
        f"; Inside Profile Operations: {operation_audit['inside_profiles']}",
        f"; Outside Profile Operations: {operation_audit['outside_profiles']}",
        f"; Profile Depth Passes: {operation_audit['profile_passes']}",
        f"; Holding Tabs: {operation_audit['tabs']}",
        f"; Machine/Tool Warnings: {operation_audit['warnings']}",
        "; Verify every operation in CAM/controller preview before cutting.",
        "; ========================================",
        "",
        "; ========================================",
        "; Program End",
        "; ========================================",
        f"G0 Z{fmt(clearance_height)} ; Final retract",
        "M5 ; Spindle off",
        "G0 X0 Y0 ; Return to work origin",
        "M30 ; Program end",
        "",
        "; End of UltimateDesk G-code",
    ])

    return "\n".join(lines)



def validate_design(params, parts):
    warnings = []

    thickness = params.material_thickness
    width = params.width

    # Edge distance rule
    min_edge = thickness * 1.5
    if min_edge < 25:
        warnings.append(f"Edge distance too small ({min_edge}mm). Increase fixing offset.")

    # Span rule
    if width > 2400 and not params.requires_centre_support:
        warnings.append("Desk width exceeds 2400mm without centre support.")

    # Sheet fit check
    for p in parts:
        if p.get("width", 0) > 2400 or p.get("height", 0) > 1200:
            warnings.append(f"Part {p.get('name')} exceeds sheet size.")

    return warnings





def get_joinery_rules(connection_type, params, part_width):
    thickness = params.material_thickness

    if connection_type == "rail_to_leg":
        return {
            "diameter": 5,
            "edge": max(30, thickness * 1.5),
            "count": 5 if part_width < 2000 else 7
        }

    if connection_type == "top_to_rail":
        return {
            "diameter": 4,
            "edge": max(40, thickness * 2),
            "count": 4 if part_width < 2000 else 6
        }

    return {
        "diameter": 5,
        "edge": 30,
        "count": 4
    }



def transform_to_global(part, x, y):
    px = part.get("x", 0)
    py = part.get("y", 0)
    rotation = part.get("rotation", 0)

    # 0 = normal
    if rotation == 0:
        return px + x, py + y

    # 90 deg
    if rotation == 90:
        return px - y, py + x

    # 180 deg
    if rotation == 180:
        return px - x, py - y

    # 270 deg
    if rotation == 270:
        return px + y, py - x

    return px + x, py + y

def generate_connection_holes(connections, params):
    holes = []

    for conn in connections:
        width = conn.part_a.get("width", 1000)

        rules = get_joinery_rules(conn.connection_type, params, width)

        count = rules["count"]
        edge = rules["edge"]
        diameter = rules["diameter"]

        span = width - edge * 2
        spacing = span / max(1, count - 1)

        part_height = conn.part_a.get("height", 100)

        for i in range(count):
            x = edge + i * spacing

            # Position based on connection type
            if conn.connection_type == "rail_to_leg":
                y = part_height / 2

            elif conn.connection_type == "top_to_rail":
                y = part_height - (diameter * 2)

            else:
                y = 20

            gx, gy = transform_to_global(conn.part_a, x, y)

            holes.append({
                "part": conn.part_a.get("name"),
                "connected_to": conn.part_b.get("name"),
                "x": round(gx, 2),
                "y": round(gy, 2),
                "diameter": diameter,
                "type": conn.connection_type
            })

    return holes

def generate_dxf(parts: List[Dict], config: CNCConfig, design_name: str) -> str:
    """Generate DXF file for CAD/CAM import with visible cut, drill, pocket, and internal cutout layers."""
    sheet_gap = 400
    title_band = 80
    sheet_indexes = sorted({part.get("sheet", 0) for part in parts}) or [0]
    sheet_count = max(sheet_indexes) + 1
    total_width = (sheet_count * config.sheet_width) + ((sheet_count - 1) * sheet_gap)
    total_height = config.sheet_height + title_band

    def num(source, *names, default=0):
        for name in names:
            if isinstance(source, dict) and source.get(name) is not None:
                try:
                    return float(source.get(name))
                except (TypeError, ValueError):
                    return float(default)
        return float(default)

    def feature_list(part, keys):
        found = []
        for key in keys:
            items = part.get(key) or []
            if isinstance(items, dict):
                items = list(items.values())
            if isinstance(items, list):
                found.extend([item for item in items if isinstance(item, dict)])
        return found

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
        "10", str(total_width),
        "20", str(total_height),
        "30", "0.0",
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "ENTITIES",
    ]

    def add_line(layer, x1, y1, x2, y2):
        dxf_lines.extend([
            "0", "LINE", "8", layer,
            "10", str(round(x1, 3)), "20", str(round(y1, 3)), "30", "0.0",
            "11", str(round(x2, 3)), "21", str(round(y2, 3)), "31", "0.0",
        ])

    def add_rect(layer, x, y, w, h):
        add_line(layer, x, y, x + w, y)
        add_line(layer, x + w, y, x + w, y + h)
        add_line(layer, x + w, y + h, x, y + h)
        add_line(layer, x, y + h, x, y)

    def add_circle(layer, cx, cy, radius):
        dxf_lines.extend([
            "0", "CIRCLE", "8", layer,
            "10", str(round(cx, 3)),
            "20", str(round(cy, 3)),
            "30", "0.0",
            "40", str(round(radius, 3)),
        ])

    def add_text(layer, x, y, size, text):
        dxf_lines.extend([
            "0", "TEXT",
            "8", layer,
            "10", str(round(x, 3)),
            "20", str(round(y, 3)),
            "30", "0.0",
            "40", str(round(size, 3)),
            "72", "1",
            "73", "2",
            "11", str(round(x, 3)),
            "21", str(round(y, 3)),
            "31", "0.0",
            "1", str(text)[:120],
        ])

    for sheet_idx in sheet_indexes:
        x_offset = sheet_idx * (config.sheet_width + sheet_gap)
        add_rect("SHEET_FRAME", x_offset, 0, config.sheet_width, config.sheet_height)
        add_text("SHEET_LABELS", x_offset + 90, config.sheet_height + 30, 28.0, f"Sheet {sheet_idx + 1}")

    for i, part in enumerate(parts):
        sheet_idx = part.get("sheet", 0)
        x_offset = sheet_idx * (config.sheet_width + sheet_gap)
        x = x_offset + part.get("x", 0)
        y = part.get("y", 0)
        w, h = part["width"], part["height"]
        part_layer = f"CUT_SHEET_{sheet_idx + 1}"

        add_rect(part_layer, x, y, w, h)

        for hole in feature_list(part, ("drill_points", "holes", "joinery_holes", "connector_holes")):
            hx = x + num(hole, "x", "center_x", "cx")
            hy = y + num(hole, "y", "center_y", "cy")
            dia = max(0.5, num(hole, "diameter", "dia", "d", default=getattr(config, "bit_size", 6)))
            add_circle("DRILL", hx, hy, dia / 2)

        for cutout in feature_list(part, ("cutouts", "inside_profiles", "internal_profiles", "internal_cutouts")):
            cx = x + num(cutout, "x", "left")
            cy = y + num(cutout, "y", "bottom", "top")
            cw = num(cutout, "width", "w")
            ch = num(cutout, "height", "h")
            if cw > 0 and ch > 0:
                add_rect("INSIDE_CUT", cx, cy, cw, ch)

        for pocket in feature_list(part, ("pockets", "rebates", "trays", "pocket_features", "recesses")):
            px = x + num(pocket, "x", "left")
            py = y + num(pocket, "y", "bottom", "top")
            pw = num(pocket, "width", "w")
            ph = num(pocket, "height", "h")
            if pw > 0 and ph > 0:
                add_rect("POCKET", px, py, pw, ph)

        label_x = x + (w / 2)
        label_y = y + (h / 2)
        label_size = max(10.0, min(24.0, min(w, h) * 0.10))
        label_text = part["name"] if min(w, h) < 140 else f"{part['name']} ({w}x{h})"
        add_text("LABELS", label_x, label_y, label_size, label_text)

    dxf_lines.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(dxf_lines)

def generate_svg(parts: List[Dict], config: CNCConfig, design_name: str) -> str:
    """Generate SVG cutting layout separated by sheet with visible CNC features."""
    sw, sh = config.sheet_width, config.sheet_height
    sheet_gap = 400
    title_band = 80

    sheet_indexes = sorted({part.get("sheet", 0) for part in parts}) or [0]
    sheet_count = max(sheet_indexes) + 1
    total_width = (sheet_count * sw) + ((sheet_count - 1) * sheet_gap)
    total_height = sh + title_band

    def num(source, *names, default=0):
        for name in names:
            if isinstance(source, dict) and source.get(name) is not None:
                try:
                    return float(source.get(name))
                except (TypeError, ValueError):
                    return float(default)
        return float(default)

    def feature_list(part, keys):
        found = []
        for key in keys:
            items = part.get(key) or []
            if isinstance(items, dict):
                items = list(items.values())
            if isinstance(items, list):
                found.extend([item for item in items if isinstance(item, dict)])
        return found

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {total_height}" width="{total_width}mm" height="{total_height}mm">',
        f'  <title>{design_name} - UltimateDesk</title>',
        '  <desc>18mm plywood cutting layout with cut, drill, pocket, and inside-cut features. Verify in CAM software before cutting.</desc>',
        '  <style>',
        '    .sheet-title { font: 28px Arial, sans-serif; fill: #333; font-weight: bold; }',
        '    .part-label { font: 16px Arial, sans-serif; fill: #222; text-anchor: middle; dominant-baseline: middle; }',
        '    .sheet-frame { fill: none; stroke: #888; stroke-width: 2; }',
        '    .part-rect { fill: none; stroke: #000; stroke-width: 2; }',
        '    .drill-hole { fill: none; stroke: #0b61ff; stroke-width: 2; }',
        '    .inside-cut { fill: rgba(255,0,0,0.10); stroke: #d11; stroke-width: 2; stroke-dasharray: 8 4; }',
        '    .pocket { fill: rgba(255,165,0,0.18); stroke: #cc7a00; stroke-width: 2; stroke-dasharray: 5 4; }',
        '    .legend { font: 18px Arial, sans-serif; fill: #333; }',
        '  </style>',
        '  <g id="legend">',
        '    <text class="legend" x="20" y="70">Black=outside cut | Blue=drill | Red dashed=inside cut | Orange dashed=pocket/rebate</text>',
        '  </g>',
    ]

    for sheet_idx in sheet_indexes:
        x_offset = sheet_idx * (sw + sheet_gap)
        lines.append(f'  <g id="sheet-{sheet_idx + 1}">')
        lines.append(f'    <text class="sheet-title" x="{x_offset + 20}" y="35">Sheet {sheet_idx + 1}</text>')
        lines.append(f'    <rect class="sheet-frame" x="{x_offset}" y="{title_band}" width="{sw}" height="{sh}"/>')
        lines.append('  </g>')

    for i, p in enumerate(parts):
        sheet_idx = p.get("sheet", 0)
        x_offset = sheet_idx * (sw + sheet_gap)
        x = x_offset + p.get("x", 0)
        y = title_band + p.get("y", 0)
        w, h = p["width"], p["height"]
        label_size = max(10, min(22, int(min(w, h) * 0.10)))
        label_text = p["name"] if min(w, h) < 140 else f'{p["name"]} ({w}x{h})'

        lines.append(f'  <g id="part-{i + 1}" data-name="{p["name"]}" data-sheet="{sheet_idx + 1}">')
        lines.append(f'    <rect class="part-rect" x="{x}" y="{y}" width="{w}" height="{h}"/>')

        for hole in feature_list(p, ("drill_points", "holes", "joinery_holes", "connector_holes")):
            hx = x + num(hole, "x", "center_x", "cx")
            hy = y + num(hole, "y", "center_y", "cy")
            dia = max(0.5, num(hole, "diameter", "dia", "d", default=getattr(config, "bit_size", 6)))
            lines.append(f'    <circle class="drill-hole" cx="{hx}" cy="{hy}" r="{dia / 2}" data-name="{hole.get("name", "drill")}"/>')

        for cutout in feature_list(p, ("cutouts", "inside_profiles", "internal_profiles", "internal_cutouts")):
            cx = x + num(cutout, "x", "left")
            cy = y + num(cutout, "y", "bottom", "top")
            cw = num(cutout, "width", "w")
            ch = num(cutout, "height", "h")
            if cw > 0 and ch > 0:
                lines.append(f'    <rect class="inside-cut" x="{cx}" y="{cy}" width="{cw}" height="{ch}" data-name="{cutout.get("name", "inside cut")}"/>')

        for pocket in feature_list(p, ("pockets", "rebates", "trays", "pocket_features", "recesses")):
            px = x + num(pocket, "x", "left")
            py = y + num(pocket, "y", "bottom", "top")
            pw = num(pocket, "width", "w")
            ph = num(pocket, "height", "h")
            if pw > 0 and ph > 0:
                lines.append(f'    <rect class="pocket" x="{px}" y="{py}" width="{pw}" height="{ph}" data-name="{pocket.get("name", "pocket")}"/>')

        lines.append(f'    <text class="part-label" x="{x + w / 2}" y="{y + h / 2}" font-size="{label_size}">{label_text}</text>')
        lines.append('  </g>')

    lines.append('</svg>')
    return "\n".join(lines)

def generate_pdf_html(parts: List[Dict], nesting: NestingResult, params: DesignParams, design_name: str) -> str:
    """Generate HTML reference cutting sheet with visible CNC feature markers."""
    sheet_w, sheet_h = 2400, 1200
    scale = 0.25

    def feature_count(part, keys):
        total = 0
        for key in keys:
            items = part.get(key) or []
            if isinstance(items, dict):
                items = list(items.values())
            if isinstance(items, list):
                total += len([item for item in items if isinstance(item, dict)])
        return total

    drill_total = sum(feature_count(p, ("drill_points", "holes", "joinery_holes", "connector_holes")) for p in parts)
    inside_total = sum(feature_count(p, ("cutouts", "inside_profiles", "internal_profiles", "internal_cutouts")) for p in parts)
    pocket_total = sum(feature_count(p, ("pockets", "rebates", "trays", "pocket_features", "recesses")) for p in parts)

    sheets_parts = {}
    for part in parts:
        sheet_idx = part.get("sheet", 0)
        sheets_parts.setdefault(sheet_idx, []).append(part)

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
        .specs {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0; }}
        .spec-box {{ background: #f5f5f5; padding: 10px; border-radius: 5px; text-align: center; }}
        .spec-box .value {{ font-size: 22px; font-weight: bold; color: #FF3B30; }}
        .spec-box .label {{ font-size: 12px; color: #666; }}
        .sheet {{ margin: 30px 0; page-break-inside: avoid; }}
        .sheet-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
        .sheet-visual {{ border: 2px solid #333; background: #D4A574; position: relative; }}
        .part {{ position: absolute; border: 2px solid #333; background: rgba(255,255,255,0.9); display: flex; align-items: center; justify-content: center; font-size: 10px; text-align: center; }}
        .legend {{ font-size: 12px; margin: 8px 0 14px; }}
        .parts-list table {{ width: 100%; border-collapse: collapse; }}
        .parts-list th, .parts-list td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .parts-list th {{ background: #f5f5f5; }}
        .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>UltimateDesk</h1>
        <h2>{design_name}</h2>
        <p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>

    <div class="disclaimer">
        <strong>IMPORTANT SAFETY DISCLAIMER</strong><br>
        This cutting sheet is a REFERENCE DOCUMENT. Verify dimensions and toolpaths in CAM before cutting.
    </div>

    <div class="specs">
        <div class="spec-box"><div class="value">{params.width}mm</div><div class="label">Width</div></div>
        <div class="spec-box"><div class="value">{params.depth}mm</div><div class="label">Depth</div></div>
        <div class="spec-box"><div class="value">{params.height}mm</div><div class="label">Height</div></div>
        <div class="spec-box"><div class="value">{nesting.sheets_required}</div><div class="label">Sheets Required</div></div>
    </div>

    <div class="specs">
        <div class="spec-box"><div class="value">{drill_total}</div><div class="label">Drill Features</div></div>
        <div class="spec-box"><div class="value">{inside_total}</div><div class="label">Inside Cuts</div></div>
        <div class="spec-box"><div class="value">{pocket_total}</div><div class="label">Pockets/Rebates</div></div>
        <div class="spec-box"><div class="value">{len(parts)}</div><div class="label">Total Parts</div></div>
    </div>

    <div class="legend">
        Legend: black box = outside profile | blue dots = drill holes | red dashed box = inside cutout | orange dashed box = pocket/rebate
    </div>
"""

    for sheet_idx, sheet_parts in sheets_parts.items():
        html += f"""
    <div class="sheet">
        <div class="sheet-title">Sheet {sheet_idx + 1} of {nesting.sheets_required} (2400mm x 1200mm)</div>
        <div class="sheet-visual" style="width: {sheet_w * scale}px; height: {sheet_h * scale}px;">
"""
        colors = ["#FFE4E1", "#E0FFE0", "#E0E0FF", "#FFFFE0", "#FFE0FF", "#E0FFFF"]
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
                <th>Width</th>
                <th>Height</th>
                <th>Sheet</th>
                <th>Rotated</th>
                <th>Drill</th>
                <th>Inside</th>
                <th>Pocket</th>
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
                <td>{feature_count(part, ('drill_points', 'holes', 'joinery_holes', 'connector_holes'))}</td>
                <td>{feature_count(part, ('cutouts', 'inside_profiles', 'internal_profiles', 'internal_cutouts'))}</td>
                <td>{feature_count(part, ('pockets', 'rebates', 'trays', 'pocket_features', 'recesses'))}</td>
            </tr>
"""

    html += """
        </table>
    </div>

    <div class="footer">
        <p><strong>UltimateDesk</strong> - Straight-frame desk build pack reference</p>
        <p>Questions? Email support@ultimatedesk.co.nz | Visit ultimatedesk.co.nz</p>
    </div>
</body>
</html>
"""
    return html

def generate_pdf_bytes(parts: List[Dict], nesting: NestingResult, params: DesignParams, design_name: str) -> bytes:
    """Generate a real PDF cutting sheet using reportlab, including visible drill/cutout/pocket features."""
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    margin = 12 * mm

    def feature_items(part, keys):
        found = []
        for key in keys:
            items = part.get(key) or []
            if isinstance(items, dict):
                items = list(items.values())
            if isinstance(items, list):
                found.extend([item for item in items if isinstance(item, dict)])
        return found

    def feature_count(part, keys):
        return len(feature_items(part, keys))

    def num(source, *names, default=0):
        for name in names:
            if isinstance(source, dict) and source.get(name) is not None:
                try:
                    return float(source.get(name))
                except (TypeError, ValueError):
                    return float(default)
        return float(default)

    drill_total = sum(feature_count(p, ("drill_points", "holes", "joinery_holes", "connector_holes")) for p in parts)
    inside_total = sum(feature_count(p, ("cutouts", "inside_profiles", "internal_profiles", "internal_cutouts")) for p in parts)
    pocket_total = sum(feature_count(p, ("pockets", "rebates", "trays", "pocket_features", "recesses")) for p in parts)

    def draw_header(title: str):
        c.setFillColor(colors.HexColor("#FF3B30"))
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, page_height - margin, "UltimateDesk")
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, page_height - margin - 8 * mm, title)
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(margin, page_height - margin - 13 * mm, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    def draw_disclaimer(top_y: float):
        box_h = 14 * mm
        c.setFillColor(colors.HexColor("#FFF3CD"))
        c.setStrokeColor(colors.HexColor("#FFE69C"))
        c.roundRect(margin, top_y - box_h, page_width - 2 * margin, box_h, 3 * mm, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#7A5A00"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin + 4 * mm, top_y - 5 * mm, "IMPORTANT")
        c.setFillColor(colors.HexColor("#444444"))
        c.setFont("Helvetica", 7)
        c.drawString(margin + 28 * mm, top_y - 5 * mm, "Reference file only. Verify all dimensions and CAM toolpaths before cutting.")

    def draw_specs(top_y: float):
        box_w = (page_width - 2 * margin - 9 * mm) / 4
        box_h = 16 * mm
        specs = [
            (f"{params.width}mm", "Width"),
            (f"{params.depth}mm", "Depth"),
            (f"{params.height}mm", "Height"),
            (f"{nesting.sheets_required}", "Sheets"),
            (f"{drill_total}", "Drill features"),
            (f"{inside_total}", "Inside cuts"),
            (f"{pocket_total}", "Pockets/rebates"),
            (f"{len(parts)}", "Parts"),
        ]
        x = margin
        y = top_y
        for i, (value, label) in enumerate(specs):
            if i == 4:
                x = margin
                y = top_y - box_h - 4 * mm
            c.setFillColor(colors.HexColor("#F5F5F5"))
            c.setStrokeColor(colors.HexColor("#DDDDDD"))
            c.roundRect(x, y - box_h, box_w, box_h, 2 * mm, fill=1, stroke=1)
            c.setFillColor(colors.HexColor("#FF3B30"))
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(x + box_w / 2, y - 6 * mm, value)
            c.setFillColor(colors.HexColor("#666666"))
            c.setFont("Helvetica", 7)
            c.drawCentredString(x + box_w / 2, y - 11 * mm, label)
            x += box_w + 3 * mm

    draw_header(design_name)
    draw_disclaimer(page_height - margin - 18 * mm)
    draw_specs(page_height - margin - 38 * mm)

    sheet_w, sheet_h = 2400, 1200
    sheets_parts = {}
    for part in parts:
        sheet_idx = part.get("sheet", 0)
        sheets_parts.setdefault(sheet_idx, []).append(part)

    colors_cycle = [
        colors.HexColor("#FDE2E4"),
        colors.HexColor("#E2F0D9"),
        colors.HexColor("#D9EAF7"),
        colors.HexColor("#FFF2CC"),
        colors.HexColor("#EADCF8"),
        colors.HexColor("#D9F2E6"),
    ]

    for sheet_idx, sheet_parts in sorted(sheets_parts.items()):
        c.showPage()
        draw_header(f"{design_name} - Sheet {sheet_idx + 1} of {nesting.sheets_required}")
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.black)
        c.drawString(margin, page_height - margin - 10 * mm, "2400mm x 1200mm sheet layout | black=part, blue=drill, red=inside cut, orange=pocket")

        draw_x = margin
        draw_y = 45 * mm
        draw_w = page_width - 2 * margin
        draw_h = page_height - 70 * mm
        scale = min(draw_w / sheet_w, draw_h / sheet_h)

        c.setFillColor(colors.HexColor("#D4A574"))
        c.setStrokeColor(colors.black)
        c.rect(draw_x, draw_y, sheet_w * scale, sheet_h * scale, fill=1, stroke=1)

        for i, part in enumerate(sheet_parts):
            px = draw_x + part.get("x", 0) * scale
            py = draw_y + (sheet_h - part.get("y", 0) - part["height"]) * scale
            pw = max(3, part["width"] * scale)
            ph = max(3, part["height"] * scale)

            c.setFillColor(colors_cycle[i % len(colors_cycle)])
            c.setStrokeColor(colors.HexColor("#333333"))
            c.rect(px, py, pw, ph, fill=1, stroke=1)

            # Cutouts first so drill circles remain visible.
            for cutout in feature_items(part, ("cutouts", "inside_profiles", "internal_profiles", "internal_cutouts")):
                fx = num(cutout, "x", "left")
                fy = num(cutout, "y", "bottom", "top")
                fw = num(cutout, "width", "w")
                fh = num(cutout, "height", "h")
                if fw > 0 and fh > 0:
                    c.setFillColor(colors.HexColor("#FFE5E5"))
                    c.setStrokeColor(colors.HexColor("#CC0000"))
                    c.rect(px + fx * scale, py + (part["height"] - fy - fh) * scale, fw * scale, fh * scale, fill=1, stroke=1)

            for pocket in feature_items(part, ("pockets", "rebates", "trays", "pocket_features", "recesses")):
                fx = num(pocket, "x", "left")
                fy = num(pocket, "y", "bottom", "top")
                fw = num(pocket, "width", "w")
                fh = num(pocket, "height", "h")
                if fw > 0 and fh > 0:
                    c.setFillColor(colors.HexColor("#FFE8BF"))
                    c.setStrokeColor(colors.HexColor("#CC7A00"))
                    c.rect(px + fx * scale, py + (part["height"] - fy - fh) * scale, fw * scale, fh * scale, fill=1, stroke=1)

            for hole in feature_items(part, ("drill_points", "holes", "joinery_holes", "connector_holes")):
                hx = num(hole, "x", "center_x", "cx")
                hy = num(hole, "y", "center_y", "cy")
                dia = max(1, num(hole, "diameter", "dia", "d", default=5))
                c.setFillColor(colors.white)
                c.setStrokeColor(colors.HexColor("#005BFF"))
                c.circle(px + hx * scale, py + (part["height"] - hy) * scale, max(1.2, dia * scale / 2), fill=1, stroke=1)

            c.setFillColor(colors.black)
            c.setFont("Helvetica", 6)
            label = f"{part['name']} ({part['width']}x{part['height']})"
            c.drawCentredString(px + pw / 2, py + ph / 2, label[:48])

    c.showPage()
    draw_header(f"{design_name} - Parts List")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.black)

    columns = [
        ("#", 9 * mm),
        ("Part Name", 58 * mm),
        ("W", 18 * mm),
        ("H", 18 * mm),
        ("Sheet", 16 * mm),
        ("Rot", 14 * mm),
        ("Drill", 16 * mm),
        ("Inside", 16 * mm),
        ("Pocket", 17 * mm),
    ]
    x_positions = [margin]
    for _, width in columns[:-1]:
        x_positions.append(x_positions[-1] + width)

    y = page_height - margin - 16 * mm
    row_h = 8 * mm

    def draw_row(values, bold=False):
        nonlocal y
        if y < 20 * mm:
            c.showPage()
            draw_header(f"{design_name} - Parts List")
            y = page_height - margin - 16 * mm
        c.setFillColor(colors.HexColor("#F5F5F5") if bold else colors.white)
        c.setStrokeColor(colors.HexColor("#DDDDDD"))
        c.rect(margin, y - row_h + 1, sum(width for _, width in columns), row_h, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 7)
        for idx, value in enumerate(values):
            c.drawString(x_positions[idx] + 1 * mm, y - 5.5 * mm, str(value)[:34])
        y -= row_h

    draw_row([label for label, _ in columns], bold=True)
    for i, part in enumerate(parts, start=1):
        draw_row([
            i,
            part["name"],
            part["width"],
            part["height"],
            part.get("sheet", 0) + 1,
            "Y" if part.get("rotated") else "N",
            feature_count(part, ("drill_points", "holes", "joinery_holes", "connector_holes")),
            feature_count(part, ("cutouts", "inside_profiles", "internal_profiles", "internal_cutouts")),
            feature_count(part, ("pockets", "rebates", "trays", "pocket_features", "recesses")),
        ])

    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def generate_review_drawing_pdf_bytes(params: DesignParams, design_name: str = "UltimateDesk Design") -> bytes:
    """Generate customer/manufacturer design review drawings before CNC export."""
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    margin = 12 * mm

    width = float(params.width)
    depth = float(params.depth)
    height = float(params.height)
    thickness = float(params.material_thickness)
    leg_size = max(44, int(round(thickness * 2.4)))
    leg_inset_x = max(70, int(round(width * 0.08)))
    leg_inset_y = max(55, int(round(depth * 0.08)))
    clear_span_x = max(300, width - ((leg_inset_x + leg_size) * 2))
    clear_span_y = max(220, depth - ((leg_inset_y + leg_size) * 2))

    parts = calculate_desk_parts(params)
    nesting = simple_nesting(parts, 2400, 1200)

    def feature_items(part, keys):
        found = []
        for key in keys:
            items = part.get(key) or []
            if isinstance(items, dict):
                items = list(items.values())
            if isinstance(items, list):
                found.extend([item for item in items if isinstance(item, dict)])
        return found

    drill_total = sum(len(feature_items(p, ("drill_points", "holes", "joinery_holes", "connector_holes"))) for p in nesting.parts)
    inside_total = sum(len(feature_items(p, ("cutouts", "inside_profiles", "internal_profiles", "internal_cutouts"))) for p in nesting.parts)
    pocket_total = sum(len(feature_items(p, ("pockets", "rebates", "trays", "pocket_features", "recesses"))) for p in nesting.parts)

    def draw_header(title: str, subtitle: str = ""):
        c.setFillColor(colors.HexColor("#FF3B30"))
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, page_height - margin, "UltimateDesk")
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(margin, page_height - margin - 8 * mm, title)
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(margin, page_height - margin - 13 * mm, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        if subtitle:
            c.drawRightString(page_width - margin, page_height - margin - 8 * mm, subtitle)

    def draw_note_box(y_top: float, text: str):
        box_h = 17 * mm
        c.setFillColor(colors.HexColor("#FFF3CD"))
        c.setStrokeColor(colors.HexColor("#E0B000"))
        c.roundRect(margin, y_top - box_h, page_width - 2 * margin, box_h, 3 * mm, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#5A4400"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin + 4 * mm, y_top - 5 * mm, "REVIEW NOTE")
        c.setFont("Helvetica", 7)
        c.drawString(margin + 28 * mm, y_top - 5 * mm, text[:160])
        c.drawString(margin + 28 * mm, y_top - 10 * mm, "Confirm dimensions, hardware, material thickness, edge details, cable positions, and CNC settings before manufacture.")

    def dim_line(x1, y1, x2, y2, label, offset=0):
        c.setStrokeColor(colors.HexColor("#555555"))
        c.setFillColor(colors.HexColor("#222222"))
        c.setLineWidth(0.6)
        c.line(x1, y1, x2, y2)
        tick = 2.5 * mm
        c.line(x1, y1 - tick, x1, y1 + tick)
        c.line(x2, y2 - tick, x2, y2 + tick)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString((x1 + x2) / 2, (y1 + y2) / 2 + offset, label)

    def draw_part_rect(x, y, w, h, label, fill="#F8F8F8", stroke="#111111"):
        c.setFillColor(colors.HexColor(fill))
        c.setStrokeColor(colors.HexColor(stroke))
        c.setLineWidth(1.0)
        c.rect(x, y, w, h, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 7)
        c.drawCentredString(x + w / 2, y + h / 2, label[:48])

    def draw_plan_page():
        draw_header(f"{design_name} - Plan / Top View", "Design Review Drawings")
        draw_note_box(page_height - margin - 18 * mm, "Plan view is for design approval and checking only. CNC files remain separate manufacturing outputs.")

        draw_x = margin + 18 * mm
        draw_y = margin + 26 * mm
        draw_w = page_width - 2 * margin - 36 * mm
        draw_h = page_height - 2 * margin - 80 * mm
        scale = min(draw_w / width, draw_h / depth)
        desk_w = width * scale
        desk_h = depth * scale
        x0 = draw_x + (draw_w - desk_w) / 2
        y0 = draw_y + (draw_h - desk_h) / 2

        draw_part_rect(x0, y0, desk_w, desk_h, "Desktop top", "#FFFFFF")

        # Legs
        leg_w = leg_size * scale
        leg_h = leg_size * scale
        leg_positions = [
            (leg_inset_x, leg_inset_y, "FL"),
            (width - leg_inset_x - leg_size, leg_inset_y, "FR"),
            (leg_inset_x, depth - leg_inset_y - leg_size, "RL"),
            (width - leg_inset_x - leg_size, depth - leg_inset_y - leg_size, "RR"),
        ]
        for lx, ly, label in leg_positions:
            draw_part_rect(x0 + lx * scale, y0 + ly * scale, leg_w, leg_h, label, "#E7F0FF", "#005BFF")

        # Cable tray / mixer / VESA indicators
        if params.has_cable_management:
            tray_w = max(500, min(width - (leg_inset_x * 2) - 120, int(width * 0.60)))
            tray_h = 85
            tx = x0 + (width - tray_w) / 2 * scale
            ty = y0 + (depth - 130) * scale
            draw_part_rect(tx, ty, tray_w * scale, tray_h * scale, "Cable tray zone", "#E8FFF0", "#0B7A35")

        if params.has_mixer_tray:
            mixer_w = max(280, min(int(params.mixer_tray_width or 520), clear_span_x))
            mx = x0 + (width - mixer_w) / 2 * scale
            my = y0 + 95 * scale
            draw_part_rect(mx, my, mixer_w * scale, 170 * scale, "Mixer tray / rebate zone", "#FFF0D8", "#CC7A00")

        if params.has_vesa_mount:
            vx = x0 + (width / 2) * scale
            vy = y0 + (depth - 145) * scale
            c.setStrokeColor(colors.HexColor("#7A2DCC"))
            c.setFillColor(colors.HexColor("#F1E6FF"))
            c.circle(vx, vy, 10 * mm, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 7)
            c.drawCentredString(vx, vy - 2, "VESA")

        dim_line(x0, y0 - 10 * mm, x0 + desk_w, y0 - 10 * mm, f"Overall width {int(width)}mm", offset=3 * mm)
        dim_line(x0 - 10 * mm, y0, x0 - 10 * mm, y0 + desk_h, f"Depth {int(depth)}mm", offset=3 * mm)

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#333333"))
        c.drawString(margin, margin + 8 * mm, f"Leg inset: approx {leg_inset_x}mm x {leg_inset_y}mm | Material: {int(thickness)}mm | Sheets: {nesting.sheets_required}")

    def draw_front_elevation():
        c.showPage()
        draw_header(f"{design_name} - Front Elevation", "Design Review Drawings")
        draw_note_box(page_height - margin - 18 * mm, "Elevation confirms overall height, leg/rail proportions, and visual frame layout.")

        draw_x = margin + 18 * mm
        draw_y = margin + 30 * mm
        draw_w = page_width - 2 * margin - 36 * mm
        draw_h = page_height - 2 * margin - 82 * mm
        scale = min(draw_w / width, draw_h / height)
        w = width * scale
        h = height * scale
        x0 = draw_x + (draw_w - w) / 2
        y0 = draw_y

        # desktop
        draw_part_rect(x0, y0 + (height - thickness) * scale, w, thickness * scale, "Desktop", "#FFFFFF")
        # legs
        leg_w = leg_size * scale
        leg_h = (height - thickness) * scale
        draw_part_rect(x0 + leg_inset_x * scale, y0, leg_w, leg_h, "Leg", "#E7F0FF", "#005BFF")
        draw_part_rect(x0 + (width - leg_inset_x - leg_size) * scale, y0, leg_w, leg_h, "Leg", "#E7F0FF", "#005BFF")
        # rails/modesty
        draw_part_rect(x0 + (leg_inset_x + leg_size) * scale, y0 + (height - thickness - 65) * scale, clear_span_x * scale, 42 * scale, "Rear upper rail", "#F4F4F4")
        draw_part_rect(x0 + (leg_inset_x + leg_size) * scale, y0 + 110 * scale, clear_span_x * scale, 30 * scale, "Front lower rail", "#F4F4F4")

        dim_line(x0, y0 - 10 * mm, x0 + w, y0 - 10 * mm, f"{int(width)}mm", offset=3 * mm)
        dim_line(x0 - 10 * mm, y0, x0 - 10 * mm, y0 + h, f"{int(height)}mm high", offset=3 * mm)
        c.setFont("Helvetica", 8)
        c.drawString(margin, margin + 8 * mm, f"Clear span between leg frames: approx {int(clear_span_x)}mm")

    def draw_side_elevation():
        c.showPage()
        draw_header(f"{design_name} - Side Elevation", "Design Review Drawings")
        draw_note_box(page_height - margin - 18 * mm, "Side elevation checks desk depth, side rail position, and leg proportions.")

        draw_x = margin + 30 * mm
        draw_y = margin + 30 * mm
        draw_w = page_width - 2 * margin - 60 * mm
        draw_h = page_height - 2 * margin - 82 * mm
        scale = min(draw_w / depth, draw_h / height)
        w = depth * scale
        h = height * scale
        x0 = draw_x + (draw_w - w) / 2
        y0 = draw_y

        draw_part_rect(x0, y0 + (height - thickness) * scale, w, thickness * scale, "Desktop depth", "#FFFFFF")
        leg_w = leg_size * scale
        leg_h = (height - thickness) * scale
        draw_part_rect(x0 + leg_inset_y * scale, y0, leg_w, leg_h, "Front leg", "#E7F0FF", "#005BFF")
        draw_part_rect(x0 + (depth - leg_inset_y - leg_size) * scale, y0, leg_w, leg_h, "Rear leg", "#E7F0FF", "#005BFF")
        draw_part_rect(x0 + (leg_inset_y + leg_size) * scale, y0 + 120 * scale, clear_span_y * scale, 30 * scale, "Side rail", "#F4F4F4")

        dim_line(x0, y0 - 10 * mm, x0 + w, y0 - 10 * mm, f"{int(depth)}mm depth", offset=3 * mm)
        dim_line(x0 - 10 * mm, y0, x0 - 10 * mm, y0 + h, f"{int(height)}mm high", offset=3 * mm)

    def draw_isometric_assembly_page():
        c.showPage()
        draw_header(f"{design_name} - Isometric Assembly View", "Design Review Drawings")
        draw_note_box(page_height - margin - 18 * mm, "Isometric view is for assembly review and design understanding. Check exact manufacture from CNC exports and schedules.")

        draw_area_x = margin + 8 * mm
        draw_area_y = margin + 22 * mm
        draw_area_w = page_width - 2 * margin - 16 * mm
        draw_area_h = page_height - 2 * margin - 82 * mm

        # Conservative scale so wide/deep desks fit the page.
        iso_extent_w = (width + depth) * 0.72
        iso_extent_h = ((width + depth) * 0.30) + height * 0.72
        scale = min(draw_area_w / max(1, iso_extent_w), draw_area_h / max(1, iso_extent_h))

        origin_x = page_width / 2
        origin_y = draw_area_y + 18 * mm

        def iso_project(x, y, z):
            px = origin_x + (x - y) * 0.72 * scale
            py = origin_y + (x + y) * 0.30 * scale + z * 0.72 * scale
            return px, py

        def poly(points, fill, stroke="#333333", line_width=0.7):
            c.setFillColor(colors.HexColor(fill))
            c.setStrokeColor(colors.HexColor(stroke))
            c.setLineWidth(line_width)
            if not points:
                return

            path_obj = c.beginPath()
            first_x, first_y = points[0]
            path_obj.moveTo(first_x, first_y)
            for point_x, point_y in points[1:]:
                path_obj.lineTo(point_x, point_y)
            path_obj.close()
            c.drawPath(path_obj, fill=1, stroke=1)

        def draw_iso_box(x, y, z, w, d, h, label="", fill_top="#FFFFFF", fill_left="#EFEFEF", fill_right="#DDDDDD", stroke="#333333"):
            p000 = iso_project(x, y, z)
            p100 = iso_project(x + w, y, z)
            p110 = iso_project(x + w, y + d, z)
            p010 = iso_project(x, y + d, z)

            p001 = iso_project(x, y, z + h)
            p101 = iso_project(x + w, y, z + h)
            p111 = iso_project(x + w, y + d, z + h)
            p011 = iso_project(x, y + d, z + h)

            # Visible faces: front/left, right, top.
            poly([p000, p100, p101, p001], fill_left, stroke)
            poly([p100, p110, p111, p101], fill_right, stroke)
            poly([p001, p101, p111, p011], fill_top, stroke)

            if label:
                lx, ly = iso_project(x + w / 2, y + d / 2, z + h + 10)
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 7)
                c.drawCentredString(lx, ly, label[:46])

        # Main assembly geometry.
        desktop_z = height - thickness
        draw_iso_box(
            0, 0, desktop_z,
            width, depth, thickness,
            "Desktop",
            fill_top="#FFFFFF",
            fill_left="#F3F3F3",
            fill_right="#E4E4E4",
            stroke="#111111",
        )

        # Legs.
        leg_positions = [
            (leg_inset_x, leg_inset_y, "FL"),
            (width - leg_inset_x - leg_size, leg_inset_y, "FR"),
            (leg_inset_x, depth - leg_inset_y - leg_size, "RL"),
            (width - leg_inset_x - leg_size, depth - leg_inset_y - leg_size, "RR"),
        ]
        for lx, ly, label in leg_positions:
            draw_iso_box(
                lx, ly, 0,
                leg_size, leg_size, desktop_z,
                f"Leg {label}",
                fill_top="#DDEBFF",
                fill_left="#CFE2FF",
                fill_right="#BBD5FF",
                stroke="#005BFF",
            )

        # Rear upper rail and front/lower rail zones.
        rail_x = leg_inset_x + leg_size
        rear_y = depth - leg_inset_y - leg_size
        front_y = leg_inset_y
        draw_iso_box(
            rail_x, rear_y, max(0, desktop_z - 65),
            clear_span_x, 30, 42,
            "Rear upper rail",
            fill_top="#F7F7F7",
            fill_left="#E8E8E8",
            fill_right="#DADADA",
            stroke="#555555",
        )
        draw_iso_box(
            rail_x, front_y, 110,
            clear_span_x, 30, 30,
            "Front lower rail",
            fill_top="#F7F7F7",
            fill_left="#E8E8E8",
            fill_right="#DADADA",
            stroke="#555555",
        )

        # Side rails.
        side_span_y = clear_span_y
        left_x = leg_inset_x
        right_x = width - leg_inset_x - leg_size
        side_y = leg_inset_y + leg_size
        draw_iso_box(
            left_x, side_y, 120,
            30, side_span_y, 30,
            "Left side rail",
            fill_top="#F7F7F7",
            fill_left="#E8E8E8",
            fill_right="#DADADA",
            stroke="#555555",
        )
        draw_iso_box(
            right_x, side_y, 120,
            30, side_span_y, 30,
            "Right side rail",
            fill_top="#F7F7F7",
            fill_left="#E8E8E8",
            fill_right="#DADADA",
            stroke="#555555",
        )

        if params.has_cable_management:
            tray_w = max(500, min(width - (leg_inset_x * 2) - 120, int(width * 0.60)))
            tray_x = (width - tray_w) / 2
            tray_y = depth - 150
            draw_iso_box(
                tray_x, tray_y, max(90, desktop_z - 170),
                tray_w, 85, 40,
                "Cable tray",
                fill_top="#E8FFF0",
                fill_left="#D8F5E1",
                fill_right="#C5EACF",
                stroke="#0B7A35",
            )

        if params.has_mixer_tray:
            mixer_w = max(280, min(int(params.mixer_tray_width or 520), clear_span_x))
            mixer_x = (width - mixer_w) / 2
            draw_iso_box(
                mixer_x, 95, max(80, desktop_z - 160),
                mixer_w, 170, 35,
                "Mixer tray",
                fill_top="#FFF0D8",
                fill_left="#FFE5BD",
                fill_right="#FFD49A",
                stroke="#CC7A00",
            )

        if params.has_headset_hook:
            hook_x = width - leg_inset_x - 90
            hook_y = 30
            draw_iso_box(
                hook_x, hook_y, desktop_z - 80,
                90, 30, 22,
                "Headset hook",
                fill_top="#F1E6FF",
                fill_left="#E5D2FF",
                fill_right="#D3B6FF",
                stroke="#7A2DCC",
            )

        if params.has_vesa_mount:
            vesa_x = width / 2 - 90
            vesa_y = depth - 210
            draw_iso_box(
                vesa_x, vesa_y, desktop_z + thickness,
                180, 100, 120,
                "VESA mount zone",
                fill_top="#F1E6FF",
                fill_left="#E5D2FF",
                fill_right="#D3B6FF",
                stroke="#7A2DCC",
            )

        # Assembly notes / legend.
        legend_x = margin
        legend_y = margin + 5 * mm
        c.setFillColor(colors.HexColor("#333333"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(legend_x, legend_y + 12 * mm, "Assembly review notes")
        c.setFont("Helvetica", 7)
        notes = [
            f"Overall: {int(width)}W x {int(depth)}D x {int(height)}H mm",
            f"Material: {int(thickness)}mm, sheets required: {nesting.sheets_required}",
            f"Parts: {len(nesting.parts)}, drill features: {drill_total}, inside cuts: {inside_total}, pockets/rebates: {pocket_total}",
            "View is schematic: verify final parts, holes, rebates, and machine file in CNC/CAM outputs.",
        ]
        for idx, note in enumerate(notes):
            c.drawString(legend_x, legend_y + (7 - idx) * mm, f"- {note}")

    def draw_assembly_details_page():
        c.showPage()
        draw_header(f"{design_name} - Assembly Details", "Manufacturing Instructions")
        draw_note_box(page_height - margin - 18 * mm, "Assembly details are manufacturing instructions only. CNC geometry remains controlled by DXF/NC exports.")

        y = page_height - margin - 42 * mm

        def section_title(title):
            nonlocal y
            c.setFillColor(colors.HexColor("#111111"))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin, y, title)
            y -= 7 * mm

        def wrapped_line(text, indent=0, size=7.5, step=4.8 * mm):
            nonlocal y
            if y < 22 * mm:
                c.showPage()
                draw_header(f"{design_name} - Assembly Details", "continued")
                y = page_height - margin - 20 * mm

            c.setFillColor(colors.HexColor("#333333"))
            c.setFont("Helvetica", size)

            max_chars = 138 - indent
            remaining = str(text)
            first = True
            while remaining:
                chunk = remaining[:max_chars]
                if len(remaining) > max_chars:
                    split_at = max(chunk.rfind(" "), 60)
                    chunk = remaining[:split_at]
                    remaining = remaining[split_at:].strip()
                else:
                    remaining = ""

                prefix = "" if first else "  "
                c.drawString(margin + indent * mm, y, prefix + chunk)
                y -= step
                first = False

        def draw_table(headers, rows, col_widths):
            nonlocal y
            row_h = 7 * mm
            total_w = sum(col_widths)

            def draw_one_row(values, bold=False, fill="#FFFFFF"):
                nonlocal y
                if y < 25 * mm:
                    c.showPage()
                    draw_header(f"{design_name} - Assembly Details", "continued")
                    y = page_height - margin - 20 * mm

                c.setFillColor(colors.HexColor(fill))
                c.setStrokeColor(colors.HexColor("#DDDDDD"))
                c.rect(margin, y - row_h + 1, total_w, row_h, fill=1, stroke=1)

                c.setFillColor(colors.black)
                c.setFont("Helvetica-Bold" if bold else "Helvetica", 6.6)
                x = margin
                for value, col_w in zip(values, col_widths):
                    c.drawString(x + 1.3 * mm, y - 4.9 * mm, str(value)[:42])
                    x += col_w
                y -= row_h

            draw_one_row(headers, bold=True, fill="#F3F3F3")
            for row in rows:
                draw_one_row(row)

            y -= 4 * mm

        section_title("Part-to-part connection map")
        connection_rows = [
            ("Desktop Top", "Rear Upper Rail", "Underside rear fixing line", "pilot holes / screws", "Check cable cutout clearance first"),
            ("Desktop Top", "Front Lower Rail", "Underside front fixing line", "pilot holes / screws", "Keep rail square before fixing"),
            ("Rear Upper Rail", "Leg Post FL / FR / RL / RR", "Rail ends into leg posts", "screws / dowels / confirm hardware", "Pre-drill and clamp square"),
            ("Front Lower Rail", "Leg Post FL / FR", "Front lower rail to front legs", "screws / dowels / confirm hardware", "Do not rack frame"),
            ("Side Rails", "Front and rear leg posts", "Left/right frame sides", "screws / dowels / confirm hardware", "Confirm handed parts"),
            ("Back Modesty Panel", "Rear rail / rear leg zone", "Rear face", "screws / pilot holes", "Fit after main frame is square"),
        ]

        if params.has_cable_management:
            connection_rows.extend([
                ("Cable Tray Base", "Cable Tray Front / Back", "Tray long edges", "small screws / pilot holes", "Assemble tray before final mounting"),
                ("Cable Tray Assembly", "Desktop underside / rear rail zone", "Rear underside", "pilot holes / screws", "Keep clear of rear cable pass-through"),
            ])

        if params.has_mixer_tray:
            connection_rows.extend([
                ("Mixer Tray", "Mixer Tray Supports", "Left/right support cheeks", "pilot holes / screws", "Check mixer width and rebate depth"),
                ("Mixer Tray Assembly", "Desktop underside", "Front underside zone", "pilot holes / screws", "Confirm slide/clearance before fixing"),
            ])

        if params.has_headset_hook:
            connection_rows.append(("Headset Hook", "Desktop / side underside", "Chosen side", "pilot holes / screws", "Confirm user handedness"))

        if params.has_vesa_mount:
            connection_rows.append(("VESA Mount Plate", "Desktop / rear zone", "Rear top/under-top zone", "bolt/screw pattern", "Confirm monitor hardware and load"))

        draw_table(
            ["Part A", "Part B", "Joint location", "Fixing type", "Manufacturing note"],
            connection_rows,
            [38 * mm, 42 * mm, 38 * mm, 34 * mm, 92 * mm],
        )

        section_title("Recommended assembly order")
        steps = [
            "1. Identify all parts from the parts schedule and keep each sheet group together.",
            "2. Lightly sand/clean CNC tabs and edges. Do not enlarge holes until hardware is confirmed.",
            "3. Build the left and right leg frames first using leg posts and side/front/rear rails.",
            "4. Dry-fit the rear upper rail, front lower rail, and side rails. Clamp square before permanent fixing.",
            "5. Fit the desktop to the frame. Align rear edge, leg inset, cable openings, and rail fixing lines.",
            "6. Fit the back modesty panel after the main frame is square.",
            "7. Assemble and install the cable tray if selected.",
            "8. Assemble and install mixer tray / VESA / headset / accessory parts if selected.",
            "9. Check final level, squareness, cable access, hardware tightness, and edge finish.",
        ]
        for step in steps:
            wrapped_line(step, indent=4)

    def draw_hardware_schedule_page():
        c.showPage()
        draw_header(f"{design_name} - Hardware / Fastener Schedule", "Manufacturing Instructions")
        draw_note_box(page_height - margin - 18 * mm, "Hardware schedule is indicative. Confirm final screw, bolt, dowel, insert, and load requirements before manufacture.")

        y = page_height - margin - 42 * mm

        def draw_table(headers, rows, col_widths):
            nonlocal y
            row_h = 7 * mm
            total_w = sum(col_widths)

            def draw_one_row(values, bold=False, fill="#FFFFFF"):
                nonlocal y
                if y < 25 * mm:
                    c.showPage()
                    draw_header(f"{design_name} - Hardware / Fastener Schedule", "continued")
                    y = page_height - margin - 20 * mm

                c.setFillColor(colors.HexColor(fill))
                c.setStrokeColor(colors.HexColor("#DDDDDD"))
                c.rect(margin, y - row_h + 1, total_w, row_h, fill=1, stroke=1)

                c.setFillColor(colors.black)
                c.setFont("Helvetica-Bold" if bold else "Helvetica", 6.7)
                x = margin
                for value, col_w in zip(values, col_widths):
                    c.drawString(x + 1.2 * mm, y - 4.9 * mm, str(value)[:48])
                    x += col_w
                y -= row_h

            draw_one_row(headers, bold=True, fill="#F3F3F3")
            for row in rows:
                draw_one_row(row)

            y -= 5 * mm

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, "Indicative hardware groups")
        y -= 8 * mm

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, "Calculated hardware quantities")
        y -= 7 * mm

        c.setFillColor(colors.HexColor("#444444"))
        c.setFont("Helvetica", 7)
        c.drawString(margin + 4 * mm, y, "Quantities are calculated from current drilled feature groups where available. Any zero/TBC rows must be manually confirmed.")
        y -= 6 * mm

        drill_keys = ("drill_points", "holes", "joinery_holes", "connector_holes")

        def count_drills_for_terms(include_terms, exclude_terms=()):
            total = 0
            matched_parts = 0
            for part in nesting.parts:
                part_name = str(part.get("name", "")).lower()
                if include_terms and not any(term in part_name for term in include_terms):
                    continue
                if exclude_terms and any(term in part_name for term in exclude_terms):
                    continue
                part_count = len(feature_items(part, drill_keys))
                if part_count:
                    matched_parts += 1
                total += part_count
            return total, matched_parts

        def qty_text(count, matched_parts, fallback="TBC - confirm from drill schedule"):
            if count > 0:
                part_word = "part" if matched_parts == 1 else "parts"
                return f"{count} drilled fixing point{'s' if count != 1 else ''} across {matched_parts} {part_word}"
            return fallback

        desktop_count, desktop_parts = count_drills_for_terms(("desktop", "top"), ("vesa", "mixer", "tray", "hook"))
        rail_leg_count, rail_leg_parts = count_drills_for_terms(("rail", "leg post", "leg", "side rail", "rear upper", "front lower"), ("cable tray", "mixer", "vesa", "hook"))
        modesty_count, modesty_parts = count_drills_for_terms(("modesty", "back panel", "back modesty", "rear panel"), ())
        cable_count, cable_parts = count_drills_for_terms(("cable tray", "cable"), ())
        mixer_count, mixer_parts = count_drills_for_terms(("mixer",), ())
        headset_count, headset_parts = count_drills_for_terms(("headset", "hook"), ())
        vesa_count, vesa_parts = count_drills_for_terms(("vesa", "monitor"), ())
        all_count, all_parts = count_drills_for_terms((), ())

        hardware_rows = [
            (
                "Desktop to rails/frame",
                "Wood screws / confirm spec",
                qty_text(desktop_count, desktop_parts),
                "Pilot drill only; avoid breakthrough through desktop",
                "Calculated" if desktop_count else "Manual check",
            ),
            (
                "Rail to leg post joints",
                "Screws/dowels/cam/confirm hardware",
                qty_text(rail_leg_count, rail_leg_parts),
                "Clamp square; confirm edge distance",
                "Calculated" if rail_leg_count else "Manual check",
            ),
            (
                "Back modesty panel",
                "Wood screws / confirm spec",
                qty_text(modesty_count, modesty_parts),
                "Install after frame is square",
                "Calculated" if modesty_count else "Manual check",
            ),
            (
                "Cable tray",
                "Small screws / confirm spec",
                qty_text(cable_count, cable_parts),
                "Keep clear of cable pass-through and grommets",
                "Calculated" if cable_count else "Manual check",
            ),
        ]

        if params.has_mixer_tray:
            hardware_rows.append((
                "Mixer tray",
                "Screws / inserts / confirm spec",
                qty_text(mixer_count, mixer_parts),
                "Check rebate depth and mixer clearance",
                "Calculated" if mixer_count else "Manual check",
            ))

        if params.has_headset_hook:
            hardware_rows.append((
                "Headset hook",
                "Small screws / confirm spec",
                qty_text(headset_count, headset_parts),
                "Confirm handed side before drilling",
                "Calculated" if headset_count else "Manual check",
            ))

        if params.has_vesa_mount:
            hardware_rows.append((
                "VESA mount",
                "Bolts/inserts/load-rated hardware",
                qty_text(vesa_count, vesa_parts),
                "Must be verified for monitor load",
                "Calculated" if vesa_count else "Manual check",
            ))

        hardware_rows.append((
            "Total drilled fixing features",
            "All drill groups",
            qty_text(all_count, all_parts, "No drilled feature groups found"),
            "Cross-check with CNC drill audit before manufacture",
            "Audit",
        ))

        draw_table(
            ["Connection", "Indicative hardware", "Calculated count / basis", "Critical check", "Status"],
            hardware_rows,
            [40 * mm, 44 * mm, 58 * mm, 76 * mm, 26 * mm],
        )

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, "Manufacturing checks before cutting / assembly")
        y -= 7 * mm

        checks = [
            "Confirm material thickness matches the quote, CNC config, and actual board thickness.",
            "Confirm cutter diameter, compensation strategy, and hole diameters before machining.",
            "Confirm edge orientation: front/back/left/right marks should be transferred to parts after cutting.",
            "Confirm all accessory positions: cable tray, mixer tray, headset hook, VESA, GPU tray, pedal platform.",
            "Confirm all tabs are removed and edges dressed before final assembly.",
            "Do not rely on this schedule as structural certification. It is a manufacturing review aid.",
        ]

        c.setFont("Helvetica", 7.5)
        for item in checks:
            if y < 25 * mm:
                c.showPage()
                draw_header(f"{design_name} - Hardware / Fastener Schedule", "continued")
                y = page_height - margin - 20 * mm
            c.drawString(margin + 4 * mm, y, f"- {item}")
            y -= 5 * mm

    def draw_part_marking_page():
        c.showPage()
        draw_header(f"{design_name} - Part Marking / Orientation", "Manufacturing Instructions")
        draw_note_box(page_height - margin - 18 * mm, "Mark each part after CNC cutting. Orientation marks help avoid flipped, reversed, or handed assembly mistakes.")

        y = page_height - margin - 42 * mm

        def infer_orientation(part_name):
            name = str(part_name).lower()

            front_edge = "Mark visible/front edge where applicable"
            back_edge = "Mark rear/back edge where applicable"
            left_edge = "Mark left edge from user position"
            right_edge = "Mark right edge from user position"
            note = "Confirm orientation before drilling or final fixing"

            if "desktop" in name or "top" in name:
                front_edge = "Long front user edge"
                back_edge = "Rear cable/accessory edge"
                left_edge = "Left side from seated/user position"
                right_edge = "Right side from seated/user position"
                note = "Transfer FRONT/BACK/LEFT/RIGHT marks before removing from sheet"

            elif "rear" in name or "back" in name:
                front_edge = "Face toward user/front"
                back_edge = "Rear/back face"
                left_edge = "Left end to left rear leg/frame"
                right_edge = "Right end to right rear leg/frame"
                note = "Keep rear-facing parts grouped together"

            elif "front" in name:
                front_edge = "Visible/front face"
                back_edge = "Inside frame face"
                left_edge = "Left end from user position"
                right_edge = "Right end from user position"
                note = "Front rail must not be reversed"

            elif "left" in name:
                front_edge = "Front end"
                back_edge = "Rear end"
                left_edge = "Outside left face"
                right_edge = "Inside face"
                note = "Handed left-side part"

            elif "right" in name:
                front_edge = "Front end"
                back_edge = "Rear end"
                left_edge = "Inside face"
                right_edge = "Outside right face"
                note = "Handed right-side part"

            elif "leg post fl" in name:
                front_edge = "Front face"
                back_edge = "Inside/rear face"
                left_edge = "Left/outside face"
                right_edge = "Inside/right face"
                note = "Front-left leg post"

            elif "leg post fr" in name:
                front_edge = "Front face"
                back_edge = "Inside/rear face"
                left_edge = "Inside/left face"
                right_edge = "Right/outside face"
                note = "Front-right leg post"

            elif "leg post rl" in name:
                front_edge = "Inside/front face"
                back_edge = "Rear face"
                left_edge = "Left/outside face"
                right_edge = "Inside/right face"
                note = "Rear-left leg post"

            elif "leg post rr" in name:
                front_edge = "Inside/front face"
                back_edge = "Rear face"
                left_edge = "Inside/left face"
                right_edge = "Right/outside face"
                note = "Rear-right leg post"

            elif "cable tray" in name:
                front_edge = "Tray front/user side"
                back_edge = "Tray rear/cable side"
                left_edge = "Left end"
                right_edge = "Right end"
                note = "Keep cable tray parts bundled together"

            elif "mixer" in name:
                front_edge = "Mixer access/user side"
                back_edge = "Rear support side"
                left_edge = "Left support side"
                right_edge = "Right support side"
                note = "Confirm mixer tray width and rebate orientation"

            elif "vesa" in name:
                front_edge = "Monitor/front side"
                back_edge = "Rear support side"
                left_edge = "Left from user position"
                right_edge = "Right from user position"
                note = "Confirm load-rated mounting hardware"

            elif "headset" in name or "hook" in name:
                front_edge = "User access side"
                back_edge = "Fixing side"
                left_edge = "Left if mounted left"
                right_edge = "Right if mounted right"
                note = "Confirm handed side before fixing"

            return front_edge, back_edge, left_edge, right_edge, note

        def draw_table(headers, rows, col_widths):
            nonlocal y
            row_h = 7 * mm
            total_w = sum(col_widths)

            def draw_one_row(values, bold=False, fill="#FFFFFF"):
                nonlocal y
                if y < 25 * mm:
                    c.showPage()
                    draw_header(f"{design_name} - Part Marking / Orientation", "continued")
                    y = page_height - margin - 20 * mm

                c.setFillColor(colors.HexColor(fill))
                c.setStrokeColor(colors.HexColor("#DDDDDD"))
                c.rect(margin, y - row_h + 1, total_w, row_h, fill=1, stroke=1)

                c.setFillColor(colors.black)
                c.setFont("Helvetica-Bold" if bold else "Helvetica", 6.2)
                x = margin
                for value, col_w in zip(values, col_widths):
                    c.drawString(x + 1 * mm, y - 4.9 * mm, str(value)[:36])
                    x += col_w
                y -= row_h

            draw_one_row(headers, bold=True, fill="#F3F3F3")
            for row in rows:
                draw_one_row(row)

            y -= 4 * mm

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, "Part marking legend")
        y -= 7 * mm

        legend_lines = [
            "Mark every cut part before sanding or assembly: ID, FRONT, BACK, LEFT, RIGHT, and visible face where relevant.",
            "Use seated/user position as the reference direction for LEFT and RIGHT.",
            "Keep handed parts grouped: FL, FR, RL, RR, Left Side, Right Side.",
            "Do not rely on board nesting position as final orientation after parts are removed from the sheet.",
        ]

        c.setFont("Helvetica", 7.3)
        for line in legend_lines:
            c.drawString(margin + 4 * mm, y, f"- {line}")
            y -= 5 * mm

        y -= 4 * mm

        rows = []
        for idx, part in enumerate(nesting.parts, start=1):
            part_name = part["name"]
            front_edge, back_edge, left_edge, right_edge, note = infer_orientation(part_name)
            mark_id = f"P{idx:02d}"
            rows.append((
                mark_id,
                part_name,
                f"{part.get('sheet', 0) + 1}",
                front_edge,
                back_edge,
                left_edge,
                right_edge,
                note,
            ))

        draw_table(
            ["ID", "Part", "Sheet", "Front mark", "Back mark", "Left mark", "Right mark", "Note"],
            rows,
            [10 * mm, 40 * mm, 12 * mm, 33 * mm, 33 * mm, 30 * mm, 30 * mm, 56 * mm],
        )

    def draw_cut_part_labels_page():
        c.showPage()
        draw_header(f"{design_name} - Cut Part Labels", "Manufacturing Instructions")
        draw_note_box(page_height - margin - 18 * mm, "Use these labels as a shop-floor marking guide after cutting. Apply labels before parts are moved or stacked.")

        y = page_height - margin - 42 * mm
        label_w = (page_width - 2 * margin - 10 * mm) / 2
        label_h = 22 * mm
        gap = 5 * mm
        x_positions = [margin, margin + label_w + gap]
        col = 0

        for idx, part in enumerate(nesting.parts, start=1):
            if y - label_h < 20 * mm:
                c.showPage()
                draw_header(f"{design_name} - Cut Part Labels", "continued")
                y = page_height - margin - 20 * mm
                col = 0

            x = x_positions[col]
            c.setFillColor(colors.HexColor("#F7F7F7"))
            c.setStrokeColor(colors.HexColor("#BBBBBB"))
            c.roundRect(x, y - label_h, label_w, label_h, 2 * mm, fill=1, stroke=1)

            mark_id = f"P{idx:02d}"
            c.setFillColor(colors.HexColor("#FF3B30"))
            c.setFont("Helvetica-Bold", 11)
            c.drawString(x + 3 * mm, y - 6 * mm, mark_id)

            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 7.2)
            c.drawString(x + 18 * mm, y - 5.5 * mm, str(part["name"])[:42])

            c.setFont("Helvetica", 6.7)
            c.drawString(x + 3 * mm, y - 11 * mm, f"Size: {part['width']} x {part['height']} mm | Sheet {part.get('sheet', 0) + 1}")
            c.drawString(x + 3 * mm, y - 15.5 * mm, "Mark: FRONT / BACK / LEFT / RIGHT before sanding")
            c.drawString(x + 3 * mm, y - 20 * mm, "Visible face: confirm before final assembly")

            col += 1
            if col > 1:
                col = 0
                y -= label_h + gap

    def draw_exploded_assembly_page():
        c.showPage()
        draw_header(f"{design_name} - Exploded Assembly View", "Manufacturing Instructions")
        draw_note_box(page_height - margin - 18 * mm, "Exploded view shows assembly relationship only. CNC geometry remains controlled by DXF/NC exports.")

        left = margin + 10 * mm
        bottom = margin + 24 * mm
        area_w = page_width - 2 * margin - 20 * mm
        area_h = page_height - 2 * margin - 86 * mm

        cx = left + area_w / 2
        base_y = bottom + 20 * mm

        desk_w = min(area_w * 0.72, 190 * mm)
        top_h = 9 * mm
        rail_h = 12 * mm
        leg_w = 13 * mm
        leg_h = 52 * mm

        def label(text, x, y, size=7, bold=False):
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
            c.drawCentredString(x, y, text[:62])

        def arrow(x1, y1, x2, y2, text=""):
            c.setStrokeColor(colors.HexColor("#666666"))
            c.setFillColor(colors.HexColor("#666666"))
            c.setLineWidth(0.8)
            c.line(x1, y1, x2, y2)
            c.line(x2, y2, x2 - 2.2 * mm, y2 + 1.6 * mm)
            c.line(x2, y2, x2 + 2.2 * mm, y2 + 1.6 * mm)
            if text:
                c.setFont("Helvetica", 6.5)
                c.drawCentredString((x1 + x2) / 2, (y1 + y2) / 2 + 2 * mm, text[:32])

        def part_box(x, y, w, h, text, fill="#F8F8F8", stroke="#333333", dashed=False):
            c.setFillColor(colors.HexColor(fill))
            c.setStrokeColor(colors.HexColor(stroke))
            c.setLineWidth(1)
            if dashed:
                c.setDash(2, 2)
            c.roundRect(x, y, w, h, 2 * mm, fill=1, stroke=1)
            c.setDash()
            label(text, x + w / 2, y + h / 2 - 2, size=7, bold=True)

        desktop_y = base_y + 82 * mm
        rail_y = base_y + 48 * mm
        leg_y = base_y

        part_box(cx - desk_w / 2, desktop_y, desk_w, top_h, "STEP 3 - DESKTOP TOP", "#FFFFFF", "#111111")
        label("Lift/position desktop after frame is square", cx, desktop_y + top_h + 5 * mm, size=7)

        part_box(cx - desk_w * 0.42, rail_y + 16 * mm, desk_w * 0.84, rail_h, "STEP 2 - REAR UPPER RAIL", "#F4F4F4", "#555555")
        part_box(cx - desk_w * 0.42, rail_y - 4 * mm, desk_w * 0.84, rail_h, "STEP 2 - FRONT LOWER RAIL", "#F4F4F4", "#555555")
        part_box(cx - desk_w * 0.52, rail_y + 2 * mm, 18 * mm, rail_h * 2.2, "SIDE RAIL L", "#F4F4F4", "#555555")
        part_box(cx + desk_w * 0.52 - 18 * mm, rail_y + 2 * mm, 18 * mm, rail_h * 2.2, "SIDE RAIL R", "#F4F4F4", "#555555")
        label("Clamp frame square before desktop fixing", cx, rail_y + 36 * mm, size=7)

        leg_positions = [
            (cx - desk_w * 0.42, leg_y, "FL"),
            (cx + desk_w * 0.42 - leg_w, leg_y, "FR"),
            (cx - desk_w * 0.28, leg_y + 8 * mm, "RL"),
            (cx + desk_w * 0.28 - leg_w, leg_y + 8 * mm, "RR"),
        ]
        for lx, ly, name in leg_positions:
            part_box(lx, ly, leg_w, leg_h, name, "#DDEBFF", "#005BFF")
        label("STEP 1 - BUILD LEG/RAIL FRAME", cx, leg_y - 8 * mm, size=8, bold=True)

        accessory_x = left + 8 * mm
        accessory_y = base_y + 105 * mm
        if params.has_cable_management:
            part_box(accessory_x, accessory_y, 46 * mm, 13 * mm, "Cable Tray", "#E8FFF0", "#0B7A35")
            arrow(accessory_x + 23 * mm, accessory_y, cx - desk_w * 0.22, rail_y + 18 * mm, "Step 4")
        if params.has_mixer_tray:
            part_box(accessory_x, accessory_y - 20 * mm, 46 * mm, 13 * mm, "Mixer Tray", "#FFF0D8", "#CC7A00")
            arrow(accessory_x + 23 * mm, accessory_y - 7 * mm, cx, desktop_y, "Step 4")
        if params.has_vesa_mount:
            part_box(left + area_w - 58 * mm, accessory_y, 48 * mm, 13 * mm, "VESA Zone", "#F1E6FF", "#7A2DCC")
            arrow(left + area_w - 34 * mm, accessory_y, cx + desk_w * 0.18, desktop_y + top_h, "Check load")
        if params.has_headset_hook:
            part_box(left + area_w - 58 * mm, accessory_y - 20 * mm, 48 * mm, 13 * mm, "Headset Hook", "#F1E6FF", "#7A2DCC")
            arrow(left + area_w - 34 * mm, accessory_y - 7 * mm, cx + desk_w * 0.42, desktop_y, "Handed side")

        c.setFillColor(colors.HexColor("#111111"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(left, bottom + area_h + 5 * mm, "Assembly direction reference")
        c.setFont("Helvetica", 7)
        c.drawString(left, bottom + area_h, "FRONT = user/seated side | BACK = cable/accessory side | LEFT/RIGHT from seated position")

        footer_x = margin
        footer_y = margin + 7 * mm
        c.setFont("Helvetica-Bold", 8)
        c.drawString(footer_x, footer_y + 12 * mm, "Exploded assembly order")
        c.setFont("Helvetica", 7)
        order = [
            "1. Build leg/rail frame and clamp square.",
            "2. Fit side/front/rear rails to legs.",
            "3. Fit desktop to frame after alignment check.",
            "4. Install cable tray, mixer tray, VESA/headset/accessories where selected.",
            "5. Final check: square, level, hardware tightness, edge finish, cable clearances.",
        ]
        for idx, item in enumerate(order):
            c.drawString(footer_x + 4 * mm, footer_y + (7 - idx) * mm, item)

    def draw_joint_detail_diagrams_page():
        c.showPage()
        draw_header(f"{design_name} - Joint Detail Diagrams", "Manufacturing Instructions")
        draw_note_box(page_height - margin - 18 * mm, "Joint diagrams are schematic manufacturing details. Confirm exact screw/dowel/insert hardware before cutting or assembly.")

        start_x = margin
        start_y = page_height - margin - 44 * mm
        box_w = (page_width - 2 * margin - 12 * mm) / 2
        box_h = 42 * mm
        gap_x = 12 * mm
        gap_y = 10 * mm

        def detail_box(index, title, subtitle, notes, col, row):
            x = start_x + col * (box_w + gap_x)
            y = start_y - row * (box_h + gap_y)

            c.setFillColor(colors.HexColor("#FAFAFA"))
            c.setStrokeColor(colors.HexColor("#CCCCCC"))
            c.roundRect(x, y - box_h, box_w, box_h, 2 * mm, fill=1, stroke=1)

            c.setFillColor(colors.HexColor("#FF3B30"))
            c.setFont("Helvetica-Bold", 9)
            c.drawString(x + 3 * mm, y - 6 * mm, f"J{index:02d}")

            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(x + 15 * mm, y - 6 * mm, title[:44])

            c.setFont("Helvetica", 6.7)
            c.setFillColor(colors.HexColor("#444444"))
            c.drawString(x + 3 * mm, y - 11 * mm, subtitle[:72])

            sx = x + box_w - 43 * mm
            sy = y - 30 * mm
            c.setStrokeColor(colors.HexColor("#333333"))
            c.setFillColor(colors.HexColor("#FFFFFF"))
            c.rect(sx, sy + 13 * mm, 34 * mm, 6 * mm, fill=1, stroke=1)
            c.setFillColor(colors.HexColor("#DDEBFF"))
            c.rect(sx + 4 * mm, sy, 8 * mm, 19 * mm, fill=1, stroke=1)
            c.rect(sx + 23 * mm, sy, 8 * mm, 19 * mm, fill=1, stroke=1)

            c.setFillColor(colors.HexColor("#FF3B30"))
            for px in [sx + 8 * mm, sx + 27 * mm]:
                c.circle(px, sy + 15.5 * mm, 1.2 * mm, fill=1, stroke=0)

            text_y = y - 17 * mm
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 6.4)
            for note in notes[:4]:
                c.drawString(x + 3 * mm, text_y, f"- {note}"[:82])
                text_y -= 4.2 * mm

        details = [
            ("Desktop to frame rail", "Use underside fixing line; avoid breakthrough through desktop.", [
                "Align desktop FRONT/BACK before fixing.",
                "Use pilot holes from CNC/drill schedule.",
                "Confirm screw length against material thickness.",
                "Check cable/mixer openings before final fixing.",
            ]),
            ("Rail end to leg post", "Rail ends fix into leg posts; clamp square before tightening.", [
                "Dry fit left/right frame first.",
                "Keep rail flush and square to leg post.",
                "Confirm edge distance before final fixing.",
                "Do not over-tighten into board edge.",
            ]),
            ("Side rail to leg frame", "Side rail locks front/rear leg frames together.", [
                "Confirm handed side before assembly.",
                "Fit rails before desktop.",
                "Check frame is not racked.",
                "Use clamps until both sides are fixed.",
            ]),
            ("Cable tray / accessory fixing", "Accessory parts fix after main frame and desktop are square.", [
                "Confirm cable tray opening direction.",
                "Keep clear of cable pass-throughs.",
                "Confirm mixer tray rebate orientation.",
                "Confirm VESA/headset load and handedness.",
            ]),
        ]

        for i, (title, subtitle, notes) in enumerate(details, start=1):
            col = (i - 1) % 2
            row = (i - 1) // 2
            detail_box(i, title, subtitle, notes, col, row)

        c.setFillColor(colors.HexColor("#333333"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin, margin + 18 * mm, "Joint detail notes")
        c.setFont("Helvetica", 7)
        footer_notes = [
            "These joint details are schematic and must be read with the part schedule, CNC files, and hardware specification.",
            "Final screw/bolt/dowel/insert type must suit material, load, edge distance, and supplier hardware.",
            "Where hardware differs from design assumptions, update the manufacturing pack before cutting production parts.",
        ]
        yy = margin + 12 * mm
        for note in footer_notes:
            c.drawString(margin + 4 * mm, yy, f"- {note}")
            yy -= 4.7 * mm

    def draw_parts_and_feature_schedule():
        c.showPage()
        draw_header(f"{design_name} - Review Schedule", "Design Review Drawings")
        draw_note_box(page_height - margin - 18 * mm, "Schedule is for design checking. Confirm feature quantities and hardware before CNC cutting.")

        y = page_height - margin - 42 * mm
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, "Design summary")
        y -= 8 * mm
        c.setFont("Helvetica", 8)
        summary = [
            f"Overall size: {int(width)}W x {int(depth)}D x {int(height)}H mm",
            f"Material thickness: {int(thickness)}mm",
            f"Sheets required: {nesting.sheets_required}",
            f"Parts: {len(nesting.parts)}",
            f"Drill features: {drill_total}",
            f"Inside cutouts: {inside_total}",
            f"Pockets/rebates: {pocket_total}",
            f"Cable management: {'Yes' if params.has_cable_management else 'No'}",
            f"Mixer tray: {'Yes' if params.has_mixer_tray else 'No'}",
            f"VESA mount: {'Yes' if params.has_vesa_mount else 'No'}",
            f"Headset hook: {'Yes' if params.has_headset_hook else 'No'}",
        ]
        for item in summary:
            c.drawString(margin + 4 * mm, y, f"- {item}")
            y -= 5 * mm

        y -= 6 * mm
        c.setFont("Helvetica-Bold", 9)
        columns = [
            ("#", 9 * mm),
            ("Part", 70 * mm),
            ("W", 18 * mm),
            ("H", 18 * mm),
            ("Sheet", 16 * mm),
            ("Drill", 16 * mm),
            ("Inside", 16 * mm),
            ("Pocket", 18 * mm),
        ]
        x_positions = [margin]
        for _, col_w in columns[:-1]:
            x_positions.append(x_positions[-1] + col_w)

        row_h = 7 * mm

        def draw_row(values, bold=False):
            nonlocal y
            if y < 22 * mm:
                c.showPage()
                draw_header(f"{design_name} - Review Schedule", "continued")
                y = page_height - margin - 20 * mm
            c.setFillColor(colors.HexColor("#F5F5F5") if bold else colors.white)
            c.setStrokeColor(colors.HexColor("#DDDDDD"))
            c.rect(margin, y - row_h + 1, sum(w for _, w in columns), row_h, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold" if bold else "Helvetica", 7)
            for idx, value in enumerate(values):
                c.drawString(x_positions[idx] + 1 * mm, y - 5 * mm, str(value)[:38])
            y -= row_h

        draw_row([label for label, _ in columns], bold=True)
        for idx, part in enumerate(nesting.parts, start=1):
            draw_row([
                idx,
                part["name"],
                part["width"],
                part["height"],
                part.get("sheet", 0) + 1,
                len(feature_items(part, ("drill_points", "holes", "joinery_holes", "connector_holes"))),
                len(feature_items(part, ("cutouts", "inside_profiles", "internal_profiles", "internal_cutouts"))),
                len(feature_items(part, ("pockets", "rebates", "trays", "pocket_features", "recesses"))),
            ])

    draw_plan_page()
    draw_front_elevation()
    draw_side_elevation()
    draw_isometric_assembly_page()
    draw_exploded_assembly_page()
    draw_joint_detail_diagrams_page()
    draw_assembly_details_page()
    draw_hardware_schedule_page()
    draw_part_marking_page()
    draw_cut_part_labels_page()
    draw_parts_and_feature_schedule()

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


@api_router.post("/review-drawings/pdf")
async def generate_review_drawings_pdf(export_req: ExportRequest):
    """Generate a dimensioned design review PDF before manufacturing export."""
    pdf_bytes = generate_review_drawing_pdf_bytes(export_req.params, export_req.design_name or "UltimateDesk Design")
    safe_name = (export_req.design_name or "UltimateDesk_Review_Drawings").replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}_review_drawings.pdf"'
        }
    )

# ============== EXPORT ENDPOINTS ==============

exports_router = APIRouter(prefix="/exports", tags=["Pro Exports"])

@exports_router.post("/check-access")
async def check_export_access(request: Request):
    """Check if user has Pro access or unused export credits."""
    user = await get_optional_user(request)

    if not user:
        return {
            "has_access": False,
            "reason": "not_authenticated",
            "message": "Please sign in to export files",
        }

    if user.get("is_pro"):
        return {
            "has_access": True,
            "plan": "pro_unlimited",
            "message": "You have unlimited Pro exports",
        }

    # Count unused single-export credits
    unused = await db.export_credits.count_documents({"user_id": user["id"], "used": False})
    if unused > 0:
        latest = await db.export_credits.find_one(
            {"user_id": user["id"], "used": False},
            sort=[("created_at", -1)],
            projection={"_id": 0, "bundle": 1, "commercial_license": 1, "design_name": 1},
        )
        return {
            "has_access": True,
            "plan": "single_export",
            "remaining": unused,
            "latest_credit": latest,
            "message": f"You have {unused} paid export(s) available",
        }

    return {
        "has_access": False,
        "reason": "no_credits",
        "message": "Purchase a single export or Pro to download files",
    }

@exports_router.post("/purchase-single")
async def purchase_single_export(request: Request):
    """Create a Stripe checkout for a single export.
    Body: { origin_url, params, bundle, commercial_license, design_name }
    Price is computed server-side from the pricing engine - NEVER trust client price.
    """
    body = await request.json()
    origin_url = body.get("origin_url", "")
    if not origin_url:
        raise HTTPException(status_code=400, detail="Origin URL required")

    raw_params = body.get("params") or {}
    try:
        design_params = DesignParams(**raw_params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid design params: {e}")

    bundle = body.get("bundle", "dxf")
    commercial_license = bool(body.get("commercial_license", False))
    design_name = body.get("design_name", "UltimateDesk Design")

    user = await get_current_user(request)

    if not HAS_EMERGENT_INTEGRATIONS:
        raise HTTPException(status_code=503, detail="Stripe checkout unavailable in local mode")

    # Compute authoritative quote on the server
    parts = calculate_desk_parts(design_params)
    nesting = simple_nesting(parts, 2400, 1200)
    total_part_qty = sum(p.get("quantity", 1) for p in parts)
    quote = calculate_quote(
        design_params.model_dump(),
        sheets_required=nesting.sheets_required,
        part_count=total_part_qty,
        bundle=bundle,
        commercial_license=commercial_license,
    )

    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    success_url = f"{origin_url}/export/success?session_id={{CHECKOUT_SESSION_ID}}&type=single"
    cancel_url = f"{origin_url}/designer"

    checkout_request = CheckoutSessionRequest(
        amount=float(quote.total),
        currency="nzd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user["id"],
            "user_email": user["email"],
            "product": "single_export",
            "bundle": quote.bundle_key,
            "commercial_license": "1" if commercial_license else "0",
            "design_name": design_name[:80],
        },
    )
    session = await stripe_checkout.create_checkout_session(checkout_request)

    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": user["id"],
        "user_email": user["email"],
        "amount": float(quote.total),
        "currency": "nzd",
        "product": "single_export",
        "bundle": quote.bundle_key,
        "commercial_license": commercial_license,
        "design_name": design_name,
        "params_snapshot": design_params.model_dump(),
        "quote_breakdown": quote.model_dump(),
        "status": "pending",
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc),
    })

    return {
        "url": session.url,
        "session_id": session.session_id,
        "amount": quote.total,
        "bundle": quote.bundle_key,
        "headline": quote.headline,
    }

@exports_router.post("/purchase-pro")
async def purchase_pro_subscription(request: Request):
    """Create checkout for Pro subscription ($19/mo)"""
    body = await request.json()
    origin_url = body.get("origin_url", "")

    if not origin_url:
        raise HTTPException(status_code=400, detail="Origin URL required")

    user = await get_current_user(request)

    if not HAS_EMERGENT_INTEGRATIONS:
        raise HTTPException(status_code=503, detail="Stripe checkout unavailable in local mode")

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
    """Generate and return export files per purchased bundle. Requires Pro OR an unused credit."""
    user = await get_current_user(request)

    has_pro = user.get("is_pro", False)
    requested_bundle = export_req.bundle if export_req.bundle in BUNDLE_OPTIONS else "dxf"
    consumed_credit_id = None

    if not has_pro:
        # Find an unused credit matching the requested bundle (or any higher-tier credit)
        credit = await db.export_credits.find_one({
            "user_id": user["id"],
            "used": False,
            "bundle": requested_bundle,
        })
        if not credit:
            raise HTTPException(
                status_code=403,
                detail="No matching paid export credit. Purchase this bundle or upgrade to Pro.",
            )
        consumed_credit_id = credit["_id"]

    # Generate files
    raw_cnc_config = getattr(export_req, "cnc_config", None) or {}
    if isinstance(raw_cnc_config, CNCConfig):
        config = raw_cnc_config
    elif isinstance(raw_cnc_config, dict):
        config = CNCConfig(**raw_cnc_config)
    else:
        config = CNCConfig()

    parts = calculate_desk_parts(export_req.params)
    nesting = simple_nesting(parts, config.sheet_width, config.sheet_height)

    bundle_cfg = BUNDLE_OPTIONS[requested_bundle]
    bundle_files = bundle_cfg["files"]

    gcode_content = generate_full_gcode(nesting.parts, config, export_req.design_name) if "gcode" in bundle_files else ""
    dxf_content = "LAYER CUT\nLAYER DRILL\nLAYER POCKET\n" +  generate_dxf(nesting.parts, config, export_req.design_name) if "dxf" in bundle_files else ""
    svg_content = generate_svg(nesting.parts, config, export_req.design_name) if "svg" in bundle_files else ""
    pdf_html = generate_pdf_html(nesting.parts, nesting, export_req.params, export_req.design_name) if "pdf" in bundle_files else ""

    export_id = str(uuid.uuid4())
    await db.exports.insert_one({
        "export_id": export_id,
        "user_id": user["id"],
        "design_name": export_req.design_name,
        "bundle": requested_bundle,
        "params": export_req.params.model_dump(),
        "cnc_config": config.model_dump(),
        "gcode": gcode_content,
        "dxf": dxf_content,
        "svg": svg_content,
        "pdf_html": pdf_html,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
    })

    # Mark credit used AFTER successful generation
    if consumed_credit_id is not None:
        await db.export_credits.update_one(
            {"_id": consumed_credit_id},
            {"$set": {"used": True, "used_at": datetime.now(timezone.utc), "export_id": export_id}},
        )

    files = {}
    for ft in bundle_files:
        files[ft] = f"/api/exports/download/{export_id}/{ft}"

    disclaimer = (
        "IMPORTANT: These files are high-quality REFERENCE files. "
        "You MUST verify all toolpaths in your CAM software (VCarve, Fusion 360, etc.) before cutting. "
        "UltimateDesk is not responsible for machine damage, material waste, or injury from unverified toolpaths."
    )

    return {
        "success": True,
        "export_id": export_id,
        "bundle": requested_bundle,
        "bundle_label": bundle_cfg["label"],
        "files": files,
        "disclaimer": disclaimer,
        "message": "Export files generated successfully. Files expire in 24 hours.",
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

    if export.get("expires_at"):
        exp = export["expires_at"]
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
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
    elif file_type == "svg":
        content = export.get("svg", "")
        filename = f"{design_name}.svg"
        media_type = "image/svg+xml"
    elif file_type == "pdf":
        params = DesignParams(**export.get("params", {}))
        config = CNCConfig(**(export.get("cnc_config") or {}))
        parts = calculate_desk_parts(params)
        nesting = simple_nesting(parts, config.sheet_width, config.sheet_height)
        content = generate_pdf_bytes(nesting.parts, nesting, params, export.get("design_name", "UltimateDesk"))
        filename = f"{design_name}_cutting_sheet.pdf"
        media_type = "application/pdf"
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")

    if not content:
        raise HTTPException(status_code=404, detail=f"This bundle does not include a {file_type} file")

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
    if not HAS_EMERGENT_INTEGRATIONS:
        raise HTTPException(status_code=503, detail="Stripe webhook unavailable in local mode")

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
                        # Add 1 export credit tied to the purchased bundle
                        bundle = transaction.get("bundle", "dxf")
                        commercial = bool(transaction.get("commercial_license", False))
                        await db.export_credits.insert_one({
                            "user_id": user_id,
                            "session_id": event.session_id,
                            "bundle": bundle,
                            "commercial_license": commercial,
                            "params_snapshot": transaction.get("params_snapshot"),
                            "design_name": transaction.get("design_name", "UltimateDesk Design"),
                            "amount_paid": transaction.get("amount"),
                            "used": False,
                            "created_at": datetime.now(timezone.utc),
                        })

        return {"received": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"received": True, "error": str(e)}

PRO_SUBSCRIPTION_PRICE = PRO_MONTHLY_PRICE  # Keep backward compatibility

# ============== PRICING ROUTES ==============

class QuoteRequestBody(BaseModel):
    params: DesignParams
    bundle: str = "dxf"
    commercial_license: bool = False


@pricing_router.get("/bundles")
async def list_bundles():
    """Return the catalog of purchasable bundles + base pricing constants for the UI."""
    from pricing import (
        BASE_FEE, SHEET_FEE, PART_FEE_OVER_THRESHOLD, PART_THRESHOLD,
        FEATURE_FEE_EACH, JOINT_FEES, COMMERCIAL_LICENSE_FEE, CURRENCY,
    )
    return {
        "currency": CURRENCY,
        "bundles": get_bundle_catalog(),
        "constants": {
            "base_fee": BASE_FEE,
            "sheet_fee": SHEET_FEE,
            "part_fee_over_threshold": PART_FEE_OVER_THRESHOLD,
            "part_threshold": PART_THRESHOLD,
            "feature_fee_each": FEATURE_FEE_EACH,
            "joint_fees": JOINT_FEES,
            "commercial_license_fee": COMMERCIAL_LICENSE_FEE,
        },
    }


@pricing_router.post("/quote", response_model=QuoteBreakdown)
async def pricing_quote(body: QuoteRequestBody):
    """Live quote - no auth required. Computes sheets + parts from params then prices."""
    parts = calculate_desk_parts(body.params)
    nesting = simple_nesting(parts, 2400, 1200)
    total_part_qty = sum(p.get("quantity", 1) for p in parts)
    return calculate_quote(
        body.params.model_dump(),
        sheets_required=nesting.sheets_required,
        part_count=total_part_qty,
        bundle=body.bundle,
        commercial_license=body.commercial_license,
    )


# ----- Shareable quote links -----

class ShareQuoteRequest(BaseModel):
    params: DesignParams
    bundle: str = "dxf"
    commercial_license: bool = False
    design_name: str = "My Custom Desk"


def _build_share_slug() -> str:
    # URL-safe short id: uuid4 first 10 chars, collision unlikely given traffic
    return uuid.uuid4().hex[:10]


@pricing_router.post("/share")
async def create_share_link(body: ShareQuoteRequest, request: Request):
    """Save a quote snapshot and return a shareable slug + public URL."""
    parts = calculate_desk_parts(body.params)
    nesting = simple_nesting(parts, 2400, 1200)
    total_part_qty = sum(p.get("quantity", 1) for p in parts)
    quote = calculate_quote(
        body.params.model_dump(),
        sheets_required=nesting.sheets_required,
        part_count=total_part_qty,
        bundle=body.bundle,
        commercial_license=body.commercial_license,
    )

    slug = _build_share_slug()
    # Prefer FRONTEND_URL env if set; else Origin header (may be cluster-internal in k8s)
    frontend_origin = (
        os.environ.get("FRONTEND_PUBLIC_URL")
        or request.headers.get("origin")
        or str(request.base_url).rstrip("/")
    )

    await db.shared_quotes.insert_one({
        "slug": slug,
        "design_name": body.design_name,
        "params": body.params.model_dump(),
        "bundle": body.bundle,
        "commercial_license": body.commercial_license,
        "quote": quote.model_dump(),
        "created_at": datetime.now(timezone.utc),
        "views": 0,
    })

    return {
        "slug": slug,
        "share_url": f"{frontend_origin}/quote/{slug}",
        "quote_api_url": f"/api/pricing/shared/{slug}",
        "pdf_url": f"/api/pricing/shared/{slug}/pdf",
        "expires": None,
    }


@pricing_router.get("/shared/{slug}")
async def get_shared_quote(slug: str):
    doc = await db.shared_quotes.find_one({"slug": slug}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Quote not found")
    await db.shared_quotes.update_one({"slug": slug}, {"$inc": {"views": 1}})
    return doc


def _render_quote_html(doc: Dict[str, Any]) -> str:
    q = doc["quote"]
    design_name = doc.get("design_name", "UltimateDesk Design")
    params = doc.get("params", {})
    li_rows = "".join(
        f"<tr><td>{li['label']}"
        + (f"<br><span class='detail'>{li['detail']}</span>" if li.get('detail') else "")
        + f"</td><td class='amt'>${li['amount']:.2f}</td></tr>"
        for li in q["line_items"]
    )
    commercial_row = (
        f"<tr><td>Commercial-use license</td><td class='amt'>${q['commercial_fee']:.2f}</td></tr>"
        if q.get("commercial_license") else ""
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Quote - {design_name}</title>
<style>
 body {{ font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 760px; margin: 40px auto; color: #111; padding: 24px; }}
 h1 {{ color: #FF3B30; margin: 0 0 4px 0; letter-spacing: -0.02em; }}
 .meta {{ color: #666; font-size: 13px; margin-bottom: 24px; }}
 .headline {{ font-size: 18px; font-weight: 600; margin: 16px 0 4px; }}
 table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
 td {{ padding: 10px 4px; border-bottom: 1px solid #eee; vertical-align: top; font-size: 14px; }}
 td.amt {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
 .detail {{ color: #888; font-size: 12px; }}
 .total {{ display: flex; justify-content: space-between; align-items: baseline; margin-top: 18px;
           border-top: 2px solid #111; padding-top: 16px; }}
 .total .amt {{ font-size: 32px; font-weight: 800; color: #FF3B30; }}
 .material {{ background: #FFF8E1; border: 1px solid #FFE082; border-radius: 8px; padding: 12px; margin: 16px 0; font-size: 13px; color: #5D4037; }}
 .bundle-tag {{ display: inline-block; padding: 4px 10px; background: #111; color: #fff; border-radius: 999px; font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; }}
 .print-btn {{ background: #111; color: #fff; border: 0; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: 600; margin-top: 24px; }}
 @media print {{ .print-btn {{ display: none; }} }}
 .footer {{ margin-top: 32px; color: #888; font-size: 12px; border-top: 1px solid #eee; padding-top: 12px; }}
</style></head>
<body>
  <h1>UltimateDesk</h1>
  <div class="meta">
    <span class="bundle-tag">{q['bundle_label']}</span>
    &nbsp;·&nbsp; Quote generated {doc['created_at'].strftime('%Y-%m-%d') if hasattr(doc.get('created_at',''), 'strftime') else ''}
  </div>
  <div class="headline">{design_name}</div>
  <div style="color:#555; font-size:14px;">{q['headline']}</div>

  <table>
    {li_rows}
    {commercial_row}
  </table>

  <div class="material">
    <strong>Material note:</strong> {q.get('material_note', '')}
  </div>

  <div class="total">
    <span style="font-weight:700;">Export total</span>
    <span class="amt">${int(q['total'])} NZD</span>
  </div>

  <button class="print-btn" onclick="window.print()">Save as PDF / Print</button>

  <div class="footer">
    Design: {params.get('desk_type', 'custom')} - {params.get('width', 0)} x {params.get('depth', 0)} x {params.get('height', 0)} mm ·
    {q['sheets_required']} sheet(s) - {q['part_count']} parts.<br>
    Export files include: {', '.join(q.get('bundle_files', []))}.<br>
    This quote is for pricing guidance and reference file generation only. Verify dimensions, toolpaths, tooling, feeds, origins and hold-down strategy in your CAM software before cutting.
  </div>
</body></html>"""


@pricing_router.get("/shared/{slug}/pdf")
async def get_shared_quote_pdf(slug: str):
    """Return an HTML document the browser can 'Save as PDF' - lightweight, no extra deps."""
    doc = await db.shared_quotes.find_one({"slug": slug})
    if not doc:
        raise HTTPException(status_code=404, detail="Quote not found")
    doc.pop("_id", None)
    html = _render_quote_html(doc)
    return Response(content=html, media_type="text/html")


# ============== INCLUDE ROUTERS ==============

api_router.include_router(auth_router)
api_router.include_router(designs_router)
api_router.include_router(chat_router)
api_router.include_router(cnc_router)
api_router.include_router(payments_router)
api_router.include_router(exports_router)
api_router.include_router(pricing_router)

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
    creds_path = ROOT_DIR.parent / "memory" / "test_credentials.md"
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
