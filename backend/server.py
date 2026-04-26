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
    """Generate export parts from the same straight-frame desk logic the preview uses."""
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

    def add_part(name: str, part_w: float, part_h: float, qty: int = 1, kind: str = "panel") -> None:
        part_w = int(round(part_w))
        part_h = int(round(part_h))
        if part_w <= 0 or part_h <= 0 or qty <= 0:
            return
        parts.append({
            "name": name,
            "width": part_w,
            "height": part_h,
            "quantity": qty,
            "type": kind,
        })

    is_oversize = bool(getattr(params, "is_oversize", False)) or width > 2400
    desktop_split_count = 2 if is_oversize else 1
    requires_centre_support = bool(getattr(params, "requires_centre_support", False)) or is_oversize

    if desktop_split_count > 1:
        left_top_w = int(math.ceil(width / 2))
        right_top_w = width - left_top_w
        add_part("Desktop Top Left Panel", left_top_w, depth)
        add_part("Desktop Top Right Panel", right_top_w, depth)
        add_part("Desktop Centre Join Plate", 180, max(300, min(depth - 120, 650)))
    else:
        add_part("Desktop Top", width, depth)

    add_part("Leg Post FL", leg_size, height - t)
    add_part("Leg Post FR", leg_size, height - t)
    add_part("Leg Post RL", leg_size, height - t)
    add_part("Leg Post RR", leg_size, height - t)

    if is_oversize:
        rear_left = int(math.ceil(clear_span_x / 2))
        rear_right = clear_span_x - rear_left
        add_part("Rear Upper Rail Left", rear_left, 42)
        add_part("Rear Upper Rail Right", rear_right, 42)
        add_part("Front Lower Rail Left", rear_left, 30)
        add_part("Front Lower Rail Right", rear_right, 30)
    else:
        add_part("Rear Upper Rail", clear_span_x, 42)
        add_part("Front Lower Rail", clear_span_x, 30)

    add_part("Left Side Rail", clear_span_y, 30)
    add_part("Right Side Rail", clear_span_y, 30)

    if requires_centre_support:
        add_part("Centre Support Post", leg_size, height - t)
        add_part("Centre Support Foot", 320, 90)
        add_part("Centre Under-Top Support Rail", max(420, min(int(width * 0.32), 900)), 55)

    back_panel_w = max(600, clear_span_x - 40)
    back_panel_h = 180 if params.desk_type == "office" else 220
    add_part("Back Modesty Panel", back_panel_w, back_panel_h)

    if params.has_cable_management:
        tray_w = max(500, min(width - (leg_inset_x * 2) - 120, int(width * 0.60)))
        add_part("Cable Tray Base", tray_w, 85)
        add_part("Cable Tray Front", tray_w, 50)
        add_part("Cable Tray Back", tray_w, 50)
        add_part("Cable Tray End Left", 85, 50)
        add_part("Cable Tray End Right", 85, 50)

    if params.has_headset_hook:
        add_part("Headset Hook Backplate", 90, 30)
        add_part("Headset Hook Arm", 60, 30)

    if params.has_gpu_tray:
        add_part("GPU Tray Base", 150, 70)
        add_part("GPU Tray Side Left", 70, 70)
        add_part("GPU Tray Side Right", 70, 70)
        add_part("GPU Tray Front Stop", 150, 25)

    if params.has_mixer_tray:
        tray_w = max(280, min(int(params.mixer_tray_width or 520), clear_span_x))
        add_part("Mixer Tray", tray_w, 170)
        add_part("Mixer Tray Support Left", 170, 120)
        add_part("Mixer Tray Support Right", 170, 120)
        add_part("Mixer Tray Front Lip", tray_w, 40)

    if getattr(params, "has_pedal_tilt", False):
        add_part("Pedal Platform", 500, 240)
        add_part("Pedal Support Left", 240, 120)
        add_part("Pedal Support Right", 240, 120)

    if params.has_vesa_mount:
        add_part("VESA Upright", 180, 100)
        add_part("VESA Mount Plate", 200, 200)
        add_part("VESA Gusset Left", 120, 120)
        add_part("VESA Gusset Right", 120, 120)

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
    """Simple bin packing algorithm for sheet nesting"""
    # Add margin for cuts
    margin = 18

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
    bundle: str = "dxf"  # dxf | dxf_svg | dxf_gcode | full_pack

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
        f"; UltimateDesk - Production G-Code",
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
        "; Thank you for using UltimateDesk!",
        "; Questions? support@ultimatedesk.co.nz"
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
    """Generate DXF file for CAD/CAM import, separated by sheet."""
    sheet_gap = 400
    title_band = 80

    sheet_indexes = sorted({part.get('sheet', 0) for part in parts}) or [0]
    sheet_count = max(sheet_indexes) + 1
    total_width = (sheet_count * config.sheet_width) + ((sheet_count - 1) * sheet_gap)
    total_height = config.sheet_height + title_band

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
        "2", "ENTITIES"
    ]

    for sheet_idx in sheet_indexes:
        x_offset = sheet_idx * (config.sheet_width + sheet_gap)

        dxf_lines.extend([
            "0", "LINE", "8", "SHEET_FRAME", "10", str(x_offset), "20", "0", "30", "0.0", "11", str(x_offset + config.sheet_width), "21", "0", "31", "0.0",
            "0", "LINE", "8", "SHEET_FRAME", "10", str(x_offset + config.sheet_width), "20", "0", "30", "0.0", "11", str(x_offset + config.sheet_width), "21", str(config.sheet_height), "31", "0.0",
            "0", "LINE", "8", "SHEET_FRAME", "10", str(x_offset + config.sheet_width), "20", str(config.sheet_height), "30", "0.0", "11", str(x_offset), "21", str(config.sheet_height), "31", "0.0",
            "0", "LINE", "8", "SHEET_FRAME", "10", str(x_offset), "20", str(config.sheet_height), "30", "0.0", "11", str(x_offset), "21", "0", "31", "0.0",
            "0", "TEXT", "8", "SHEET_LABELS", "10", str(x_offset + 20), "20", str(config.sheet_height + 30), "30", "0.0", "40", "28.0", "1", f"Sheet {sheet_idx + 1}"
        ])

    for i, part in enumerate(parts):
        sheet_idx = part.get('sheet', 0)
        x_offset = sheet_idx * (config.sheet_width + sheet_gap)
        x = x_offset + part.get('x', 0)
        y = part.get('y', 0)
        w, h = part['width'], part['height']

        dxf_lines.extend([
            "0", "LINE", "8", f"PART_{sheet_idx+1}_{i+1}", "10", str(x), "20", str(y), "30", "0.0", "11", str(x + w), "21", str(y), "31", "0.0",
            "0", "LINE", "8", f"PART_{sheet_idx+1}_{i+1}", "10", str(x + w), "20", str(y), "30", "0.0", "11", str(x + w), "21", str(y + h), "31", "0.0",
            "0", "LINE", "8", f"PART_{sheet_idx+1}_{i+1}", "10", str(x + w), "20", str(y + h), "30", "0.0", "11", str(x), "21", str(y + h), "31", "0.0",
            "0", "LINE", "8", f"PART_{sheet_idx+1}_{i+1}", "10", str(x), "20", str(y + h), "30", "0.0", "11", str(x), "21", str(y), "31", "0.0"
        ])

        label_x = x + (w / 2)
        label_y = y + (h / 2)
        label_size = max(10.0, min(24.0, min(w, h) * 0.10))
        label_text = part['name'] if min(w, h) < 140 else f"{part['name']} ({w}x{h})"

        dxf_lines.extend([
            "0", "TEXT",
            "8", "LABELS",
            "10", str(label_x),
            "20", str(label_y),
            "30", "0.0",
            "40", str(label_size),
            "72", "1",
            "73", "2",
            "11", str(label_x),
            "21", str(label_y),
            "31", "0.0",
            "1", label_text
        ])

    dxf_lines.extend([
        "0", "ENDSEC",
        "0", "EOF"
    ])

    return '\n'.join(dxf_lines)

