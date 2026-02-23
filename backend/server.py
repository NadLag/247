from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Query, BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import secrets
import httpx
import random
import asyncio
import resend
import bcrypt
from icalendar import Calendar
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

stripe_api_key = os.environ.get('STRIPE_API_KEY')
resend_api_key = os.environ.get('RESEND_API_KEY')
sender_email = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')

# Initialize Resend
if resend_api_key:
    resend.api_key = resend_api_key

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== MODELS =====
class SessionExchange(BaseModel):
    session_id: str
    invitation_token: Optional[str] = None

class CompanySetup(BaseModel):
    name: str

class PropertyCreate(BaseModel):
    name: str
    address: str
    property_type: str = ""
    rooms: int = 0
    suites: int = 0
    bathrooms: int = 0
    city: str = ""
    country: str = ""
    notes: str = ""
    assigned_cohost: Optional[str] = None
    owner_first_name: str
    owner_last_name: str
    owner_phone: str
    owner_email: str
    units: int
    active: bool = True

class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    property_type: Optional[str] = None
    rooms: Optional[int] = None
    suites: Optional[int] = None
    bathrooms: Optional[int] = None
    city: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    assigned_cohost: Optional[str] = None
    owner_first_name: Optional[str] = None
    owner_last_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    units: Optional[int] = None
    active: Optional[bool] = None

class StaffCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: str
    salary: float = 0
    payment_terms: str = "Monthly"
    payment_type: str = "salary"
    staff_role: str = "housekeeper"
    per_checkin_rate: Optional[float] = None
    per_checkout_rate: Optional[float] = None
    assigned_properties: List[str] = []

class StaffUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    salary: Optional[float] = None
    payment_terms: Optional[str] = None
    payment_type: Optional[str] = None
    staff_role: Optional[str] = None
    per_checkin_rate: Optional[float] = None
    per_checkout_rate: Optional[float] = None
    assigned_properties: Optional[List[str]] = None
    active: Optional[bool] = None

class ExpenseCreate(BaseModel):
    property_id: str
    type: str
    category: str
    amount: float
    description: str
    date: str
    recurring: bool = False
    recurring_frequency: Optional[str] = None

class ExpenseUpdate(BaseModel):
    property_id: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    date: Optional[str] = None
    recurring: Optional[bool] = None
    recurring_frequency: Optional[str] = None

class BookingCreate(BaseModel):
    property_id: str
    guest_name: str
    check_in: str
    check_out: str
    total_amount: float
    guests_count: int = 1
    assigned_cohost: Optional[str] = None
    status: str = "confirmed"
    booking_type: str = "reservation"  # reservation | blocked
    force_override: bool = False  # Allow override of blocked dates

class BookingUpdate(BaseModel):
    guest_name: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    total_amount: Optional[float] = None
    guests_count: Optional[int] = None
    assigned_cohost: Optional[str] = None
    status: Optional[str] = None
    booking_type: Optional[str] = None

class InvitationCreate(BaseModel):
    email: str
    role: str
    name: Optional[str] = None
    assigned_properties: Optional[List[str]] = None
    permissions: Optional[Dict] = None

class CheckoutRequest(BaseModel):
    plan: str
    origin_url: str

class OTASyncEvent(BaseModel):
    source: str  # airbnb, booking, vrbo, etc.
    property_id: Optional[str] = None
    event_type: str  # booking_created, booking_updated, booking_cancelled, availability_sync
    data: Dict
    external_id: Optional[str] = None

class OTASyncLogResponse(BaseModel):
    id: str
    source: str
    event_type: str
    status: str
    message: Optional[str] = None
    created_at: str

# ===== OTA ICAL MODELS =====
class OTAFeedCreate(BaseModel):
    property_id: str
    source: str  # airbnb, booking.com, vrbo, expedia, other
    ical_url: str
    name: Optional[str] = None

class OTAFeedUpdate(BaseModel):
    source: Optional[str] = None
    ical_url: Optional[str] = None
    name: Optional[str] = None
    active: Optional[bool] = None

# ===== SERVICE MODELS =====
class ServiceCreate(BaseModel):
    name: str
    description: str = ""
    category: str  # airport_transfer, meals, excursions, cleaning, spa, tours, other
    price: float = 0
    price_type: str = "fixed"  # fixed, per_person, per_hour
    provider_type: str = "internal"  # internal (staff) or external (third-party)
    assigned_staff_id: Optional[str] = None
    external_provider_name: Optional[str] = None
    external_provider_phone: Optional[str] = None
    external_provider_email: Optional[str] = None
    active: bool = True

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    price_type: Optional[str] = None
    provider_type: Optional[str] = None
    assigned_staff_id: Optional[str] = None
    external_provider_name: Optional[str] = None
    external_provider_phone: Optional[str] = None
    external_provider_email: Optional[str] = None
    active: Optional[bool] = None

class BookingServiceCreate(BaseModel):
    booking_id: str
    service_id: str
    quantity: int = 1
    notes: Optional[str] = None
    scheduled_date: Optional[str] = None
    status: str = "pending"  # pending, confirmed, completed, cancelled

class BookingServiceUpdate(BaseModel):
    quantity: Optional[int] = None
    notes: Optional[str] = None
    scheduled_date: Optional[str] = None
    status: Optional[str] = None

# ===== REGISTRATION & AUTH MODELS =====
class InviteRegistration(BaseModel):
    token: str
    first_name: str
    last_name: str = ""
    email: str
    phone: str = ""
    password: str

class PasswordLogin(BaseModel):
    email: str
    password: str

# ===== TASK MODELS =====
class TaskCreate(BaseModel):
    title: str
    description: str = ""
    task_type: str = "general"  # cleaning, maintenance, check_in, check_out, admin, general
    property_id: Optional[str] = None
    booking_id: Optional[str] = None
    assigned_staff_id: str
    due_date: Optional[str] = None
    priority: str = "medium"  # low, medium, high, urgent

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[str] = None
    property_id: Optional[str] = None
    booking_id: Optional[str] = None
    assigned_staff_id: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None  # pending, in_progress, completed, cancelled

# ===== HELPERS =====
def booking_is_data_complete(booking: dict) -> bool:
    """Check if a booking has all required data (guest name and amount)"""
    guest_name = booking.get("guest_name")
    total_amount = booking.get("total_amount")
    has_guest = bool(guest_name and guest_name.strip())
    has_amount = total_amount is not None and total_amount > 0
    return has_guest and has_amount

async def check_and_create_incomplete_notification(company_id: str):
    """Check for incomplete iCal bookings and create/update notification"""
    incomplete_count = await db.bookings.count_documents({
        "company_id": company_id,
        "is_data_complete": False,
        "booking_type": "reservation",
        "status": {"$nin": ["cancelled", "blocked"]},
    })
    
    if incomplete_count == 0:
        # Auto-resolve any existing unresolved notifications of this type
        await db.notifications.update_many(
            {"company_id": company_id, "type": "incomplete_bookings", "resolved": {"$ne": True}},
            {"$set": {"read": True, "resolved": True, "resolved_at": datetime.now(timezone.utc).isoformat()}}
        )
        return
    
    # Check if there's already an unresolved notification
    existing = await db.notifications.find_one({
        "company_id": company_id,
        "type": "incomplete_bookings",
        "resolved": {"$ne": True},
    }, {"_id": 0})
    
    now_str = datetime.now(timezone.utc).isoformat()
    
    if existing:
        # Update the count
        await db.notifications.update_one(
            {"id": existing["id"]},
            {"$set": {
                "count": incomplete_count,
                "message": f"{incomplete_count} booking{'s' if incomplete_count != 1 else ''} require{'s' if incomplete_count == 1 else ''} guest name and/or amount.",
                "read": False,
                "updated_at": now_str,
            }}
        )
    else:
        # Create new notification
        await db.notifications.insert_one({
            "id": f"notif_{uuid.uuid4().hex[:12]}",
            "company_id": company_id,
            "type": "incomplete_bookings",
            "title": "Missing Booking Details",
            "message": f"{incomplete_count} booking{'s' if incomplete_count != 1 else ''} require{'s' if incomplete_count == 1 else ''} guest name and/or amount.",
            "count": incomplete_count,
            "action_url": "/bookings?filter=incomplete",
            "read": False,
            "resolved": False,
            "created_at": now_str,
            "updated_at": now_str,
        })

SUBSCRIPTION_EXEMPT_PATHS = ["/api/auth/", "/api/subscription/", "/api/companies/", "/api/webhook/", "/api/invitations/validate/", "/api/seed-demo-data"]

SUBSCRIPTION_PLANS = {
    "starter": {"name": "Starter", "price": 29.00, "max_properties": 5},
    "professional": {"name": "Professional", "price": 79.00, "max_properties": 20},
    "enterprise": {"name": "Enterprise", "price": 199.00, "max_properties": -1},
}

