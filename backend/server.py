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

class BookingUpdate(BaseModel):
    guest_name: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    total_amount: Optional[float] = None
    guests_count: Optional[int] = None
    assigned_cohost: Optional[str] = None
    status: Optional[str] = None

class InvitationCreate(BaseModel):
    email: str
    role: str

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

    # Build booking query based on role
    booking_query = {"company_id": company_id}
    if role in ["owner", "staff"]:
        booking_query["property_id"] = {"$in": property_ids}
    
    current_bookings = await db.bookings.find(
        {**booking_query, "check_in": {"$gte": current_month_start.isoformat()[:10]}}, {"_id": 0}
    ).to_list(1000)
    last_bookings = await db.bookings.find(
        {**booking_query, "check_in": {"$gte": last_month_start.isoformat()[:10], "$lt": current_month_start.isoformat()[:10]}}, {"_id": 0}
    ).to_list(1000)

    current_revenue = sum(b.get("total_amount", 0) for b in current_bookings)
    last_revenue = sum(b.get("total_amount", 0) for b in last_bookings)

    # Expenses query based on role
    expense_query = {"company_id": company_id, "date": {"$gte": current_month_start.isoformat()[:10]}}
    if role in ["owner", "staff"]:
        expense_query["property_id"] = {"$in": property_ids}
    current_expenses = await db.expenses.find(expense_query, {"_id": 0}).to_list(1000)
    total_expenses = sum(e.get("amount", 0) for e in current_expenses)

    active_properties = len([p for p in properties if p.get("active", True)])
    total_units = sum(p.get("units", 0) for p in properties)

    active_bookings_query = {**booking_query, "status": {"$in": ["confirmed", "checked_in"]}}
    active_bookings = await db.bookings.count_documents(active_bookings_query)

    nights_booked = 0
    for b in current_bookings:
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
async def list_bookings(user=Depends(get_current_user)):
    company_id = user.get("company_id")
    if not company_id:
        return []
    return await db.bookings.find({"company_id": company_id}, {"_id": 0}).sort("check_in", -1).to_list(1000)

@api_router.post("/bookings", status_code=201)
async def create_booking(data: BookingCreate, user=Depends(require_admin)):
    booking = {
        "id": f"book_{uuid.uuid4().hex[:12]}",
        "company_id": user["company_id"],
        **data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.bookings.insert_one(booking)
    return await db.bookings.find_one({"id": booking["id"]}, {"_id": 0})

@api_router.put("/bookings/{booking_id}")
async def update_booking(booking_id: str, data: BookingUpdate, user=Depends(require_admin)):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.bookings.update_one({"id": booking_id, "company_id": user["company_id"]}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return await db.bookings.find_one({"id": booking_id}, {"_id": 0})

@api_router.get("/bookings/by-status")
async def list_bookings_by_status(user=Depends(get_current_user)):
    """Get bookings grouped by status with today's check-ins highlighted"""
    company_id = user.get("company_id")
    if not company_id:
        return {"checked_in_today": [], "upcoming": [], "confirmed": [], "checked_out": [], "cancelled": []}
    
    today = datetime.now(timezone.utc).isoformat()[:10]
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()[:10]
    
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
            
        bookings = await db.bookings.find(booking_query, {"_id": 0}).to_list(1000)
        
        expense_query = {"company_id": company_id, "date": {"$gte": start.isoformat()[:10], "$lt": end.isoformat()[:10]}}
        if property_id:
            expense_query["property_id"] = property_id
        expenses = await db.expenses.find(expense_query, {"_id": 0}).to_list(1000)
        
        revenue = sum(b.get("total_amount", 0) for b in bookings)
        expense_total = sum(e.get("amount", 0) for e in expenses)
        
        nights_booked = 0
        for b in bookings:
            try:
                ci = datetime.fromisoformat(b["check_in"])
                co = datetime.fromisoformat(b["check_out"])
                nights_booked += (co - ci).days
            except:
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
            "total_bookings": len(bookings),
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
@api_router.get("/invitations")
async def list_invitations(user=Depends(require_admin)):
    return await db.invitations.find({"company_id": user["company_id"]}, {"_id": 0}).to_list(1000)

@api_router.post("/invitations", status_code=201)
async def create_invitation(data: InvitationCreate, user=Depends(require_admin)):
    if data.role not in ["owner", "staff"]:
        raise HTTPException(status_code=400, detail="Role must be 'owner' or 'staff'")
    existing = await db.invitations.find_one(
        {"email": data.email, "company_id": user["company_id"], "used": False}, {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Invitation already pending for this email")

    token = secrets.token_urlsafe(32)
    invitation = {
        "id": f"inv_{uuid.uuid4().hex[:12]}",
        "company_id": user["company_id"],
        "email": data.email,
        "role": data.role,
        "token": token,
        "used": False,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.invitations.insert_one(invitation)
    return await db.invitations.find_one({"id": invitation["id"]}, {"_id": 0})

@api_router.delete("/invitations/{inv_id}")
async def delete_invitation(inv_id: str, user=Depends(require_admin)):
    result = await db.invitations.delete_one({"id": inv_id, "company_id": user["company_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return {"message": "Invitation deleted"}

@api_router.get("/invitations/validate/{token}")
async def validate_invitation(token: str):
    invitation = await db.invitations.find_one({"token": token, "used": False}, {"_id": 0})
    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    expires_at = invitation.get("expires_at", "")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invitation has expired")
    company = await db.companies.find_one({"company_id": invitation["company_id"]}, {"_id": 0})
    return {
        "email": invitation["email"],
        "role": invitation["role"],
        "company_name": company["name"] if company else "Unknown",
        "token": token,
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
    await db.invitations.create_index([("company_id", 1)])
    await db.invitations.create_index("token", unique=True)
    await db.payment_transactions.create_index("session_id")
    await db.ota_sync_logs.create_index([("company_id", 1)])
    await db.ota_sync_logs.create_index([("company_id", 1), ("status", 1)])
    logger.info("Database indexes created")

@app.on_event("shutdown")
async def shutdown():
    client.close()
