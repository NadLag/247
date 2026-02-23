import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { FileText, Download, Building2, DollarSign, Percent, CalendarDays, TrendingUp, ArrowUpRight, BarChart3 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v || 0);
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const COLORS = ["#0D9488", "#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"];

const payoutStatusColors = {
  pending: "bg-amber-500/10 text-amber-600 border-amber-200",
  paid: "bg-emerald-500/10 text-emerald-600 border-emerald-200",
};

export default function Reports() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState(null);
  const [properties, setProperties] = useState([]);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedProperty, setSelectedProperty] = useState("all");

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const propRes = await fetch(`${API}/api/properties`, { credentials: "include" });
      if (propRes.ok) setProperties(await propRes.json());

      let url = `${API}/api/reports/owner?year=${selectedYear}&month=${selectedMonth}`;
      if (selectedProperty !== "all") url += `&property_id=${selectedProperty}`;
      const res = await fetch(url, { credentials: "include" });
      if (res.ok) setReport(await res.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchReport(); }, [user, selectedYear, selectedMonth, selectedProperty]); // eslint-disable-line

  const exportCSV = () => {
    if (!report?.properties?.length) return;
    const headers = ["Property", "Bookings", "Occupancy %", "Gross Revenue", "Expenses", "Net Profit", "Owner Share %", "Payout Amount", "Payout Status"];
    const rows = report.properties.map(p => [
      p.property_name, p.total_bookings, p.occupancy_rate, p.gross_revenue, p.total_expenses, p.net_profit, p.owner_share_pct, p.owner_payout_amount, p.payout_status,
    ]);
    const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `owner-report-${MONTHS[selectedMonth - 1]}-${selectedYear}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const revenueChartData = report?.properties?.map(p => ({
    name: p.property_name?.length > 15 ? p.property_name.slice(0, 15) + "..." : p.property_name,
    Revenue: p.gross_revenue,
    Expenses: p.total_expenses,
    Profit: p.net_profit,
  })) || [];

  const sourceChartData = report?.properties?.reduce((acc, p) => {
    Object.entries(p.revenue_by_source || {}).forEach(([src, amt]) => {
      const existing = acc.find(a => a.name === src);
      if (existing) existing.value += amt;
      else acc.push({ name: src, value: amt });
    });
    return acc;
  }, []) || [];

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="reports-page">
        {/* Header */}
        <div className="flex items-center justify-between animate-fade-in">
          <div>
            <h1 className="font-heading text-2xl font-bold text-foreground">Owner Reports</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Financial report for {MONTHS[selectedMonth - 1]} {selectedYear}
            </p>
          </div>
          <Button variant="outline" onClick={exportCSV} disabled={!report?.properties?.length} data-testid="export-csv-btn">
            <Download className="mr-2 h-4 w-4" />Export CSV
          </Button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3" data-testid="report-filters">
          <Select value={selectedProperty} onValueChange={setSelectedProperty}>
            <SelectTrigger className="w-[200px] h-9" data-testid="report-property-filter">
              <Building2 className="h-4 w-4 mr-2" />
              <SelectValue placeholder="All Properties" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Properties</SelectItem>
              {properties.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={String(selectedMonth)} onValueChange={v => setSelectedMonth(parseInt(v))}>
            <SelectTrigger className="w-[160px] h-9" data-testid="report-month-filter">
              <CalendarDays className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>{MONTHS.map((m, i) => <SelectItem key={i} value={String(i + 1)}>{m}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={String(selectedYear)} onValueChange={v => setSelectedYear(parseInt(v))}>
            <SelectTrigger className="w-[120px] h-9" data-testid="report-year-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>{[2024, 2025, 2026, 2027].map(y => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}</SelectContent>
          </Select>
        </div>

        {loading ? (
          <Card><CardContent className="p-6 h-48 animate-pulse bg-muted" /></Card>
        ) : !report || !report.properties?.length ? (
          <Card className="border-dashed"><CardContent className="p-12 text-center">
            <FileText className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No data available for this period</p>
          </CardContent></Card>
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="report-summary">
              <Card><CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Total Revenue</p>
                <p className="text-xl font-bold font-data text-primary">{fmt(report.summary.total_revenue)}</p>
              </CardContent></Card>
              <Card><CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Total Expenses</p>
                <p className="text-xl font-bold font-data text-red-500">{fmt(report.summary.total_expenses)}</p>
              </CardContent></Card>
              <Card><CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Net Profit</p>
                <p className={`text-xl font-bold font-data ${report.summary.net_profit >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {fmt(report.summary.net_profit)}
                </p>
              </CardContent></Card>
              <Card><CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Avg Occupancy</p>
                <p className="text-xl font-bold font-data">{report.summary.avg_occupancy}%</p>
              </CardContent></Card>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Revenue vs Expenses Chart */}
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

              {/* Revenue by Source */}
              {sourceChartData.length > 0 && (
                <Card data-testid="source-chart">
                  <CardHeader className="pb-2"><CardTitle className="text-base font-semibold flex items-center gap-2"><TrendingUp className="h-4 w-4" />Revenue by Channel</CardTitle></CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-6">
                      <div className="w-[180px] h-[180px] shrink-0">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie data={sourceChartData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" stroke="hsl(var(--background))" strokeWidth={2}>
                              {sourceChartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                            </Pie>
                            <Tooltip formatter={v => fmt(v)} contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="flex-1 space-y-2 min-w-0">
                        {sourceChartData.map((s, i) => {
                          const total = sourceChartData.reduce((a, b) => a + b.value, 0);
                          return (
                            <div key={i} className="flex items-center gap-2 text-sm" data-testid={`channel-item-${s.name.toLowerCase()}`}>
                              <div className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
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
                    {report.properties.map((p) => (
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
                          {p.payment_date && <span className="block text-xs text-muted-foreground mt-0.5">{p.payment_date}</span>}
                          {p.payment_method && <span className="block text-xs text-muted-foreground">{p.payment_method}</span>}
                        </TableCell>
                      </TableRow>
                    ))}
                    {/* Totals Row */}
                    <TableRow className="bg-muted/50 font-semibold">
                      <TableCell>Total</TableCell>
                      <TableCell className="text-center">{report.properties.reduce((s, p) => s + p.total_bookings, 0)}</TableCell>
                      <TableCell className="text-center">{report.summary.avg_occupancy}%</TableCell>
                      <TableCell className="text-right font-data">{fmt(report.summary.total_revenue)}</TableCell>
                      <TableCell className="text-right font-data text-red-500">{fmt(report.summary.total_expenses)}</TableCell>
                      <TableCell className="text-right font-data">
                        <span className={report.summary.net_profit >= 0 ? "text-emerald-600" : "text-red-500"}>
                          {fmt(report.summary.net_profit)}
                        </span>
                      </TableCell>
                      <TableCell />
                      <TableCell className="text-right font-data font-bold">
                        {fmt(report.properties.reduce((s, p) => s + p.owner_payout_amount, 0))}
                      </TableCell>
                      <TableCell />
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </Card>

            {/* Revenue Breakdown per property */}
            {report.properties.some(p => Object.keys(p.revenue_by_source || {}).length > 1) && (
              <Card data-testid="channel-breakdown-table">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <ArrowUpRight className="h-4 w-4" />Revenue by Channel per Property
                  </CardTitle>
                </CardHeader>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Property</TableHead>
                        {[...new Set(report.properties.flatMap(p => Object.keys(p.revenue_by_source || {})))].map(src => (
                          <TableHead key={src} className="text-right">{src}</TableHead>
                        ))}
                        <TableHead className="text-right">Total</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {report.properties.map(p => {
                        const allSources = [...new Set(report.properties.flatMap(pr => Object.keys(pr.revenue_by_source || {})))];
                        return (
                          <TableRow key={p.property_id}>
                            <TableCell className="font-medium">{p.property_name}</TableCell>
                            {allSources.map(src => (
                              <TableCell key={src} className="text-right font-data text-sm">
                                {p.revenue_by_source?.[src] ? fmt(p.revenue_by_source[src]) : "-"}
                              </TableCell>
                            ))}
                            <TableCell className="text-right font-data font-medium">{fmt(p.gross_revenue)}</TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              </Card>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}
