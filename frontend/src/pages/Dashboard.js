import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import OnboardingWizard from "@/components/OnboardingWizard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DollarSign, TrendingUp, Home, CalendarDays, Percent, BarChart3, ArrowUpRight, ArrowDownRight, Building2, AlertTriangle, Clock, CheckCircle, Download, ClipboardList } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v);

// Premium KPI Card Component
function KPICard({ label, value, subtitle, icon: Icon, trend, large = false, delay = 0, variant = "default" }) {
  const isPositive = trend > 0;
  const showTrend = trend !== undefined && trend !== null && trend !== 0;
  
  const bgColors = {
    default: "bg-teal-50 dark:bg-teal-900/30",
    warning: "bg-amber-50 dark:bg-amber-900/30",
    success: "bg-emerald-50 dark:bg-emerald-900/30",
  };
  const iconColors = {
    default: "text-teal-600 dark:text-teal-400",
    warning: "text-amber-600 dark:text-amber-400",
    success: "text-emerald-600 dark:text-emerald-400",
  };
  
  return (
    <div 
      className={`kpi-card hover-lift ${large ? 'p-8' : 'p-6'} animate-fade-in opacity-0`}
      style={{ animationDelay: `${delay}s` }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1 min-w-0 flex-1">
          <p className="kpi-label">{label}</p>
          <p className={`font-heading tabular-nums tracking-tight text-gray-900 dark:text-gray-100 ${large ? 'text-4xl font-bold' : 'text-2xl font-bold'}`}>
            {value}
          </p>
          {subtitle && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>
          )}
          {showTrend && (
            <div className={`flex items-center gap-1 mt-2 text-sm font-medium ${isPositive ? 'text-teal-600 dark:text-teal-400' : 'text-red-500 dark:text-red-400'}`}>
              {isPositive ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
              <span>{Math.abs(trend).toFixed(1)}% vs last month</span>
            </div>
          )}
        </div>
        <div className={`h-12 w-12 rounded-xl ${bgColors[variant]} flex items-center justify-center shrink-0 transition-transform hover:scale-110`}>
          <Icon className={`h-6 w-6 ${iconColors[variant]}`} />
        </div>
      </div>
    </div>
  );
}

// Alert Card for missing data
function AlertCard({ title, count, description, actionLabel, onAction, delay = 0 }) {
  if (count === 0) return null;
  return (
    <div 
      className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-xl animate-fade-in opacity-0"
      style={{ animationDelay: `${delay}s` }}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="font-semibold text-amber-800 dark:text-amber-200">{title}</p>
          <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">{description}</p>
          <Button variant="outline" size="sm" className="mt-3 border-amber-300 hover:bg-amber-100" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
        <Badge className="bg-amber-200 text-amber-800 border-0">{count}</Badge>
      </div>
    </div>
  );
}

// Compact booking item
function BookingItem({ booking, propertyName, index = 0 }) {
  const statusColors = {
    confirmed: "bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-900/30 dark:text-teal-400",
    checked_in: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400",
    checked_out: "bg-gray-50 text-gray-600 border-gray-200 dark:bg-gray-800 dark:text-gray-400",
  };
  
  const today = new Date().toISOString().slice(0, 10);
  const isCheckingToday = booking.check_in === today || booking.check_out === today;
  
  return (
    <div 
      className={`flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 -mx-2 px-2 rounded-lg transition-colors animate-fade-in opacity-0 ${isCheckingToday ? 'bg-amber-50/50 dark:bg-amber-900/10' : ''}`}
      style={{ animationDelay: `${0.3 + index * 0.05}s` }}
    >
      <div className="min-w-0">
        <p className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">{propertyName}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          {booking.check_in} → {booking.check_out}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {isCheckingToday && (
          <Badge variant="outline" className="text-[10px] bg-amber-100 text-amber-700 border-amber-200">
            Today
          </Badge>
        )}
        <Badge variant="outline" className={`text-[10px] capitalize ${statusColors[booking.status] || ''}`}>
          {booking.status?.replace('_', ' ')}
        </Badge>
      </div>
    </div>
  );
}

