# PropStack - Multi-Tenant Property & Hospitality Management SaaS

## Original Problem Statement
Multi-tenant Property & Hospitality Management SaaS with Google OAuth, RBAC (Admin/Owner/Staff), KPI Dashboard, Properties/Staff/Expenses/Bookings modules, Invitations system, Stripe subscription, dark/light mode.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI (port 3000)
- **Backend**: FastAPI + Motor (async MongoDB) (port 8001)
- **Database**: MongoDB with company_id row-level isolation
- **Auth**: Dual auth - Google OAuth + Password-based registration
- **Payments**: Stripe via emergentintegrations library
- **Email**: Resend for invitation emails
- **Theme**: Dark/Light toggle with CSS variables

## User Personas
1. **Company Admin** - Full CRUD on all modules, billing, invitations, staff/task management
2. **Owner** - View-only access to their properties' revenue, expenses, bookings, analytics
3. **Staff** - Tasks management, assigned properties, earnings tracking, payout status

## What's Been Implemented (Feb 22, 2026)

### Core Features
- [x] Landing page with hero, features, CTAs
- [x] **Dual Authentication** - Google OAuth + Password-based login
- [x] **Invitation-Based Registration** - Read-only info (Name, Email, Role, Company) + password setup
- [x] Company setup flow for new users
- [x] Admin Dashboard with 8 KPIs + revenue trends chart
- [x] **Role-Specific Dashboards** (Admin/Owner/Staff views)
- [x] Properties CRUD (cards with owner details, units, OTA sync)
- [x] Staff CRUD (table with salary, assignments, status)
- [x] **Tasks CRUD** (full task management with assignments)
- [x] Expenses CRUD (fixed/variable tabs, property filter, recurring)
- [x] Bookings CRUD (status tabs: Checked-in, Upcoming, Confirmed, etc.)
- [x] Services CRUD (add-on services with staff/external provider assignment)
- [x] Analytics page (KPIs, trends, filters by property/month/year)
- [x] Invitations system with Resend email integration
- [x] Stripe subscription integration (3 plans)
- [x] Dark/Light mode toggle
- [x] Responsive sidebar navigation with role-based items
- [x] **"Hey, {FirstName}" greeting** in header
- [x] **Audit logging** for account activation and logins

### Authentication System
- [x] Google OAuth (Emergent Auth)
- [x] Password-based registration via invitation links
- [x] Password login with bcrypt hashing
- [x] Session management with 7-day cookie expiry
- [x] Both auth methods supported for invited users

### Invitation Registration Flow (Fixed Feb 22, 2026)
1. Admin creates invitation for Staff/Owner → email sent via Resend
2. Invitee clicks link → `/invite/{token}` page loads
3. Page shows **read-only** fields: Name, Email, Role, Company (pre-filled from staff/property records)
4. User only needs to: Create Password OR Continue with Google
5. Upon success → redirected to role-specific dashboard

### Role-Based Features
- **Admin**: Full access to all modules, Tasks, Invitations, Staff management
- **Owner (View-Only)**: Properties, Bookings, Analytics (filtered to their properties)
- **Staff**: Tasks, Bookings, Earnings, Dashboard with work summary

### Tasks Module
- Task types: Cleaning, Maintenance, Check-in, Check-out, Admin, General
- Priorities: Low, Medium, High, Urgent
- Status workflow: Pending → In Progress → Completed → Cancelled
- Staff can only update their own tasks' status
- Admin can create, edit, delete, assign tasks
- Task summary cards for staff (Pending, In Progress, Completed MTD)

### Mock OTA Integration
- [x] Simulated sync for Airbnb, Booking.com, VRBO, Expedia
- [x] "Sync All OTA" button on Properties page
- [x] "Sync OTA" button per property
- [x] OTA source badges on synced bookings

## Test Results (Feb 22, 2026 - Latest)
- Backend: 100% (20/20 tests passed)
- Frontend: 100% (All UI features verified)

## API Endpoints

### Authentication
- `POST /api/auth/register-with-invite` - Password registration via invitation
- `POST /api/auth/login` - Email/password login
- `GET /api/auth/google` - Google OAuth initiation
- `GET /api/auth/me` - Current user info
- `POST /api/auth/logout` - Logout

### Tasks
- `GET /api/tasks` - List tasks (role-filtered)
- `POST /api/tasks` - Create task (admin only)
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task (admin only)
- `GET /api/tasks/my-summary` - Staff task summary

### Staff Earnings
- `GET /api/staff/my-earnings` - Staff earnings data

## Navigation by Role

### Admin Sidebar
Dashboard, Properties, Staff, Bookings, Tasks, Services, Expenses, Analytics, Invitations, Billing, Settings

### Owner Sidebar
Dashboard, Properties, Bookings, Analytics, Settings

### Staff Sidebar
Dashboard, Tasks, Bookings, Settings

## Database Collections
- users (with password_hash, auth_method, first_name, last_name)
- companies, user_sessions
- properties, staff, bookings, expenses, invitations
- tasks (with assigned_staff_id, status, priority, task_type)
- services, booking_services
- payment_transactions, ota_sync_logs
- audit_logs (account_activated, login events)
- payouts

## Environment Variables
```
# Backend (.env)
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
STRIPE_API_KEY=sk_test_emergent
RESEND_API_KEY=re_123456789
SENDER_EMAIL=onboarding@resend.dev
```

## Prioritized Backlog

### P1 (Next)
- Real OTA iCal integration
- Production Resend API key for real emails
- Staff payout tracking and history
- Owner financial reports (PDF/CSV export)

### P2
- JWT authentication migration
- Audit logs viewer in admin panel
- Booking calendar view for owners
- Task notifications for staff

### P3
- AI revenue forecasting
- Multi-currency support
- Multi-language
- Automated owner payouts
- Smart expense categorization
