import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { DollarSign, TrendingUp, TrendingDown, Percent, CalendarDays, BarChart3, Home, ArrowUpRight, ArrowDownRight, Filter, Globe } from "lucide-react";
import { AreaChart, Area, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }).format(v);

function KPICard({ title, value, previousValue, change, icon: Icon, testId, variant = "default" }) {
  const isPositive = change > 0;
  const variantStyles = {
    default: "bg-primary/10 text-primary",
    success: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
    info: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  };

  return (
    <Card data-testid={testId}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground font-medium">{title}</p>
            <p className="text-2xl font-bold font-data tracking-tight">{value}</p>
            {previousValue !== undefined && (
              <p className="text-xs text-muted-foreground">vs {previousValue} last month</p>
            )}
          </div>
          <div className={`h-10 w-10 rounded-lg flex items-center justify-center shrink-0 ${variantStyles[variant]}`}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
        {change !== undefined && change !== null && (
          <div className={`flex items-center gap-1 mt-3 text-xs font-medium ${isPositive ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
            {isPositive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            <span>{isPositive ? "+" : ""}{change}% vs last month</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function Analytics() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState(null);
  const [sourceBreakdown, setSourceBreakdown] = useState(null);
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedProperty, setSelectedProperty] = useState("all");
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const propRes = await fetch(`${API}/api/properties`, { credentials: "include" });
      if (propRes.ok) setProperties(await propRes.json());

      let url = `${API}/api/analytics?year=${selectedYear}&month=${selectedMonth}`;
      let srcUrl = `${API}/api/analytics/source-breakdown?year=${selectedYear}&month=${selectedMonth}`;
      if (selectedProperty !== "all") {
        url += `&property_id=${selectedProperty}`;
        srcUrl += `&property_id=${selectedProperty}`;
      }
      
      const [analyticsRes, srcRes] = await Promise.all([
        fetch(url, { credentials: "include" }),
        fetch(srcUrl, { credentials: "include" }),
      ]);
      if (analyticsRes.ok) setAnalytics(await analyticsRes.json());
      if (srcRes.ok) setSourceBreakdown(await srcRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchData(); }, [user, selectedProperty, selectedYear, selectedMonth]); // eslint-disable-line

  if (authLoading || !user) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  const currentYear = new Date().getFullYear();
  const years = [currentYear, currentYear - 1, currentYear - 2];
  const months = [
    { value: 1, label: "January" },
    { value: 2, label: "February" },
    { value: 3, label: "March" },
    { value: 4, label: "April" },
    { value: 5, label: "May" },
    { value: 6, label: "June" },
    { value: 7, label: "July" },
    { value: 8, label: "August" },
    { value: 9, label: "September" },
    { value: 10, label: "October" },
    { value: 11, label: "November" },
    { value: 12, label: "December" },
  ];

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="analytics-page">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-in">
          <div>
            <h1 className="font-heading text-2xl font-bold text-foreground">Analytics</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {analytics?.period?.current_month || "Loading..."}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Select value={selectedProperty} onValueChange={setSelectedProperty}>
              <SelectTrigger className="w-[180px] hover:border-primary/30" data-testid="property-filter">
                <Filter className="h-4 w-4 mr-2 text-muted-foreground" />
                <SelectValue placeholder="All Properties" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Properties</SelectItem>
                {properties.map(p => (
                  <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={String(selectedMonth)} onValueChange={v => setSelectedMonth(parseInt(v))}>
              <SelectTrigger className="w-[140px] hover:border-primary/30" data-testid="month-filter">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {months.map(m => (
                  <SelectItem key={m.value} value={String(m.value)}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={String(selectedYear)} onValueChange={v => setSelectedYear(parseInt(v))}>
              <SelectTrigger className="w-[100px] hover:border-primary/30" data-testid="year-filter">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {years.map(y => (
                  <SelectItem key={y} value={String(y)}>{y}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <Card key={i}><CardContent className="p-5"><Skeleton className="h-4 w-24 mb-3" /><Skeleton className="h-8 w-32" /></CardContent></Card>
            ))}
          </div>
        ) : analytics ? (
          <>
            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KPICard 
                title="Revenue MTD" 
                value={fmt(analytics.current.revenue)} 
                previousValue={fmt(analytics.previous.revenue)}
                change={analytics.changes.revenue_change}
                icon={DollarSign} 
                testId="kpi-revenue"
              />
              <KPICard 
                title="Net Income" 
                value={fmt(analytics.current.net_income)} 
                previousValue={fmt(analytics.previous.net_income)}
                icon={TrendingUp} 
                variant="success"
                testId="kpi-net-income"
              />
              <KPICard 
                title="Occupancy Rate" 
                value={`${analytics.current.occupancy_rate}%`}
                previousValue={`${analytics.previous.occupancy_rate}%`}
                change={analytics.changes.occupancy_change}
                icon={Percent} 
                testId="kpi-occupancy"
              />
              <KPICard 
                title="Nights Booked" 
                value={analytics.current.nights_booked}
                previousValue={analytics.previous.nights_booked}
                icon={CalendarDays} 
                variant="info"
                testId="kpi-nights"
              />
              <KPICard 
                title="ADR" 
                value={fmt(analytics.current.adr)}
                previousValue={fmt(analytics.previous.adr)}
                change={analytics.changes.adr_change}
                icon={BarChart3} 
                testId="kpi-adr"
              />
              <KPICard 
                title="RevPAN" 
                value={fmt(analytics.current.revpan)}
                previousValue={fmt(analytics.previous.revpan)}
                icon={TrendingDown} 
                testId="kpi-revpan"
              />
              <KPICard 
                title="Active Properties" 
                value={`${analytics.current.active_properties} / ${analytics.current.total_properties}`}
                previousValue={`${analytics.previous.active_properties} last month`}
                icon={Home} 
                testId="kpi-properties"
              />
              <KPICard 
                title="Bookings" 
                value={analytics.current.total_bookings}
                previousValue={analytics.previous.total_bookings}
                change={analytics.changes.bookings_change}
                icon={CalendarDays} 
                variant="warning"
                testId="kpi-bookings"
              />
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

              {/* Source Breakdown Charts */}
              {sourceBreakdown && sourceBreakdown.sources.length > 0 && (
                <>
                  <SourceBreakdownChart 
                    data={sourceBreakdown} 
                    title="Bookings by Source"
                    metric="bookings"
                    pctKey="booking_pct"
                    testId="source-bookings-chart"
                  />
                  <SourceBreakdownChart 
                    data={sourceBreakdown} 
                    metric="revenue"
                    title="Revenue by Source"
                    pctKey="revenue_pct"
                    testId="source-revenue-chart"
                  />
                </>
              )}

              {/* Revenue Trend Chart */}
              <Card className="lg:col-span-2" data-testid="revenue-trend-chart">
                <CardHeader>
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <DollarSign className="h-4 w-4" />
                    Revenue & Expenses Trend (12 Months)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={analytics.trends} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="hsl(var(--chart-2))" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="hsl(var(--chart-2))" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="month" tick={{ fontSize: 11 }} className="text-muted-foreground" />
                        <YAxis tick={{ fontSize: 11 }} className="text-muted-foreground" tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                          formatter={(value, name) => [fmt(value), name === "revenue" ? "Revenue" : name === "expenses" ? "Expenses" : "Net Income"]}
                        />
                        <Legend />
                        <Area type="monotone" dataKey="revenue" name="Revenue" stroke="hsl(var(--chart-2))" fill="url(#colorRevenue)" strokeWidth={2} />
                        <Area type="monotone" dataKey="expenses" name="Expenses" stroke="hsl(var(--chart-5))" fill="transparent" strokeWidth={1.5} strokeDasharray="4 4" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              {/* Occupancy Trend */}
              <Card data-testid="occupancy-chart">
                <CardHeader>
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <Percent className="h-4 w-4" />
                    Occupancy Rate Trend
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={analytics.trends} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="month" tick={{ fontSize: 11 }} className="text-muted-foreground" />
                        <YAxis tick={{ fontSize: 11 }} className="text-muted-foreground" tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                          formatter={(value) => [`${value}%`, "Occupancy"]}
                        />
                        <Line type="monotone" dataKey="occupancy_rate" name="Occupancy" stroke="hsl(var(--chart-1))" strokeWidth={2} dot={{ fill: "hsl(var(--chart-1))", strokeWidth: 0, r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              {/* ADR Trend */}
              <Card data-testid="adr-chart">
                <CardHeader>
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <BarChart3 className="h-4 w-4" />
                    ADR Trend
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.trends} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="month" tick={{ fontSize: 11 }} className="text-muted-foreground" />
                        <YAxis tick={{ fontSize: 11 }} className="text-muted-foreground" tickFormatter={(v) => `$${v}`} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                          formatter={(value) => [fmt(value), "ADR"]}
                        />
                        <Bar dataKey="adr" name="ADR" fill="hsl(var(--chart-3))" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              {/* Nights Booked */}
              <Card className="lg:col-span-2" data-testid="nights-chart">
                <CardHeader>
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <CalendarDays className="h-4 w-4" />
                    Nights Booked vs Total Bookings
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.trends} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="month" tick={{ fontSize: 11 }} className="text-muted-foreground" />
                        <YAxis yAxisId="left" tick={{ fontSize: 11 }} className="text-muted-foreground" />
                        <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} className="text-muted-foreground" />
                        <Tooltip
                          contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                        />
                        <Legend />
                        <Bar yAxisId="left" dataKey="nights_booked" name="Nights Booked" fill="hsl(var(--chart-4))" radius={[4, 4, 0, 0]} />
                        <Bar yAxisId="right" dataKey="total_bookings" name="Total Bookings" fill="hsl(var(--chart-2))" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardContent className="p-5">
                  <h3 className="text-sm font-medium text-muted-foreground mb-3">Period Comparison</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Current Month</span>
                      <Badge variant="default">{analytics.period.current_month}</Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Previous Month</span>
                      <Badge variant="outline">{analytics.period.previous_month}</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-5">
                  <h3 className="text-sm font-medium text-muted-foreground mb-3">Revenue Summary</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Total Revenue</span>
                      <span className="font-data font-medium">{fmt(analytics.current.revenue)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Total Expenses</span>
                      <span className="font-data font-medium text-red-600 dark:text-red-400">-{fmt(analytics.current.expenses)}</span>
                    </div>
                    <div className="flex justify-between items-center pt-2 border-t">
                      <span className="text-sm font-medium">Net Income</span>
                      <span className="font-data font-bold text-emerald-600 dark:text-emerald-400">{fmt(analytics.current.net_income)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-5">
                  <h3 className="text-sm font-medium text-muted-foreground mb-3">Performance Metrics</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Avg Daily Rate</span>
                      <span className="font-data font-medium">{fmt(analytics.current.adr)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">RevPAN</span>
                      <span className="font-data font-medium">{fmt(analytics.current.revpan)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Active Bookings</span>
                      <span className="font-data font-medium">{analytics.current.active_bookings}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        ) : (
          <Card className="border-dashed">
            <CardContent className="p-12 text-center">
              <BarChart3 className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">No analytics data available</p>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
}
