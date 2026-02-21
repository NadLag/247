import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Receipt, Filter } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v);

const FIXED_CATEGORIES = ["Salaries", "Rent", "Insurance", "Software"];
const VARIABLE_CATEGORIES = ["Utilities", "Cleaning", "Maintenance", "OTA Fees"];

const empty = { property_id: "", type: "fixed", category: "", amount: "", description: "", date: new Date().toISOString().slice(0, 10), recurring: false, recurring_frequency: "" };

export default function Expenses() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [expenses, setExpenses] = useState([]);
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [filterProp, setFilterProp] = useState("all");
  const [activeTab, setActiveTab] = useState("all");

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const params = new URLSearchParams();
      if (filterProp && filterProp !== "all") params.append("property_id", filterProp);
      const [expRes, propRes] = await Promise.all([
        fetch(`${API}/api/expenses?${params}`, { credentials: "include" }),
        fetch(`${API}/api/properties`, { credentials: "include" }),
      ]);
      if (expRes.ok) setExpenses(await expRes.json());
      if (propRes.ok) setProperties(await propRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchData(); }, [user, filterProp]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const method = editing ? "PUT" : "POST";
      const url = editing ? `${API}/api/expenses/${editing}` : `${API}/api/expenses`;
      const body = { ...form, amount: parseFloat(form.amount) || 0 };
      if (!body.recurring) body.recurring_frequency = null;
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify(body) });
      if (res.ok) {
        toast.success(editing ? "Expense updated" : "Expense created");
        setDialogOpen(false); setForm(empty); setEditing(null); fetchData();
      } else { const err = await res.json(); toast.error(err.detail || "Failed"); }
    } catch (err) { toast.error("Error"); } finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this expense?")) return;
    try {
      const res = await fetch(`${API}/api/expenses/${id}`, { method: "DELETE", credentials: "include" });
      if (res.ok) { toast.success("Expense deleted"); fetchData(); }
    } catch (err) { toast.error("Error"); }
  };

  const openEdit = (exp) => {
    setForm({ property_id: exp.property_id, type: exp.type, category: exp.category, amount: exp.amount, description: exp.description, date: exp.date, recurring: exp.recurring, recurring_frequency: exp.recurring_frequency || "" });
    setEditing(exp.id); setDialogOpen(true);
  };

  const openAdd = (type) => {
    setForm({ ...empty, type });
    setEditing(null); setDialogOpen(true);
  };

  const getPropName = (id) => properties.find(p => p.id === id)?.name || "—";
  const categories = form.type === "fixed" ? FIXED_CATEGORIES : VARIABLE_CATEGORIES;
  const filteredExpenses = activeTab === "all" ? expenses : expenses.filter(e => e.type === activeTab);
  const totalFixed = expenses.filter(e => e.type === "fixed").reduce((s, e) => s + (e.amount || 0), 0);
  const totalVariable = expenses.filter(e => e.type === "variable").reduce((s, e) => s + (e.amount || 0), 0);

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  const isAdmin = user?.role === "company_admin";

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="expenses-page">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="font-heading text-2xl font-bold">Expenses</h1>
            <p className="text-sm text-muted-foreground mt-1">Fixed: {fmt(totalFixed)} | Variable: {fmt(totalVariable)}</p>
          </div>
          <div className="flex items-center gap-3">
            <Select value={filterProp} onValueChange={setFilterProp}>
              <SelectTrigger className="w-[180px]" data-testid="filter-property-select">
                <Filter className="h-4 w-4 mr-2" /><SelectValue placeholder="All Properties" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Properties</SelectItem>
                {properties.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
              </SelectContent>
            </Select>
            {isAdmin && <Button onClick={() => openAdd("fixed")} data-testid="add-expense-btn"><Plus className="mr-2 h-4 w-4" />Add Expense</Button>}
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList data-testid="expense-tabs">
            <TabsTrigger value="all" data-testid="tab-all">All</TabsTrigger>
            <TabsTrigger value="fixed" data-testid="tab-fixed">Fixed</TabsTrigger>
            <TabsTrigger value="variable" data-testid="tab-variable">Variable</TabsTrigger>
          </TabsList>

          <TabsContent value={activeTab} className="mt-4">
            {loading ? (
              <Card><CardContent className="p-6 h-32 animate-pulse bg-muted" /></Card>
            ) : filteredExpenses.length === 0 ? (
              <Card className="border-dashed"><CardContent className="p-12 text-center">
                <Receipt className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                <p className="text-muted-foreground">No expenses found</p>
              </CardContent></Card>
            ) : (
              <Card>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Category</TableHead>
                        <TableHead>Property</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead>Amount</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Recurring</TableHead>
                        {isAdmin && <TableHead className="text-right">Actions</TableHead>}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredExpenses.map((exp) => (
                        <TableRow key={exp.id} data-testid={`expense-row-${exp.id}`}>
                          <TableCell className="font-medium">{exp.category}</TableCell>
                          <TableCell>{getPropName(exp.property_id)}</TableCell>
                          <TableCell className="max-w-[200px] truncate">{exp.description}</TableCell>
                          <TableCell>{exp.date}</TableCell>
                          <TableCell className="font-data">{fmt(exp.amount)}</TableCell>
                          <TableCell><Badge variant={exp.type === "fixed" ? "default" : "secondary"}>{exp.type}</Badge></TableCell>
                          <TableCell>{exp.recurring ? <Badge variant="outline">{exp.recurring_frequency}</Badge> : "—"}</TableCell>
                          {isAdmin && (
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-1">
                                <Button variant="ghost" size="icon" onClick={() => openEdit(exp)}><Pencil className="h-4 w-4" /></Button>
                                <Button variant="ghost" size="icon" onClick={() => handleDelete(exp.id)} className="text-destructive"><Trash2 className="h-4 w-4" /></Button>
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
          </TabsContent>
        </Tabs>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader><DialogTitle className="font-heading">{editing ? "Edit Expense" : "Add Expense"}</DialogTitle></DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Type</Label>
                  <Select value={form.type} onValueChange={v => setForm(p => ({ ...p, type: v, category: "" }))}>
                    <SelectTrigger data-testid="expense-type-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fixed">Fixed</SelectItem>
                      <SelectItem value="variable">Variable</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Select value={form.category} onValueChange={v => setForm(p => ({ ...p, category: v }))}>
                    <SelectTrigger data-testid="expense-category-select"><SelectValue placeholder="Select..." /></SelectTrigger>
                    <SelectContent>{categories.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Property</Label>
                <Select value={form.property_id} onValueChange={v => setForm(p => ({ ...p, property_id: v }))}>
                  <SelectTrigger data-testid="expense-property-select"><SelectValue placeholder="Select property..." /></SelectTrigger>
                  <SelectContent>{properties.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Amount</Label><Input data-testid="expense-amount-input" type="number" step="0.01" value={form.amount} onChange={e => setForm(p => ({ ...p, amount: e.target.value }))} /></div>
                <div className="space-y-2"><Label>Date</Label><Input data-testid="expense-date-input" type="date" value={form.date} onChange={e => setForm(p => ({ ...p, date: e.target.value }))} /></div>
              </div>
              <div className="space-y-2"><Label>Description</Label><Input data-testid="expense-desc-input" value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} placeholder="Expense description" /></div>
              <div className="flex items-center gap-3">
                <Switch checked={form.recurring} onCheckedChange={v => setForm(p => ({ ...p, recurring: v }))} data-testid="expense-recurring-switch" />
                <Label>Recurring</Label>
                {form.recurring && (
                  <Select value={form.recurring_frequency} onValueChange={v => setForm(p => ({ ...p, recurring_frequency: v }))}>
                    <SelectTrigger className="w-32"><SelectValue placeholder="Frequency" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="monthly">Monthly</SelectItem>
                      <SelectItem value="quarterly">Quarterly</SelectItem>
                      <SelectItem value="yearly">Yearly</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSave} disabled={!form.category || !form.property_id || saving} data-testid="save-expense-btn">{saving ? "Saving..." : editing ? "Update" : "Create"}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
