import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { DollarSign, TrendingUp, TrendingDown, Home, CalendarDays, Percent, BarChart3, Users, ArrowUpRight, ArrowDownRight, Loader2, CheckCircle2, Clock, Briefcase } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }).format(v);

function KPICard({ title, value, subtitle, icon: Icon, trend, testId, variant = "default" }) {
  const isPositive = trend > 0;
  const variantStyles = {
    default: "bg-primary/10 text-primary",
    success: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
    info: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  };
  return (
    <Card className="relative overflow-hidden" data-testid={testId}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground font-medium">{title}</p>
            <p className="text-2xl font-bold font-data tracking-tight">{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          <div className={`h-9 w-9 rounded-lg flex items-center justify-center shrink-0 ${variantStyles[variant]}`}>
            <Icon className="h-4 w-4" />
          </div>
        </div>
        {trend !== undefined && trend !== null && (
          <div className={`flex items-center gap-1 mt-3 text-xs font-medium ${isPositive ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
            {isPositive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            <span>{Math.abs(trend).toFixed(1)}% vs last month</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AdminDashboard({ kpis, trends, bookings, loadingData, revenueTrend, navigate }) {
  return (
    <>
      {/* KPI Grid for Admins */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard title="Revenue MTD" value={fmt(kpis.revenue_mtd)} icon={DollarSign} trend={revenueTrend} subtitle={`Last month: ${fmt(kpis.revenue_last_month)}`} testId="kpi-revenue" />
        <KPICard title="Net Income" value={fmt(kpis.net_income)} icon={TrendingUp} subtitle={`Expenses: ${fmt(kpis.total_expenses)}`} testId="kpi-net-income" />
        <KPICard title="Occupancy Rate" value={`${kpis.occupancy_rate}%`} icon={Percent} testId="kpi-occupancy" />
        <KPICard title="Nights Booked" value={kpis.nights_booked} icon={CalendarDays} testId="kpi-nights" />
        <KPICard title="ADR" value={fmt(kpis.adr)} icon={BarChart3} subtitle="Avg Daily Rate" testId="kpi-adr" />
        <KPICard title="RevPAN" value={fmt(kpis.revpan)} icon={TrendingDown} subtitle="Rev Per Available Night" testId="kpi-revpan" />
        <KPICard title="Active Properties" value={`${kpis.active_properties} / ${kpis.total_properties}`} icon={Home} testId="kpi-properties" />
        <KPICard title="Active Bookings" value={kpis.active_bookings} icon={CalendarDays} testId="kpi-bookings" />
      </div>

      {/* Charts & Lists */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Revenue Trends */}
        <Card className="lg:col-span-8" data-testid="revenue-trends-chart">
          <CardHeader className="pb-2">
            <CardTitle className="font-heading text-base font-semibold">Revenue Trends</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--chart-2))" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(var(--chart-2))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} className="text-muted-foreground" />
                  <YAxis tick={{ fontSize: 12 }} className="text-muted-foreground" tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                    formatter={(value) => [fmt(value)]}
                  />
                  <Area type="monotone" dataKey="revenue" stroke="hsl(var(--chart-2))" fill="url(#colorRevenue)" strokeWidth={2} />
                  <Area type="monotone" dataKey="expenses" stroke="hsl(var(--chart-5))" fill="transparent" strokeWidth={1.5} strokeDasharray="4 4" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Recent Bookings */}
        <Card className="lg:col-span-4" data-testid="recent-bookings">
          <CardHeader className="pb-2">
            <CardTitle className="font-heading text-base font-semibold">Recent Bookings</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {bookings.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">No bookings yet</p>
            ) : (
              <div className="space-y-3">
                {bookings.map((b) => (
                  <div key={b.id} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{b.guest_name}</p>
                      <p className="text-xs text-muted-foreground">{b.check_in} - {b.check_out}</p>
                    </div>
                    <div className="text-right shrink-0 ml-3">
                      <p className="text-sm font-data font-medium">{fmt(b.total_amount)}</p>
                      <Badge variant={b.status === "confirmed" ? "default" : b.status === "checked_in" ? "secondary" : "outline"} className="text-xs mt-0.5">
                        {b.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Staff Payments Due */}
      {kpis.staff_payments_due > 0 && (
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate("/staff")} data-testid="staff-payments-card">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="h-10 w-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
                <Users className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-sm font-medium">Staff Payments Due</p>
                <p className="text-2xl font-bold font-data">{fmt(kpis.staff_payments_due)}</p>
              </div>
            </div>
            <ArrowUpRight className="h-5 w-5 text-muted-foreground" />
          </CardContent>
        </Card>
      )}
    </>
  );
}

function OwnerDashboard({ kpis, trends, bookings, revenueTrend }) {
  return (
    <>
      {/* Owner-specific KPI Grid - focused on their properties' financials */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard title="My Revenue MTD" value={fmt(kpis.revenue_mtd)} icon={DollarSign} trend={revenueTrend} subtitle={`Last month: ${fmt(kpis.revenue_last_month)}`} testId="kpi-owner-revenue" />
        <KPICard title="Net Income" value={fmt(kpis.net_income)} icon={TrendingUp} variant="success" subtitle={`Expenses: ${fmt(kpis.total_expenses)}`} testId="kpi-owner-net-income" />
        <KPICard title="Occupancy Rate" value={`${kpis.occupancy_rate}%`} icon={Percent} testId="kpi-owner-occupancy" />
        <KPICard title="My Properties" value={kpis.total_properties} icon={Home} variant="info" testId="kpi-owner-properties" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <KPICard title="ADR" value={fmt(kpis.adr)} icon={BarChart3} subtitle="Avg Daily Rate" testId="kpi-owner-adr" />
        <KPICard title="Nights Booked" value={kpis.nights_booked} icon={CalendarDays} testId="kpi-owner-nights" />
        <KPICard title="Active Bookings" value={kpis.active_bookings} icon={CalendarDays} testId="kpi-owner-bookings" />
      </div>

      {/* Revenue Trends for Owner */}
      <Card data-testid="owner-revenue-trends-chart">
        <CardHeader className="pb-2">
          <CardTitle className="font-heading text-base font-semibold">My Properties - Revenue Trends</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorOwnerRevenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--chart-2))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--chart-2))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} className="text-muted-foreground" />
                <YAxis tick={{ fontSize: 12 }} className="text-muted-foreground" tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                  formatter={(value) => [fmt(value)]}
                />
                <Area type="monotone" dataKey="revenue" stroke="hsl(var(--chart-2))" fill="url(#colorOwnerRevenue)" strokeWidth={2} />
                <Area type="monotone" dataKey="expenses" stroke="hsl(var(--chart-5))" fill="transparent" strokeWidth={1.5} strokeDasharray="4 4" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Recent Bookings for Owner */}
      <Card data-testid="owner-recent-bookings">
        <CardHeader className="pb-2">
          <CardTitle className="font-heading text-base font-semibold">Recent Bookings on My Properties</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          {bookings.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">No bookings yet</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {bookings.slice(0, 6).map((b) => (
                <div key={b.id} className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{b.guest_name}</p>
                    <p className="text-xs text-muted-foreground">{b.check_in} - {b.check_out}</p>
                  </div>
                  <div className="text-right shrink-0 ml-3">
                    <p className="text-sm font-data font-medium">{fmt(b.total_amount)}</p>
                    <Badge variant={b.status === "confirmed" ? "default" : b.status === "checked_in" ? "secondary" : "outline"} className="text-xs mt-0.5">
                      {b.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}

function StaffDashboard({ kpis, bookings }) {
  return (
    <>
      {/* Staff-specific KPI Grid - focused on tasks and earnings */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard 
          title="My Earnings (MTD)" 
          value={fmt(kpis.staff_earnings || 0)} 
          icon={DollarSign} 
          variant="success"
          subtitle="This month" 
          testId="kpi-staff-earnings" 
        />
        <KPICard 
          title="Tasks Completed" 
          value={kpis.tasks_completed || 0} 
          icon={CheckCircle2} 
          variant="success"
          subtitle="This month" 
          testId="kpi-staff-tasks-completed" 
        />
        <KPICard 
          title="Upcoming Tasks" 
          value={kpis.upcoming_tasks || 0} 
          icon={Clock} 
          variant="warning"
          subtitle="Next 7 days" 
          testId="kpi-staff-upcoming-tasks" 
        />
        <KPICard 
          title="Assigned Properties" 
          value={kpis.total_properties} 
          icon={Home} 
          variant="info"
          testId="kpi-staff-properties" 
        />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card data-testid="staff-active-bookings">
          <CardHeader className="pb-2">
            <CardTitle className="font-heading text-base font-semibold flex items-center gap-2">
              <Briefcase className="h-4 w-4" />
              Active Assignments
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-muted/50 text-center">
                <p className="text-3xl font-bold font-data">{kpis.active_bookings}</p>
                <p className="text-sm text-muted-foreground">Active Bookings</p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50 text-center">
                <p className="text-3xl font-bold font-data">{kpis.nights_booked}</p>
                <p className="text-sm text-muted-foreground">Nights This Month</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="staff-performance">
          <CardHeader className="pb-2">
            <CardTitle className="font-heading text-base font-semibold flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Performance Overview
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-emerald-500/10 text-center">
                <p className="text-3xl font-bold font-data text-emerald-600 dark:text-emerald-400">{kpis.occupancy_rate}%</p>
                <p className="text-sm text-muted-foreground">Occupancy Rate</p>
              </div>
              <div className="p-4 rounded-lg bg-blue-500/10 text-center">
                <p className="text-3xl font-bold font-data text-blue-600 dark:text-blue-400">{kpis.active_properties}</p>
                <p className="text-sm text-muted-foreground">Properties Active</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Upcoming Check-ins/Check-outs */}
      <Card data-testid="staff-upcoming-work">
        <CardHeader className="pb-2">
          <CardTitle className="font-heading text-base font-semibold">Upcoming Work</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          {bookings.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">No upcoming bookings</p>
          ) : (
            <div className="space-y-3">
              {bookings.slice(0, 8).map((b) => (
                <div key={b.id} className="flex items-center justify-between py-3 px-4 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
                      b.status === "confirmed" ? "bg-blue-500/10" : 
                      b.status === "checked_in" ? "bg-emerald-500/10" : "bg-muted"
                    }`}>
                      {b.status === "confirmed" ? (
                        <CalendarDays className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                      ) : (
                        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{b.guest_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {b.status === "confirmed" ? `Check-in: ${b.check_in}` : `Check-out: ${b.check_out}`}
                      </p>
                    </div>
                  </div>
                  <Badge variant={b.status === "confirmed" ? "default" : "secondary"} className="text-xs">
                    {b.status === "confirmed" ? "Arriving" : "Departing"}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}

export default function Dashboard() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [kpis, setKpis] = useState(null);
  const [trends, setTrends] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [loadingData, setLoadingData] = useState(true);
  const [seeding, setSeeding] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) navigate("/");
  }, [user, authLoading, navigate]);

  useEffect(() => {
    if (!user?.company_id) return;
    const fetchData = async () => {
      try {
        const [kpiRes, trendRes, bookRes] = await Promise.all([
          fetch(`${API}/api/dashboard/kpis`, { credentials: "include" }),
          fetch(`${API}/api/dashboard/revenue-trends`, { credentials: "include" }),
          fetch(`${API}/api/bookings`, { credentials: "include" }),
        ]);
        if (kpiRes.ok) setKpis(await kpiRes.json());
        if (trendRes.ok) setTrends(await trendRes.json());
        if (bookRes.ok) {
          const b = await bookRes.json();
          setBookings(b.slice(0, 8));
        }
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        setLoadingData(false);
      }
    };
    fetchData();
  }, [user]);

  const handleSeedData = async () => {
    setSeeding(true);
    try {
      const res = await fetch(`${API}/api/seed-demo-data`, { method: "POST", credentials: "include" });
      if (res.ok) {
        toast.success("Demo data created! Refreshing...");
        setTimeout(() => window.location.reload(), 1000);
      } else {
        toast.error("Failed to seed demo data");
      }
    } catch (err) {
      toast.error("Error seeding data");
    } finally {
      setSeeding(false);
    }
  };

  if (authLoading || !user) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  const revenueTrend = kpis && kpis.revenue_last_month > 0 ? ((kpis.revenue_mtd - kpis.revenue_last_month) / kpis.revenue_last_month) * 100 : null;
  const userRole = kpis?.role || user?.role || "company_admin";

  // Get role-specific title
  const getDashboardTitle = () => {
    switch (userRole) {
      case "owner":
        return "Owner Dashboard";
      case "staff":
        return "Staff Dashboard";
      default:
        return "Dashboard";
    }
  };

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="dashboard-page">
        {/* Role indicator for non-admin users */}
        {userRole !== "company_admin" && (
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs" data-testid="role-badge">
              {userRole === "owner" ? "Property Owner" : "Staff Member"}
            </Badge>
            <h1 className="text-lg font-heading font-semibold">{getDashboardTitle()}</h1>
          </div>
        )}

        {/* Empty state - only for admins */}
        {kpis && kpis.total_properties === 0 && userRole === "company_admin" && (
          <Card className="border-dashed" data-testid="empty-state-card">
            <CardContent className="p-6 text-center space-y-4">
              <Home className="h-10 w-10 mx-auto text-muted-foreground" />
              <div>
                <h3 className="font-heading font-semibold text-lg">No properties yet</h3>
                <p className="text-sm text-muted-foreground mt-1">Add properties manually or load demo data to explore the dashboard.</p>
              </div>
              <div className="flex justify-center gap-3">
                <Button onClick={() => navigate("/properties")} data-testid="add-property-btn">Add Property</Button>
                <Button variant="outline" onClick={handleSeedData} disabled={seeding} data-testid="seed-data-btn">
                  {seeding && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Load Demo Data
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Loading state */}
        {loadingData ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <Card key={i}><CardContent className="p-5"><Skeleton className="h-4 w-24 mb-3" /><Skeleton className="h-8 w-32" /></CardContent></Card>
            ))}
          </div>
        ) : kpis && (
          <>
            {/* Role-specific dashboard views */}
            {userRole === "company_admin" && (
              <AdminDashboard 
                kpis={kpis} 
                trends={trends} 
                bookings={bookings} 
                loadingData={loadingData} 
                revenueTrend={revenueTrend} 
                navigate={navigate} 
              />
            )}
            {userRole === "owner" && (
              <OwnerDashboard 
                kpis={kpis} 
                trends={trends} 
                bookings={bookings} 
                revenueTrend={revenueTrend} 
              />
            )}
            {userRole === "staff" && (
              <StaffDashboard 
                kpis={kpis} 
                bookings={bookings} 
              />
            )}
          </>
        )}
      </div>
    </Layout>
  );
}
