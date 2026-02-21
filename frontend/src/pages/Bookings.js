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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Plus, Pencil, CalendarDays } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v);
const empty = { property_id: "", guest_name: "", check_in: "", check_out: "", total_amount: "", status: "confirmed" };

export default function Bookings() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [bookings, setBookings] = useState([]);
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const [bookRes, propRes] = await Promise.all([
        fetch(`${API}/api/bookings`, { credentials: "include" }),
        fetch(`${API}/api/properties`, { credentials: "include" }),
      ]);
      if (bookRes.ok) setBookings(await bookRes.json());
      if (propRes.ok) setProperties(await propRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchData(); }, [user]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const method = editing ? "PUT" : "POST";
      const url = editing ? `${API}/api/bookings/${editing}` : `${API}/api/bookings`;
      const body = { ...form, total_amount: parseFloat(form.total_amount) || 0 };
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify(body) });
      if (res.ok) {
        toast.success(editing ? "Booking updated" : "Booking created");
        setDialogOpen(false); setForm(empty); setEditing(null); fetchData();
      } else { const err = await res.json(); toast.error(err.detail || "Failed"); }
    } catch (err) { toast.error("Error"); } finally { setSaving(false); }
  };

  const openEdit = (b) => {
    setForm({ property_id: b.property_id, guest_name: b.guest_name, check_in: b.check_in, check_out: b.check_out, total_amount: b.total_amount, status: b.status });
    setEditing(b.id); setDialogOpen(true);
  };

  const getPropName = (id) => properties.find(p => p.id === id)?.name || "—";
  const statusColors = { confirmed: "default", checked_in: "secondary", checked_out: "outline", cancelled: "destructive" };

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  const isAdmin = user?.role === "company_admin";

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="bookings-page">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold">Bookings</h1>
            <p className="text-sm text-muted-foreground mt-1">{bookings.length} total bookings</p>
          </div>
          {isAdmin && <Button onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }} data-testid="add-booking-btn"><Plus className="mr-2 h-4 w-4" />Add Booking</Button>}
        </div>

        {loading ? (
          <Card><CardContent className="p-6 h-32 animate-pulse bg-muted" /></Card>
        ) : bookings.length === 0 ? (
          <Card className="border-dashed"><CardContent className="p-12 text-center">
            <CalendarDays className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No bookings yet</p>
          </CardContent></Card>
        ) : (
          <Card>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Guest</TableHead>
                    <TableHead>Property</TableHead>
                    <TableHead>Check-in</TableHead>
                    <TableHead>Check-out</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    {isAdmin && <TableHead className="text-right">Actions</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bookings.map((b) => (
                    <TableRow key={b.id} data-testid={`booking-row-${b.id}`}>
                      <TableCell className="font-medium">{b.guest_name}</TableCell>
                      <TableCell>{getPropName(b.property_id)}</TableCell>
                      <TableCell>{b.check_in}</TableCell>
                      <TableCell>{b.check_out}</TableCell>
                      <TableCell className="font-data">{fmt(b.total_amount)}</TableCell>
                      <TableCell><Badge variant={statusColors[b.status] || "outline"} className="capitalize">{b.status?.replace("_", " ")}</Badge></TableCell>
                      {isAdmin && (
                        <TableCell className="text-right">
                          <Button variant="ghost" size="icon" onClick={() => openEdit(b)} data-testid={`edit-booking-${b.id}`}><Pencil className="h-4 w-4" /></Button>
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
            <DialogHeader><DialogTitle className="font-heading">{editing ? "Edit Booking" : "Add Booking"}</DialogTitle></DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="space-y-2">
                <Label>Property</Label>
                <Select value={form.property_id} onValueChange={v => setForm(p => ({ ...p, property_id: v }))}>
                  <SelectTrigger data-testid="booking-property-select"><SelectValue placeholder="Select property..." /></SelectTrigger>
                  <SelectContent>{properties.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2"><Label>Guest Name</Label><Input data-testid="booking-guest-input" value={form.guest_name} onChange={e => setForm(p => ({ ...p, guest_name: e.target.value }))} placeholder="Guest name" /></div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Check-in</Label><Input data-testid="booking-checkin-input" type="date" value={form.check_in} onChange={e => setForm(p => ({ ...p, check_in: e.target.value }))} /></div>
                <div className="space-y-2"><Label>Check-out</Label><Input data-testid="booking-checkout-input" type="date" value={form.check_out} onChange={e => setForm(p => ({ ...p, check_out: e.target.value }))} /></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Amount</Label><Input data-testid="booking-amount-input" type="number" step="0.01" value={form.total_amount} onChange={e => setForm(p => ({ ...p, total_amount: e.target.value }))} /></div>
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select value={form.status} onValueChange={v => setForm(p => ({ ...p, status: v }))}>
                    <SelectTrigger data-testid="booking-status-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="confirmed">Confirmed</SelectItem>
                      <SelectItem value="checked_in">Checked In</SelectItem>
                      <SelectItem value="checked_out">Checked Out</SelectItem>
                      <SelectItem value="cancelled">Cancelled</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSave} disabled={!form.property_id || !form.guest_name || saving} data-testid="save-booking-btn">{saving ? "Saving..." : editing ? "Update" : "Create"}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
