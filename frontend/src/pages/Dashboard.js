import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DollarSign, TrendingUp, Home, CalendarDays, Percent, BarChart3, ArrowUpRight, ArrowDownRight, Building2, Moon } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v);

// Premium KPI Card Component
function KPICard({ label, value, subtitle, icon: Icon, trend, large = false, delay = 0 }) {
  const isPositive = trend > 0;
  const showTrend = trend !== undefined && trend !== null && trend !== 0;
  
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
        <div className="h-12 w-12 rounded-xl bg-teal-50 dark:bg-teal-900/30 flex items-center justify-center shrink-0 transition-transform hover:scale-110">
          <Icon className="h-6 w-6 text-teal-600 dark:text-teal-400" />
        </div>
      </div>
    </div>
  );
}

// Secondary KPI (smaller)
function SecondaryKPI({ label, value, icon: Icon, delay = 0 }) {
  return (
    <div 
      className="bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-xl p-4 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 animate-fade-in opacity-0"
      style={{ animationDelay: `${delay}s` }}
    >
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-gray-50 dark:bg-gray-700/50 flex items-center justify-center">
          <Icon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">{label}</p>
          <p className="text-lg font-bold font-heading text-gray-900 dark:text-gray-100 tabular-nums">{value}</p>
        </div>
      </div>
    </div>
  );
}

// Recent Booking Item
function BookingItem({ booking, propertyName, index = 0 }) {
  const statusColors = {
    confirmed: "bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-900/30 dark:text-teal-400 dark:border-teal-700",
    checked_in: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-700",
    checked_out: "bg-gray-50 text-gray-600 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-600",
    cancelled: "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-700",
    blocked: "bg-gray-100 text-gray-500 border-gray-300 dark:bg-gray-800 dark:text-gray-500 dark:border-gray-600",
  };
  
  return (
    <div 
      className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 -mx-2 px-2 rounded-lg transition-colors animate-fade-in opacity-0"
      style={{ animationDelay: `${0.3 + index * 0.05}s` }}
    >
      <div className="min-w-0 flex-1">
        <p className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">{booking.guest_name}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{propertyName}</p>
      </div>
      <div className="flex items-center gap-3 ml-4">
        <Badge variant="outline" className={`text-xs ${statusColors[booking.status] || ''}`}>
          {booking.status?.replace('_', ' ')}
        </Badge>
        <span className="text-sm font-semibold font-heading tabular-nums text-gray-900 dark:text-gray-100">
          {fmt(booking.total_amount || 0)}
        </span>
      </div>
    </div>
  );
}

// Custom Tooltip for Chart
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
      <p className="text-xs font-semibold text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-bold font-heading text-gray-900">{fmt(payload[0].value)}</p>
    </div>
  );
}

