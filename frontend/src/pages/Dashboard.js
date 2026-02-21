import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { DollarSign, TrendingUp, TrendingDown, Home, CalendarDays, Percent, BarChart3, Users, ArrowUpRight, ArrowDownRight, Loader2 } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }).format(v);

function KPICard({ title, value, subtitle, icon: Icon, trend, testId }) {
  const isPositive = trend > 0;
  return (
    <Card className="relative overflow-hidden" data-testid={testId}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground font-medium">{title}</p>
            <p className="text-2xl font-bold font-data tracking-tight">{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <Icon className="h-4 w-4 text-primary" />
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

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="dashboard-page">
        {/* Empty state */}
        {kpis && kpis.total_properties === 0 && user?.role === "company_admin" && (
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

        {/* KPI Grid */}
        {loadingData ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <Card key={i}><CardContent className="p-5"><Skeleton className="h-4 w-24 mb-3" /><Skeleton className="h-8 w-32" /></CardContent></Card>
            ))}
          </div>
        ) : kpis && (
          <>
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
            {user?.role === "company_admin" && kpis.staff_payments_due > 0 && (
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
        )}
      </div>
    </Layout>
  );
}
