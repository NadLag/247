import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DollarSign, TrendingUp, TrendingDown, Percent, CalendarDays, BarChart3, Home, ArrowUpRight, ArrowDownRight, Filter, Globe, Download, Building2, FileText } from "lucide-react";
import { AreaChart, Area, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }).format(v || 0);
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

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

const SOURCE_COLORS = ["#0D9488", "#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"];

function SourceBreakdownChart({ data, title, metric, pctKey, testId }) {
  const chartData = data.sources.map((s, i) => ({
    name: s.label,
    value: s[metric],
    pct: s[pctKey],
    fill: SOURCE_COLORS[i % SOURCE_COLORS.length],
  }));
  
  const total = metric === "revenue" 
    ? `$${data.total_revenue.toLocaleString()}`
    : data.total_bookings;

  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <Globe className="h-4 w-4" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6">
          <div className="w-[180px] h-[180px] shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  dataKey="value"
                  stroke="hsl(var(--background))"
                  strokeWidth={2}
                >
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                  formatter={(value, name) => [
                    metric === "revenue" ? `$${value.toLocaleString()}` : value,
                    name
                  ]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 space-y-2 min-w-0">
            <p className="text-xs text-muted-foreground mb-3">
              Total: <span className="font-semibold text-foreground">{total}</span>
            </p>
            {chartData.map((entry, i) => (
              <div key={i} className="flex items-center gap-2 text-sm" data-testid={`source-item-${entry.name.toLowerCase().replace(/\s/g, '-')}`}>
                <div className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: entry.fill }} />
                <span className="truncate flex-1 text-muted-foreground">{entry.name}</span>
                <span className="font-data font-medium tabular-nums shrink-0">
                  {entry.pct}%
                </span>
                <span className="font-data text-xs text-muted-foreground tabular-nums shrink-0">
                  {metric === "revenue" ? `$${entry.value.toLocaleString()}` : entry.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

const payoutStatusColors = {
  pending: "bg-amber-500/10 text-amber-600 border-amber-200",
  paid: "bg-emerald-500/10 text-emerald-600 border-emerald-200",
};

export default function Analytics() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState(null);
  const [sourceBreakdown, setSourceBreakdown] = useState(null);
  const [ownerReport, setOwnerReport] = useState(null);
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedProperty, setSelectedProperty] = useState("all");
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [activeTab, setActiveTab] = useState("performance");

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const propRes = await fetch(`${API}/api/properties`, { credentials: "include" });
      if (propRes.ok) setProperties(await propRes.json());

      let url = `${API}/api/analytics?year=${selectedYear}&month=${selectedMonth}`;
      let srcUrl = `${API}/api/analytics/source-breakdown?year=${selectedYear}&month=${selectedMonth}`;
      let reportUrl = `${API}/api/reports/owner?year=${selectedYear}&month=${selectedMonth}`;
      
      if (selectedProperty !== "all") {
        url += `&property_id=${selectedProperty}`;
        srcUrl += `&property_id=${selectedProperty}`;
        reportUrl += `&property_id=${selectedProperty}`;
      }
      
      const [analyticsRes, srcRes, reportRes] = await Promise.all([
        fetch(url, { credentials: "include" }),
        fetch(srcUrl, { credentials: "include" }),
        fetch(reportUrl, { credentials: "include" }),
      ]);
      
      if (analyticsRes.ok) setAnalytics(await analyticsRes.json());
      if (srcRes.ok) setSourceBreakdown(await srcRes.json());
      if (reportRes.ok) setOwnerReport(await reportRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchData(); }, [user, selectedProperty, selectedYear, selectedMonth]); // eslint-disable-line

  const exportCSV = () => {
    if (!ownerReport?.properties?.length) return;
    const headers = ["Property", "Bookings", "Occupancy %", "Gross Revenue", "Expenses", "Net Profit", "Owner Share %", "Payout Amount", "Payout Status"];
    const rows = ownerReport.properties.map(p => [
      p.property_name, p.total_bookings, p.occupancy_rate, p.gross_revenue, p.total_expenses, p.net_profit, p.owner_share_pct, p.owner_payout_amount, p.payout_status,
    ]);
    const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `financial-report-${MONTHS[selectedMonth - 1]}-${selectedYear}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (authLoading || !user) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  const currentYear = new Date().getFullYear();
  const years = [currentYear, currentYear - 1, currentYear - 2];
  const months = MONTHS.map((label, i) => ({ value: i + 1, label }));

  // Report chart data
  const revenueChartData = ownerReport?.properties?.map(p => ({
    name: p.property_name?.length > 15 ? p.property_name.slice(0, 15) + "..." : p.property_name,
    Revenue: p.gross_revenue,
    Expenses: p.total_expenses,
    Profit: p.net_profit,
  })) || [];

  const sourceChartData = ownerReport?.properties?.reduce((acc, p) => {
    Object.entries(p.revenue_by_source || {}).forEach(([src, amt]) => {
      const existing = acc.find(a => a.name === src);
      if (existing) existing.value += amt;
      else acc.push({ name: src, value: amt });
    });
    return acc;
  }, []) || [];

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="analytics-page">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-in">
          <div>
            <h1 className="font-heading text-2xl font-bold text-foreground">Analytics</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {MONTHS[selectedMonth - 1]} {selectedYear}
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

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="performance" data-testid="tab-performance">
              <BarChart3 className="h-4 w-4 mr-2" />Performance
            </TabsTrigger>
            <TabsTrigger value="reports" data-testid="tab-reports">
              <FileText className="h-4 w-4 mr-2" />Financial Reports
            </TabsTrigger>
          </TabsList>

          {/* Performance Analytics Tab */}
          <TabsContent value="performance" className="mt-6 space-y-6">
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
                  <KPICard title="Revenue MTD" value={fmt(analytics.current.revenue)} previousValue={fmt(analytics.previous.revenue)} change={analytics.changes.revenue_change} icon={DollarSign} testId="kpi-revenue" />
                  <KPICard title="Net Income" value={fmt(analytics.current.net_income)} previousValue={fmt(analytics.previous.net_income)} icon={TrendingUp} variant="success" testId="kpi-net-income" />
                  <KPICard title="Occupancy Rate" value={`${analytics.current.occupancy_rate}%`} previousValue={`${analytics.previous.occupancy_rate}%`} change={analytics.changes.occupancy_change} icon={Percent} testId="kpi-occupancy" />
                  <KPICard title="Nights Booked" value={analytics.current.nights_booked} previousValue={analytics.previous.nights_booked} icon={CalendarDays} variant="info" testId="kpi-nights" />
                  <KPICard title="ADR" value={fmt(analytics.current.adr)} previousValue={fmt(analytics.previous.adr)} change={analytics.changes.adr_change} icon={BarChart3} testId="kpi-adr" />
                  <KPICard title="RevPAN" value={fmt(analytics.current.revpan)} previousValue={fmt(analytics.previous.revpan)} icon={TrendingDown} testId="kpi-revpan" />
                  <KPICard title="Active Properties" value={`${analytics.current.active_properties} / ${analytics.current.total_properties}`} previousValue={`${analytics.previous.active_properties} last month`} icon={Home} testId="kpi-properties" />
                  <KPICard title="Bookings" value={analytics.current.total_bookings} previousValue={analytics.previous.total_bookings} change={analytics.changes.bookings_change} icon={CalendarDays} variant="warning" testId="kpi-bookings" />
                </div>

                {/* Charts */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {sourceBreakdown && sourceBreakdown.sources.length > 0 && (
                    <>
                      <SourceBreakdownChart data={sourceBreakdown} title="Bookings by Source" metric="bookings" pctKey="booking_pct" testId="source-bookings-chart" />
                      <SourceBreakdownChart data={sourceBreakdown} metric="revenue" title="Revenue by Source" pctKey="revenue_pct" testId="source-revenue-chart" />
                    </>
                  )}

                  {/* Revenue Trend Chart */}
                  <Card className="lg:col-span-2" data-testid="revenue-trend-chart">
                    <CardHeader>
                      <CardTitle className="text-base font-semibold flex items-center gap-2">
                        <DollarSign className="h-4 w-4" />Revenue & Expenses Trend (12 Months)
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
                            <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} formatter={(value, name) => [fmt(value), name === "revenue" ? "Revenue" : name === "expenses" ? "Expenses" : "Net Income"]} />
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
                        <Percent className="h-4 w-4" />Occupancy Rate Trend
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[250px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={analytics.trends} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                            <XAxis dataKey="month" tick={{ fontSize: 11 }} className="text-muted-foreground" />
                            <YAxis tick={{ fontSize: 11 }} className="text-muted-foreground" tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
                            <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} formatter={(value) => [`${value}%`, "Occupancy"]} />
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
                        <BarChart3 className="h-4 w-4" />ADR Trend
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[250px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={analytics.trends} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                            <XAxis dataKey="month" tick={{ fontSize: 11 }} className="text-muted-foreground" />
                            <YAxis tick={{ fontSize: 11 }} className="text-muted-foreground" tickFormatter={(v) => `$${v}`} />
                            <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} formatter={(value) => [fmt(value), "ADR"]} />
                            <Bar dataKey="adr" name="ADR" fill="hsl(var(--chart-3))" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
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
          </TabsContent>

          {/* Financial Reports Tab */}
          <TabsContent value="reports" className="mt-6 space-y-6">
            <div className="flex justify-end">
              <Button variant="outline" onClick={exportCSV} disabled={!ownerReport?.properties?.length} data-testid="export-csv-btn">
                <Download className="mr-2 h-4 w-4" />Export CSV
              </Button>
            </div>

            {loading ? (
              <Card><CardContent className="p-6 h-48 animate-pulse bg-muted" /></Card>
            ) : !ownerReport || !ownerReport.properties?.length ? (
              <Card className="border-dashed">
                <CardContent className="p-12 text-center">
                  <FileText className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                  <p className="text-muted-foreground">No data available for this period</p>
                </CardContent>
              </Card>
            ) : (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="report-summary">
                  <Card><CardContent className="p-4">
                    <p className="text-xs text-muted-foreground">Total Revenue</p>
                    <p className="text-xl font-bold font-data text-primary">{fmt(ownerReport.summary.total_revenue)}</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <p className="text-xs text-muted-foreground">Total Expenses</p>
                    <p className="text-xl font-bold font-data text-red-500">{fmt(ownerReport.summary.total_expenses)}</p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <p className="text-xs text-muted-foreground">Net Profit</p>
                    <p className={`text-xl font-bold font-data ${ownerReport.summary.net_profit >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                      {fmt(ownerReport.summary.net_profit)}
                    </p>
                  </CardContent></Card>
                  <Card><CardContent className="p-4">
                    <p className="text-xs text-muted-foreground">Avg Occupancy</p>
                    <p className="text-xl font-bold font-data">{ownerReport.summary.avg_occupancy}%</p>
                  </CardContent></Card>
                </div>

                {/* Charts */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {revenueChartData.length > 0 && (
                    <Card data-testid="revenue-expense-chart">
                      <CardHeader className="pb-2"><CardTitle className="text-base font-semibold flex items-center gap-2"><BarChart3 className="h-4 w-4" />Revenue vs Expenses</CardTitle></CardHeader>
                      <CardContent>
                        <ResponsiveContainer width="100%" height={250}>
                          <BarChart data={revenueChartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                            <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `$${v >= 1000 ? `${(v/1000).toFixed(0)}k` : v}`} />
                            <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} formatter={v => fmt(v)} />
                            <Bar dataKey="Revenue" fill="#0D9488" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="Expenses" fill="#EF4444" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </CardContent>
                    </Card>
                  )}

                  {sourceChartData.length > 0 && (
                    <Card data-testid="source-chart">
                      <CardHeader className="pb-2"><CardTitle className="text-base font-semibold flex items-center gap-2"><TrendingUp className="h-4 w-4" />Revenue by Channel</CardTitle></CardHeader>
                      <CardContent>
                        <div className="flex items-center gap-6">
                          <div className="w-[180px] h-[180px] shrink-0">
                            <ResponsiveContainer width="100%" height="100%">
                              <PieChart>
                                <Pie data={sourceChartData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" stroke="hsl(var(--background))" strokeWidth={2}>
                                  {sourceChartData.map((_, i) => <Cell key={i} fill={SOURCE_COLORS[i % SOURCE_COLORS.length]} />)}
                                </Pie>
                                <Tooltip formatter={v => fmt(v)} contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} />
                              </PieChart>
                            </ResponsiveContainer>
                          </div>
                          <div className="flex-1 space-y-2 min-w-0">
                            {sourceChartData.map((s, i) => {
                              const total = sourceChartData.reduce((a, b) => a + b.value, 0);
                              return (
                                <div key={i} className="flex items-center gap-2 text-sm">
                                  <div className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: SOURCE_COLORS[i % SOURCE_COLORS.length] }} />
                                  <span className="truncate flex-1 text-muted-foreground">{s.name}</span>
                                  <span className="font-data font-medium tabular-nums shrink-0">{total > 0 ? Math.round(s.value / total * 100) : 0}%</span>
                                  <span className="font-data text-xs text-muted-foreground tabular-nums shrink-0">{fmt(s.value)}</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>

                {/* Property Detail Table */}
                <Card data-testid="property-report-table">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base font-semibold flex items-center gap-2">
                      <FileText className="h-4 w-4" />Property Breakdown
                    </CardTitle>
                  </CardHeader>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Property</TableHead>
                          <TableHead className="text-center">Bookings</TableHead>
                          <TableHead className="text-center">Occupancy</TableHead>
                          <TableHead className="text-right">Gross Revenue</TableHead>
                          <TableHead className="text-right">Expenses</TableHead>
                          <TableHead className="text-right">Net Profit</TableHead>
                          <TableHead className="text-center">Owner %</TableHead>
                          <TableHead className="text-right">Payout</TableHead>
                          <TableHead className="text-center">Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {ownerReport.properties.map((p) => (
                          <TableRow key={p.property_id} data-testid={`report-row-${p.property_id}`}>
                            <TableCell className="font-medium">{p.property_name}</TableCell>
                            <TableCell className="text-center">{p.total_bookings}</TableCell>
                            <TableCell className="text-center">
                              <Badge variant="outline" className={p.occupancy_rate >= 70 ? "text-emerald-600" : p.occupancy_rate >= 40 ? "text-amber-600" : "text-red-500"}>
                                {p.occupancy_rate}%
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right font-data">{fmt(p.gross_revenue)}</TableCell>
                            <TableCell className="text-right font-data text-red-500">{fmt(p.total_expenses)}</TableCell>
                            <TableCell className="text-right font-data font-medium">
                              <span className={p.net_profit >= 0 ? "text-emerald-600" : "text-red-500"}>{fmt(p.net_profit)}</span>
                            </TableCell>
                            <TableCell className="text-center">{p.owner_share_pct}%</TableCell>
                            <TableCell className="text-right font-data font-bold">{fmt(p.owner_payout_amount)}</TableCell>
                            <TableCell className="text-center">
                              <Badge variant="outline" className={payoutStatusColors[p.payout_status] || ""}>
                                {p.payout_status}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                        <TableRow className="bg-muted/50 font-semibold">
                          <TableCell>Total</TableCell>
                          <TableCell className="text-center">{ownerReport.properties.reduce((s, p) => s + p.total_bookings, 0)}</TableCell>
                          <TableCell className="text-center">{ownerReport.summary.avg_occupancy}%</TableCell>
                          <TableCell className="text-right font-data">{fmt(ownerReport.summary.total_revenue)}</TableCell>
                          <TableCell className="text-right font-data text-red-500">{fmt(ownerReport.summary.total_expenses)}</TableCell>
                          <TableCell className="text-right font-data">
                            <span className={ownerReport.summary.net_profit >= 0 ? "text-emerald-600" : "text-red-500"}>
                              {fmt(ownerReport.summary.net_profit)}
                            </span>
                          </TableCell>
                          <TableCell />
                          <TableCell className="text-right font-data font-bold">
                            {fmt(ownerReport.properties.reduce((s, p) => s + p.owner_payout_amount, 0))}
                          </TableCell>
                          <TableCell />
                        </TableRow>
                      </TableBody>
                    </Table>
                  </div>
                </Card>
              </>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