// Loading Skeleton
function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1,2,3,4,5,6].map(i => (
          <Skeleton key={i} className="h-32 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Skeleton className="lg:col-span-2 h-80 rounded-xl" />
        <Skeleton className="h-80 rounded-xl" />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [kpis, setKpis] = useState({});
  const [trends, setTrends] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) navigate("/");
  }, [user, authLoading, navigate]);

  useEffect(() => {
    if (!user?.company_id) return;
    
    const fetchData = async () => {
      try {
        const [kpiRes, trendRes, bookRes, propRes] = await Promise.all([
          fetch(`${API}/api/dashboard/kpis`, { credentials: "include" }),
          fetch(`${API}/api/dashboard/revenue-trends`, { credentials: "include" }),
          fetch(`${API}/api/bookings?limit=8`, { credentials: "include" }),
          fetch(`${API}/api/properties`, { credentials: "include" }),
        ]);
        
        if (kpiRes.ok) setKpis(await kpiRes.json());
        if (trendRes.ok) setTrends(await trendRes.json());
        if (bookRes.ok) {
          const data = await bookRes.json();
          setBookings(data.filter(b => b.status !== 'blocked').slice(0, 6));
        }
        if (propRes.ok) setProperties(await propRes.json());
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [user]);

  const getPropName = (id) => properties.find(p => p.id === id)?.name || "Unknown";
  
  const revenueTrend = kpis.revenue_last_month > 0 
    ? ((kpis.revenue_mtd - kpis.revenue_last_month) / kpis.revenue_last_month * 100) 
    : 0;

  if (authLoading || !user) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600" />
      </div>
    );
  }

  return (
    <Layout>
      <div className="space-y-8" data-testid="dashboard-page">
        {/* Header */}
        <div className="flex items-end justify-between animate-fade-in">
          <div>
            <h1 className="text-2xl font-bold font-heading text-gray-900 dark:text-gray-100">
              Hey, {user.name?.split(' ')[0] || 'there'}
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">Here's your performance overview</p>
          </div>
          <Badge variant="outline" className="text-xs font-medium capitalize bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-400 border-teal-200 dark:border-teal-700">
            {user.role?.replace('_', ' ')}
          </Badge>
        </div>

        {loading ? <DashboardSkeleton /> : (
          <>
            {/* Primary KPIs - Row 1 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <KPICard 
                label="Revenue MTD" 
                value={fmt(kpis.revenue_mtd || 0)} 
                subtitle={`Last month: ${fmt(kpis.revenue_last_month || 0)}`}
                icon={DollarSign} 
                trend={revenueTrend}
                large
                delay={0.1}
              />
              <KPICard 
                label="Net Income" 
                value={fmt(kpis.net_income || 0)} 
                subtitle={`Expenses: ${fmt(kpis.total_expenses || 0)}`}
                icon={TrendingUp}
                large
                delay={0.15}
              />
              <KPICard 
                label="Occupancy Rate" 
                value={`${kpis.occupancy_rate || 0}%`}
                subtitle={`${kpis.nights_booked || 0} nights booked`}
                icon={Percent}
                large
                delay={0.2}
              />
            </div>

            {/* Primary KPIs - Row 2 */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <KPICard 
                label="ADR" 
                value={fmt(kpis.adr || 0)} 
                subtitle="Average Daily Rate"
                icon={BarChart3}
                delay={0.25}
              />
              <KPICard 
                label="RevPAN" 
                value={fmt(kpis.revpan || 0)} 
                subtitle="Revenue Per Available Night"
                icon={Moon}
                delay={0.3}
              />
              <KPICard 
                label="Active Bookings" 
                value={kpis.active_bookings || 0}
                subtitle={`${kpis.total_properties || 0} properties`}
                icon={CalendarDays}
                delay={0.35}
              />
            </div>

            {/* Secondary KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <SecondaryKPI label="Properties" value={`${kpis.active_properties || 0} / ${kpis.total_properties || 0}`} icon={Building2} delay={0.4} />
              <SecondaryKPI label="Nights Booked" value={kpis.nights_booked || 0} icon={CalendarDays} delay={0.45} />
              <SecondaryKPI label="Expense Ratio" value={kpis.revenue_mtd > 0 ? `${((kpis.total_expenses || 0) / kpis.revenue_mtd * 100).toFixed(0)}%` : '0%'} icon={TrendingUp} delay={0.5} />
              <SecondaryKPI label="Active Properties" value={kpis.active_properties || 0} icon={Home} delay={0.55} />
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Revenue Trend Chart */}
              <Card className="lg:col-span-2 shadow-sm border-gray-100 dark:border-gray-700/50 animate-fade-in opacity-0" style={{ animationDelay: '0.4s' }} data-testid="revenue-chart">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-semibold font-heading text-gray-900 dark:text-gray-100">Revenue Trend</CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="h-[320px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={trends} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#0D9488" stopOpacity={0.2} />
                            <stop offset="100%" stopColor="#0D9488" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <XAxis 
                          dataKey="month" 
                          axisLine={false} 
                          tickLine={false} 
                          tick={{ fill: '#9CA3AF', fontSize: 12 }}
                          dy={10}
                        />
                        <YAxis 
                          axisLine={false} 
                          tickLine={false} 
                          tick={{ fill: '#9CA3AF', fontSize: 12 }}
                          tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`}
                          dx={-10}
                        />
                        <Tooltip content={<ChartTooltip />} />
                        <Area 
                          type="monotone" 
                          dataKey="revenue" 
                          stroke="#0D9488" 
                          strokeWidth={2.5}
                          fill="url(#revenueGradient)" 
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              {/* Recent Bookings */}
              <Card className="shadow-sm border-gray-100 dark:border-gray-700/50 animate-fade-in opacity-0" style={{ animationDelay: '0.45s' }} data-testid="recent-bookings">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold font-heading text-gray-900 dark:text-gray-100">Recent Bookings</CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="max-h-[320px] overflow-y-auto pr-2">
                    {bookings.length === 0 ? (
                      <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-8">No recent bookings</p>
                    ) : (
                      bookings.map((b, i) => (
                        <BookingItem key={b.id} booking={b} propertyName={getPropName(b.property_id)} index={i} />
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
