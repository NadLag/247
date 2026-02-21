from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import secrets
import httpx
import random
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
    owner_first_name: str
    owner_last_name: str
    owner_phone: str
    owner_email: str
    units: int
    active: bool = True

class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
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
    salary: float
    payment_terms: str
    assigned_properties: List[str] = []

class StaffUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    salary: Optional[float] = None
    payment_terms: Optional[str] = None
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
    status: str = "confirmed"

class BookingUpdate(BaseModel):
    guest_name: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    total_amount: Optional[float] = None
    status: Optional[str] = None

class InvitationCreate(BaseModel):
    email: str
    role: str

class CheckoutRequest(BaseModel):
    plan: str
    origin_url: str

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
    if not company_id:
        return {"revenue_mtd": 0, "revenue_last_month": 0, "net_income": 0, "occupancy_rate": 0,
                "nights_booked": 0, "adr": 0, "revpan": 0, "active_properties": 0,
                "total_properties": 0, "active_bookings": 0, "staff_payments_due": 0, "total_expenses": 0}

    now = datetime.now(timezone.utc)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

    current_bookings = await db.bookings.find(
        {"company_id": company_id, "check_in": {"$gte": current_month_start.isoformat()[:10]}}, {"_id": 0}
    ).to_list(1000)
    last_bookings = await db.bookings.find(
        {"company_id": company_id, "check_in": {"$gte": last_month_start.isoformat()[:10], "$lt": current_month_start.isoformat()[:10]}}, {"_id": 0}
    ).to_list(1000)

    current_revenue = sum(b.get("total_amount", 0) for b in current_bookings)
    last_revenue = sum(b.get("total_amount", 0) for b in last_bookings)

    current_expenses = await db.expenses.find(
        {"company_id": company_id, "date": {"$gte": current_month_start.isoformat()[:10]}}, {"_id": 0}
    ).to_list(1000)
    total_expenses = sum(e.get("amount", 0) for e in current_expenses)

    properties = await db.properties.find({"company_id": company_id}, {"_id": 0}).to_list(1000)
    active_properties = len([p for p in properties if p.get("active", True)])
    total_units = sum(p.get("units", 0) for p in properties)

    active_bookings = await db.bookings.count_documents(
        {"company_id": company_id, "status": {"$in": ["confirmed", "checked_in"]}}
    )

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

    staff_list = await db.staff.find({"company_id": company_id, "active": True}, {"_id": 0}).to_list(1000)
    staff_payments_due = sum(s.get("salary", 0) for s in staff_list)

    return {
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

@api_router.post("/expenses")
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

@api_router.post("/bookings")
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

# ===== INVITATION ROUTES =====
@api_router.get("/invitations")
async def list_invitations(user=Depends(require_admin)):
    return await db.invitations.find({"company_id": user["company_id"]}, {"_id": 0}).to_list(1000)

@api_router.post("/invitations")
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
    await db.expenses.create_index([("company_id", 1)])
    await db.bookings.create_index([("company_id", 1)])
    await db.invitations.create_index([("company_id", 1)])
    await db.invitations.create_index("token", unique=True)
    await db.payment_transactions.create_index("session_id")
    logger.info("Database indexes created")

@app.on_event("shutdown")
async def shutdown():
    client.close()