// Task item for staff dashboard
function TaskItem({ task, index = 0 }) {
  const priorityColors = {
    high: "bg-red-100 text-red-700",
    medium: "bg-amber-100 text-amber-700",
    low: "bg-gray-100 text-gray-600",
  };
  
  return (
    <div 
      className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700/50 last:border-0 animate-fade-in opacity-0"
      style={{ animationDelay: `${0.3 + index * 0.05}s` }}
    >
      <div className="min-w-0">
        <p className="font-medium text-sm text-gray-900 dark:text-gray-100">{task.title}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Due: {task.due_date}</p>
      </div>
      <Badge className={`text-[10px] ${priorityColors[task.priority] || priorityColors.medium}`}>
        {task.priority}
      </Badge>
    </div>
  );
}

// Dashboard skeleton
function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="p-8 bg-white dark:bg-gray-800/50 rounded-2xl border border-gray-100 dark:border-gray-700/50">
            <Skeleton className="h-4 w-24 mb-3" />
            <Skeleton className="h-10 w-32" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Skeleton className="h-64 rounded-2xl" />
        <Skeleton className="h-64 rounded-2xl" />
      </div>
    </div>
  );
}

// ============ ROLE-SPECIFIC DASHBOARDS ============

function AdminDashboard({ kpis, trends, bookings, properties, navigate }) {
  const getPropName = (id) => properties.find(p => p.id === id)?.name || "Property";
  const revenueTrend = kpis.revenue_last_month > 0 ? ((kpis.revenue_mtd - kpis.revenue_last_month) / kpis.revenue_last_month * 100) : 0;
  
  // Filter for today's check-ins/outs
  const today = new Date().toISOString().slice(0, 10);
  const checkingToday = bookings.filter(b => b.check_in === today || b.check_out === today);
  const upcomingBookings = bookings.filter(b => b.check_in > today).slice(0, 5);
  
  return (
    <>
      {/* Primary KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <KPICard label="Revenue MTD" value={fmt(kpis.revenue_mtd || 0)} subtitle={`Last month: ${fmt(kpis.revenue_last_month || 0)}`} icon={DollarSign} trend={revenueTrend} large delay={0.1} />
        <KPICard label="Net Income" value={fmt(kpis.net_income || 0)} subtitle={`Expenses: ${fmt(kpis.total_expenses || 0)}`} icon={TrendingUp} large delay={0.15} />
        <KPICard label="Occupancy Rate" value={`${kpis.occupancy_rate || 0}%`} subtitle={`${kpis.nights_booked || 0} nights booked`} icon={Percent} large delay={0.2} />
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-xl animate-fade-in opacity-0" style={{ animationDelay: '0.25s' }}>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center">
              <Building2 className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Properties</p>
              <p className="text-lg font-bold">{kpis.active_properties || 0}</p>
            </div>
          </div>
        </div>
        <div className="p-4 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-xl animate-fade-in opacity-0" style={{ animationDelay: '0.3s' }}>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-teal-50 dark:bg-teal-900/30 flex items-center justify-center">
              <CalendarDays className="h-5 w-5 text-teal-600" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Active Bookings</p>
              <p className="text-lg font-bold">{kpis.active_bookings || 0}</p>
            </div>
          </div>
        </div>
        <div className="p-4 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-xl animate-fade-in opacity-0" style={{ animationDelay: '0.35s' }}>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-amber-50 dark:bg-amber-900/30 flex items-center justify-center">
              <Clock className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Check-ins Today</p>
              <p className="text-lg font-bold">{checkingToday.filter(b => b.check_in === today).length}</p>
            </div>
          </div>
        </div>
        <div className="p-4 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-xl animate-fade-in opacity-0" style={{ animationDelay: '0.4s' }}>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-purple-50 dark:bg-purple-900/30 flex items-center justify-center">
              <CheckCircle className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Check-outs Today</p>
              <p className="text-lg font-bold">{checkingToday.filter(b => b.check_out === today).length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Charts and Lists */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Chart */}
        <Card className="border-gray-100 dark:border-gray-700/50 animate-fade-in opacity-0" style={{ animationDelay: '0.45s' }}>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-primary" />Revenue Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                  <defs>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `$${v >= 1000 ? `${(v/1000).toFixed(0)}k` : v}`} />
                  <Tooltip formatter={v => fmt(v)} contentStyle={{ fontSize: 12 }} />
                  <Area type="monotone" dataKey="revenue" stroke="hsl(var(--primary))" fill="url(#colorRevenue)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Upcoming Bookings */}
        <Card className="border-gray-100 dark:border-gray-700/50 animate-fade-in opacity-0" style={{ animationDelay: '0.5s' }}>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <CalendarDays className="h-4 w-4 text-primary" />Upcoming Bookings
            </CardTitle>
          </CardHeader>
          <CardContent>
            {upcomingBookings.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No upcoming bookings</p>
            ) : (
              <div className="space-y-1">
                {upcomingBookings.map((b, i) => (
                  <BookingItem key={b.id} booking={b} propertyName={getPropName(b.property_id)} index={i} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function OwnerDashboard({ kpis, trends, properties, navigate }) {
  const revenueTrend = kpis.revenue_last_month > 0 ? ((kpis.revenue_mtd - kpis.revenue_last_month) / kpis.revenue_last_month * 100) : 0;
  
  return (
    <>
      {/* Simple KPIs for Owners */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard label="My Properties" value={kpis.active_properties || 0} icon={Building2} large delay={0.1} />
        <KPICard label="Revenue This Month" value={fmt(kpis.revenue_mtd || 0)} icon={DollarSign} trend={revenueTrend} large delay={0.15} />
        <KPICard label="Net Profit" value={fmt(kpis.net_income || 0)} subtitle={`After ${fmt(kpis.total_expenses || 0)} expenses`} icon={TrendingUp} variant="success" large delay={0.2} />
        <KPICard label="Upcoming Bookings" value={kpis.active_bookings || 0} icon={CalendarDays} delay={0.25} />
      </div>

      {/* Revenue Chart */}
      <Card className="animate-fade-in opacity-0" style={{ animationDelay: '0.3s' }}>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base font-semibold">Monthly Revenue</CardTitle>
          <Button variant="outline" size="sm" onClick={() => navigate('/analytics')}>
            <Download className="h-4 w-4 mr-2" />View Reports
          </Button>
        </CardHeader>
        <CardContent>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                <defs>
                  <linearGradient id="colorRevenueOwner" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `$${v >= 1000 ? `${(v/1000).toFixed(0)}k` : v}`} />
                <Tooltip formatter={v => fmt(v)} />
                <Area type="monotone" dataKey="revenue" stroke="hsl(var(--primary))" fill="url(#colorRevenueOwner)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Properties List */}
      {properties.length > 0 && (
        <Card className="animate-fade-in opacity-0" style={{ animationDelay: '0.35s' }}>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Your Properties</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {properties.slice(0, 4).map((p, i) => (
                <div key={p.id} className="p-4 bg-muted/30 rounded-xl flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Home className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium text-sm">{p.name}</p>
                    <p className="text-xs text-muted-foreground">{p.city || 'No location'}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </>
  );
}

function StaffDashboard({ tasks, properties }) {
  const today = new Date().toISOString().slice(0, 10);
  const todayTasks = tasks.filter(t => t.due_date === today && t.status !== 'completed');
  const upcomingTasks = tasks.filter(t => t.due_date > today && t.status !== 'completed').slice(0, 5);
  const completedToday = tasks.filter(t => t.due_date === today && t.status === 'completed').length;
  
  return (
    <>
      {/* Staff KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KPICard label="Tasks Today" value={todayTasks.length} subtitle={`${completedToday} completed`} icon={ClipboardList} variant="warning" large delay={0.1} />
        <KPICard label="Upcoming Tasks" value={upcomingTasks.length} icon={Clock} delay={0.15} />
        <KPICard label="Assigned Properties" value={properties.length} icon={Building2} delay={0.2} />
      </div>

      {/* Today's Tasks */}
      <Card className="animate-fade-in opacity-0" style={{ animationDelay: '0.25s' }}>
        <CardHeader>
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <ClipboardList className="h-4 w-4 text-primary" />Today's Tasks
          </CardTitle>
        </CardHeader>
        <CardContent>
          {todayTasks.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle className="h-10 w-10 mx-auto text-emerald-500 mb-2" />
              <p className="text-sm text-muted-foreground">All tasks completed for today!</p>
            </div>
          ) : (
            <div className="space-y-1">
              {todayTasks.map((t, i) => <TaskItem key={t.id} task={t} index={i} />)}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upcoming Tasks */}
      {upcomingTasks.length > 0 && (
        <Card className="animate-fade-in opacity-0" style={{ animationDelay: '0.3s' }}>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Upcoming Tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {upcomingTasks.map((t, i) => <TaskItem key={t.id} task={t} index={i} />)}
            </div>
          </CardContent>
        </Card>
      )}
    </>
  );
}

// ============ MAIN DASHBOARD COMPONENT ============

export default function Dashboard() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [kpis, setKpis] = useState({});
  const [trends, setTrends] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [properties, setProperties] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) navigate("/");
  }, [user, authLoading, navigate]);

  useEffect(() => {
    if (!user?.company_id) return;
    
    const fetchData = async () => {
      try {
        const endpoints = [
          fetch(`${API}/api/dashboard/kpis`, { credentials: "include" }),
          fetch(`${API}/api/dashboard/revenue-trends`, { credentials: "include" }),
          fetch(`${API}/api/bookings?limit=10`, { credentials: "include" }),
          fetch(`${API}/api/properties`, { credentials: "include" }),
        ];
        
        // Staff also needs tasks
        if (user.role === 'staff') {
          endpoints.push(fetch(`${API}/api/tasks`, { credentials: "include" }));
        }
        
        const responses = await Promise.all(endpoints);
        
        if (responses[0].ok) setKpis(await responses[0].json());
        if (responses[1].ok) setTrends(await responses[1].json());
        if (responses[2].ok) {
          const data = await responses[2].json();
          setBookings(data.filter(b => b.booking_type !== 'blocked' && b.status !== 'blocked'));
        }
        if (responses[3].ok) {
          const propData = await responses[3].json();
          setProperties(propData);
          // Show onboarding if admin with no properties
          if (user.role === 'company_admin' && propData.length === 0) {
            setShowOnboarding(true);
          }
        }
        if (responses[4]?.ok) setTasks(await responses[4].json());
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [user]);

  if (authLoading || !user) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  // Show onboarding wizard for new admins
  if (showOnboarding) {
    return <OnboardingWizard onComplete={() => { setShowOnboarding(false); window.location.reload(); }} />;
  }

  const role = user.role;
  const greeting = role === 'staff' ? 'Ready to work' : role === 'owner' ? 'Your portfolio overview' : "Here's your performance overview";

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="dashboard-page">
        {/* Header */}
        <div className="flex items-end justify-between animate-fade-in">
          <div>
            <h1 className="text-2xl font-bold font-heading text-gray-900 dark:text-gray-100">
              Hey, {user.name?.split(' ')[0] || 'there'}
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">{greeting}</p>
          </div>
          <Badge variant="outline" className="text-xs font-medium capitalize bg-primary/10 text-primary border-primary/20">
            {role?.replace('_', ' ')}
          </Badge>
        </div>

        {loading ? (
          <DashboardSkeleton />
        ) : (
          <>
            {role === 'company_admin' && (
              <AdminDashboard 
                kpis={kpis} 
                trends={trends} 
                bookings={bookings} 
                properties={properties} 
                navigate={navigate}
              />
            )}
            {role === 'owner' && (
              <OwnerDashboard 
                kpis={kpis} 
                trends={trends} 
                properties={properties}
                navigate={navigate}
              />
            )}
            {role === 'staff' && (
              <StaffDashboard 
                tasks={tasks} 
                properties={properties}
              />
            )}
          </>
        )}
      </div>
    </Layout>
  );
}
