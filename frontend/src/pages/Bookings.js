import { useState, useEffect, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";
import { Plus, Pencil, CalendarDays, List, ChevronLeft, ChevronRight, Filter, AlertTriangle, Clock, CalendarCheck, History, Ban, Globe, X, Eye } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v);
const empty = { property_id: "", guest_name: "", check_in: "", check_out: "", total_amount: "", guests_count: 1, status: "confirmed", notes: "" };

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
  blocked: "bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-300 dark:border-slate-600",
};

// Calendar Component with Day Detail Modal
function BookingCalendar({ bookings, blockedDates, properties, currentMonth, onMonthChange, onBookingClick, propertyFilter }) {
  const [selectedDay, setSelectedDay] = useState(null);
  const [dayModalOpen, setDayModalOpen] = useState(false);
  
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
  
  const getBlockedForDay = (day) => {
    if (!day) return [];
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return blockedDates.filter(b => {
      if (propertyFilter && b.property_id !== propertyFilter) return false;
      return b.check_in <= dateStr && b.check_out > dateStr;
    });
  };

  const getPropName = (id) => {
    const p = properties.find(pr => pr.id === id);
    return p ? p.name : "Property";
  };
  
  const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  
  const handleDayClick = (day) => {
    if (!day) return;
    const dayBookings = getBookingsForDay(day);
    const dayBlocked = getBlockedForDay(day);
    if (dayBookings.length > 0 || dayBlocked.length > 0) {
      setSelectedDay({ day, bookings: dayBookings, blocked: dayBlocked });
      setDayModalOpen(true);
    }
  };
  
  const selectedDateStr = selectedDay ? `${monthNames[month]} ${selectedDay.day}, ${year}` : '';
  
  return (
    <div className="space-y-4">
      {/* Calendar Header */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => onMonthChange(-1)}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <h2 className="font-semibold font-heading">{monthNames[month]} {year}</h2>
        <Button variant="ghost" size="sm" onClick={() => onMonthChange(1)}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
      
      {/* Days of Week */}
      <div className="grid grid-cols-7 gap-1">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(d => (
          <div key={d} className="text-center text-xs font-medium text-muted-foreground py-2">{d}</div>
        ))}
      </div>
      
      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-1">
        {days.map((day, idx) => {
          const dayBookings = getBookingsForDay(day);
          const dayBlocked = getBlockedForDay(day);
          const hasContent = dayBookings.length > 0 || dayBlocked.length > 0;
          const isToday = day && new Date().getDate() === day && new Date().getMonth() === month && new Date().getFullYear() === year;
          
          return (
            <div
              key={idx}
              onClick={() => handleDayClick(day)}
              className={`min-h-[80px] border rounded-lg p-1 ${day ? 'bg-card cursor-pointer hover:border-primary/50' : 'bg-muted/20'} ${isToday ? 'ring-2 ring-primary/50' : ''}`}
            >
              {day && (
                <>
                  <div className={`text-xs font-medium mb-1 ${isToday ? 'text-primary' : 'text-muted-foreground'}`}>{day}</div>
                  <div className="space-y-0.5">
                    {dayBookings.slice(0, 2).map(b => (
                      <div 
                        key={b.id} 
                        className="text-[10px] px-1 py-0.5 rounded bg-primary/10 text-primary truncate"
                        onClick={(e) => { e.stopPropagation(); onBookingClick(b); }}
                      >
                        {getPropName(b.property_id)}
                      </div>
                    ))}
                    {dayBlocked.slice(0, dayBookings.length > 1 ? 0 : 1).map(b => (
                      <div key={b.id} className="text-[10px] px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-500 truncate">
                        Blocked
                      </div>
                    ))}
                    {hasContent && (dayBookings.length + dayBlocked.length) > 2 && (
                      <div className="text-[10px] text-muted-foreground">+{(dayBookings.length + dayBlocked.length) - 2} more</div>
                    )}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
      
      {/* Day Detail Modal */}
      <Dialog open={dayModalOpen} onOpenChange={setDayModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">{selectedDateStr}</DialogTitle>
            <DialogDescription>{selectedDay?.bookings.length || 0} bookings, {selectedDay?.blocked.length || 0} blocked</DialogDescription>
          </DialogHeader>
          <ScrollArea className="max-h-[400px]">
            <div className="space-y-3 py-2">
              {selectedDay?.bookings.map(b => (
                <Card key={b.id} className="cursor-pointer hover:border-primary/50" onClick={() => { setDayModalOpen(false); onBookingClick(b); }}>
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-sm">{getPropName(b.property_id)}</p>
                        <p className="text-xs text-muted-foreground">{b.check_in} → {b.check_out}</p>
                      </div>
                      <Badge className={`${statusColors[b.status]} text-xs`}>{b.status}</Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {selectedDay?.blocked.map(b => (
                <Card key={b.id} className="bg-slate-50 dark:bg-slate-800/30">
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-sm text-muted-foreground">{getPropName(b.property_id)}</p>
                        <p className="text-xs text-muted-foreground">{b.check_in} → {b.check_out}</p>
                      </div>
                      <Badge variant="secondary">Blocked</Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Sectioned List View
function SectionedBookingList({ bookings, blockedDates, properties, onEdit, onView, isAdmin }) {
  const getPropName = (id) => {
    if (!id) return "No Property";
    if (!properties || properties.length === 0) return "Loading...";
    const prop = properties.find(p => p.id === id);
    return prop?.name || `Unknown (${id})`;
  };
  
  const today = new Date().toISOString().slice(0, 10);
  
  const getSourceLabel = (b) => {
    const src = b.ota_source;
    if (!src || src === "manual") return "Direct";
    return src.charAt(0).toUpperCase() + src.slice(1);
  };

  // Categorize bookings
  const checkingToday = bookings.filter(b => b.check_in === today || b.check_out === today);
  const upcoming = bookings.filter(b => b.check_in > today && b.status !== 'cancelled');
  const past = bookings.filter(b => b.check_out < today || b.status === 'checked_out');
  const activeNow = bookings.filter(b => b.check_in <= today && b.check_out > today && b.check_in !== today);
  
  // Sort each section
  const sortByCheckIn = (a, b) => new Date(a.check_in) - new Date(b.check_in);
  const sortByCheckInDesc = (a, b) => new Date(b.check_in) - new Date(a.check_in);
  
  const BookingRow = ({ b }) => {
    const isIcalImport = b.ota_source && b.ota_source !== 'manual';
    const sourceLabel = getSourceLabel(b);
    const sourceStyle = isIcalImport
      ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border-blue-200 dark:border-blue-700"
      : "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 border-emerald-200 dark:border-emerald-700";
    
    // Amount display - no "Not in iCal" text, just show amount or dash
    const amountDisplay = b.total_amount > 0 ? fmt(b.total_amount) : "-";
    
    return (
      <TableRow key={b.id} data-testid={`booking-row-${b.id}`} className="hover:bg-muted/30">
        <TableCell className="font-medium text-sm">{getPropName(b.property_id)}</TableCell>
        <TableCell className="text-sm">{b.check_in}</TableCell>
        <TableCell className="text-sm">{b.check_out}</TableCell>
        <TableCell>
          <Badge variant="outline" className={`text-[10px] capitalize ${sourceStyle}`} data-testid={`booking-source-${b.id}`}>
            {sourceLabel}
          </Badge>
        </TableCell>
        <TableCell className="text-sm font-data">{amountDisplay}</TableCell>
        <TableCell>
          <Badge className={`text-xs capitalize ${statusColors[b.status] || ''}`}>
            {b.status?.replace('_', ' ')}
          </Badge>
        </TableCell>
        <TableCell className="text-right">
          <div className="flex items-center justify-end gap-1">
            <Button variant="ghost" size="sm" onClick={() => onView(b)} data-testid={`view-booking-${b.id}`}>
              <Eye className="h-4 w-4" />
            </Button>
            {isAdmin && (
              <Button variant="ghost" size="sm" onClick={() => onEdit(b)} data-testid={`edit-booking-${b.id}`}>
                <Pencil className="h-4 w-4" />
              </Button>
            )}
          </div>
        </TableCell>
      </TableRow>
    );
  };
  
  const BlockedRow = ({ b }) => (
    <TableRow key={b.id} className="bg-slate-50 dark:bg-slate-800/30">
      <TableCell className="font-medium text-sm text-muted-foreground">{getPropName(b.property_id)}</TableCell>
      <TableCell className="text-sm text-muted-foreground">{b.check_in}</TableCell>
      <TableCell className="text-sm text-muted-foreground">{b.check_out}</TableCell>
      <TableCell>
        <Badge variant="outline" className="text-[10px] capitalize">{getSourceLabel(b)}</Badge>
      </TableCell>
      <TableCell className="text-sm text-muted-foreground">-</TableCell>
      <TableCell>
        <Badge variant="secondary" className="text-xs">Blocked</Badge>
      </TableCell>
      <TableCell />
    </TableRow>
  );
  
  const TableHeaders = () => (
    <TableHeader>
      <TableRow>
        <TableHead>Property</TableHead>
        <TableHead>Check-in</TableHead>
        <TableHead>Check-out</TableHead>
        <TableHead>Source</TableHead>
        <TableHead>Amount</TableHead>
        <TableHead>Status</TableHead>
        <TableHead className="text-right">Actions</TableHead>
      </TableRow>
    </TableHeader>
  );
  
  const totalCount = bookings.length + blockedDates.length;
  
  if (totalCount === 0) {
    return (
      <div className="py-16 text-center text-muted-foreground">
        <CalendarDays className="h-10 w-10 mx-auto mb-3 opacity-40" />
        <p>No bookings found</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* Checking Today Section */}
      {checkingToday.length > 0 && (
        <Card>
          <CardHeader className="py-3 px-4 bg-amber-50 dark:bg-amber-900/20 border-b">
            <CardTitle className="text-sm font-semibold flex items-center gap-2 text-amber-700 dark:text-amber-400">
              <Clock className="h-4 w-4" />
              Checking In/Out Today
              <Badge className="ml-2 bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300">{checkingToday.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeaders />
              <TableBody>
                {checkingToday.sort(sortByCheckIn).map(b => <BookingRow key={b.id} b={b} />)}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      
      {/* Active Now Section */}
      {activeNow.length > 0 && (
        <Card>
          <CardHeader className="py-3 px-4 bg-blue-50 dark:bg-blue-900/20 border-b">
            <CardTitle className="text-sm font-semibold flex items-center gap-2 text-blue-700 dark:text-blue-400">
              <CalendarCheck className="h-4 w-4" />
              Currently Staying
              <Badge className="ml-2 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">{activeNow.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeaders />
              <TableBody>
                {activeNow.sort(sortByCheckIn).map(b => <BookingRow key={b.id} b={b} />)}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      
      {/* Upcoming Section */}
      {upcoming.length > 0 && (
        <Card>
          <CardHeader className="py-3 px-4 bg-primary/5 border-b">
            <CardTitle className="text-sm font-semibold flex items-center gap-2 text-primary">
              <CalendarDays className="h-4 w-4" />
              Upcoming
              <Badge className="ml-2 bg-primary/10 text-primary">{upcoming.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeaders />
              <TableBody>
                {upcoming.sort(sortByCheckIn).map(b => <BookingRow key={b.id} b={b} />)}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      
      {/* Unavailable/Blocked Section */}
      {blockedDates.length > 0 && (
        <Card>
          <CardHeader className="py-3 px-4 bg-slate-100 dark:bg-slate-800/50 border-b">
            <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-600 dark:text-slate-400">
              <Ban className="h-4 w-4" />
              Unavailable / Blocked
              <Badge variant="secondary" className="ml-2">{blockedDates.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeaders />
              <TableBody>
                {blockedDates.sort(sortByCheckIn).map(b => <BlockedRow key={b.id} b={b} />)}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      
      {/* Past Bookings Section */}
      {past.length > 0 && (
        <Card>
          <CardHeader className="py-3 px-4 bg-muted/30 border-b">
            <CardTitle className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
              <History className="h-4 w-4" />
              Past Bookings
              <Badge variant="outline" className="ml-2">{past.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeaders />
              <TableBody>
                {past.sort(sortByCheckInDesc).map(b => <BookingRow key={b.id} b={b} />)}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function Bookings() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [bookings, setBookings] = useState([]);
  const [blockedDates, setBlockedDates] = useState([]);
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  
  // Detail view state
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState(null);
  
  // Override conflict state
  const [overrideDialogOpen, setOverrideDialogOpen] = useState(false);
  const [conflictDetails, setConflictDetails] = useState(null);
  
  // View state
  const [viewMode, setViewMode] = useState("calendar");
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [propertyFilter, setPropertyFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [sources, setSources] = useState([]);

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    setLoading(true);
    try {
      let url = `${API}/api/bookings`;
      const params = new URLSearchParams();
      if (sourceFilter && sourceFilter !== "all") params.append("source", sourceFilter);
      if (params.toString()) url += `?${params}`;
      
      const [bookingsRes, blockedRes, propsRes] = await Promise.all([
        fetch(url, { credentials: "include" }),
        fetch(`${API}/api/bookings/blocked-dates`, { credentials: "include" }),
        fetch(`${API}/api/properties`, { credentials: "include" }),
      ]);
      
      if (bookingsRes.ok) {
        const data = await bookingsRes.json();
        setBookings(data);
        // Extract unique sources
        const srcSet = new Set(data.map(b => b.ota_source || "manual"));
        setSources(Array.from(srcSet));
      }
      if (blockedRes.ok) setBlockedDates(await blockedRes.json());
      if (propsRes.ok) setProperties(await propsRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchData(); }, [user, sourceFilter]); // eslint-disable-line

  const handleSave = async (forceOverride = false) => {
    if (!form.property_id) { toast.error("Property is required"); return; }
    if (!form.check_in || !form.check_out) { toast.error("Check-in and check-out dates are required"); return; }
    
    // Validate check-in not in past for new bookings
    const today = new Date().toISOString().slice(0, 10);
    if (!editing && form.check_in < today) {
      toast.error("Check-in date cannot be in the past");
      return;
    }
    
    setSaving(true);
    try {
      const method = editing ? "PUT" : "POST";
      const url = editing ? `${API}/api/bookings/${editing}` : `${API}/api/bookings`;
      const body = {
        ...form,
        total_amount: parseFloat(form.total_amount) || 0,
        guests_count: parseInt(form.guests_count) || 1,
        force_override: forceOverride,
      };
      
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify(body) });
      const data = await res.json();
      
      if (res.ok) {
        toast.success(editing ? "Booking updated" : "Booking created");
        setDialogOpen(false);
        setForm(empty);
        setEditing(null);
        fetchData();
      } else if (res.status === 409 && data.conflicts) {
        // Show override dialog
        setConflictDetails(data);
        setOverrideDialogOpen(true);
      } else {
        toast.error(data.detail || "Failed to save booking");
      }
    } catch (err) { toast.error("Error saving booking"); } finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this booking?")) return;
    try {
      const res = await fetch(`${API}/api/bookings/${id}`, { method: "DELETE", credentials: "include" });
      if (res.ok) { toast.success("Booking deleted"); setDetailOpen(false); fetchData(); }
    } catch (err) { toast.error("Error deleting booking"); }
  };

  const openEdit = (b) => {
    setForm({
      property_id: b.property_id,
      guest_name: b.guest_name || "",
      check_in: b.check_in,
      check_out: b.check_out,
      total_amount: b.total_amount || "",
      guests_count: b.guests_count || 1,
      status: b.status,
      notes: b.notes || "",
    });
    setEditing(b.id);
    setDialogOpen(true);
  };

  const openView = (b) => {
    setSelectedBooking(b);
    setDetailOpen(true);
  };

  const handleMonthChange = (delta) => {
    const newDate = new Date(currentMonth);
    newDate.setMonth(newDate.getMonth() + delta);
    setCurrentMonth(newDate);
  };

  const getPropName = (id) => properties.find(p => p.id === id)?.name || "Property";
  const getSourceLabel = (b) => {
    const src = b?.ota_source;
    if (!src || src === "manual") return "Direct";
    return src.charAt(0).toUpperCase() + src.slice(1);
  };

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  
  const isAdmin = user?.role === "company_admin";
  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  // Apply filters
  const filteredBookings = bookings.filter(b => {
    if (propertyFilter && propertyFilter !== "all" && b.property_id !== propertyFilter) return false;
    if (statusFilter && statusFilter !== "all" && b.status !== statusFilter) return false;
    return true;
  });
  
  const filteredBlocked = blockedDates.filter(b => {
    if (propertyFilter && propertyFilter !== "all" && b.property_id !== propertyFilter) return false;
    return true;
  });

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="bookings-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-in">
          <div>
            <h1 className="font-heading text-2xl font-bold text-foreground">Bookings</h1>
            <p className="text-sm text-muted-foreground mt-1">{bookings.length} total bookings</p>
          </div>
          <div className="flex items-center gap-2">
            {/* View Toggle */}
            <div className="flex items-center rounded-lg border bg-muted/30 p-0.5">
              <Button variant={viewMode === "calendar" ? "default" : "ghost"} size="sm" className="h-8" onClick={() => setViewMode("calendar")} data-testid="view-calendar-btn">
                <CalendarDays className="h-4 w-4" />
              </Button>
              <Button variant={viewMode === "list" ? "default" : "ghost"} size="sm" className="h-8" onClick={() => setViewMode("list")} data-testid="view-list-btn">
                <List className="h-4 w-4" />
              </Button>
            </div>
            {isAdmin && (
              <Button onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }} data-testid="add-booking-btn" className="shadow-sm">
                <Plus className="mr-2 h-4 w-4" />Add Booking
              </Button>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2 items-center">
          <Select value={propertyFilter || "all"} onValueChange={setPropertyFilter}>
            <SelectTrigger className="w-[180px] h-9" data-testid="filter-property">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="All Properties" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Properties</SelectItem>
              {properties.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
            </SelectContent>
          </Select>
          
          <Select value={sourceFilter || "all"} onValueChange={setSourceFilter}>
            <SelectTrigger className="w-[140px] h-9" data-testid="filter-source">
              <Globe className="h-4 w-4 mr-2" />
              <SelectValue placeholder="All Sources" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sources</SelectItem>
              <SelectItem value="direct">Direct</SelectItem>
              {sources.filter(s => s !== "manual").map(s => (
                <SelectItem key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Select value={statusFilter || "all"} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px] h-9" data-testid="filter-status">
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
        </div>

        {/* Main Content */}
        {loading ? (
          <Card><CardContent className="p-6 h-48 animate-pulse bg-muted" /></Card>
        ) : viewMode === "calendar" ? (
          <Card>
            <CardContent className="p-4">
              <BookingCalendar
                bookings={filteredBookings}
                blockedDates={filteredBlocked}
                properties={properties}
                currentMonth={currentMonth}
                onMonthChange={handleMonthChange}
                onBookingClick={openView}
                propertyFilter={propertyFilter !== "all" ? propertyFilter : ""}
              />
            </CardContent>
          </Card>
        ) : (
          <SectionedBookingList
            bookings={filteredBookings}
            blockedDates={filteredBlocked}
            properties={properties}
            onEdit={openEdit}
            onView={openView}
            isAdmin={isAdmin}
          />
        )}

        {/* Add/Edit Booking Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-heading">{editing ? "Edit Booking" : "Add Booking"}</DialogTitle>
              <DialogDescription>
                {editing ? "Update booking details" : "Create a new direct booking"}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="space-y-2">
                <Label>Property *</Label>
                <Select value={form.property_id} onValueChange={v => set("property_id", v)}>
                  <SelectTrigger data-testid="booking-property-select"><SelectValue placeholder="Select property..." /></SelectTrigger>
                  <SelectContent>
                    {properties.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Guest Name *</Label>
                <Input data-testid="booking-guest-input" value={form.guest_name} onChange={e => set("guest_name", e.target.value)} placeholder="Guest's full name" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Check-in *</Label>
                  <Input data-testid="booking-checkin-input" type="date" value={form.check_in} onChange={e => set("check_in", e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Check-out *</Label>
                  <Input data-testid="booking-checkout-input" type="date" value={form.check_out} onChange={e => set("check_out", e.target.value)} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Amount *</Label>
                  <Input data-testid="booking-amount-input" type="number" step="0.01" value={form.total_amount} onChange={e => set("total_amount", e.target.value)} placeholder="0.00" />
                </div>
                <div className="space-y-2">
                  <Label>Guests</Label>
                  <Input data-testid="booking-guests-input" type="number" min="1" value={form.guests_count} onChange={e => set("guests_count", e.target.value)} />
                </div>
              </div>
              {editing && (
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
              )}
              <div className="space-y-2">
                <Label>Internal Notes</Label>
                <Textarea data-testid="booking-notes-input" value={form.notes} onChange={e => set("notes", e.target.value)} placeholder="Add any internal notes..." rows={2} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={() => handleSave(false)} disabled={saving} data-testid="save-booking-btn">
                {saving ? "Saving..." : editing ? "Update" : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Booking Detail View Dialog */}
        <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="font-heading">Booking Details</DialogTitle>
            </DialogHeader>
            {selectedBooking && (
              <div className="space-y-4 py-2">
                <div className="flex items-center justify-between">
                  <Badge className={`${statusColors[selectedBooking.status]} text-sm`}>
                    {selectedBooking.status?.replace('_', ' ')}
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    {getSourceLabel(selectedBooking)}
                  </Badge>
                </div>
                
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-muted-foreground">Property</p>
                    <p className="font-medium">{getPropName(selectedBooking.property_id)}</p>
                  </div>
                  
                  {/* Guest name only visible in detail view for direct bookings */}
                  {selectedBooking.guest_name && selectedBooking.guest_name.trim() && (
                    <div>
                      <p className="text-xs text-muted-foreground">Guest Name</p>
                      <p className="font-medium">{selectedBooking.guest_name}</p>
                    </div>
                  )}
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground">Check-in</p>
                      <p className="font-medium">{selectedBooking.check_in}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Check-out</p>
                      <p className="font-medium">{selectedBooking.check_out}</p>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground">Nights</p>
                      <p className="font-medium">{calcNights(selectedBooking.check_in, selectedBooking.check_out)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Amount</p>
                      <p className="font-medium font-data">{selectedBooking.total_amount > 0 ? fmt(selectedBooking.total_amount) : "-"}</p>
                    </div>
                  </div>
                  
                  {selectedBooking.notes && (
                    <div>
                      <p className="text-xs text-muted-foreground">Notes</p>
                      <p className="text-sm">{selectedBooking.notes}</p>
                    </div>
                  )}
                </div>
                
                {isAdmin && (
                  <div className="flex gap-2 pt-4 border-t">
                    <Button variant="outline" className="flex-1" onClick={() => { setDetailOpen(false); openEdit(selectedBooking); }}>
                      <Pencil className="h-4 w-4 mr-2" />Edit
                    </Button>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Override Conflict Dialog */}
        <Dialog open={overrideDialogOpen} onOpenChange={setOverrideDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="font-heading text-amber-600">Booking Conflict</DialogTitle>
              <DialogDescription>
                This booking overlaps with blocked dates. Do you want to override?
              </DialogDescription>
            </DialogHeader>
            {conflictDetails && (
              <div className="space-y-3 py-2">
                <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3">
                  <p className="text-sm text-amber-800 dark:text-amber-200">
                    {conflictDetails.conflicts?.length || 0} conflict(s) found
                  </p>
                  {conflictDetails.conflicts?.map((c, i) => (
                    <p key={i} className="text-xs text-amber-600 dark:text-amber-300 mt-1">
                      {c.check_in} - {c.check_out}
                    </p>
                  ))}
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setOverrideDialogOpen(false)}>Cancel</Button>
              <Button variant="destructive" onClick={() => { setOverrideDialogOpen(false); handleSave(true); }}>
                Override & Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
