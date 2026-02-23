import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Users, DollarSign, CheckCircle, Clock, XCircle, CreditCard } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v || 0);

const STAFF_ROLES = [
  { value: "housekeeper", label: "Housekeeper" },
  { value: "maintenance", label: "Maintenance" },
  { value: "driver", label: "Driver" },
  { value: "co_host", label: "Co-Host" },
];

const PAYMENT_TYPES = [
  { value: "salary", label: "Salary" },
  { value: "per_job", label: "Per Job" },
  { value: "commission", label: "Commission" },
];

const PAYMENT_METHODS = ["Bank Transfer", "Cash", "Check", "PayPal", "Zelle", "Wise", "Other"];

const empty = {
  first_name: "", last_name: "", phone: "", email: "",
  salary: "", payment_terms: "Monthly", payment_type: "salary",
  staff_role: "housekeeper", per_checkin_rate: "", per_checkout_rate: "",
  assigned_properties: [],
};

const emptyPayout = {
  staff_id: "", property_id: "", period_start: "", period_end: "",
  task_description: "", amount: "", payment_method: "", notes: "",
};

const statusColors = {
  pending: "bg-amber-500/10 text-amber-600 border-amber-200",
  paid: "bg-emerald-500/10 text-emerald-600 border-emerald-200",
  overdue: "bg-red-500/10 text-red-500 border-red-200",
};