def generate_svg(parts: List[Dict], config: CNCConfig, design_name: str) -> str:
    """Generate SVG cutting layout separated by sheet."""
    sw, sh = config.sheet_width, config.sheet_height
    sheet_gap = 400
    title_band = 80

    sheet_indexes = sorted({part.get('sheet', 0) for part in parts}) or [0]
    sheet_count = max(sheet_indexes) + 1
    total_width = (sheet_count * sw) + ((sheet_count - 1) * sheet_gap)
    total_height = sh + title_band

    lines = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {total_height}" width="{total_width}mm" height="{total_height}mm">',
        f'  <title>{design_name} - UltimateDesk</title>',
        f'  <desc>18mm plywood cutting layout. Verify in CAM software before cutting.</desc>',
        f'  <style>',
        f'    .sheet-title {{ font: 28px Arial, sans-serif; fill: #333; font-weight: bold; }}',
        f'    .part-label {{ font: 16px Arial, sans-serif; fill: #222; text-anchor: middle; dominant-baseline: middle; }}',
        f'    .sheet-frame {{ fill: none; stroke: #888; stroke-width: 2; }}',
        f'    .part-rect {{ fill: none; stroke: #000; stroke-width: 2; }}',
        f'  </style>',
    ]

    for sheet_idx in sheet_indexes:
        x_offset = sheet_idx * (sw + sheet_gap)
        lines.append(f'  <g id="sheet-{sheet_idx + 1}">')
        lines.append(f'    <text class="sheet-title" x="{x_offset + 20}" y="35">Sheet {sheet_idx + 1}</text>')
        lines.append(f'    <rect class="sheet-frame" x="{x_offset}" y="{title_band}" width="{sw}" height="{sh}"/>')
        lines.append(f'  </g>')

    for i, p in enumerate(parts):
        sheet_idx = p.get("sheet", 0)
        x_offset = sheet_idx * (sw + sheet_gap)
        x = x_offset + p.get("x", 0)
        y = title_band + p.get("y", 0)
        w, h = p["width"], p["height"]
        label_size = max(10, min(22, int(min(w, h) * 0.10)))
        label_text = p["name"] if min(w, h) < 140 else f'{p["name"]} ({w}x{h})'
        lines.append(
            f'  <g id="part-{i+1}" data-name="{p["name"]}" data-sheet="{sheet_idx + 1}">'
            f'<rect class="part-rect" x="{x}" y="{y}" width="{w}" height="{h}"/>'
            f'<text class="part-label" x="{x + w/2}" y="{y + h/2}" font-size="{label_size}">{label_text}</text>'
            f'</g>'
        )

    lines.append('</svg>')
    return '\n'.join(lines)

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
        <h1>UltimateDesk</h1>
        <h2>{design_name}</h2>
        <p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>

    <div class="disclaimer">
        <strong>IMPORTANT SAFETY DISCLAIMER</strong><br>
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
        <p><strong>UltimateDesk</strong> - Straight-frame desk build pack reference</p>
        <p>Questions? Email support@ultimatedesk.co.nz | Visit ultimatedesk.co.nz</p>
    </div>
