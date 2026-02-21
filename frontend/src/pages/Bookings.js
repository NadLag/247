import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { Plus, Pencil, CalendarDays, Moon as MoonNight, Users as UsersIcon, UserCheck, RefreshCw, LogIn, Clock, CheckCircle, XCircle, LogOut } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v);
const empty = { property_id: "", guest_name: "", check_in: "", check_out: "", total_amount: "", guests_count: 1, assigned_cohost: "", status: "confirmed" };

function calcNights(checkIn, checkOut) {
  if (!checkIn || !checkOut) return 0;
  const ci = new Date(checkIn);
  const co = new Date(checkOut);
  const diff = (co - ci) / (1000 * 60 * 60 * 24);
  return diff > 0 ? Math.round(diff) : 0;
}

const statusConfig = {
  checked_in_today: { label: "Today's Check-ins", icon: LogIn, color: "text-blue-600 dark:text-blue-400", bg: "bg-blue-500/10" },
  upcoming: { label: "Upcoming", icon: Clock, color: "text-amber-600 dark:text-amber-400", bg: "bg-amber-500/10" },
  confirmed: { label: "Confirmed", icon: CheckCircle, color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/10" },
  checked_out: { label: "Checked Out", icon: LogOut, color: "text-slate-600 dark:text-slate-400", bg: "bg-slate-500/10" },
  cancelled: { label: "Cancelled", icon: XCircle, color: "text-red-600 dark:text-red-400", bg: "bg-red-500/10" },
};

function BookingTable({ bookings, properties, cohosts, isAdmin, onEdit, getPropName, getCohostName }) {
  if (bookings.length === 0) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        <CalendarDays className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>No bookings in this category</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Guest</TableHead>
            <TableHead>Property</TableHead>
            <TableHead>Check-in</TableHead>
            <TableHead>Check-out</TableHead>
            <TableHead>Nights</TableHead>
            <TableHead>Guests</TableHead>
            <TableHead>Co-Host</TableHead>
            <TableHead>Amount</TableHead>
            <TableHead>Status</TableHead>
            {isAdmin && <TableHead className="text-right">Actions</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {bookings.map((b) => (
            <TableRow key={b.id} data-testid={`booking-row-${b.id}`}>
              <TableCell className="font-medium">
                <div>
                  {b.guest_name}
                  {b.ota_source && (
                    <Badge variant="outline" className="ml-2 text-xs">{b.ota_source}</Badge>
                  )}
                </div>
              </TableCell>
              <TableCell>{getPropName(b.property_id)}</TableCell>
              <TableCell>{b.check_in}</TableCell>
              <TableCell>{b.check_out}</TableCell>
              <TableCell>
                <Badge variant="outline" className="font-data">
                  {calcNights(b.check_in, b.check_out)}
                </Badge>
              </TableCell>
              <TableCell>
                <span className="flex items-center gap-1 text-sm"><UsersIcon className="h-3.5 w-3.5" />{b.guests_count || 1}</span>
              </TableCell>
              <TableCell>
                {getCohostName(b.assigned_cohost) ? (
                  <span className="flex items-center gap-1 text-sm"><UserCheck className="h-3.5 w-3.5 text-primary" />{getCohostName(b.assigned_cohost)}</span>
                ) : <span className="text-xs text-muted-foreground">—</span>}
              </TableCell>
              <TableCell className="font-data">{fmt(b.total_amount)}</TableCell>
              <TableCell>
                <Badge 
                  variant={b.status === "confirmed" ? "default" : b.status === "checked_in" ? "secondary" : b.status === "cancelled" ? "destructive" : "outline"} 
                  className="capitalize"
                >
                  {b.status?.replace("_", " ")}
                </Badge>
              </TableCell>
              {isAdmin && (
                <TableCell className="text-right">
                  <Button variant="ghost" size="icon" onClick={() => onEdit(b)} data-testid={`edit-booking-${b.id}`}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export default function Bookings() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [bookingsByStatus, setBookingsByStatus] = useState(null);
  const [properties, setProperties] = useState([]);
  const [cohosts, setCohosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("checked_in_today");

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const [bookRes, propRes, cohostRes] = await Promise.all([
        fetch(`${API}/api/bookings/by-status`, { credentials: "include" }),
        fetch(`${API}/api/properties`, { credentials: "include" }),
        fetch(`${API}/api/staff/cohosts`, { credentials: "include" }),
      ]);
      if (bookRes.ok) setBookingsByStatus(await bookRes.json());
      if (propRes.ok) setProperties(await propRes.json());
      if (cohostRes.ok) setCohosts(await cohostRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchData(); }, [user]); // eslint-disable-line

  const nights = useMemo(() => calcNights(form.check_in, form.check_out), [form.check_in, form.check_out]);

  const selectedPropertyCohost = useMemo(() => {
    if (!form.property_id) return null;
    const prop = properties.find(p => p.id === form.property_id);
    return prop?.assigned_cohost || null;
  }, [form.property_id, properties]);

  const handlePropertyChange = (propId) => {
    const prop = properties.find(p => p.id === propId);
    setForm(prev => ({
      ...prev,
      property_id: propId,
      assigned_cohost: prop?.assigned_cohost || prev.assigned_cohost,
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const method = editing ? "PUT" : "POST";
      const url = editing ? `${API}/api/bookings/${editing}` : `${API}/api/bookings`;
      const body = {
        ...form,
        total_amount: parseFloat(form.total_amount) || 0,
        guests_count: parseInt(form.guests_count) || 1,
        assigned_cohost: form.assigned_cohost || null,
      };
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify(body) });
      if (res.ok) {
        toast.success(editing ? "Booking updated" : "Booking created");
        setDialogOpen(false); setForm(empty); setEditing(null); fetchData();
      } else { const err = await res.json(); toast.error(err.detail || "Failed"); }
    } catch (err) { toast.error("Error"); } finally { setSaving(false); }
  };

  const handleOTASync = async () => {
    setSyncing(true);
    try {
      // This would trigger a manual OTA sync - for now just refresh
      toast.info("Checking for OTA updates...");
      await fetchData();
      toast.success("Bookings refreshed");
    } catch (err) {
      toast.error("Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const openEdit = (b) => {
    setForm({
      property_id: b.property_id, guest_name: b.guest_name, check_in: b.check_in, check_out: b.check_out,
      total_amount: b.total_amount, guests_count: b.guests_count || 1,
      assigned_cohost: b.assigned_cohost || "", status: b.status,
    });
    setEditing(b.id); setDialogOpen(true);
  };

  const getPropName = (id) => properties.find(p => p.id === id)?.name || "—";
  const getCohostName = (id) => { const ch = cohosts.find(c => c.id === id); return ch ? `${ch.first_name} ${ch.last_name}` : null; };

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  const isAdmin = user?.role === "company_admin";
  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const totalBookings = bookingsByStatus 
    ? Object.values(bookingsByStatus).reduce((sum, arr) => sum + arr.length, 0)
    : 0;

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="bookings-page">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold">Bookings</h1>
            <p className="text-sm text-muted-foreground mt-1">{totalBookings} total bookings</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleOTASync} disabled={syncing} data-testid="ota-sync-btn">
              <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
              Sync OTA
            </Button>
            {isAdmin && (
              <Button onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }} data-testid="add-booking-btn">
                <Plus className="mr-2 h-4 w-4" />Add Booking
              </Button>
            )}
          </div>
        </div>

        {loading ? (
          <Card><CardContent className="p-6 h-32 animate-pulse bg-muted" /></Card>
        ) : !bookingsByStatus || totalBookings === 0 ? (
          <Card className="border-dashed"><CardContent className="p-12 text-center">
            <CalendarDays className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No bookings yet</p>
          </CardContent></Card>
        ) : (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
            <TabsList className="grid w-full grid-cols-5 lg:w-auto lg:inline-grid" data-testid="booking-tabs">
              {Object.entries(statusConfig).map(([key, config]) => {
                const count = bookingsByStatus[key]?.length || 0;
                const IconComponent = config.icon;
                return (
                  <TabsTrigger key={key} value={key} className="gap-2" data-testid={`tab-${key}`}>
                    <IconComponent className={`h-4 w-4 ${config.color}`} />
                    <span className="hidden sm:inline">{config.label}</span>
                    <Badge variant="secondary" className="ml-1 h-5 min-w-5 px-1.5">{count}</Badge>
                  </TabsTrigger>
                );
              })}
            </TabsList>

            {Object.entries(statusConfig).map(([key, config]) => (
              <TabsContent key={key} value={key}>
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-base font-semibold">
                      <div className={`h-8 w-8 rounded-lg ${config.bg} flex items-center justify-center`}>
                        <config.icon className={`h-4 w-4 ${config.color}`} />
                      </div>
                      {config.label}
                      <Badge variant="outline" className="ml-auto">{bookingsByStatus[key]?.length || 0}</Badge>
                    </CardTitle>
                  </CardHeader>
                  <BookingTable 
                    bookings={bookingsByStatus[key] || []}
                    properties={properties}
                    cohosts={cohosts}
                    isAdmin={isAdmin}
                    onEdit={openEdit}
                    getPropName={getPropName}
                    getCohostName={getCohostName}
                  />
                </Card>
              </TabsContent>
            ))}
          </Tabs>
        )}

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader><DialogTitle className="font-heading">{editing ? "Edit Booking" : "Add Booking"}</DialogTitle></DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="space-y-2">
                <Label>Property *</Label>
                <Select value={form.property_id} onValueChange={handlePropertyChange}>
                  <SelectTrigger data-testid="booking-property-select"><SelectValue placeholder="Select property..." /></SelectTrigger>
                  <SelectContent>{properties.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2"><Label>Guest Name *</Label><Input data-testid="booking-guest-input" value={form.guest_name} onChange={e => set("guest_name", e.target.value)} placeholder="Guest name" /></div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Check-in</Label><Input data-testid="booking-checkin-input" type="date" value={form.check_in} onChange={e => set("check_in", e.target.value)} /></div>
                <div className="space-y-2"><Label>Check-out</Label><Input data-testid="booking-checkout-input" type="date" value={form.check_out} onChange={e => set("check_out", e.target.value)} /></div>
              </div>
              {nights > 0 && (
                <div className="flex items-center gap-3 bg-muted/50 rounded-lg p-3 border" data-testid="nights-display">
                  <MoonNight className="h-5 w-5 text-primary" />
                  <div>
                    <p className="text-sm font-medium">{nights} Night{nights !== 1 ? "s" : ""}</p>
                    <p className="text-xs text-muted-foreground">{form.check_in} to {form.check_out}</p>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Guests</Label><Input data-testid="booking-guests-input" type="number" min="1" value={form.guests_count} onChange={e => set("guests_count", e.target.value)} /></div>
                <div className="space-y-2"><Label>Amount</Label><Input data-testid="booking-amount-input" type="number" step="0.01" value={form.total_amount} onChange={e => set("total_amount", e.target.value)} /></div>
              </div>
              <div className="space-y-2">
                <Label>Assigned Co-Host</Label>
                <Select value={form.assigned_cohost || "none"} onValueChange={v => set("assigned_cohost", v === "none" ? "" : v)}>
                  <SelectTrigger data-testid="booking-cohost-select"><SelectValue placeholder="Select co-host..." /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No Co-Host</SelectItem>
                    {cohosts.map(ch => <SelectItem key={ch.id} value={ch.id}>{ch.first_name} {ch.last_name}</SelectItem>)}
                  </SelectContent>
                </Select>
                {selectedPropertyCohost && getCohostName(selectedPropertyCohost) && form.assigned_cohost === selectedPropertyCohost && (
                  <p className="text-xs text-emerald-600 dark:text-emerald-400">Auto-assigned from property co-host</p>
                )}
              </div>
              <Separator />
              <div className="space-y-2">
                <Label>Status</Label>
                <Select value={form.status} onValueChange={v => set("status", v)}>
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