export default function StaffPage() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState("staff");
  const [staff, setStaff] = useState([]);
  const [properties, setProperties] = useState([]);
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [payoutDialogOpen, setPayoutDialogOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [payoutForm, setPayoutForm] = useState(emptyPayout);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [payoutFilter, setPayoutFilter] = useState("all");

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const [staffRes, propRes, payRes] = await Promise.all([
        fetch(`${API}/api/staff`, { credentials: "include" }),
        fetch(`${API}/api/properties`, { credentials: "include" }),
        fetch(`${API}/api/payouts`, { credentials: "include" }),
      ]);
      if (staffRes.ok) setStaff(await staffRes.json());
      if (propRes.ok) setProperties(await propRes.json());
      if (payRes.ok) setPayouts(await payRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchData(); }, [user]); // eslint-disable-line

  // Staff CRUD
  const handleSave = async () => {
    setSaving(true);
    try {
      const method = editing ? "PUT" : "POST";
      const url = editing ? `${API}/api/staff/${editing}` : `${API}/api/staff`;
      const body = {
        ...form,
        salary: parseFloat(form.salary) || 0,
        per_checkin_rate: form.staff_role === "co_host" && form.per_checkin_rate ? parseFloat(form.per_checkin_rate) : null,
        per_checkout_rate: form.staff_role === "co_host" && form.per_checkout_rate ? parseFloat(form.per_checkout_rate) : null,
      };
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify(body) });
      if (res.ok) {
        toast.success(editing ? "Staff updated" : "Staff added");
        setDialogOpen(false); setForm(empty); setEditing(null); fetchData();
      } else { const err = await res.json(); toast.error(err.detail || "Failed"); }
    } catch (err) { toast.error("Error"); } finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this staff member?")) return;
    try {
      const res = await fetch(`${API}/api/staff/${id}`, { method: "DELETE", credentials: "include" });
      if (res.ok) { toast.success("Staff removed"); fetchData(); }
    } catch (err) { toast.error("Error"); }
  };

  const openEdit = (s) => {
    setForm({
      first_name: s.first_name, last_name: s.last_name, phone: s.phone, email: s.email,
      salary: s.salary, payment_terms: s.payment_terms || "Monthly",
      payment_type: s.payment_type || "salary", staff_role: s.staff_role || "housekeeper",
      per_checkin_rate: s.per_checkin_rate || "", per_checkout_rate: s.per_checkout_rate || "",
      assigned_properties: s.assigned_properties || [],
    });
    setEditing(s.id); setDialogOpen(true);
  };

  // Payout CRUD
  const handleSavePayout = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/payouts`, {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify({ ...payoutForm, amount: parseFloat(payoutForm.amount) || 0 }),
      });
      if (res.ok) {
        toast.success("Payout created");
        setPayoutDialogOpen(false); setPayoutForm(emptyPayout); fetchData();
      } else { const err = await res.json(); toast.error(err.detail || "Failed"); }
    } catch (err) { toast.error("Error"); } finally { setSaving(false); }
  };

  const handlePayoutStatusChange = async (id, status) => {
    try {
      const res = await fetch(`${API}/api/payouts/${id}`, {
        method: "PUT", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify({ status }),
      });
      if (res.ok) { toast.success(`Payout marked as ${status}`); fetchData(); }
    } catch (err) { toast.error("Error"); }
  };

  const handleDeletePayout = async (id) => {
    if (!window.confirm("Delete this payout?")) return;
    try {
      const res = await fetch(`${API}/api/payouts/${id}`, { method: "DELETE", credentials: "include" });
      if (res.ok) { toast.success("Payout deleted"); fetchData(); }
    } catch (err) { toast.error("Error"); }
  };

  const toggleProperty = (propId) => {
    setForm(prev => {
      const current = prev.assigned_properties || [];
      return { ...prev, assigned_properties: current.includes(propId) ? current.filter(id => id !== propId) : [...current, propId] };
    });
  };

  const getPropName = (id) => properties.find(p => p.id === id)?.name || id;
  const getRoleLabel = (v) => STAFF_ROLES.find(r => r.value === v)?.label || v;
  const getPaymentLabel = (v) => PAYMENT_TYPES.find(p => p.value === v)?.label || v;
  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));
  const setPay = (k, v) => setPayoutForm(p => ({ ...p, [k]: v }));

  const filteredPayouts = useMemo(() => {
    if (payoutFilter === "all") return payouts;
    return payouts.filter(p => p.status === payoutFilter);
  }, [payouts, payoutFilter]);

  const payoutSummary = useMemo(() => ({
    total: payouts.reduce((s, p) => s + (p.amount || 0), 0),
    pending: payouts.filter(p => p.status === "pending").reduce((s, p) => s + (p.amount || 0), 0),
    paid: payouts.filter(p => p.status === "paid").reduce((s, p) => s + (p.amount || 0), 0),
  }), [payouts]);

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  const isAdmin = user?.role === "company_admin";

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="staff-page">
        {/* Header */}
        <div className="flex items-center justify-between animate-fade-in">
          <div>
            <h1 className="font-heading text-2xl font-bold text-foreground">Staff</h1>
            <p className="text-sm text-muted-foreground mt-1">{staff.length} staff members</p>
          </div>
          {isAdmin && tab === "staff" && (
            <Button onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }} data-testid="add-staff-btn" className="shadow-sm">
              <Plus className="mr-2 h-4 w-4" />Add Staff
            </Button>
          )}
          {isAdmin && tab === "payouts" && (
            <Button onClick={() => { setPayoutForm(emptyPayout); setPayoutDialogOpen(true); }} data-testid="add-payout-btn" className="shadow-sm">
              <Plus className="mr-2 h-4 w-4" />Record Payout
            </Button>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b" data-testid="staff-tabs">
          <button
            onClick={() => setTab("staff")}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${tab === "staff" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}
            data-testid="tab-staff"
          >
            <Users className="h-4 w-4 inline mr-2" />Staff Members
          </button>
          <button
            onClick={() => setTab("payouts")}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${tab === "payouts" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}
            data-testid="tab-payouts"
          >
            <DollarSign className="h-4 w-4 inline mr-2" />Payouts
          </button>
        </div>

        {/* ========== STAFF TAB ========== */}
        {tab === "staff" && (
          <>
            {loading ? (
              <Card><CardContent className="p-6 h-48 animate-pulse bg-muted" /></Card>
            ) : staff.length === 0 ? (
              <Card className="border-dashed"><CardContent className="p-12 text-center">
                <Users className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                <p className="text-muted-foreground">No staff members yet</p>
              </CardContent></Card>
            ) : (
              <Card>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Contact</TableHead>
                        <TableHead>Payment Type</TableHead>
                        <TableHead>Salary/Rate</TableHead>
                        <TableHead>Properties</TableHead>
                        <TableHead>Status</TableHead>
                        {isAdmin && <TableHead className="text-right">Actions</TableHead>}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {staff.map((s) => (
                        <TableRow key={s.id} data-testid={`staff-row-${s.id}`}>
                          <TableCell className="font-medium">{s.first_name} {s.last_name}</TableCell>
                          <TableCell><Badge variant="outline">{getRoleLabel(s.staff_role)}</Badge></TableCell>
                          <TableCell>
                            <div className="text-sm">{s.email}</div>
                            <div className="text-xs text-muted-foreground">{s.phone}</div>
                          </TableCell>
                          <TableCell><Badge variant="secondary" className="text-xs">{getPaymentLabel(s.payment_type)}</Badge></TableCell>
                          <TableCell>
                            <div className="font-data text-sm">{fmt(s.salary)}</div>
                            {s.staff_role === "co_host" && (s.per_checkin_rate || s.per_checkout_rate) && (
                              <div className="text-xs text-muted-foreground mt-0.5">
                                {s.per_checkin_rate ? `CI: ${fmt(s.per_checkin_rate)}` : ""}
                                {s.per_checkin_rate && s.per_checkout_rate ? " / " : ""}
                                {s.per_checkout_rate ? `CO: ${fmt(s.per_checkout_rate)}` : ""}
                              </div>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {(s.assigned_properties || []).map(pid => (
                                <Badge key={pid} variant="outline" className="text-xs">{getPropName(pid)}</Badge>
                              ))}
                              {(!s.assigned_properties || s.assigned_properties.length === 0) && <span className="text-xs text-muted-foreground">None</span>}
                            </div>
                          </TableCell>
                          <TableCell><Badge variant={s.active ? "default" : "secondary"}>{s.active ? "Active" : "Inactive"}</Badge></TableCell>
                          {isAdmin && (
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-1">
                                <Button variant="ghost" size="icon" onClick={() => openEdit(s)} data-testid={`edit-staff-${s.id}`}><Pencil className="h-4 w-4" /></Button>
                                <Button variant="ghost" size="icon" onClick={() => handleDelete(s.id)} className="text-destructive" data-testid={`delete-staff-${s.id}`}><Trash2 className="h-4 w-4" /></Button>
                              </div>
                            </TableCell>
                          )}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </Card>
            )}
          </>
        )}

        {/* ========== PAYOUTS TAB ========== */}
        {tab === "payouts" && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Card><CardContent className="p-4 flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center"><DollarSign className="h-5 w-5 text-primary" /></div>
                <div><p className="text-xs text-muted-foreground">Total Payouts</p><p className="text-lg font-bold font-data">{fmt(payoutSummary.total)}</p></div>
              </CardContent></Card>
              <Card><CardContent className="p-4 flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-amber-500/10 flex items-center justify-center"><Clock className="h-5 w-5 text-amber-500" /></div>
                <div><p className="text-xs text-muted-foreground">Pending</p><p className="text-lg font-bold font-data">{fmt(payoutSummary.pending)}</p></div>
              </CardContent></Card>
              <Card><CardContent className="p-4 flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-emerald-500/10 flex items-center justify-center"><CheckCircle className="h-5 w-5 text-emerald-500" /></div>
                <div><p className="text-xs text-muted-foreground">Paid</p><p className="text-lg font-bold font-data">{fmt(payoutSummary.paid)}</p></div>
              </CardContent></Card>
            </div>

            {/* Filter */}
            <div className="flex gap-2" data-testid="payout-filter">
              {["all", "pending", "paid"].map(s => (
                <Button key={s} variant={payoutFilter === s ? "default" : "outline"} size="sm" className="capitalize h-8" onClick={() => setPayoutFilter(s)}>
                  {s}
                </Button>
              ))}
            </div>

            {/* Payouts Table */}
            {filteredPayouts.length === 0 ? (
              <Card className="border-dashed"><CardContent className="p-12 text-center">
                <CreditCard className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                <p className="text-muted-foreground">{payoutFilter !== "all" ? `No ${payoutFilter} payouts` : "No payouts recorded yet"}</p>
              </CardContent></Card>
            ) : (
              <Card>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Staff Name</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Property</TableHead>
                        <TableHead>Period</TableHead>
                        <TableHead>Task</TableHead>
                        <TableHead>Amount</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Method</TableHead>
                        {isAdmin && <TableHead className="text-right">Actions</TableHead>}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredPayouts.map((p) => (
                        <TableRow key={p.id} data-testid={`payout-row-${p.id}`}>
                          <TableCell className="font-medium">{p.staff_name}</TableCell>
                          <TableCell><Badge variant="outline" className="text-xs capitalize">{p.staff_role?.replace("_", " ")}</Badge></TableCell>
                          <TableCell className="text-sm">{p.property_name}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">{p.period_start?.slice(0, 10)} — {p.period_end?.slice(0, 10)}</TableCell>
                          <TableCell className="text-sm max-w-[150px] truncate">{p.task_description || "-"}</TableCell>
                          <TableCell className="font-data font-medium">{fmt(p.amount)}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className={statusColors[p.status] || ""}>{p.status}</Badge>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">{p.payment_method || "-"}</TableCell>
                          {isAdmin && (
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-1">
                                {p.status === "pending" && (
                                  <Button variant="ghost" size="icon" onClick={() => handlePayoutStatusChange(p.id, "paid")} title="Mark as Paid" data-testid={`mark-paid-${p.id}`}>
                                    <CheckCircle className="h-4 w-4 text-emerald-500" />
                                  </Button>
                                )}
                                <Button variant="ghost" size="icon" onClick={() => handleDeletePayout(p.id)} className="text-destructive" data-testid={`delete-payout-${p.id}`}>
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </TableCell>
                          )}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </Card>
            )}
          </>
        )}

        {/* Staff Add/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
            <DialogHeader><DialogTitle className="font-heading">{editing ? "Edit Staff" : "Add Staff"}</DialogTitle></DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>First Name *</Label><Input data-testid="staff-fn-input" value={form.first_name} onChange={e => set("first_name", e.target.value)} /></div>
                <div className="space-y-2"><Label>Last Name *</Label><Input data-testid="staff-ln-input" value={form.last_name} onChange={e => set("last_name", e.target.value)} /></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Phone</Label><Input data-testid="staff-phone-input" value={form.phone} onChange={e => set("phone", e.target.value)} /></div>
                <div className="space-y-2"><Label>Email</Label><Input data-testid="staff-email-input" value={form.email} onChange={e => set("email", e.target.value)} /></div>
              </div>
              <div className="space-y-2">
                <Label>Role *</Label>
                <Select value={form.staff_role} onValueChange={v => set("staff_role", v)}>
                  <SelectTrigger data-testid="staff-role-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{STAFF_ROLES.map(r => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Payment Type *</Label>
                  <Select value={form.payment_type} onValueChange={v => set("payment_type", v)}>
                    <SelectTrigger data-testid="staff-payment-type-select"><SelectValue /></SelectTrigger>
                    <SelectContent>{PAYMENT_TYPES.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-2"><Label>Salary / Rate</Label><Input data-testid="staff-salary-input" type="number" value={form.salary} onChange={e => set("salary", e.target.value)} placeholder="0.00" /></div>
              </div>
              <div className="space-y-2"><Label>Payment Terms</Label><Input data-testid="staff-terms-input" value={form.payment_terms} onChange={e => set("payment_terms", e.target.value)} /></div>
              {form.staff_role === "co_host" && (
                <div className="border rounded-lg p-4 space-y-4 bg-muted/30">
                  <p className="text-sm font-medium">Co-Host Payment Rates</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2"><Label>Per Check-in Rate</Label><Input data-testid="staff-checkin-rate-input" type="number" step="0.01" value={form.per_checkin_rate} onChange={e => set("per_checkin_rate", e.target.value)} placeholder="0.00" /></div>
                    <div className="space-y-2"><Label>Per Check-out Rate</Label><Input data-testid="staff-checkout-rate-input" type="number" step="0.01" value={form.per_checkout_rate} onChange={e => set("per_checkout_rate", e.target.value)} placeholder="0.00" /></div>
                  </div>
                </div>
              )}
              <div className="space-y-2">
                <Label>Assign Properties</Label>
                <div className="grid grid-cols-1 gap-2 max-h-32 overflow-y-auto border rounded-md p-2">
                  {properties.map(prop => (
                    <label key={prop.id} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-muted p-1 rounded">
                      <input type="checkbox" checked={(form.assigned_properties || []).includes(prop.id)} onChange={() => toggleProperty(prop.id)} className="rounded border-input" />
                      {prop.name}
                    </label>
                  ))}
                  {properties.length === 0 && <p className="text-xs text-muted-foreground">No properties available</p>}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSave} disabled={!form.first_name.trim() || saving} data-testid="save-staff-btn">{saving ? "Saving..." : editing ? "Update" : "Add"}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Payout Create Dialog */}
        <Dialog open={payoutDialogOpen} onOpenChange={setPayoutDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-heading flex items-center gap-2"><DollarSign className="h-5 w-5" />Record Payout</DialogTitle>
              <DialogDescription>Track a payment to a staff member</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="space-y-2">
                <Label>Staff Member *</Label>
                <Select value={payoutForm.staff_id} onValueChange={v => setPay("staff_id", v)}>
                  <SelectTrigger data-testid="payout-staff-select"><SelectValue placeholder="Select staff..." /></SelectTrigger>
                  <SelectContent>
                    {staff.map(s => <SelectItem key={s.id} value={s.id}>{s.first_name} {s.last_name} — {getRoleLabel(s.staff_role)}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Property</Label>
                <Select value={payoutForm.property_id} onValueChange={v => setPay("property_id", v)}>
                  <SelectTrigger data-testid="payout-property-select"><SelectValue placeholder="All Properties" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Properties</SelectItem>
                    {properties.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Period Start *</Label><Input type="date" data-testid="payout-start" value={payoutForm.period_start} onChange={e => setPay("period_start", e.target.value)} /></div>
                <div className="space-y-2"><Label>Period End *</Label><Input type="date" data-testid="payout-end" value={payoutForm.period_end} onChange={e => setPay("period_end", e.target.value)} /></div>
              </div>
              <div className="space-y-2"><Label>Task / Description</Label><Input data-testid="payout-task" value={payoutForm.task_description} onChange={e => setPay("task_description", e.target.value)} placeholder="e.g., Monthly salary, Check-in services" /></div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Amount *</Label><Input type="number" step="0.01" data-testid="payout-amount" value={payoutForm.amount} onChange={e => setPay("amount", e.target.value)} placeholder="0.00" /></div>
                <div className="space-y-2">
                  <Label>Payment Method</Label>
                  <Select value={payoutForm.payment_method} onValueChange={v => setPay("payment_method", v)}>
                    <SelectTrigger data-testid="payout-method"><SelectValue placeholder="Select..." /></SelectTrigger>
                    <SelectContent>{PAYMENT_METHODS.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2"><Label>Notes</Label><Textarea data-testid="payout-notes" value={payoutForm.notes} onChange={e => setPay("notes", e.target.value)} rows={2} /></div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setPayoutDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSavePayout} disabled={!payoutForm.staff_id || !payoutForm.amount || saving} data-testid="save-payout-btn">
                {saving ? "Saving..." : "Record Payout"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
