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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Users } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v);
const empty = { first_name: "", last_name: "", phone: "", email: "", salary: "", payment_terms: "Monthly", assigned_properties: [] };

export default function StaffPage() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [staff, setStaff] = useState([]);
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const [staffRes, propRes] = await Promise.all([
        fetch(`${API}/api/staff`, { credentials: "include" }),
        fetch(`${API}/api/properties`, { credentials: "include" }),
      ]);
      if (staffRes.ok) setStaff(await staffRes.json());
      if (propRes.ok) setProperties(await propRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchData(); }, [user]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const method = editing ? "PUT" : "POST";
      const url = editing ? `${API}/api/staff/${editing}` : `${API}/api/staff`;
      const body = { ...form, salary: parseFloat(form.salary) || 0 };
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
    setForm({ first_name: s.first_name, last_name: s.last_name, phone: s.phone, email: s.email, salary: s.salary, payment_terms: s.payment_terms, assigned_properties: s.assigned_properties || [] });
    setEditing(s.id); setDialogOpen(true);
  };

  const toggleProperty = (propId) => {
    setForm(prev => {
      const current = prev.assigned_properties || [];
      return { ...prev, assigned_properties: current.includes(propId) ? current.filter(id => id !== propId) : [...current, propId] };
    });
  };

  const getPropName = (id) => properties.find(p => p.id === id)?.name || id;

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  const isAdmin = user?.role === "company_admin";

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="staff-page">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold">Staff</h1>
            <p className="text-sm text-muted-foreground mt-1">{staff.length} staff members</p>
          </div>
          {isAdmin && <Button onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }} data-testid="add-staff-btn"><Plus className="mr-2 h-4 w-4" />Add Staff</Button>}
        </div>

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
                    <TableHead>Contact</TableHead>
                    <TableHead>Salary</TableHead>
                    <TableHead>Payment</TableHead>
                    <TableHead>Properties</TableHead>
                    <TableHead>Status</TableHead>
                    {isAdmin && <TableHead className="text-right">Actions</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {staff.map((s) => (
                    <TableRow key={s.id} data-testid={`staff-row-${s.id}`}>
                      <TableCell className="font-medium">{s.first_name} {s.last_name}</TableCell>
                      <TableCell>
                        <div className="text-sm">{s.email}</div>
                        <div className="text-xs text-muted-foreground">{s.phone}</div>
                      </TableCell>
                      <TableCell className="font-data">{fmt(s.salary)}</TableCell>
                      <TableCell>{s.payment_terms}</TableCell>
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

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader><DialogTitle className="font-heading">{editing ? "Edit Staff" : "Add Staff"}</DialogTitle></DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>First Name</Label><Input data-testid="staff-fn-input" value={form.first_name} onChange={e => setForm(p => ({ ...p, first_name: e.target.value }))} /></div>
                <div className="space-y-2"><Label>Last Name</Label><Input data-testid="staff-ln-input" value={form.last_name} onChange={e => setForm(p => ({ ...p, last_name: e.target.value }))} /></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Phone</Label><Input data-testid="staff-phone-input" value={form.phone} onChange={e => setForm(p => ({ ...p, phone: e.target.value }))} /></div>
                <div className="space-y-2"><Label>Email</Label><Input data-testid="staff-email-input" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} /></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Salary</Label><Input data-testid="staff-salary-input" type="number" value={form.salary} onChange={e => setForm(p => ({ ...p, salary: e.target.value }))} /></div>
                <div className="space-y-2"><Label>Payment Terms</Label><Input data-testid="staff-terms-input" value={form.payment_terms} onChange={e => setForm(p => ({ ...p, payment_terms: e.target.value }))} /></div>
              </div>
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
      </div>
    </Layout>
  );
}