</body>
</html>
"""
    return html

def generate_pdf_bytes(parts: List[Dict], nesting: NestingResult, params: DesignParams, design_name: str) -> bytes:
    """Generate a real PDF cutting sheet using reportlab."""
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    margin = 12 * mm

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
            (f"{params.material_thickness}mm", "Material"),
            (f"{nesting.waste_percentage}%", "Waste"),
            (f"${nesting.sheets_required * 80:.0f}", "Material NZD"),
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
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)
        c.drawString(margin, page_height - margin - 10 * mm, "2400mm x 1200mm sheet layout")

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
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 6)
            label = f"{part['name']} ({part['width']}x{part['height']})"
            c.drawCentredString(px + pw / 2, py + ph / 2, label[:48])

    c.showPage()
    draw_header(f"{design_name} - Parts List")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.black)

    columns = [
        ("#", 10 * mm),
        ("Part Name", 68 * mm),
        ("Width", 24 * mm),
        ("Height", 24 * mm),
        ("Sheet", 18 * mm),
        ("Rotated", 22 * mm),
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
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 8)
        for idx, value in enumerate(values):
            c.drawString(x_positions[idx] + 2 * mm, y - 5.5 * mm, str(value))
        y -= row_h

    draw_row([label for label, _ in columns], bold=True)
    for i, part in enumerate(parts, start=1):
        draw_row([
            i,
            part["name"],
            part["width"],
            part["height"],
            part.get("sheet", 0) + 1,
            "Yes" if part.get("rotated") else "No",
        ])

    c.save()
    buffer.seek(0)
    return buffer.getvalue()

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
    config = CNCConfig()
    parts = calculate_desk_parts(export_req.params)
    nesting = simple_nesting(parts, config.sheet_width, config.sheet_height)

    bundle_cfg = BUNDLE_OPTIONS[requested_bundle]
    bundle_files = bundle_cfg["files"]

    gcode_content = generate_full_gcode(nesting.parts, config, export_req.design_name) if "gcode" in bundle_files else ""
    dxf_content = generate_dxf(nesting.parts, config, export_req.design_name) if "dxf" in bundle_files else ""
    svg_content = generate_svg(nesting.parts, config, export_req.design_name) if "svg" in bundle_files else ""
    pdf_html = generate_pdf_html(nesting.parts, nesting, export_req.params, export_req.design_name) if "pdf" in bundle_files else ""

    export_id = str(uuid.uuid4())
    await db.exports.insert_one({
        "export_id": export_id,
        "user_id": user["id"],
        "design_name": export_req.design_name,
        "bundle": requested_bundle,
        "params": export_req.params.model_dump(),
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
        config = CNCConfig()
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
