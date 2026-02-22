import { useState, useEffect, useMemo } from "react";
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
import { Plus, Pencil, CalendarDays, List, ChevronLeft, ChevronRight, Filter } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v);
const empty = { property_id: "", guest_name: "", check_in: "", check_out: "", total_amount: "", guests_count: 1, status: "confirmed" };

function calcNights(checkIn, checkOut) {
  if (!checkIn || !checkOut) return 0;
  const ci = new Date(checkIn);
  const co = new Date(checkOut);
  const diff = (co - ci) / (1000 * 60 * 60 * 24);
  return diff > 0 ? Math.round(diff) : 0;
}

const statusColors = {
  confirmed: "bg-primary/80 text-white",
  checked_in: "bg-blue-500 text-white",
  checked_out: "bg-slate-400 text-white",
  cancelled: "bg-red-400 text-white",
  pending: "bg-amber-400 text-white",
  blocked: "bg-slate-300 text-slate-600 border border-slate-400",
};

// Calendar Component
function BookingCalendar({ bookings, properties, currentMonth, onMonthChange, onBookingClick, propertyFilter }) {
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startPad = firstDay.getDay();
  const daysInMonth = lastDay.getDate();
  
  const days = [];
  for (let i = 0; i < startPad; i++) days.push(null);
  for (let i = 1; i <= daysInMonth; i++) days.push(i);
  
  const getBookingsForDay = (day) => {
    if (!day) return [];
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return bookings.filter(b => {
      if (propertyFilter && b.property_id !== propertyFilter) return false;
      return b.check_in <= dateStr && b.check_out > dateStr;
    });
  };

  const getPropName = (id) => {
    const p = properties.find(pr => pr.id === id);
    return p ? p.name.slice(0, 15) : "Unknown";
  };
  
  const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  
  return (
    <div className="space-y-4">
      {/* Calendar Header */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => onMonthChange(-1)}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <h2 className="font-semibold">{monthNames[month]} {year}</h2>
        <Button variant="ghost" size="sm" onClick={() => onMonthChange(1)}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
      
      {/* Calendar Grid */}
      <div className="border rounded-lg overflow-hidden">
        {/* Day Headers */}
        <div className="grid grid-cols-7 bg-muted/50">
          {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(d => (
            <div key={d} className="p-2 text-center text-xs font-medium text-muted-foreground border-b">
              {d}
            </div>
          ))}
        </div>
        
        {/* Days Grid */}
        <div className="grid grid-cols-7">
          {days.map((day, idx) => {
            const dayBookings = getBookingsForDay(day);
            const isToday = day && new Date().toDateString() === new Date(year, month, day).toDateString();
            
            return (
              <div 
                key={idx} 
                className={`min-h-[100px] border-b border-r p-1 ${!day ? 'bg-muted/20' : ''} ${isToday ? 'bg-primary/5' : ''}`}
              >
                {day && (
                  <>
                    <div className={`text-xs font-medium mb-1 ${isToday ? 'text-primary' : 'text-muted-foreground'}`}>
                      {day}
                    </div>
                    <div className="space-y-0.5">
                      {dayBookings.slice(0, 3).map((b, i) => (
                        <div 
                          key={i}
                          onClick={() => onBookingClick(b)}
                          className={`text-[10px] px-1 py-0.5 rounded cursor-pointer truncate ${statusColors[b.status] || 'bg-primary/80 text-white'}`}
                          title={`${b.guest_name} - ${getPropName(b.property_id)}`}
                        >
                          {b.guest_name.split(' ')[0]}
                        </div>
                      ))}
                      {dayBookings.length > 3 && (
                        <div className="text-[10px] text-muted-foreground text-center">
                          +{dayBookings.length - 3} more
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
      
      {/* Legend */}
      <div className="flex gap-4 text-xs">
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded bg-primary/80" /> Confirmed</div>
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded bg-blue-500" /> Checked In</div>
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded bg-slate-400" /> Checked Out</div>
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded bg-red-400" /> Cancelled</div>
      </div>
    </div>
  );
}

// List View Component
function BookingList({ bookings, properties, isAdmin, onEdit, propertyFilter, statusFilter, sortBy, onSort }) {
  const getPropName = (id) => properties.find(p => p.id === id)?.name || "Unknown";
  
  const filteredBookings = bookings.filter(b => {
    if (propertyFilter && b.property_id !== propertyFilter) return false;
    if (statusFilter && b.status !== statusFilter) return false;
    return true;
  });
  
  const sortedBookings = [...filteredBookings].sort((a, b) => {
    if (sortBy === "check_in") return new Date(a.check_in) - new Date(b.check_in);
    if (sortBy === "check_out") return new Date(a.check_out) - new Date(b.check_out);
    if (sortBy === "guest") return a.guest_name.localeCompare(b.guest_name);
    return 0;
  });
  
  if (sortedBookings.length === 0) {
    return (
      <div className="py-16 text-center text-muted-foreground">
        <CalendarDays className="h-10 w-10 mx-auto mb-3 opacity-40" />
        <p>No bookings found</p>
      </div>
    );
  }
  
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="cursor-pointer hover:text-primary" onClick={() => onSort("guest")}>Guest</TableHead>
            <TableHead>Property</TableHead>
            <TableHead className="cursor-pointer hover:text-primary" onClick={() => onSort("check_in")}>Check-in</TableHead>
            <TableHead className="cursor-pointer hover:text-primary" onClick={() => onSort("check_out")}>Check-out</TableHead>
            <TableHead>Nights</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Amount</TableHead>
            {isAdmin && <TableHead className="text-right">Actions</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedBookings.map(b => (
            <TableRow key={b.id} data-testid={`booking-row-${b.id}`}>
              <TableCell className="font-medium">{b.guest_name}</TableCell>
              <TableCell>{getPropName(b.property_id)}</TableCell>
              <TableCell>{b.check_in}</TableCell>
              <TableCell>{b.check_out}</TableCell>
              <TableCell>{calcNights(b.check_in, b.check_out)}</TableCell>
              <TableCell>
                {b.ota_source ? (
                  <Badge variant="outline" className="text-xs capitalize">{b.ota_source}</Badge>
                ) : (
                  <span className="text-muted-foreground text-xs">Manual</span>
                )}
              </TableCell>
              <TableCell>
                <Badge className={`text-xs capitalize ${statusColors[b.status] || ''}`}>
                  {b.status?.replace('_', ' ')}
                </Badge>
              </TableCell>
              <TableCell>{fmt(b.total_amount || 0)}</TableCell>
              {isAdmin && (
                <TableCell className="text-right">
                  <Button variant="ghost" size="sm" onClick={() => onEdit(b)} data-testid={`edit-booking-${b.id}`}>
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
  const [bookings, setBookings] = useState([]);
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  
  // View state
  const [viewMode, setViewMode] = useState("calendar");
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [propertyFilter, setPropertyFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortBy, setSortBy] = useState("check_in");
  const [selectedBooking, setSelectedBooking] = useState(null);

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

  useEffect(() => { if (user?.company_id) fetchData(); }, [user]); // eslint-disable-line

  const nights = useMemo(() => calcNights(form.check_in, form.check_out), [form.check_in, form.check_out]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const method = editing ? "PUT" : "POST";
      const url = editing ? `${API}/api/bookings/${editing}` : `${API}/api/bookings`;
      const body = {
        ...form,
        total_amount: parseFloat(form.total_amount) || 0,
        guests_count: parseInt(form.guests_count) || 1,
      };
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify(body) });
      if (res.ok) {
        toast.success(editing ? "Booking updated" : "Booking created");
        setDialogOpen(false); setForm(empty); setEditing(null); fetchData();
      } else { const err = await res.json(); toast.error(err.detail || "Failed"); }
    } catch (err) { toast.error("Error saving booking"); } finally { setSaving(false); }
  };

  const openEdit = (b) => {
    setForm({
      property_id: b.property_id,
      guest_name: b.guest_name,
      check_in: b.check_in,
      check_out: b.check_out,
      total_amount: b.total_amount?.toString() || "",
      guests_count: b.guests_count || 1,
      status: b.status || "confirmed",
    });
    setEditing(b.id);
    setDialogOpen(true);
    setSelectedBooking(null);
  };

  const handleMonthChange = (delta) => {
    setCurrentMonth(prev => new Date(prev.getFullYear(), prev.getMonth() + delta, 1));
  };

  const handleBookingClick = (b) => {
    setSelectedBooking(b);
  };

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  const isAdmin = user?.role === "company_admin";
  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  return (
    <Layout>
      <div className="space-y-6" data-testid="bookings-page">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-xl font-semibold">Bookings</h1>
            <p className="text-sm text-muted-foreground">{bookings.length} total bookings</p>
          </div>
          <div className="flex items-center gap-2">
            {/* View Toggle */}
            <div className="flex border rounded-lg p-0.5 bg-muted/50">
              <Button 
                variant={viewMode === "calendar" ? "default" : "ghost"} 
                size="sm" 
                className="h-8"
                onClick={() => setViewMode("calendar")}
                data-testid="calendar-view-btn"
              >
                <CalendarDays className="h-4 w-4 mr-1" /> Calendar
              </Button>
              <Button 
                variant={viewMode === "list" ? "default" : "ghost"} 
                size="sm"
                className="h-8"
                onClick={() => setViewMode("list")}
                data-testid="list-view-btn"
              >
                <List className="h-4 w-4 mr-1" /> List
              </Button>
            </div>
            {isAdmin && (
              <Button size="sm" onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }} data-testid="add-booking-btn">
                <Plus className="mr-2 h-4 w-4" /> Add Booking
              </Button>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <Select value={propertyFilter} onValueChange={setPropertyFilter}>
            <SelectTrigger className="w-[200px] h-9" data-testid="property-filter">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="All Properties" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Properties</SelectItem>
              {properties.map(p => (
                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {viewMode === "list" && (
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[160px] h-9" data-testid="status-filter">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="confirmed">Confirmed</SelectItem>
                <SelectItem value="checked_in">Checked In</SelectItem>
                <SelectItem value="checked_out">Checked Out</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          )}
        </div>

        {/* Content */}
        {loading ? (
          <Card>
            <CardContent className="p-8">
              <div className="h-64 animate-pulse bg-muted/50 rounded-lg" />
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="p-4">
              {viewMode === "calendar" ? (
                <BookingCalendar 
                  bookings={bookings}
                  properties={properties}
                  currentMonth={currentMonth}
                  onMonthChange={handleMonthChange}
                  onBookingClick={handleBookingClick}
                  propertyFilter={propertyFilter === "all" ? "" : propertyFilter}
                />
              ) : (
                <BookingList 
                  bookings={bookings}
                  properties={properties}
                  isAdmin={isAdmin}
                  onEdit={openEdit}
                  propertyFilter={propertyFilter === "all" ? "" : propertyFilter}
                  statusFilter={statusFilter === "all" ? "" : statusFilter}
                  sortBy={sortBy}
                  onSort={setSortBy}
                />
              )}
            </CardContent>
          </Card>
        )}

        {/* Booking Detail Popup (Calendar click) */}
        <Dialog open={!!selectedBooking} onOpenChange={() => setSelectedBooking(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Booking Details</DialogTitle>
            </DialogHeader>
            {selectedBooking && (
              <div className="space-y-4 py-2">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground text-xs mb-1">Guest</p>
                    <p className="font-medium">{selectedBooking.guest_name}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs mb-1">Property</p>
                    <p>{properties.find(p => p.id === selectedBooking.property_id)?.name || "Unknown"}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs mb-1">Check-in</p>
                    <p>{selectedBooking.check_in}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs mb-1">Check-out</p>
                    <p>{selectedBooking.check_out}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs mb-1">Nights</p>
                    <p>{calcNights(selectedBooking.check_in, selectedBooking.check_out)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs mb-1">Status</p>
                    <Badge className={`capitalize ${statusColors[selectedBooking.status] || ''}`}>
                      {selectedBooking.status?.replace('_', ' ')}
                    </Badge>
                  </div>
                  {selectedBooking.ota_source && (
                    <div>
                      <p className="text-muted-foreground text-xs mb-1">Source</p>
                      <Badge variant="outline" className="capitalize">{selectedBooking.ota_source}</Badge>
                    </div>
                  )}
                  <div>
                    <p className="text-muted-foreground text-xs mb-1">Amount</p>
                    <p className="font-medium">{fmt(selectedBooking.total_amount || 0)}</p>
                  </div>
                </div>
                {isAdmin && (
                  <div className="flex gap-2 pt-4 border-t">
                    <Button className="flex-1" onClick={() => openEdit(selectedBooking)}>
                      <Pencil className="mr-2 h-4 w-4" /> Edit Booking
                    </Button>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Add/Edit Booking Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>{editing ? "Edit Booking" : "New Booking"}</DialogTitle>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label>Property *</Label>
                <Select value={form.property_id} onValueChange={v => set("property_id", v)}>
                  <SelectTrigger data-testid="booking-property-select">
                    <SelectValue placeholder="Select property..." />
                  </SelectTrigger>
                  <SelectContent>
                    {properties.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Guest Name *</Label>
                <Input value={form.guest_name} onChange={e => set("guest_name", e.target.value)} placeholder="Guest name" data-testid="booking-guest-input" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Check-in *</Label>
                  <Input type="date" value={form.check_in} onChange={e => set("check_in", e.target.value)} data-testid="booking-checkin-input" />
                </div>
                <div className="space-y-2">
                  <Label>Check-out *</Label>
                  <Input type="date" value={form.check_out} onChange={e => set("check_out", e.target.value)} data-testid="booking-checkout-input" />
                </div>
              </div>
              {nights > 0 && (
                <div className="text-sm text-muted-foreground bg-muted/50 px-3 py-2 rounded-md">
                  Duration: <span className="font-medium text-foreground">{nights} night{nights !== 1 ? 's' : ''}</span>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Total Amount</Label>
                  <Input type="number" value={form.total_amount} onChange={e => set("total_amount", e.target.value)} placeholder="0.00" data-testid="booking-amount-input" />
                </div>
                <div className="space-y-2">
                  <Label>Guests</Label>
                  <Input type="number" min="1" value={form.guests_count} onChange={e => set("guests_count", e.target.value)} data-testid="booking-guests-input" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Status</Label>
                <Select value={form.status} onValueChange={v => set("status", v)}>
                  <SelectTrigger data-testid="booking-status-select">
                    <SelectValue />
                  </SelectTrigger>
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
              <Button onClick={handleSave} disabled={!form.property_id || !form.guest_name || !form.check_in || !form.check_out || saving} data-testid="save-booking-btn">
                {saving ? "Saving..." : editing ? "Update" : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