# ===== AUTH HELPER =====
async def get_current_user(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_doc = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return user_doc

async def require_admin(request: Request):
    user = await get_current_user(request)
    if user.get("role") != "company_admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_admin_or_owner(request: Request):
    user = await get_current_user(request)
    if user.get("role") not in ["company_admin", "owner"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return user

# ===== AUTH ROUTES =====
@api_router.post("/auth/session")
async def exchange_session(data: SessionExchange, response: Response):
    async with httpx.AsyncClient() as http_client:
        resp = await http_client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": data.session_id}
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session ID")

    auth_data = resp.json()
    email = auth_data["email"]
    name = auth_data["name"]
    picture = auth_data.get("picture", "")
    session_token = auth_data["session_token"]

    existing_user = await db.users.find_one({"email": email}, {"_id": 0})

    if existing_user:
        await db.users.update_one(
            {"email": email},
            {"$set": {"name": name, "picture": picture, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        user_id = existing_user["user_id"]
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        company_id = None
        role = None

        invitation = None
        if data.invitation_token:
            invitation = await db.invitations.find_one(
                {"token": data.invitation_token, "used": False}, {"_id": 0}
            )
        if not invitation:
            invitation = await db.invitations.find_one(
                {"email": email, "used": False}, {"_id": 0}
            )

        if invitation:
            exp = invitation.get("expires_at", "")
            if isinstance(exp, str):
                exp = datetime.fromisoformat(exp)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp >= datetime.now(timezone.utc):
                company_id = invitation["company_id"]
                role = invitation["role"]
                await db.invitations.update_one(
                    {"token": invitation["token"]},
                    {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}}
                )

        new_user = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "company_id": company_id,
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(new_user)

    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.user_sessions.insert_one(session_doc)

    response.set_cookie(
        key="session_token", value=session_token,
        httponly=True, secure=True, samesite="none", path="/", max_age=7 * 24 * 60 * 60,
    )

    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return user

@api_router.get("/auth/me")
async def get_me(user=Depends(get_current_user)):
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"message": "Logged out"}

# ===== PASSWORD-BASED REGISTRATION =====
@api_router.post("/auth/register-with-invite")
async def register_with_invite(data: InviteRegistration, response: Response):
    """Register a new user using an invitation token with password"""
    logger.info(f"Registration attempt for email: {data.email}")
    
    # Validate invitation
    invitation = await db.invitations.find_one({"token": data.token, "used": False}, {"_id": 0})
    if not invitation:
        logger.warning(f"Invalid or expired invitation token for email: {data.email}")
        raise HTTPException(status_code=404, detail="Invalid or expired invitation token")
    
    expires_at = invitation.get("expires_at", "")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        logger.warning(f"Invitation expired for email: {data.email}")
        raise HTTPException(status_code=400, detail="Invitation has expired")
    
    # Check if email matches
    if data.email.lower() != invitation["email"].lower():
        logger.warning(f"Email mismatch: {data.email} vs {invitation['email']}")
        raise HTTPException(status_code=400, detail="Email does not match invitation")
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": data.email.lower()}, {"_id": 0})
    if existing_user:
        logger.warning(f"User already exists: {data.email}")
        raise HTTPException(status_code=400, detail="User with this email already exists. Please sign in instead.")
    
    # Hash password
    password_hash = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create user with proper name handling
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    first_name = data.first_name.strip() if data.first_name else data.email.split('@')[0]
    last_name = data.last_name.strip() if data.last_name else ""
    full_name = f"{first_name} {last_name}".strip()
    
    new_user = {
        "user_id": user_id,
        "email": data.email.lower(),
        "name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "phone": data.phone or "",
        "password_hash": password_hash,
        "auth_method": "password",
        "picture": "",
        "company_id": invitation["company_id"],
        "role": invitation["role"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(new_user)
    logger.info(f"User created successfully: {user_id} with role {invitation['role']}")
    
    # Mark invitation as used
    await db.invitations.update_one(
        {"token": data.token},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": invitation["company_id"],
        "user_id": user_id,
        "action": "account_activated",
        "details": {"role": invitation["role"], "method": "password"},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    
    # Create session
    session_token = secrets.token_urlsafe(32)
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.user_sessions.insert_one(session_doc)
    
    response.set_cookie(
        key="session_token", value=session_token,
        httponly=True, secure=True, samesite="none", path="/", max_age=7 * 24 * 60 * 60,
    )
    
    # Return user without password_hash
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    return user

@api_router.post("/auth/login")
async def password_login(data: PasswordLogin, response: Response):
    """Login with email and password"""
    user = await db.users.find_one({"email": data.email.lower()}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check password
    password_hash = user.get("password_hash")
    if not password_hash:
        raise HTTPException(status_code=401, detail="Please sign in with Google")
    
    if not bcrypt.checkpw(data.password.encode('utf-8'), password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": f"audit_{uuid.uuid4().hex[:12]}",
        "company_id": user.get("company_id"),
        "user_id": user["user_id"],
        "action": "login",
        "details": {"method": "password"},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    
    # Create session
    session_token = secrets.token_urlsafe(32)
    session_doc = {
        "user_id": user["user_id"],
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.user_sessions.insert_one(session_doc)
    
    response.set_cookie(
        key="session_token", value=session_token,
        httponly=True, secure=True, samesite="none", path="/", max_age=7 * 24 * 60 * 60,
    )
    
    # Return user without password_hash
    user.pop("password_hash", None)
    return user

# ===== COMPANY ROUTES =====
@api_router.post("/companies/setup")
async def setup_company(data: CompanySetup, user=Depends(get_current_user)):
    if user.get("company_id"):
        raise HTTPException(status_code=400, detail="User already has a company")

    company_id = f"comp_{uuid.uuid4().hex[:12]}"
    company = {
        "company_id": company_id,
        "name": data.name,
        "subscription_status": "trial",
        "subscription_plan": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.companies.insert_one(company)

    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"company_id": company_id, "role": "company_admin", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    updated_user = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return updated_user

@api_router.get("/companies/me")
async def get_my_company(user=Depends(get_current_user)):
    if not user.get("company_id"):
        raise HTTPException(status_code=404, detail="No company found")
    company = await db.companies.find_one({"company_id": user["company_id"]}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

# ===== NOTIFICATION ROUTES =====
@api_router.get("/notifications")
async def list_notifications(user=Depends(get_current_user)):
    company_id = user.get("company_id")
    if not company_id:
        return []
    return await db.notifications.find(
        {"company_id": company_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)

@api_router.get("/notifications/unread-count")
async def get_unread_count(user=Depends(get_current_user)):
    company_id = user.get("company_id")
    if not company_id:
        return {"count": 0}
    count = await db.notifications.count_documents({"company_id": company_id, "read": False})
    return {"count": count}

@api_router.put("/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, user=Depends(get_current_user)):
    company_id = user.get("company_id")
    result = await db.notifications.update_one(
        {"id": notif_id, "company_id": company_id},
        {"$set": {"read": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}

@api_router.put("/notifications/read-all")
async def mark_all_read(user=Depends(get_current_user)):
    company_id = user.get("company_id")
    if not company_id:
        return {"message": "No company"}
    await db.notifications.update_many(
        {"company_id": company_id, "read": False},
        {"$set": {"read": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "All notifications marked as read"}

# ===== DASHBOARD ROUTES =====
@api_router.get("/dashboard/kpis")
async def get_dashboard_kpis(user=Depends(get_current_user)):
    company_id = user.get("company_id")
    role = user.get("role")
    user_email = user.get("email")
    
    if not company_id:
        return {"role": role, "revenue_mtd": 0, "revenue_last_month": 0, "net_income": 0, "occupancy_rate": 0,
                "nights_booked": 0, "adr": 0, "revpan": 0, "active_properties": 0,
                "total_properties": 0, "active_bookings": 0, "staff_payments_due": 0, "total_expenses": 0}

    now = datetime.now(timezone.utc)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    today_str = now.isoformat()[:10]

    # Role-based property filtering
    if role == "owner":
        properties = await db.properties.find({"company_id": company_id, "owner_email": user_email}, {"_id": 0}).to_list(1000)
        property_ids = [p["id"] for p in properties]
    elif role == "staff":
        staff_doc = await db.staff.find_one({"company_id": company_id, "email": user_email}, {"_id": 0})
        property_ids = staff_doc.get("assigned_properties", []) if staff_doc else []
        properties = await db.properties.find({"company_id": company_id, "id": {"$in": property_ids}}, {"_id": 0}).to_list(1000)
    else:
        properties = await db.properties.find({"company_id": company_id}, {"_id": 0}).to_list(1000)
        property_ids = [p["id"] for p in properties]

    # Build booking query based on role - EXCLUDE blocked dates from all KPIs
    booking_query = {"company_id": company_id}
    if role in ["owner", "staff"]:
        booking_query["property_id"] = {"$in": property_ids}
    
    # Exclude blocked dates from revenue calculations using booking_type
    reservation_filter = {
        "$or": [
            {"booking_type": "reservation"},
            {"booking_type": {"$exists": False}, "status": {"$nin": ["blocked", "overridden"]}}
        ]
    }
    
    current_bookings = await db.bookings.find(
        {**booking_query, **reservation_filter, "check_in": {"$gte": current_month_start.isoformat()[:10]}}, {"_id": 0}
    ).to_list(1000)
    last_bookings = await db.bookings.find(
        {**booking_query, **reservation_filter, "check_in": {"$gte": last_month_start.isoformat()[:10], "$lt": current_month_start.isoformat()[:10]}}, {"_id": 0}
    ).to_list(1000)

    # Only count non-cancelled bookings for revenue - exclude incomplete iCal bookings (amount=0)
    current_revenue = sum(b.get("total_amount", 0) for b in current_bookings if b.get("status") != "cancelled" and b.get("is_data_complete", True))
    last_revenue = sum(b.get("total_amount", 0) for b in last_bookings if b.get("status") != "cancelled" and b.get("is_data_complete", True))

    # Expenses query based on role
    expense_query = {"company_id": company_id, "date": {"$gte": current_month_start.isoformat()[:10]}}
    if role in ["owner", "staff"]:
        expense_query["property_id"] = {"$in": property_ids}
    current_expenses = await db.expenses.find(expense_query, {"_id": 0}).to_list(1000)
    total_expenses = sum(e.get("amount", 0) for e in current_expenses)

    active_properties = len([p for p in properties if p.get("active", True)])
    total_units = sum(p.get("units", 0) for p in properties)

    # Only count real bookings (not blocked) for active bookings
    active_bookings_query = {
        **booking_query, 
        **reservation_filter,
        "status": {"$in": ["confirmed", "checked_in"]}
    }
    active_bookings = await db.bookings.count_documents(active_bookings_query)

    # Only count nights from real reservations (not blocked)
    nights_booked = 0
    for b in current_bookings:
        if b.get("status") == "cancelled":
            continue
        try:
            ci = datetime.fromisoformat(b["check_in"])
            co = datetime.fromisoformat(b["check_out"])
            nights_booked += (co - ci).days
        except Exception:
            pass

    if current_month_start.month == 12:
        days_in_month = 31
    else:
        days_in_month = (current_month_start.replace(month=current_month_start.month + 1) - current_month_start).days
    total_available_nights = total_units * days_in_month
    occupancy_rate = (nights_booked / total_available_nights * 100) if total_available_nights > 0 else 0
    adr = (current_revenue / nights_booked) if nights_booked > 0 else 0
    revpan = (current_revenue / total_available_nights) if total_available_nights > 0 else 0

    # Staff-specific: calculate their earnings
    staff_payments_due = 0
    staff_earnings = 0
    tasks_completed = 0
    upcoming_tasks = 0
    
    if role == "company_admin":
        staff_list = await db.staff.find({"company_id": company_id, "active": True}, {"_id": 0}).to_list(1000)
        staff_payments_due = sum(s.get("salary", 0) for s in staff_list)
    elif role == "staff":
        staff_doc = await db.staff.find_one({"company_id": company_id, "email": user_email}, {"_id": 0})
        if staff_doc:
            # Calculate earnings based on payment type
            if staff_doc.get("payment_type") == "per_job":
                checkin_rate = staff_doc.get("per_checkin_rate", 0) or 0
                checkout_rate = staff_doc.get("per_checkout_rate", 0) or 0
                # Count completed check-ins and check-outs this month
                checkouts_this_month = await db.bookings.count_documents({
                    "company_id": company_id,
                    "property_id": {"$in": property_ids},
                    "check_out": {"$gte": current_month_start.isoformat()[:10], "$lte": today_str},
                    "status": "checked_out"
                })
                checkins_this_month = await db.bookings.count_documents({
                    "company_id": company_id,
                    "property_id": {"$in": property_ids},
                    "check_in": {"$gte": current_month_start.isoformat()[:10], "$lte": today_str},
                    "status": {"$in": ["checked_in", "checked_out"]}
                })
                staff_earnings = (checkins_this_month * checkin_rate) + (checkouts_this_month * checkout_rate)
                tasks_completed = checkins_this_month + checkouts_this_month
            else:
                staff_earnings = staff_doc.get("salary", 0)
            
            # Calculate upcoming tasks (check-ins/check-outs in next 7 days)
            next_week = (now + timedelta(days=7)).isoformat()[:10]
            upcoming_tasks = await db.bookings.count_documents({
                "company_id": company_id,
                "property_id": {"$in": property_ids},
                "$or": [
                    {"check_in": {"$gte": today_str, "$lte": next_week}, "status": "confirmed"},
                    {"check_out": {"$gte": today_str, "$lte": next_week}, "status": "checked_in"}
                ]
            })

    base_response = {
        "role": role,
        "revenue_mtd": round(current_revenue, 2),
        "revenue_last_month": round(last_revenue, 2),
        "net_income": round(current_revenue - total_expenses, 2),
        "occupancy_rate": round(occupancy_rate, 1),
        "nights_booked": nights_booked,
        "adr": round(adr, 2),
        "revpan": round(revpan, 2),
        "active_properties": active_properties,
        "total_properties": len(properties),
        "active_bookings": active_bookings,
        "staff_payments_due": round(staff_payments_due, 2),
        "total_expenses": round(total_expenses, 2),
    }
    
    # Add role-specific fields
    if role == "staff":
        base_response["staff_earnings"] = round(staff_earnings, 2)
        base_response["tasks_completed"] = tasks_completed
        base_response["upcoming_tasks"] = upcoming_tasks
    
    return base_response

@api_router.get("/dashboard/revenue-trends")
async def get_revenue_trends(user=Depends(get_current_user)):
    company_id = user.get("company_id")
    if not company_id:
        return []
    now = datetime.now(timezone.utc)
    trends = []
    for i in range(6):
        month_date = now - timedelta(days=30 * i)
        month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1)

        bookings = await db.bookings.find(
            {"company_id": company_id, "check_in": {"$gte": month_start.isoformat()[:10], "$lt": next_month_start.isoformat()[:10]}}, {"_id": 0}
        ).to_list(1000)
        expenses = await db.expenses.find(
            {"company_id": company_id, "date": {"$gte": month_start.isoformat()[:10], "$lt": next_month_start.isoformat()[:10]}}, {"_id": 0}
        ).to_list(1000)

        revenue = sum(b.get("total_amount", 0) for b in bookings)
        expense_total = sum(e.get("amount", 0) for e in expenses)
        trends.append({"month": month_start.strftime("%b %Y"), "revenue": round(revenue, 2), "expenses": round(expense_total, 2), "net_income": round(revenue - expense_total, 2)})
    trends.reverse()
    return trends

# ===== PROPERTY ROUTES =====
@api_router.get("/properties")
async def list_properties(user=Depends(get_current_user)):
    company_id = user.get("company_id")
    if not company_id:
        return []
    query = {"company_id": company_id}
    if user.get("role") == "owner":
        query["owner_email"] = user.get("email")
    properties = await db.properties.find(query, {"_id": 0}).to_list(1000)
    return properties

@api_router.post("/properties", status_code=201)
async def create_property(data: PropertyCreate, user=Depends(require_admin)):
    prop = {
        "id": f"prop_{uuid.uuid4().hex[:12]}",
        "company_id": user["company_id"],
        **data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.properties.insert_one(prop)
    return await db.properties.find_one({"id": prop["id"]}, {"_id": 0})

@api_router.get("/properties/{prop_id}")
async def get_property(prop_id: str, user=Depends(get_current_user)):
    """Get a single property by ID"""
    company_id = user.get("company_id")
    if not company_id:
        raise HTTPException(status_code=404, detail="Property not found")
    prop = await db.properties.find_one({"id": prop_id, "company_id": company_id}, {"_id": 0})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop

@api_router.put("/properties/{prop_id}")
async def update_property(prop_id: str, data: PropertyUpdate, user=Depends(require_admin)):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.properties.update_one({"id": prop_id, "company_id": user["company_id"]}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Property not found")
    return await db.properties.find_one({"id": prop_id}, {"_id": 0})

@api_router.delete("/properties/{prop_id}")
async def delete_property(prop_id: str, user=Depends(require_admin)):
    result = await db.properties.delete_one({"id": prop_id, "company_id": user["company_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"message": "Property deleted"}

# ===== STAFF ROUTES =====
@api_router.get("/staff")
async def list_staff(user=Depends(get_current_user)):
    company_id = user.get("company_id")
    if not company_id:
        return []
    if user.get("role") == "staff":
        return await db.staff.find({"company_id": company_id, "email": user["email"]}, {"_id": 0}).to_list(10)
    return await db.staff.find({"company_id": company_id}, {"_id": 0}).to_list(1000)

@api_router.post("/staff", status_code=201)
async def create_staff(data: StaffCreate, user=Depends(require_admin)):
    staff = {
        "id": f"staff_{uuid.uuid4().hex[:12]}",
        "company_id": user["company_id"],
        **data.model_dump(),
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.staff.insert_one(staff)
    return await db.staff.find_one({"id": staff["id"]}, {"_id": 0})

@api_router.get("/staff/cohosts")
async def list_cohosts(user=Depends(get_current_user)):
    company_id = user.get("company_id")
    if not company_id:
        return []
    return await db.staff.find({"company_id": company_id, "staff_role": "co_host", "active": True}, {"_id": 0}).to_list(1000)

@api_router.put("/staff/{staff_id}")
async def update_staff(staff_id: str, data: StaffUpdate, user=Depends(require_admin)):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.staff.update_one({"id": staff_id, "company_id": user["company_id"]}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Staff not found")
    return await db.staff.find_one({"id": staff_id}, {"_id": 0})

@api_router.delete("/staff/{staff_id}")
async def delete_staff(staff_id: str, user=Depends(require_admin)):
    result = await db.staff.delete_one({"id": staff_id, "company_id": user["company_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"message": "Staff deleted"}

# ===== EXPENSE ROUTES =====
@api_router.get("/expenses")
async def list_expenses(
    user=Depends(get_current_user),
    property_id: Optional[str] = None,
    expense_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    company_id = user.get("company_id")
    if not company_id:
        return []
    query = {"company_id": company_id}
    if property_id:
        query["property_id"] = property_id
    if expense_type:
        query["type"] = expense_type
    if date_from or date_to:
        date_q = {}
        if date_from:
            date_q["$gte"] = date_from
        if date_to:
            date_q["$lte"] = date_to
        query["date"] = date_q
    return await db.expenses.find(query, {"_id": 0}).to_list(1000)

@api_router.post("/expenses", status_code=201)
async def create_expense(data: ExpenseCreate, user=Depends(require_admin)):
    expense = {
        "id": f"exp_{uuid.uuid4().hex[:12]}",
        "company_id": user["company_id"],
        **data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.expenses.insert_one(expense)
    return await db.expenses.find_one({"id": expense["id"]}, {"_id": 0})

@api_router.put("/expenses/{expense_id}")
async def update_expense(expense_id: str, data: ExpenseUpdate, user=Depends(require_admin)):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.expenses.update_one({"id": expense_id, "company_id": user["company_id"]}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Expense not found")
    return await db.expenses.find_one({"id": expense_id}, {"_id": 0})

@api_router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str, user=Depends(require_admin)):
    result = await db.expenses.delete_one({"id": expense_id, "company_id": user["company_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"message": "Expense deleted"}

# ===== BOOKING ROUTES =====
@api_router.get("/bookings")
async def list_bookings(
    user=Depends(get_current_user),
    include_blocked: bool = False,
    source: Optional[str] = None,
    incomplete_only: bool = False
):
    """List bookings. By default, blocked dates are excluded from the list."""
    company_id = user.get("company_id")
    if not company_id:
        return []
    
    # Auto-update expired bookings to checked_out
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db.bookings.update_many(
        {
            "company_id": company_id,
            "check_out": {"$lt": today},
            "status": {"$in": ["confirmed", "checked_in"]},
            "booking_type": {"$ne": "blocked"}
        },
        {"$set": {"status": "checked_out", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    query = {"company_id": company_id}
    if not include_blocked:
        query["$or"] = [
            {"booking_type": {"$ne": "blocked"}},
            {"booking_type": {"$exists": False}, "status": {"$ne": "blocked"}}
        ]
    
    # Filter by source
    if source:
        if source == "direct":
            query["$and"] = query.get("$and", []) + [
                {"$or": [{"ota_source": "manual"}, {"ota_source": None}, {"ota_source": {"$exists": False}}]}
            ]
        else:
            query["ota_source"] = source
    
    # Filter incomplete bookings only
    if incomplete_only:
        query["is_data_complete"] = False
        query["booking_type"] = "reservation"
    
    return await db.bookings.find(query, {"_id": 0}).sort("check_in", -1).to_list(1000)

@api_router.get("/bookings/sources")
async def list_booking_sources(user=Depends(get_current_user)):
    """Get unique booking sources for filter dropdown"""
    company_id = user.get("company_id")
    if not company_id:
        return []
    
    # Get distinct sources
    sources = await db.bookings.distinct("ota_source", {"company_id": company_id, "booking_type": {"$ne": "blocked"}})
    # Also check for manual bookings without ota_source
    has_manual = await db.bookings.count_documents({
        "company_id": company_id, 
        "booking_type": {"$ne": "blocked"},
        "$or": [{"ota_source": None}, {"ota_source": {"$exists": False}}, {"ota_source": "manual"}]
    })
    
    result = []
    if has_manual > 0:
        result.append({"value": "direct", "label": "Direct Booking"})
    for source in sources:
        if source and source not in [None, "manual"]:
            result.append({"value": source, "label": source.title()})
    
    return result

@api_router.get("/bookings/blocked-dates")
async def list_blocked_dates(user=Depends(get_current_user), property_id: Optional[str] = None):
    """Get blocked dates only - for calendar display"""
    company_id = user.get("company_id")
    if not company_id:
        return []
    
    query = {
        "company_id": company_id,
        "$or": [
            {"booking_type": "blocked"},
            {"status": "blocked", "booking_type": {"$exists": False}}  # Backwards compat
        ]
    }
    if property_id:
        query["property_id"] = property_id
    
    return await db.bookings.find(query, {"_id": 0}).sort("check_in", 1).to_list(1000)

@api_router.post("/bookings", status_code=201)
async def create_booking(data: BookingCreate, user=Depends(require_admin)):
    company_id = user["company_id"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Validate check-in date is not in the past for manual bookings
    if data.check_in and data.check_in < today:
        raise HTTPException(
            status_code=400,
            detail="Check-in date cannot be in the past. Please select today or a future date."
        )
    
    # Validate check-out date is not in the past
    if data.check_out and data.check_out < today:
        raise HTTPException(
            status_code=400,
            detail="Check-out date cannot be in the past. Please select today or a future date."
        )
    
    # Validate check-out is after check-in
    if data.check_in and data.check_out and data.check_out <= data.check_in:
        raise HTTPException(
            status_code=400,
            detail="Check-out date must be after check-in date."
        )
    
    # Check for overlapping blocked dates
    if data.property_id and data.check_in and data.check_out and not data.force_override:
        overlapping_blocked = await db.bookings.find_one({
            "company_id": company_id,
            "property_id": data.property_id,
            "$or": [
                {"booking_type": "blocked"},
                {"status": "blocked", "booking_type": {"$exists": False}}
            ],
            "$and": [
                {"check_in": {"$lt": data.check_out}},
                {"check_out": {"$gt": data.check_in}}
            ]
        }, {"_id": 0})
        
        if overlapping_blocked:
            raise HTTPException(
                status_code=409,  # Conflict status
                detail={
                    "message": "This date range overlaps with blocked/unavailable dates.",
                    "blocked_period": {
                        "check_in": overlapping_blocked.get("check_in"),
                        "check_out": overlapping_blocked.get("check_out")
                    },
                    "requires_override": True
                }
            )
    
    # If force_override, handle blocked date override
    if data.force_override and data.property_id and data.check_in and data.check_out:
        # Find and update overlapping blocked dates to "overridden"
        overlapping_result = await db.bookings.update_many(
            {
                "company_id": company_id,
                "property_id": data.property_id,
                "$or": [
                    {"booking_type": "blocked"},
                    {"status": "blocked", "booking_type": {"$exists": False}}
                ],
                "$and": [
                    {"check_in": {"$lt": data.check_out}},
                    {"check_out": {"$gt": data.check_in}}
                ]
            },
            {"$set": {
                "status": "overridden",
                "booking_type": "blocked",  # Keep type as blocked
                "overridden_at": datetime.now(timezone.utc).isoformat(),
                "overridden_by": user.get("user_id")
            }}
        )
        
        # Log the override action
        if overlapping_result.modified_count > 0:
            await db.audit_logs.insert_one({
                "id": f"audit_{uuid.uuid4().hex[:12]}",
                "company_id": company_id,
                "user_id": user.get("user_id"),
                "user_email": user.get("email"),
                "action": "booking_override",
                "details": {
                    "property_id": data.property_id,
                    "check_in": data.check_in,
                    "check_out": data.check_out,
                    "guest_name": data.guest_name,
                    "blocked_periods_overridden": overlapping_result.modified_count
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    # Create the booking
    booking_data = data.model_dump()
    booking_data.pop("force_override", None)  # Remove force_override from stored data
    
    booking = {
        "id": f"book_{uuid.uuid4().hex[:12]}",
        "company_id": company_id,
        **booking_data,
        "booking_type": "reservation",  # Manual bookings are always reservations
        "ota_source": "manual",
        "is_data_complete": True,  # Manual bookings have all data
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.bookings.insert_one(booking)
    return await db.bookings.find_one({"id": booking["id"]}, {"_id": 0})

@api_router.put("/bookings/{booking_id}")
async def update_booking(booking_id: str, data: BookingUpdate, user=Depends(require_admin)):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Recalculate is_data_complete after update
    existing = await db.bookings.find_one({"id": booking_id, "company_id": user["company_id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    merged = {**existing, **update_data}
    update_data["is_data_complete"] = booking_is_data_complete(merged)
    
    await db.bookings.update_one({"id": booking_id, "company_id": user["company_id"]}, {"$set": update_data})
    
    # Re-check incomplete notifications for this company
    await check_and_create_incomplete_notification(user["company_id"])
    
    return await db.bookings.find_one({"id": booking_id}, {"_id": 0})

@api_router.get("/bookings/by-status")
async def list_bookings_by_status(user=Depends(get_current_user)):
    """Get bookings grouped by status with today's check-ins highlighted"""
    company_id = user.get("company_id")
    if not company_id:
        return {"checked_in_today": [], "upcoming": [], "confirmed": [], "checked_out": [], "cancelled": []}
    
    today = datetime.now(timezone.utc).isoformat()[:10]
    
    all_bookings = await db.bookings.find({"company_id": company_id}, {"_id": 0}).to_list(1000)
    
    result = {
        "checked_in_today": [],
        "upcoming": [],
        "confirmed": [],
        "checked_out": [],
        "cancelled": []
    }
    
    for b in all_bookings:
        check_in = b.get("check_in", "")
        status = b.get("status", "")
        
        if status == "cancelled":
            result["cancelled"].append(b)
        elif status == "checked_out":
            result["checked_out"].append(b)
        elif status == "checked_in":
            # Currently checked in - check if check-in was today
            if check_in == today:
                result["checked_in_today"].append(b)
            else:
                result["confirmed"].append(b)  # Show in confirmed as "in-house"
        elif status == "confirmed":
            if check_in == today:
                result["checked_in_today"].append(b)  # Due to check in today
            elif check_in > today:
                result["upcoming"].append(b)
            else:
                result["confirmed"].append(b)
    
    # Sort each list by check_in date
    for key in result:
        result[key].sort(key=lambda x: x.get("check_in", ""), reverse=(key in ["checked_out", "cancelled"]))
    
    return result

# ===== TASK ROUTES =====
@api_router.get("/tasks")
async def list_tasks(
    user=Depends(get_current_user),
    status: Optional[str] = None,
    assigned_to_me: bool = False,
    property_id: Optional[str] = None
):
    """List tasks - admin sees all, staff sees only their assigned tasks"""
    company_id = user.get("company_id")
    if not company_id:
        return []
    
    query = {"company_id": company_id}
    
    # Staff can only see their own tasks
    if user.get("role") == "staff" or assigned_to_me:
        staff_doc = await db.staff.find_one({"company_id": company_id, "email": user.get("email")}, {"_id": 0})
        if staff_doc:
            query["assigned_staff_id"] = staff_doc["id"]
        else:
            return []
    
    if status:
        query["status"] = status
    if property_id:
        query["property_id"] = property_id
    
    tasks = await db.tasks.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Enrich with staff and property names
    for task in tasks:
        if task.get("assigned_staff_id"):
            staff = await db.staff.find_one({"id": task["assigned_staff_id"]}, {"_id": 0})
            if staff:
                task["assigned_staff_name"] = f"{staff.get('first_name', '')} {staff.get('last_name', '')}"
        if task.get("property_id"):
            prop = await db.properties.find_one({"id": task["property_id"]}, {"_id": 0})
            if prop:
                task["property_name"] = prop.get("name", "")
    
    return tasks

@api_router.post("/tasks", status_code=201)
async def create_task(data: TaskCreate, user=Depends(require_admin)):
    """Create a new task (admin only)"""
    # Validate assigned staff exists
    staff = await db.staff.find_one({"id": data.assigned_staff_id, "company_id": user["company_id"]}, {"_id": 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Assigned staff not found")
    
    # Validate property if provided
    if data.property_id:
        prop = await db.properties.find_one({"id": data.property_id, "company_id": user["company_id"]}, {"_id": 0})
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
    
    task = {
        "id": f"task_{uuid.uuid4().hex[:12]}",
        "company_id": user["company_id"],
        **data.model_dump(),
        "status": "pending",
        "created_by": user["user_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.tasks.insert_one(task)
    
    # Add staff name to response
    task["assigned_staff_name"] = f"{staff.get('first_name', '')} {staff.get('last_name', '')}"
    return await db.tasks.find_one({"id": task["id"]}, {"_id": 0})

@api_router.put("/tasks/{task_id}")
async def update_task(task_id: str, data: TaskUpdate, user=Depends(get_current_user)):
    """Update task - admin can update all fields, staff can only update status"""
    task = await db.tasks.find_one({"id": task_id, "company_id": user["company_id"]}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Staff can only update their own tasks' status
    if user.get("role") == "staff":
        staff_doc = await db.staff.find_one({"company_id": user["company_id"], "email": user.get("email")}, {"_id": 0})
        if not staff_doc or task.get("assigned_staff_id") != staff_doc["id"]:
            raise HTTPException(status_code=403, detail="You can only update your own tasks")
        # Staff can only update status
        update_data = {"status": data.status} if data.status else {}
    else:
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if not update_data:
        return task
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # If status changed to completed, log completion time
    if update_data.get("status") == "completed" and task.get("status") != "completed":
        update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
        update_data["completed_by"] = user["user_id"]
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    return await db.tasks.find_one({"id": task_id}, {"_id": 0})

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, user=Depends(require_admin)):
    """Delete task (admin only)"""
    result = await db.tasks.delete_one({"id": task_id, "company_id": user["company_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted"}

@api_router.get("/tasks/my-summary")
async def get_my_task_summary(user=Depends(get_current_user)):
    """Get task summary for staff member"""
    if user.get("role") != "staff":
        return {"pending": 0, "in_progress": 0, "completed_this_month": 0, "total": 0}
    
    company_id = user.get("company_id")
    staff_doc = await db.staff.find_one({"company_id": company_id, "email": user.get("email")}, {"_id": 0})
    if not staff_doc:
        return {"pending": 0, "in_progress": 0, "completed_this_month": 0, "total": 0}
    
    staff_id = staff_doc["id"]
    current_month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()[:10]
    
    pending = await db.tasks.count_documents({"company_id": company_id, "assigned_staff_id": staff_id, "status": "pending"})
    in_progress = await db.tasks.count_documents({"company_id": company_id, "assigned_staff_id": staff_id, "status": "in_progress"})
    completed = await db.tasks.count_documents({
        "company_id": company_id, 
        "assigned_staff_id": staff_id, 
        "status": "completed",
        "completed_at": {"$gte": current_month_start}
    })
    total = await db.tasks.count_documents({"company_id": company_id, "assigned_staff_id": staff_id})
    
    return {"pending": pending, "in_progress": in_progress, "completed_this_month": completed, "total": total}

# ===== STAFF EARNINGS & PAYOUTS =====
@api_router.get("/staff/my-earnings")
async def get_my_earnings(user=Depends(get_current_user)):
    """Get earnings summary for staff member"""
    if user.get("role") != "staff":
        raise HTTPException(status_code=403, detail="Staff access only")
    
    company_id = user.get("company_id")
    staff_doc = await db.staff.find_one({"company_id": company_id, "email": user.get("email")}, {"_id": 0})
    if not staff_doc:
        raise HTTPException(status_code=404, detail="Staff record not found")
    
    now = datetime.now(timezone.utc)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    today_str = now.isoformat()[:10]
    
    # Calculate earnings based on payment type
    if staff_doc.get("payment_type") == "per_job":
        checkin_rate = staff_doc.get("per_checkin_rate", 0) or 0
        checkout_rate = staff_doc.get("per_checkout_rate", 0) or 0
        
        # Count check-ins/check-outs from bookings
        property_ids = staff_doc.get("assigned_properties", [])
        checkins = await db.bookings.count_documents({
            "company_id": company_id,
            "property_id": {"$in": property_ids},
            "check_in": {"$gte": current_month_start.isoformat()[:10], "$lte": today_str},
            "status": {"$in": ["checked_in", "checked_out"]}
        })
        checkouts = await db.bookings.count_documents({
            "company_id": company_id,
            "property_id": {"$in": property_ids},
            "check_out": {"$gte": current_month_start.isoformat()[:10], "$lte": today_str},
            "status": "checked_out"
        })
        
        earnings_mtd = (checkins * checkin_rate) + (checkouts * checkout_rate)
        payment_structure = f"${checkin_rate}/check-in, ${checkout_rate}/check-out"
    else:
        earnings_mtd = staff_doc.get("salary", 0)
        payment_structure = f"${staff_doc.get('salary', 0)}/{staff_doc.get('payment_terms', 'Monthly')}"
    
    # Get payout history
    payouts = await db.payouts.find(
        {"company_id": company_id, "staff_id": staff_doc["id"]}, 
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    return {
        "staff_id": staff_doc["id"],
        "name": f"{staff_doc.get('first_name', '')} {staff_doc.get('last_name', '')}",
        "role": staff_doc.get("staff_role", ""),
        "payment_type": staff_doc.get("payment_type", "salary"),
        "payment_structure": payment_structure,
        "earnings_mtd": round(earnings_mtd, 2),
        "payment_status": "pending",  # Would be calculated based on payouts
        "next_payout_date": "End of month",
        "payouts": payouts,
    }

# ===== SERVICE ROUTES =====
@api_router.get("/services")
async def list_services(user=Depends(get_current_user), category: Optional[str] = None, active_only: bool = True):
    company_id = user.get("company_id")
    if not company_id:
        return []
    query = {"company_id": company_id}
    if category:
        query["category"] = category
    if active_only:
        query["active"] = True
    return await db.services.find(query, {"_id": 0}).to_list(1000)

@api_router.post("/services", status_code=201)
async def create_service(data: ServiceCreate, user=Depends(require_admin)):
    service = {
        "id": f"svc_{uuid.uuid4().hex[:12]}",
        "company_id": user["company_id"],
        **data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.services.insert_one(service)
    return await db.services.find_one({"id": service["id"]}, {"_id": 0})

@api_router.put("/services/{service_id}")
async def update_service(service_id: str, data: ServiceUpdate, user=Depends(require_admin)):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.services.update_one({"id": service_id, "company_id": user["company_id"]}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Service not found")
    return await db.services.find_one({"id": service_id}, {"_id": 0})

@api_router.delete("/services/{service_id}")
async def delete_service(service_id: str, user=Depends(require_admin)):
    result = await db.services.delete_one({"id": service_id, "company_id": user["company_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"message": "Service deleted"}

# ===== BOOKING SERVICES (Add-ons) =====
@api_router.get("/booking-services/{booking_id}")
async def list_booking_services(booking_id: str, user=Depends(get_current_user)):
    company_id = user.get("company_id")
    if not company_id:
        return []
    # Verify booking belongs to company
    booking = await db.bookings.find_one({"id": booking_id, "company_id": company_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking_services = await db.booking_services.find({"booking_id": booking_id}, {"_id": 0}).to_list(100)
    # Enrich with service details
    for bs in booking_services:
        service = await db.services.find_one({"id": bs["service_id"]}, {"_id": 0})
        if service:
            bs["service_name"] = service.get("name")
            bs["service_price"] = service.get("price")
            bs["service_category"] = service.get("category")
    return booking_services

@api_router.post("/booking-services", status_code=201)
async def add_booking_service(data: BookingServiceCreate, user=Depends(require_admin)):
    # Verify booking and service belong to company
    booking = await db.bookings.find_one({"id": data.booking_id, "company_id": user["company_id"]}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    service = await db.services.find_one({"id": data.service_id, "company_id": user["company_id"]}, {"_id": 0})
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    booking_service = {
        "id": f"bsvc_{uuid.uuid4().hex[:12]}",
        "company_id": user["company_id"],
        **data.model_dump(),
        "total_price": service.get("price", 0) * data.quantity,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.booking_services.insert_one(booking_service)
    return await db.booking_services.find_one({"id": booking_service["id"]}, {"_id": 0})

@api_router.put("/booking-services/{bs_id}")
async def update_booking_service(bs_id: str, data: BookingServiceUpdate, user=Depends(require_admin)):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Recalculate total price if quantity changed
    if "quantity" in update_data:
        bs = await db.booking_services.find_one({"id": bs_id, "company_id": user["company_id"]}, {"_id": 0})
        if bs:
            service = await db.services.find_one({"id": bs["service_id"]}, {"_id": 0})
            if service:
                update_data["total_price"] = service.get("price", 0) * update_data["quantity"]
    
    result = await db.booking_services.update_one({"id": bs_id, "company_id": user["company_id"]}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking service not found")
    return await db.booking_services.find_one({"id": bs_id}, {"_id": 0})

@api_router.delete("/booking-services/{bs_id}")
async def delete_booking_service(bs_id: str, user=Depends(require_admin)):
    result = await db.booking_services.delete_one({"id": bs_id, "company_id": user["company_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking service not found")
    return {"message": "Booking service deleted"}

# ===== ANALYTICS ROUTES =====
@api_router.get("/analytics")
async def get_analytics(
    user=Depends(get_current_user),
    property_id: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """Get comprehensive analytics with comparison to previous period"""
    company_id = user.get("company_id")
    if not company_id:
        return {"current": {}, "previous": {}, "trends": []}
    
    now = datetime.now(timezone.utc)
    
    # Default to current month/year
    target_year = year or now.year
    target_month = month or now.month
    
    # Calculate date ranges
    current_month_start = datetime(target_year, target_month, 1, tzinfo=timezone.utc)
    if target_month == 12:
        current_month_end = datetime(target_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        current_month_end = datetime(target_year, target_month + 1, 1, tzinfo=timezone.utc)
    
    # Previous month
    if target_month == 1:
        prev_month_start = datetime(target_year - 1, 12, 1, tzinfo=timezone.utc)
        prev_month_end = current_month_start
    else:
        prev_month_start = datetime(target_year, target_month - 1, 1, tzinfo=timezone.utc)
        prev_month_end = current_month_start
    
    # Build query filters
    base_query = {"company_id": company_id}
    if property_id:
        base_query["property_id"] = property_id
    
    # Get properties for the query
    prop_query = {"company_id": company_id}
    if property_id:
        prop_query["id"] = property_id
    properties = await db.properties.find(prop_query, {"_id": 0}).to_list(1000)
    property_ids = [p["id"] for p in properties]
    total_units = sum(p.get("units", 0) for p in properties)
    active_properties = len([p for p in properties if p.get("active", True)])
    
    # Helper to calculate metrics for a period
    async def calc_period_metrics(start: datetime, end: datetime):
        booking_query = {**base_query, "check_in": {"$gte": start.isoformat()[:10], "$lt": end.isoformat()[:10]}}
        if property_id:
            booking_query["property_id"] = property_id
        else:
            booking_query["property_id"] = {"$in": property_ids}
        
        # Exclude blocked dates from analytics
        booking_query["status"] = {"$ne": "blocked"}
        bookings = await db.bookings.find(booking_query, {"_id": 0}).to_list(1000)
        
        expense_query = {"company_id": company_id, "date": {"$gte": start.isoformat()[:10], "$lt": end.isoformat()[:10]}}
        if property_id:
            expense_query["property_id"] = property_id
        expenses = await db.expenses.find(expense_query, {"_id": 0}).to_list(1000)
        
        # Only count non-blocked, non-cancelled bookings for revenue
        revenue = sum(b.get("total_amount", 0) for b in bookings if b.get("status") not in ["blocked", "cancelled"])
        expense_total = sum(e.get("amount", 0) for e in expenses)
        
        nights_booked = 0
        for b in bookings:
            if b.get("status") in ["blocked", "cancelled"]:
                continue
            try:
                ci = datetime.fromisoformat(b["check_in"])
                co = datetime.fromisoformat(b["check_out"])
                nights_booked += (co - ci).days
            except (ValueError, KeyError):
                pass
        
        days_in_month = (end - start).days
        total_available_nights = total_units * days_in_month
        occupancy_rate = (nights_booked / total_available_nights * 100) if total_available_nights > 0 else 0
        adr = (revenue / nights_booked) if nights_booked > 0 else 0
        revpan = (revenue / total_available_nights) if total_available_nights > 0 else 0
        
        return {
            "revenue": round(revenue, 2),
            "expenses": round(expense_total, 2),
            "net_income": round(revenue - expense_total, 2),
            "occupancy_rate": round(occupancy_rate, 1),
            "nights_booked": nights_booked,
            "adr": round(adr, 2),
            "revpan": round(revpan, 2),
            "active_bookings": len([b for b in bookings if b.get("status") in ["confirmed", "checked_in"]]),
            "total_bookings": len([b for b in bookings if b.get("status") != "blocked"]),
            "active_properties": active_properties,
            "total_properties": len(properties),
        }
    
    current_metrics = await calc_period_metrics(current_month_start, current_month_end)
    previous_metrics = await calc_period_metrics(prev_month_start, prev_month_end)
    
    # Calculate percentage changes
    def calc_change(curr, prev):
        if prev == 0:
            return 100 if curr > 0 else 0
        return round(((curr - prev) / prev) * 100, 1)
    
    changes = {
        "revenue_change": calc_change(current_metrics["revenue"], previous_metrics["revenue"]),
        "expenses_change": calc_change(current_metrics["expenses"], previous_metrics["expenses"]),
        "occupancy_change": calc_change(current_metrics["occupancy_rate"], previous_metrics["occupancy_rate"]),
        "adr_change": calc_change(current_metrics["adr"], previous_metrics["adr"]),
        "bookings_change": calc_change(current_metrics["total_bookings"], previous_metrics["total_bookings"]),
    }
    
    # Get 12-month trends
    trends = []
    for i in range(11, -1, -1):
        trend_date = now - timedelta(days=30 * i)
        trend_month_start = trend_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if trend_month_start.month == 12:
            trend_month_end = trend_month_start.replace(year=trend_month_start.year + 1, month=1)
        else:
            trend_month_end = trend_month_start.replace(month=trend_month_start.month + 1)
        
        trend_metrics = await calc_period_metrics(trend_month_start, trend_month_end)
        trends.append({
            "month": trend_month_start.strftime("%b %Y"),
            "month_num": trend_month_start.month,
            "year": trend_month_start.year,
            **trend_metrics
        })
    
    return {
        "current": current_metrics,
        "previous": previous_metrics,
        "changes": changes,
        "trends": trends,
        "period": {
            "current_month": current_month_start.strftime("%B %Y"),
            "previous_month": prev_month_start.strftime("%B %Y"),
        }
    }

@api_router.get("/analytics/source-breakdown")
async def get_source_breakdown(
    user=Depends(get_current_user),
    property_id: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """Get booking analytics broken down by source (Airbnb, Booking.com, Direct, etc.)"""
    company_id = user.get("company_id")
    if not company_id:
        return {"sources": [], "total_bookings": 0, "total_revenue": 0}
    
    now = datetime.now(timezone.utc)
    target_year = year or now.year
    target_month = month or now.month
    
    month_start = datetime(target_year, target_month, 1, tzinfo=timezone.utc)
    if target_month == 12:
        month_end = datetime(target_year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        month_end = datetime(target_year, target_month + 1, 1, tzinfo=timezone.utc)
    
    query = {
        "company_id": company_id,
        "check_in": {"$gte": month_start.isoformat()[:10], "$lt": month_end.isoformat()[:10]},
        "booking_type": {"$ne": "blocked"},
        "status": {"$nin": ["blocked", "cancelled"]},
    }
    if property_id:
        query["property_id"] = property_id
    
    bookings = await db.bookings.find(query, {"_id": 0, "ota_source": 1, "total_amount": 1, "check_in": 1, "check_out": 1}).to_list(5000)
    
    source_map = {}
    for b in bookings:
        src = b.get("ota_source") or "manual"
        label = "Direct" if src == "manual" else src.replace("_", " ").replace(".", ".").title()
        if label not in source_map:
            source_map[label] = {"label": label, "key": src, "bookings": 0, "revenue": 0, "nights": 0}
        source_map[label]["bookings"] += 1
        source_map[label]["revenue"] += b.get("total_amount", 0) or 0
        try:
            ci = datetime.fromisoformat(b["check_in"])
            co = datetime.fromisoformat(b["check_out"])
            source_map[label]["nights"] += max((co - ci).days, 0)
        except Exception:
            pass
    
    sources = sorted(source_map.values(), key=lambda s: s["revenue"], reverse=True)
    total_bookings = sum(s["bookings"] for s in sources)
    total_revenue = sum(s["revenue"] for s in sources)
    
    for s in sources:
        s["booking_pct"] = round((s["bookings"] / total_bookings * 100), 1) if total_bookings > 0 else 0
        s["revenue_pct"] = round((s["revenue"] / total_revenue * 100), 1) if total_revenue > 0 else 0
        s["revenue"] = round(s["revenue"], 2)
    
    return {
        "sources": sources,
        "total_bookings": total_bookings,
        "total_revenue": round(total_revenue, 2),
    }

@api_router.get("/invitations")
async def list_invitations(user=Depends(require_admin)):
    return await db.invitations.find({"company_id": user["company_id"]}, {"_id": 0}).to_list(1000)

async def send_invitation_email(email: str, role: str, token: str, company_name: str, inviter_name: str, base_url: str):
    """Send invitation email using Resend"""
    if not resend_api_key:
        logger.warning("Resend API key not configured, skipping email send")
        return False
    
    invite_link = f"{base_url}/invite/{token}"
    role_display = "Property Owner" if role == "owner" else "Staff Member"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f4f4f5;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
            <tr>
                <td style="padding: 40px 30px; text-align: center; background: linear-gradient(135deg, #1e293b 0%, #334155 100%);">
                    <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">PropStack</h1>
                    <p style="margin: 8px 0 0; color: #94a3b8; font-size: 14px;">Property & Hospitality Management</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 40px 30px;">
                    <h2 style="margin: 0 0 16px; color: #1e293b; font-size: 20px; font-weight: 600;">You're Invited!</h2>
                    <p style="margin: 0 0 24px; color: #64748b; font-size: 16px; line-height: 1.6;">
                        <strong>{inviter_name}</strong> has invited you to join <strong>{company_name}</strong> as a <strong>{role_display}</strong>.
                    </p>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                        <tr>
                            <td style="padding: 20px; background-color: #f8fafc; border-radius: 8px; border-left: 4px solid #3b82f6;">
                                <p style="margin: 0 0 8px; color: #1e293b; font-size: 14px; font-weight: 600;">Your Role: {role_display}</p>
                                <p style="margin: 0; color: #64748b; font-size: 14px;">
                                    {"View financials, properties, and analytics for your portfolio." if role == "owner" else "Access assigned properties, manage bookings, and track your tasks."}
                                </p>
                            </td>
                        </tr>
                    </table>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top: 32px;">
                        <tr>
                            <td style="text-align: center;">
                                <a href="{invite_link}" style="display: inline-block; padding: 14px 32px; background-color: #3b82f6; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: 600; border-radius: 8px;">Accept Invitation</a>
                            </td>
                        </tr>
                    </table>
                    <p style="margin: 24px 0 0; color: #94a3b8; font-size: 13px; text-align: center;">
                        Or copy this link: <br>
                        <span style="color: #64748b; word-break: break-all;">{invite_link}</span>
                    </p>
                    <p style="margin: 24px 0 0; color: #94a3b8; font-size: 13px; text-align: center;">
                        This invitation expires in 7 days.
                    </p>
                </td>
            </tr>
            <tr>
                <td style="padding: 24px 30px; background-color: #f8fafc; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0; color: #94a3b8; font-size: 12px;">
                        © {datetime.now().year} PropStack. Smart Property Operations.
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": sender_email,
            "to": [email],
            "subject": f"You're invited to join {company_name} on PropStack",
            "html": html_content
        }
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Invitation email sent to {email}, ID: {result.get('id')}")
        return True
    except Exception as e:
        logger.error(f"Failed to send invitation email to {email}: {str(e)}")
        return False

@api_router.post("/invitations", status_code=201)
async def create_invitation(data: InvitationCreate, request: Request, background_tasks: BackgroundTasks, user=Depends(require_admin)):
    if data.role not in ["owner", "staff"]:
        raise HTTPException(status_code=400, detail="Role must be 'owner' or 'staff'")
    existing = await db.invitations.find_one(
        {"email": data.email, "company_id": user["company_id"], "used": False}, {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Invitation already pending for this email")

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    invitation = {
        "id": f"inv_{uuid.uuid4().hex[:12]}",
        "company_id": user["company_id"],
        "email": data.email,
        "name": data.name or "",
        "role": data.role,
        "assigned_properties": data.assigned_properties or [],
        "permissions": data.permissions or {},
        "token": token,
        "status": "pending",
        "used": False,
        "email_sent": False,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.invitations.insert_one(invitation)
    
    # Get company and user info for email
    company = await db.companies.find_one({"company_id": user["company_id"]}, {"_id": 0})
    company_name = company.get("name", "Your Company") if company else "Your Company"
    inviter_name = user.get("name", user.get("email", "Admin"))
    
    # Get base URL from request
    base_url = str(request.base_url).rstrip("/")
    if "/api" in base_url:
        base_url = base_url.split("/api")[0]
    
    # Send email in background
    background_tasks.add_task(
        send_invitation_email_and_update,
        invitation["id"],
        data.email,
        data.role,
        token,
        company_name,
        inviter_name,
        base_url
    )
    
    return await db.invitations.find_one({"id": invitation["id"]}, {"_id": 0})

async def send_invitation_email_and_update(inv_id: str, email: str, role: str, token: str, company_name: str, inviter_name: str, base_url: str):
    """Send email and update invitation status"""
    success = await send_invitation_email(email, role, token, company_name, inviter_name, base_url)
    if success:
        await db.invitations.update_one({"id": inv_id}, {"$set": {"email_sent": True}})

@api_router.post("/invitations/{inv_id}/resend")
async def resend_invitation_email(inv_id: str, request: Request, background_tasks: BackgroundTasks, user=Depends(require_admin)):
    """Resend invitation email"""
    invitation = await db.invitations.find_one({"id": inv_id, "company_id": user["company_id"], "used": False}, {"_id": 0})
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found or already used")
    
    company = await db.companies.find_one({"company_id": user["company_id"]}, {"_id": 0})
    company_name = company.get("name", "Your Company") if company else "Your Company"
    inviter_name = user.get("name", user.get("email", "Admin"))
    base_url = str(request.base_url).rstrip("/").split("/api")[0]
    
    background_tasks.add_task(
        send_invitation_email_and_update,
        inv_id,
        invitation["email"],
        invitation["role"],
        invitation["token"],
        company_name,
        inviter_name,
        base_url
    )
    
    return {"message": "Invitation email queued for resend"}

@api_router.delete("/invitations/{inv_id}")
async def delete_invitation(inv_id: str, user=Depends(require_admin)):
    result = await db.invitations.delete_one({"id": inv_id, "company_id": user["company_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return {"message": "Invitation deleted"}

@api_router.get("/invitations/validate/{token}")
async def validate_invitation(token: str):
    """Validate invitation token and return pre-filled user data"""
    # First check if invitation exists (including used ones)
    invitation = await db.invitations.find_one({"token": token}, {"_id": 0})
    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    
    # Check if already used
    if invitation.get("used", False):
        return {
            "email": invitation["email"],
            "role": invitation["role"],
            "company_name": "",
            "company_id": invitation["company_id"],
            "first_name": "",
            "last_name": "",
            "phone": "",
            "token": token,
            "used": True,
        }
    
    expires_at = invitation.get("expires_at", "")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invitation has expired")
    
    company = await db.companies.find_one({"company_id": invitation["company_id"]}, {"_id": 0})
    
    # Get pre-filled user info from staff or property owner records
    first_name = ""
    last_name = ""
    phone = ""
    
    if invitation["role"] == "staff":
        # Look for staff record with this email
        staff = await db.staff.find_one({"company_id": invitation["company_id"], "email": invitation["email"]}, {"_id": 0})
        if staff:
            first_name = staff.get("first_name", "")
            last_name = staff.get("last_name", "")
            phone = staff.get("phone", "")
    elif invitation["role"] == "owner":
        # Look for property with this owner email
        prop = await db.properties.find_one({"company_id": invitation["company_id"], "owner_email": invitation["email"]}, {"_id": 0})
        if prop:
            first_name = prop.get("owner_first_name", "")
            last_name = prop.get("owner_last_name", "")
            phone = prop.get("owner_phone", "")
    
    return {
        "email": invitation["email"],
        "role": invitation["role"],
        "company_name": company.get("name", "Unknown") if company else "Unknown",
        "company_id": invitation["company_id"],
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone,
        "token": token,
        "used": invitation.get("used", False),
    }

# ===== SUBSCRIPTION ROUTES =====
@api_router.post("/subscription/checkout")
async def create_checkout(data: CheckoutRequest, request: Request, user=Depends(require_admin)):
    if data.plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")
    plan = SUBSCRIPTION_PLANS[data.plan]
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest as StripeCSR

    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)

    success_url = f"{data.origin_url}/billing?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{data.origin_url}/billing"

    checkout_request = StripeCSR(
        amount=plan["price"], currency="usd",
        success_url=success_url, cancel_url=cancel_url,
        metadata={"company_id": user["company_id"], "user_id": user["user_id"], "plan": data.plan, "plan_name": plan["name"]},
    )
    session = await stripe_checkout.create_checkout_session(checkout_request)

    transaction = {
        "id": f"txn_{uuid.uuid4().hex[:12]}",
        "company_id": user["company_id"],
        "user_id": user["user_id"],
        "session_id": session.session_id,
        "amount": plan["price"],
        "currency": "usd",
        "plan": data.plan,
        "payment_status": "pending",
        "status": "initiated",
        "metadata": {"company_id": user["company_id"], "plan": data.plan},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.payment_transactions.insert_one(transaction)
    return {"url": session.url, "session_id": session.session_id}

@api_router.get("/subscription/status/{session_id}")
async def get_checkout_status(session_id: str, request: Request, user=Depends(get_current_user)):
    from emergentintegrations.payments.stripe.checkout import StripeCheckout

    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    status = await stripe_checkout.get_checkout_status(session_id)

    if status.payment_status == "paid":
        txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if txn and txn.get("payment_status") != "paid":
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "paid", "status": "completed", "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            await db.companies.update_one(
                {"company_id": user["company_id"]},
                {"$set": {"subscription_status": "active", "subscription_plan": txn.get("plan", "starter"), "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
    elif status.status == "expired":
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "expired", "status": "expired", "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
    return {"status": status.status, "payment_status": status.payment_status, "amount_total": status.amount_total, "currency": status.currency}

@api_router.get("/subscription/current")
async def get_current_subscription(user=Depends(get_current_user)):
    company = await db.companies.find_one({"company_id": user.get("company_id")}, {"_id": 0})
    if not company:
        return {"subscription_status": "none", "subscription_plan": None}
    return {"subscription_status": company.get("subscription_status", "trial"), "subscription_plan": company.get("subscription_plan"), "company_name": company.get("name")}

@api_router.get("/subscription/plans")
async def get_plans():
    return SUBSCRIPTION_PLANS

# ===== WEBHOOK =====
@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    try:
        from emergentintegrations.payments.stripe.checkout import StripeCheckout
        body = await request.body()
        signature = request.headers.get("Stripe-Signature")
        host_url = str(request.base_url).rstrip("/")
        webhook_url = f"{host_url}/api/webhook/stripe"
        stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        if webhook_response.payment_status == "paid":
            session_id = webhook_response.session_id
            txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
            if txn and txn.get("payment_status") != "paid":
                await db.payment_transactions.update_one(
                    {"session_id": session_id},
                    {"$set": {"payment_status": "paid", "status": "completed", "updated_at": datetime.now(timezone.utc).isoformat()}},
                )
                await db.companies.update_one(
                    {"company_id": txn.get("company_id")},
                    {"$set": {"subscription_status": "active", "subscription_plan": txn.get("plan", "starter"), "updated_at": datetime.now(timezone.utc).isoformat()}},
                )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "detail": str(e)}

# ===== OTA SYNC WEBHOOK =====
async def process_ota_sync(log_id: str, event: OTASyncEvent, company_id: str):
    """Background task to process OTA sync events"""
    try:
        logger.info(f"Processing OTA sync: {event.source} - {event.event_type}")
        
        if event.event_type == "booking_created":
            # Create a new booking from OTA data
            booking_data = event.data
            booking = {
                "id": f"book_{uuid.uuid4().hex[:12]}",
                "company_id": company_id,
                "property_id": event.property_id,
                "guest_name": booking_data.get("guest_name", "OTA Guest"),
                "check_in": booking_data.get("check_in"),
                "check_out": booking_data.get("check_out"),
                "total_amount": booking_data.get("total_amount", 0),
                "guests_count": booking_data.get("guests_count", 1),
                "status": "confirmed",
                "ota_source": event.source,
                "ota_external_id": event.external_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.bookings.insert_one(booking)
            await db.ota_sync_logs.update_one(
                {"id": log_id},
                {"$set": {"status": "completed", "message": f"Booking {booking['id']} created", "processed_at": datetime.now(timezone.utc).isoformat()}}
            )
            
        elif event.event_type == "booking_updated":
            # Update existing booking
            if event.external_id:
                existing = await db.bookings.find_one({"ota_external_id": event.external_id, "company_id": company_id}, {"_id": 0})
                if existing:
                    update_data = {k: v for k, v in event.data.items() if k in ["check_in", "check_out", "total_amount", "guests_count"]}
                    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                    await db.bookings.update_one({"id": existing["id"]}, {"$set": update_data})
                    await db.ota_sync_logs.update_one(
                        {"id": log_id},
                        {"$set": {"status": "completed", "message": f"Booking {existing['id']} updated", "processed_at": datetime.now(timezone.utc).isoformat()}}
                    )
                else:
                    await db.ota_sync_logs.update_one(
                        {"id": log_id},
                        {"$set": {"status": "failed", "message": "Booking not found for update", "processed_at": datetime.now(timezone.utc).isoformat()}}
                    )
                    
        elif event.event_type == "booking_cancelled":
            if event.external_id:
                result = await db.bookings.update_one(
                    {"ota_external_id": event.external_id, "company_id": company_id},
                    {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                if result.modified_count > 0:
                    await db.ota_sync_logs.update_one(
                        {"id": log_id},
                        {"$set": {"status": "completed", "message": "Booking cancelled", "processed_at": datetime.now(timezone.utc).isoformat()}}
                    )
                else:
                    await db.ota_sync_logs.update_one(
                        {"id": log_id},
                        {"$set": {"status": "failed", "message": "Booking not found for cancellation", "processed_at": datetime.now(timezone.utc).isoformat()}}
                    )
                    
        elif event.event_type == "availability_sync":
            # Just log availability sync requests for now
            await db.ota_sync_logs.update_one(
                {"id": log_id},
                {"$set": {"status": "completed", "message": "Availability sync acknowledged", "processed_at": datetime.now(timezone.utc).isoformat()}}
            )
        else:
            await db.ota_sync_logs.update_one(
                {"id": log_id},
                {"$set": {"status": "failed", "message": f"Unknown event type: {event.event_type}", "processed_at": datetime.now(timezone.utc).isoformat()}}
            )
            
    except Exception as e:
        logger.error(f"OTA sync processing error: {e}")
        await db.ota_sync_logs.update_one(
            {"id": log_id},
            {"$set": {"status": "failed", "message": str(e), "processed_at": datetime.now(timezone.utc).isoformat()}}
        )

@api_router.post("/ota-webhook/{company_id}")
async def ota_sync_webhook(company_id: str, event: OTASyncEvent, background_tasks: BackgroundTasks, request: Request):
    """Receive sync events from OTAs (Airbnb, Booking.com, VRBO, etc.)"""
    # Validate company exists
    company = await db.companies.find_one({"company_id": company_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Validate property if provided
    if event.property_id:
        prop = await db.properties.find_one({"id": event.property_id, "company_id": company_id}, {"_id": 0})
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
    
    # Create sync log
    log_id = f"ota_{uuid.uuid4().hex[:12]}"
    sync_log = {
        "id": log_id,
        "company_id": company_id,
        "source": event.source,
        "property_id": event.property_id,
        "event_type": event.event_type,
        "external_id": event.external_id,
        "data": event.data,
        "status": "pending",
        "message": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "processed_at": None,
    }
    await db.ota_sync_logs.insert_one(sync_log)
    
    # Process in background
    background_tasks.add_task(process_ota_sync, log_id, event, company_id)
    
    return {"status": "received", "log_id": log_id}

@api_router.get("/ota-sync-logs")
async def list_ota_sync_logs(
    user=Depends(require_admin),
    status: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 50
):
    """List OTA sync logs for the company"""
    query = {"company_id": user["company_id"]}
    if status:
        query["status"] = status
    if source:
        query["source"] = source
    
    logs = await db.ota_sync_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return logs

# ===== OTA ICAL FEEDS MANAGEMENT =====
OTA_SOURCES = ["airbnb", "booking.com", "vrbo", "expedia", "other"]

# Mock iCal data generator for testing
def generate_mock_ical(property_name: str, source: str) -> str:
    """Generate mock iCal data for testing"""
    now = datetime.now(timezone.utc)
    events = []
    
    guest_names = ["Emma Thompson", "James Wilson", "Sophie Chen", "Michael Brown", "Olivia Garcia"]
    
    # Generate 2-4 random bookings
    for i in range(random.randint(2, 4)):
        check_in_offset = random.randint(1, 45)
        nights = random.randint(2, 7)
        check_in = now + timedelta(days=check_in_offset)
        check_out = check_in + timedelta(days=nights)
        guest = random.choice(guest_names)
        uid = f"{source.replace('.', '-')}_{uuid.uuid4().hex[:8]}@propstack.com"
        
        event_lines = [
            "BEGIN:VEVENT",
            f"DTSTART;VALUE=DATE:{check_in.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{check_out.strftime('%Y%m%d')}",
            f"SUMMARY:{guest} - {property_name}",
            f"UID:{uid}",
            f"DESCRIPTION:Guest booking from {source}",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ]
        events.append("\r\n".join(event_lines))
    
    cal_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PropStack//OTA Sync//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{property_name} - {source}",
    ]
    
    ical_content = "\r\n".join(cal_lines) + "\r\n" + "\r\n".join(events) + "\r\nEND:VCALENDAR"
    
    return ical_content

async def fetch_ical_data(url: str) -> str:
    """Fetch iCal data from URL or generate mock data"""
    # Check if this is a mock URL
    if url.startswith("mock://"):
        # Parse mock URL: mock://airbnb/PropertyName
        parts = url.replace("mock://", "").split("/", 1)
        source = parts[0] if parts else "airbnb"
        prop_name = parts[1] if len(parts) > 1 else "Property"
        return generate_mock_ical(prop_name, source)
    
    # Real URL fetch
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.error(f"Failed to fetch iCal from {url}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch iCal data: {str(e)}")

def parse_ical_bookings(ical_content: str, source: str, property_id: str) -> List[Dict]:
    """Parse iCal content and extract booking events"""
    bookings = []
    skipped_count = 0
    blocked_count = 0
    try:
        cal = Calendar.from_ical(ical_content)
        
        for component in cal.walk():
            if component.name == "VEVENT":
                # Extract booking data
                dtstart = component.get('DTSTART')
                dtend = component.get('DTEND')
                summary = str(component.get('SUMMARY', 'Guest'))
                uid = str(component.get('UID', f"{source}_{uuid.uuid4().hex[:8]}"))
                status = str(component.get('STATUS', 'CONFIRMED')).upper()
                description = str(component.get('DESCRIPTION', ''))
                
                if not dtstart or not dtend:
                    logger.debug(f"Skipping event without dates: {summary}")
                    skipped_count += 1
                    continue
                
                # Convert dates
                check_in = dtstart.dt if hasattr(dtstart, 'dt') else dtstart
                check_out = dtend.dt if hasattr(dtend, 'dt') else dtend
                
                # Handle datetime vs date
                if hasattr(check_in, 'date'):
                    check_in = check_in.date()
                if hasattr(check_out, 'date'):
                    check_out = check_out.date()
                
                # Calculate nights
                nights = (check_out - check_in).days
                if nights <= 0:
                    logger.debug(f"Skipping zero/negative night booking: {summary}")
                    skipped_count += 1
                    continue
                
                # Check for blocked/unavailable dates - import as blocked type (NOT a booking)
                summary_lower = summary.lower()
                is_blocked = any(blocked in summary_lower for blocked in ['blocked', 'unavailable', 'not available'])
                
                if is_blocked:
                    # Import as blocked date - NOT a real booking
                    bookings.append({
                        "uid": uid,
                        "guest_name": None,  # No guest for blocked dates
                        "check_in": check_in.isoformat() if hasattr(check_in, 'isoformat') else str(check_in),
                        "check_out": check_out.isoformat() if hasattr(check_out, 'isoformat') else str(check_out),
                        "nights": nights,
                        "status": "blocked",  # Keep for backwards compat, but booking_type is primary
                        "booking_type": "blocked",  # NEW: Primary type indicator
                        "source": source,
                        "property_id": property_id,
                        "description": f"Blocked: {summary}",
                        "total_amount": 0,  # Blocked dates have no revenue
                    })
                    blocked_count += 1
                    continue
                
                # Extract guest name from summary
                # Airbnb uses "Reserved" for actual bookings
                if summary.lower() == 'reserved':
                    guest_name = "Airbnb Guest"
                elif ' - ' in summary:
                    guest_name = summary.split(' - ')[0].strip()
                else:
                    guest_name = summary.strip()
                
                # Determine booking status from iCal status
                booking_status = "confirmed"
                if status == "CANCELLED":
                    booking_status = "cancelled"
                elif status == "TENTATIVE":
                    booking_status = "pending"
                
                bookings.append({
                    "uid": uid,
                    "guest_name": guest_name[:100],
                    "check_in": check_in.isoformat() if hasattr(check_in, 'isoformat') else str(check_in),
                    "check_out": check_out.isoformat() if hasattr(check_out, 'isoformat') else str(check_out),
                    "nights": nights,
                    "status": booking_status,
                    "booking_type": "reservation",  # NEW: Real booking
                    "source": source,
                    "property_id": property_id,
                    "description": description[:500],
                })
        
        logger.info(f"Parsed iCal: {len(bookings)} total ({len(bookings) - blocked_count} bookings, {blocked_count} blocked), {skipped_count} skipped")
                
    except Exception as e:
        logger.error(f"Failed to parse iCal content: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse iCal data: {str(e)}")
    
    return bookings

async def process_ical_booking(booking_data: Dict, company_id: str, feed_id: str) -> Dict:
    """Process a single booking from iCal - create, update, or skip"""
    uid = booking_data["uid"]
    property_id = booking_data["property_id"]
    
    # Check if booking already exists by UID or date range + property
    existing = await db.bookings.find_one({
        "company_id": company_id,
        "$or": [
            {"ota_external_id": uid},
            {
                "property_id": property_id,
                "check_in": booking_data["check_in"],
                "check_out": booking_data["check_out"],
                "ota_source": {"$exists": True}
            }
        ]
    }, {"_id": 0})
    
    now_str = datetime.now(timezone.utc).isoformat()
    
    if existing:
        # Check if cancelled
        if booking_data["status"] == "cancelled":
            await db.bookings.update_one(
                {"id": existing["id"]},
                {"$set": {"status": "cancelled", "updated_at": now_str}}
            )
            return {"action": "cancelled", "booking_id": existing["id"]}
        
        # Update if dates changed
        if existing["check_in"] != booking_data["check_in"] or existing["check_out"] != booking_data["check_out"]:
            await db.bookings.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "check_in": booking_data["check_in"],
                    "check_out": booking_data["check_out"],
                    "guest_name": booking_data["guest_name"],
                    "updated_at": now_str
                }}
            )
            return {"action": "updated", "booking_id": existing["id"]}
        
        return {"action": "skipped", "booking_id": existing["id"], "reason": "no_changes"}
    
    # Create new booking
    if booking_data["status"] == "cancelled":
        return {"action": "skipped", "reason": "cancelled_not_found"}
    
    booking_id = f"book_{uuid.uuid4().hex[:12]}"
    booking_type = booking_data.get("booking_type", "reservation")
    
    new_booking = {
        "id": booking_id,
        "company_id": company_id,
        "property_id": property_id,
        "guest_name": booking_data["guest_name"] if booking_type == "reservation" else None,
        "check_in": booking_data["check_in"],
        "check_out": booking_data["check_out"],
        "total_amount": booking_data.get("total_amount", 0) if booking_type == "reservation" else 0,
        "guests_count": 1 if booking_type == "reservation" else 0,
        "status": booking_data.get("status", "confirmed"),
        "booking_type": booking_type,  # NEW: reservation or blocked
        "ota_source": booking_data["source"],
        "ota_external_id": uid,
        "ota_feed_id": feed_id,
        "is_data_complete": booking_is_data_complete({
            "guest_name": booking_data["guest_name"] if booking_type == "reservation" else None,
            "total_amount": booking_data.get("total_amount", 0) if booking_type == "reservation" else 0,
        }) if booking_type == "reservation" else True,
        "imported_at": now_str,
        "created_at": now_str,
        "updated_at": now_str,
    }
    await db.bookings.insert_one(new_booking)
    return {"action": "created", "booking_id": booking_id, "booking_type": booking_type}

async def sync_ota_feeds_background(company_id: str, sync_log_id: str):
    """Background task to sync all OTA feeds for a company"""
    try:
        logger.info(f"Starting OTA iCal sync for company {company_id}")
        
        # Get all active feeds
        feeds = await db.ota_feeds.find({"company_id": company_id, "active": True}, {"_id": 0}).to_list(100)
        
        if not feeds:
            await db.ota_sync_logs.update_one(
                {"id": sync_log_id},
                {"$set": {"status": "completed", "message": "No active OTA feeds configured", "processed_at": datetime.now(timezone.utc).isoformat()}}
            )
            return
        
        total_created = 0
        total_updated = 0
        total_cancelled = 0
        total_skipped = 0
        errors = []
        properties_synced = set()
        
        for feed in feeds:
            try:
                # Fetch iCal data
                ical_content = await fetch_ical_data(feed["ical_url"])
                
                # Parse bookings
                bookings = parse_ical_bookings(ical_content, feed["source"], feed["property_id"])
                
                # Process each booking
                for booking_data in bookings:
                    result = await process_ical_booking(booking_data, company_id, feed["id"])
                    
                    if result["action"] == "created":
                        total_created += 1
                    elif result["action"] == "updated":
                        total_updated += 1
                    elif result["action"] == "cancelled":
                        total_cancelled += 1
                    else:
                        total_skipped += 1
                
                # Update feed's last sync timestamp
                await db.ota_feeds.update_one(
                    {"id": feed["id"]},
                    {"$set": {"last_sync_at": datetime.now(timezone.utc).isoformat(), "last_sync_status": "success"}}
                )
                properties_synced.add(feed["property_id"])
                
            except Exception as e:
                logger.error(f"Error syncing feed {feed['id']}: {e}")
                errors.append(f"{feed['source']}: {str(e)}")
                await db.ota_feeds.update_one(
                    {"id": feed["id"]},
                    {"$set": {"last_sync_at": datetime.now(timezone.utc).isoformat(), "last_sync_status": "error", "last_sync_error": str(e)}}
                )
        
        # Update properties' last sync timestamp
        if properties_synced:
            await db.properties.update_many(
                {"id": {"$in": list(properties_synced)}, "company_id": company_id},
                {"$set": {"last_ota_sync_at": datetime.now(timezone.utc).isoformat()}}
            )
        
        # Update sync log
        status = "completed" if not errors else "completed_with_errors"
        message = f"Created: {total_created}, Updated: {total_updated}, Cancelled: {total_cancelled}, Skipped: {total_skipped}"
        if errors:
            message += f" | Errors: {'; '.join(errors[:3])}"
        
        await db.ota_sync_logs.update_one(
            {"id": sync_log_id},
            {"$set": {
                "status": status,
                "message": message,
                "stats": {
                    "created": total_created,
                    "updated": total_updated,
                    "cancelled": total_cancelled,
                    "skipped": total_skipped,
                    "feeds_processed": len(feeds),
                    "properties_synced": len(properties_synced),
                    "errors": len(errors)
                },
                "processed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        logger.info(f"OTA sync completed for company {company_id}: {message}")
        
        # Check for incomplete bookings and create notification
        await check_and_create_incomplete_notification(company_id)
        
    except Exception as e:
        logger.error(f"OTA sync background task failed: {e}")
        await db.ota_sync_logs.update_one(
            {"id": sync_log_id},
            {"$set": {"status": "failed", "message": str(e), "processed_at": datetime.now(timezone.utc).isoformat()}}
        )

# Global sync lock to prevent parallel syncs
_sync_locks = {}

@api_router.post("/ota/sync")
async def trigger_ota_sync(background_tasks: BackgroundTasks, user=Depends(require_admin)):
    """Trigger OTA iCal sync for all configured feeds - Single button sync"""
    company_id = user["company_id"]
    
    # Check for existing running sync
    if company_id in _sync_locks and _sync_locks[company_id]:
        raise HTTPException(status_code=429, detail="Sync already in progress. Please wait.")
    
    # Set lock
    _sync_locks[company_id] = True
    
    try:
        # Check if feeds exist
        feed_count = await db.ota_feeds.count_documents({"company_id": company_id, "active": True})
        if feed_count == 0:
            _sync_locks[company_id] = False
            return {"status": "no_feeds", "message": "No OTA feeds configured. Add feeds in OTA Settings first."}
        
        # Create sync log
        sync_log_id = f"ota_sync_{uuid.uuid4().hex[:12]}"
        sync_log = {
            "id": sync_log_id,
            "company_id": company_id,
            "source": "ical_sync",
            "event_type": "bulk_sync",
            "status": "processing",
            "message": "Sync in progress...",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "processed_at": None,
        }
        await db.ota_sync_logs.insert_one(sync_log)
        
        # Start background sync
        async def run_sync_and_release():
            try:
                await sync_ota_feeds_background(company_id, sync_log_id)
            finally:
                _sync_locks[company_id] = False
        
        background_tasks.add_task(run_sync_and_release)
        
        return {
            "status": "started",
            "sync_id": sync_log_id,
            "message": f"Syncing {feed_count} OTA feed(s) in background...",
            "feeds_count": feed_count
        }
        
    except Exception as e:
        _sync_locks[company_id] = False
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/ota/sync-status")
async def get_ota_sync_status(user=Depends(require_admin)):
    """Get the latest sync status"""
    company_id = user["company_id"]
    
    # Get most recent sync log
    latest_log = await db.ota_sync_logs.find_one(
        {"company_id": company_id, "event_type": "bulk_sync"},
        {"_id": 0},
        sort=[("created_at", -1)]
    )
    
    # Get feed count
    feed_count = await db.ota_feeds.count_documents({"company_id": company_id, "active": True})
    
    # Check if sync is running
    is_syncing = _sync_locks.get(company_id, False)
    
    return {
        "is_syncing": is_syncing,
        "feeds_count": feed_count,
        "latest_sync": latest_log
    }

# ===== OTA IMPORT - CREATE PROPERTY FROM ICAL =====
class OTAImportRequest(BaseModel):
    name: str
    source: str
    ical_url: str

@api_router.post("/ota/import-property")
async def import_property_from_ota(data: OTAImportRequest, user=Depends(require_admin)):
    """Create a NEW property from OTA iCal URL and import all bookings"""
    company_id = user["company_id"]
    
    logger.info(f"OTA import: Creating property '{data.name}' from {data.source}")
    
    try:
        # Fetch iCal data
        ical_content = await fetch_ical_data(data.ical_url)
        
        # Parse bookings to get count
        bookings_data = parse_ical_bookings(ical_content, data.source, "temp")
        
        # Create new property
        property_id = f"prop_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now(timezone.utc).isoformat()
        
        new_property = {
            "id": property_id,
            "company_id": company_id,
            "name": data.name.strip(),
            "address": "",
            "property_type": "",
            "rooms": 0,
            "suites": 0,
            "bathrooms": 0,
            "city": "",
            "country": "",
            "notes": f"Imported from {data.source}",
            "owner_first_name": "",
            "owner_last_name": "",
            "owner_phone": "",
            "owner_email": "",
            "assigned_cohost": None,
            "units": 1,
            "active": True,
            "ota_source": data.source,
            "ota_ical_url": data.ical_url,
            "last_ota_sync_at": now_str,
            "created_at": now_str,
            "updated_at": now_str,
        }
        await db.properties.insert_one(new_property)
        logger.info(f"Created property: {property_id}")
        
        # Create OTA feed for future syncs
        feed_id = f"feed_{uuid.uuid4().hex[:12]}"
        feed = {
            "id": feed_id,
            "company_id": company_id,
            "property_id": property_id,
            "source": data.source,
            "ical_url": data.ical_url,
            "name": f"{data.name} - {data.source}",
            "active": True,
            "last_sync_at": now_str,
            "last_sync_status": "success",
            "last_sync_error": None,
            "created_at": now_str,
            "updated_at": now_str,
        }
        await db.ota_feeds.insert_one(feed)
        
        # Import bookings
        bookings_created = 0
        for booking_data in bookings_data:
            booking_data["property_id"] = property_id
            
            # Check for duplicates by UID
            existing = await db.bookings.find_one({
                "company_id": company_id,
                "ota_external_id": booking_data["uid"]
            }, {"_id": 0})
            
            if not existing and booking_data["status"] != "cancelled":
                booking_id = f"book_{uuid.uuid4().hex[:12]}"
                guest_name = booking_data["guest_name"]
                new_booking = {
                    "id": booking_id,
                    "company_id": company_id,
                    "property_id": property_id,
                    "guest_name": guest_name,
                    "check_in": booking_data["check_in"],
                    "check_out": booking_data["check_out"],
                    "total_amount": 0,
                    "guests_count": 1,
                    "status": "confirmed",
                    "booking_type": booking_data.get("booking_type", "reservation"),
                    "ota_source": data.source,
                    "ota_external_id": booking_data["uid"],
                    "ota_feed_id": feed_id,
                    "is_data_complete": booking_is_data_complete({"guest_name": guest_name, "total_amount": 0}),
                    "imported_at": now_str,
                    "created_at": now_str,
                    "updated_at": now_str,
                }
                await db.bookings.insert_one(new_booking)
                bookings_created += 1
        
        logger.info(f"Imported {bookings_created} bookings for property {property_id}")
        
        # Check for incomplete bookings and create notification
        await check_and_create_incomplete_notification(company_id)
        
        # Create sync log
        sync_log_id = f"ota_sync_{uuid.uuid4().hex[:12]}"
        sync_log = {
            "id": sync_log_id,
            "company_id": company_id,
            "source": data.source,
            "event_type": "property_import",
            "status": "completed",
            "message": f"Property created with {bookings_created} bookings",
            "stats": {
                "property_id": property_id,
                "bookings_created": bookings_created,
            },
            "created_at": now_str,
            "processed_at": now_str,
        }
        await db.ota_sync_logs.insert_one(sync_log)
        
        return {
            "status": "success",
            "property_id": property_id,
            "property_name": data.name,
            "bookings_imported": bookings_created,
            "feed_id": feed_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTA import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import property: {str(e)}")

# ===== OTA FEEDS CRUD =====
@api_router.get("/ota/feeds")
async def list_ota_feeds(user=Depends(require_admin)):
    """List all OTA iCal feeds for the company"""
    feeds = await db.ota_feeds.find({"company_id": user["company_id"]}, {"_id": 0}).to_list(100)
    
    # Enrich with property names
    property_ids = list(set(f["property_id"] for f in feeds))
    properties = await db.properties.find({"id": {"$in": property_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(100)
    prop_map = {p["id"]: p["name"] for p in properties}
    
    for feed in feeds:
        feed["property_name"] = prop_map.get(feed["property_id"], "Unknown Property")
    
    return feeds

@api_router.post("/ota/feeds")
async def create_ota_feed(data: OTAFeedCreate, user=Depends(require_admin)):
    """Add a new OTA iCal feed"""
    company_id = user["company_id"]
    
    # Validate property
    prop = await db.properties.find_one({"id": data.property_id, "company_id": company_id}, {"_id": 0})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Check for duplicate
    existing = await db.ota_feeds.find_one({
        "company_id": company_id,
        "property_id": data.property_id,
        "source": data.source
    }, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail=f"A {data.source} feed already exists for this property")
    
    feed_id = f"feed_{uuid.uuid4().hex[:12]}"
    feed = {
        "id": feed_id,
        "company_id": company_id,
        "property_id": data.property_id,
        "source": data.source,
        "ical_url": data.ical_url,
        "name": data.name or f"{prop['name']} - {data.source}",
        "active": True,
        "last_sync_at": None,
        "last_sync_status": None,
        "last_sync_error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.ota_feeds.insert_one(feed)
    
    feed["property_name"] = prop["name"]
    return feed

@api_router.put("/ota/feeds/{feed_id}")
async def update_ota_feed(feed_id: str, data: OTAFeedUpdate, user=Depends(require_admin)):
    """Update an OTA feed"""
    company_id = user["company_id"]
    
    feed = await db.ota_feeds.find_one({"id": feed_id, "company_id": company_id}, {"_id": 0})
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.ota_feeds.update_one({"id": feed_id}, {"$set": update_data})
    
    updated = await db.ota_feeds.find_one({"id": feed_id}, {"_id": 0})
    return updated

@api_router.delete("/ota/feeds/{feed_id}")
async def delete_ota_feed(feed_id: str, user=Depends(require_admin)):
    """Delete an OTA feed"""
    result = await db.ota_feeds.delete_one({"id": feed_id, "company_id": user["company_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feed not found")
    return {"message": "Feed deleted"}

# ===== SEED DATA =====
@api_router.post("/seed-demo-data")
async def seed_demo_data(user=Depends(require_admin)):
    company_id = user["company_id"]
    existing = await db.properties.count_documents({"company_id": company_id})
    if existing > 0:
        return {"message": "Demo data already exists"}

    props = [
        {"id": f"prop_{uuid.uuid4().hex[:12]}", "company_id": company_id, "name": "Oceanview Villa", "address": "123 Beach Rd, Miami, FL", "owner_first_name": "John", "owner_last_name": "Smith", "owner_phone": "+1234567890", "owner_email": "john@example.com", "units": 4, "active": True},
        {"id": f"prop_{uuid.uuid4().hex[:12]}", "company_id": company_id, "name": "Mountain Lodge", "address": "456 Pine Trail, Aspen, CO", "owner_first_name": "Sarah", "owner_last_name": "Johnson", "owner_phone": "+1987654321", "owner_email": "sarah@example.com", "units": 6, "active": True},
        {"id": f"prop_{uuid.uuid4().hex[:12]}", "company_id": company_id, "name": "City Center Apts", "address": "789 Main St, New York, NY", "owner_first_name": "Mike", "owner_last_name": "Davis", "owner_phone": "+1122334455", "owner_email": "mike@example.com", "units": 12, "active": True},
        {"id": f"prop_{uuid.uuid4().hex[:12]}", "company_id": company_id, "name": "Lakeside Retreat", "address": "321 Lake Dr, Lake Tahoe, NV", "owner_first_name": "Emma", "owner_last_name": "Wilson", "owner_phone": "+1555666777", "owner_email": "emma@example.com", "units": 3, "active": True},
    ]
    now_str = datetime.now(timezone.utc).isoformat()
    for p in props:
        p["created_at"] = now_str
        p["updated_at"] = now_str
    await db.properties.insert_many(props)

    staff_list = [
        {"id": f"staff_{uuid.uuid4().hex[:12]}", "company_id": company_id, "first_name": "Alice", "last_name": "Brown", "phone": "+1111222333", "email": "alice@example.com", "salary": 3500.00, "payment_terms": "Monthly", "assigned_properties": [props[0]["id"], props[1]["id"]], "active": True},
        {"id": f"staff_{uuid.uuid4().hex[:12]}", "company_id": company_id, "first_name": "Bob", "last_name": "Garcia", "phone": "+1444555666", "email": "bob@example.com", "salary": 3200.00, "payment_terms": "Monthly", "assigned_properties": [props[2]["id"]], "active": True},
    ]
    for s in staff_list:
        s["created_at"] = now_str
        s["updated_at"] = now_str
    await db.staff.insert_many(staff_list)

    now = datetime.now(timezone.utc)
    bookings = []
    for i in range(15):
        prop = random.choice(props)
        day = random.randint(1, 28)
        dur = random.randint(2, 7)
        amt = round(random.uniform(150, 500) * dur, 2)
        ci = now.replace(day=day)
        co = ci + timedelta(days=dur)
        bookings.append({"id": f"book_{uuid.uuid4().hex[:12]}", "company_id": company_id, "property_id": prop["id"], "guest_name": f"Guest {i+1}", "check_in": ci.isoformat()[:10], "check_out": co.isoformat()[:10], "total_amount": amt, "status": random.choice(["confirmed", "checked_in", "checked_out"]), "created_at": now_str, "updated_at": now_str})
    last = now - timedelta(days=30)
    for i in range(10):
        prop = random.choice(props)
        day = random.randint(1, 28)
        dur = random.randint(2, 7)
        amt = round(random.uniform(150, 500) * dur, 2)
        ci = last.replace(day=day)
        co = ci + timedelta(days=dur)
        bookings.append({"id": f"book_{uuid.uuid4().hex[:12]}", "company_id": company_id, "property_id": prop["id"], "guest_name": f"Previous Guest {i+1}", "check_in": ci.isoformat()[:10], "check_out": co.isoformat()[:10], "total_amount": amt, "status": "checked_out", "created_at": now_str, "updated_at": now_str})
    await db.bookings.insert_many(bookings)

    expenses = [
        {"id": f"exp_{uuid.uuid4().hex[:12]}", "company_id": company_id, "property_id": props[0]["id"], "type": "fixed", "category": "Insurance", "amount": 450.00, "description": "Property insurance", "date": now.isoformat()[:10], "recurring": True, "recurring_frequency": "monthly"},
        {"id": f"exp_{uuid.uuid4().hex[:12]}", "company_id": company_id, "property_id": props[1]["id"], "type": "variable", "category": "Cleaning", "amount": 180.00, "description": "Cleaning service", "date": now.isoformat()[:10], "recurring": False, "recurring_frequency": None},
        {"id": f"exp_{uuid.uuid4().hex[:12]}", "company_id": company_id, "property_id": props[2]["id"], "type": "variable", "category": "Maintenance", "amount": 320.00, "description": "HVAC repair", "date": now.isoformat()[:10], "recurring": False, "recurring_frequency": None},
        {"id": f"exp_{uuid.uuid4().hex[:12]}", "company_id": company_id, "property_id": props[0]["id"], "type": "fixed", "category": "Software", "amount": 99.00, "description": "PMS subscription", "date": now.isoformat()[:10], "recurring": True, "recurring_frequency": "monthly"},
        {"id": f"exp_{uuid.uuid4().hex[:12]}", "company_id": company_id, "property_id": props[3]["id"], "type": "variable", "category": "Utilities", "amount": 210.00, "description": "Electricity bill", "date": now.isoformat()[:10], "recurring": False, "recurring_frequency": None},
    ]
    for e in expenses:
        e["created_at"] = now_str
        e["updated_at"] = now_str
    await db.expenses.insert_many(expenses)
    return {"message": "Demo data seeded successfully"}

# ===== INCLUDE ROUTER =====
app.include_router(api_router)

# ===== SUBSCRIPTION VALIDATION MIDDLEWARE =====
class SubscriptionMiddleware(BaseHTTPMiddleware):
    """Middleware to validate subscription status and block access for inactive subscriptions"""
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip middleware for exempt paths
        for exempt in SUBSCRIPTION_EXEMPT_PATHS:
            if path.startswith(exempt):
                return await call_next(request)
        
        # Skip for non-API paths
        if not path.startswith("/api/"):
            return await call_next(request)
        
        # Try to get session token
        session_token = request.cookies.get("session_token")
        if not session_token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                session_token = auth_header.split(" ")[1]
        
        # If no session, let the auth dependency handle it
        if not session_token:
            return await call_next(request)
        
        try:
            # Get session
            session_doc = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
            if not session_doc:
                return await call_next(request)
            
            # Get user
            user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
            if not user_doc or not user_doc.get("company_id"):
                return await call_next(request)
            
            # Get company subscription status
            company = await db.companies.find_one({"company_id": user_doc["company_id"]}, {"_id": 0})
            if not company:
                return await call_next(request)
            
            subscription_status = company.get("subscription_status", "trial")
            
            # Allow trial and active subscriptions
            if subscription_status in ["trial", "active"]:
                return await call_next(request)
            
            # Block inactive/cancelled/expired subscriptions
            # Still allow GET requests for viewing data
            if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
                return Response(
                    content='{"detail": "Subscription inactive. Please renew your subscription to continue."}',
                    status_code=402,
                    media_type="application/json"
                )
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Subscription middleware error: {e}")
            return await call_next(request)

app.add_middleware(SubscriptionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await db.users.create_index("user_id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.users.create_index("company_id")
    await db.user_sessions.create_index("session_token", unique=True)
    await db.properties.create_index([("company_id", 1)])
    await db.staff.create_index([("company_id", 1)])
    await db.staff.create_index([("company_id", 1), ("email", 1)])
    await db.expenses.create_index([("company_id", 1)])
    await db.bookings.create_index([("company_id", 1)])
    await db.bookings.create_index([("company_id", 1), ("ota_external_id", 1)])
    await db.bookings.create_index([("company_id", 1), ("status", 1)])
    await db.bookings.create_index([("company_id", 1), ("booking_type", 1)])
    await db.bookings.create_index([("company_id", 1), ("ota_source", 1)])
    await db.bookings.create_index([("company_id", 1), ("is_data_complete", 1)])
    await db.notifications.create_index([("company_id", 1)])
    await db.notifications.create_index([("company_id", 1), ("read", 1)])
    await db.invitations.create_index([("company_id", 1)])
    await db.invitations.create_index("token", unique=True)
    await db.payment_transactions.create_index("session_id")
    await db.ota_sync_logs.create_index([("company_id", 1)])
    await db.ota_sync_logs.create_index([("company_id", 1), ("status", 1)])
    await db.services.create_index([("company_id", 1)])
    await db.services.create_index([("company_id", 1), ("category", 1)])
    await db.booking_services.create_index([("company_id", 1)])
    await db.booking_services.create_index([("booking_id", 1)])
    await db.tasks.create_index([("company_id", 1)])
    await db.tasks.create_index([("company_id", 1), ("assigned_staff_id", 1)])
    await db.tasks.create_index([("company_id", 1), ("status", 1)])
    await db.audit_logs.create_index([("company_id", 1)])
    await db.audit_logs.create_index([("user_id", 1)])
    await db.payouts.create_index([("company_id", 1), ("staff_id", 1)])
    await db.ota_feeds.create_index([("company_id", 1)])
    await db.ota_feeds.create_index([("company_id", 1), ("property_id", 1)])
    logger.info("Database indexes created")
    
    # Migrate existing blocked bookings to use booking_type field
    await migrate_blocked_bookings()
    
    # Run auto-checkout on startup and schedule periodic task
    await auto_checkout_expired_bookings()
    asyncio.create_task(periodic_auto_checkout())
    
    # Migrate existing bookings to set is_data_complete
    await migrate_is_data_complete()

async def migrate_blocked_bookings():
    """One-time migration to add booking_type field to existing bookings"""
    try:
        # Update blocked bookings (status=blocked) to have booking_type=blocked
        blocked_result = await db.bookings.update_many(
            {"status": "blocked", "booking_type": {"$exists": False}},
            {"$set": {"booking_type": "blocked", "guest_name": None, "total_amount": 0}}
        )
        
        # Also fix bookings where guest_name was "Blocked" (from old iCal imports)
        blocked_name_result = await db.bookings.update_many(
            {"guest_name": "Blocked", "booking_type": {"$ne": "blocked"}},
            {"$set": {"booking_type": "blocked", "guest_name": None, "total_amount": 0, "status": "blocked"}}
        )
        
        # Update all other bookings to have booking_type=reservation
        reservation_result = await db.bookings.update_many(
            {"status": {"$ne": "blocked"}, "booking_type": {"$exists": False}},
            {"$set": {"booking_type": "reservation"}}
        )
        
        total_blocked = blocked_result.modified_count + blocked_name_result.modified_count
        logger.info(f"Migration complete: {total_blocked} blocked dates updated, {reservation_result.modified_count} reservations updated")
    except Exception as e:
        logger.error(f"Migration error: {e}")

async def auto_checkout_expired_bookings():
    """Auto-update bookings to checked_out when checkout date has passed"""
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        result = await db.bookings.update_many(
            {
                "check_out": {"$lt": today},
                "status": {"$in": ["confirmed", "checked_in"]},
                "booking_type": {"$ne": "blocked"}
            },
            {"$set": {"status": "checked_out", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        if result.modified_count > 0:
            logger.info(f"Auto-checkout: Updated {result.modified_count} expired bookings to checked_out")
    except Exception as e:
        logger.error(f"Auto-checkout error: {e}")

async def migrate_is_data_complete():
    """One-time migration to set is_data_complete on existing bookings"""
    try:
        bookings_without_flag = await db.bookings.find(
            {"is_data_complete": {"$exists": False}, "booking_type": {"$ne": "blocked"}},
            {"_id": 0, "id": 1, "guest_name": 1, "total_amount": 1}
        ).to_list(5000)
        
        complete_ids = []
        incomplete_ids = []
        for b in bookings_without_flag:
            if booking_is_data_complete(b):
                complete_ids.append(b["id"])
            else:
                incomplete_ids.append(b["id"])
        
        if complete_ids:
            await db.bookings.update_many(
                {"id": {"$in": complete_ids}},
                {"$set": {"is_data_complete": True}}
            )
        if incomplete_ids:
            await db.bookings.update_many(
                {"id": {"$in": incomplete_ids}},
                {"$set": {"is_data_complete": False}}
            )
        
        # Set blocked bookings as complete (they don't need guest/amount)
        await db.bookings.update_many(
            {"is_data_complete": {"$exists": False}, "booking_type": "blocked"},
            {"$set": {"is_data_complete": True}}
        )
        
        total = len(complete_ids) + len(incomplete_ids)
        if total > 0:
            logger.info(f"is_data_complete migration: {len(complete_ids)} complete, {len(incomplete_ids)} incomplete")
        
        # Create notifications for companies with incomplete bookings
        if incomplete_ids:
            # Get unique company_ids from incomplete bookings
            company_ids = await db.bookings.distinct("company_id", {"id": {"$in": incomplete_ids}})
            for cid in company_ids:
                await check_and_create_incomplete_notification(cid)
    except Exception as e:
        logger.error(f"is_data_complete migration error: {e}")

async def periodic_auto_checkout():
    """Run auto-checkout every hour"""
    while True:
        await asyncio.sleep(3600)
        await auto_checkout_expired_bookings()

@app.on_event("shutdown")
async def shutdown():
    client.close()
