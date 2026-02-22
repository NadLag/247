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
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Building2, MapPin, User, BedDouble, Bath, FileText, UserCheck, RefreshCw, Clock, Link2 } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const PROPERTY_TYPES = ["Apartment", "Villa", "Hotel", "Resort", "Cabin", "Townhouse", "Condo", "House", "Studio", "Penthouse"];
const COUNTRIES = ["United States", "United Kingdom", "Canada", "Australia", "France", "Germany", "Spain", "Italy", "Portugal", "Greece", "Turkey", "UAE", "Thailand", "Mexico", "Brazil", "Japan", "Indonesia", "South Africa", "Morocco", "Egypt", "Saudi Arabia", "Switzerland", "Netherlands", "Austria", "Sweden"];

const empty = {
  name: "", address: "", property_type: "", rooms: 1, suites: 0, bathrooms: 1,
  city: "", country: "", notes: "", assigned_cohost: "",
  owner_first_name: "", owner_last_name: "", owner_phone: "", owner_email: "",
  units: 1, active: true,
};

function PropertyCard({ prop, isAdmin, onEdit, onDelete, getCohostName }) {
  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow h-full flex flex-col" data-testid={`property-card-${prop.id}`}>
      <div className="h-2 bg-primary shrink-0" />
      <CardContent className="p-5 flex flex-col flex-1">
        {/* Header - Fixed height section */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="min-w-0 flex-1">
            <h3 className="font-heading font-semibold text-base truncate">{prop.name}</h3>
            {prop.property_type && (
              <Badge variant="outline" className="text-xs mt-1">{prop.property_type}</Badge>
            )}
          </div>
          <Badge variant={prop.active ? "default" : "secondary"} className="shrink-0">
            {prop.active ? "Active" : "Inactive"}
          </Badge>
        </div>

        {/* Location */}
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-3">
          <MapPin className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">
            {prop.city && prop.country ? `${prop.city}, ${prop.country}` : prop.address || "No location set"}
          </span>
        </div>

        {/* Room stats - Fixed grid */}
        <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground mb-3 pb-3 border-b">
          <div className="flex items-center gap-1">
            <BedDouble className="h-3.5 w-3.5 shrink-0" />
            <span>{prop.rooms || 0} Rooms</span>
          </div>
          <div className="flex items-center gap-1">
            <BedDouble className="h-3.5 w-3.5 shrink-0" />
            <span>{prop.suites || 0} Suites</span>
          </div>
          <div className="flex items-center gap-1">
            <Bath className="h-3.5 w-3.5 shrink-0" />
            <span>{prop.bathrooms || 0} Baths</span>
          </div>
        </div>

        {/* Owner & Units - Fixed grid */}
        <div className="grid grid-cols-2 gap-3 text-sm mb-3">
          <div className="flex items-center gap-1.5 text-muted-foreground min-w-0">
            <User className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{prop.owner_first_name} {prop.owner_last_name}</span>
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Building2 className="h-3.5 w-3.5 shrink-0" />
            <span>{prop.units} unit{prop.units !== 1 ? "s" : ""}</span>
          </div>
        </div>

        {/* Flexible content area - grows to fill space */}
        <div className="flex-1 space-y-2 min-h-[48px]">
          {getCohostName(prop.assigned_cohost) && (
            <div className="flex items-center gap-1.5 text-xs bg-primary/5 rounded-md px-2.5 py-2 border border-primary/10">
              <UserCheck className="h-3.5 w-3.5 text-primary shrink-0" />
              <span className="truncate">
                <span className="font-medium">Co-Host:</span> {getCohostName(prop.assigned_cohost)}
              </span>
            </div>
          )}
          {prop.notes && (
            <div className="flex items-start gap-1.5 text-xs text-muted-foreground">
              <FileText className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span className="line-clamp-2">{prop.notes}</span>
            </div>
          )}
        </div>

        {/* Actions - Fixed at bottom */}
        {isAdmin && (
          <div className="flex gap-2 pt-3 mt-auto border-t">
            <Button variant="outline" size="sm" onClick={() => onEdit(prop)} data-testid={`edit-property-${prop.id}`}>
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button variant="outline" size="sm" className="text-destructive hover:text-destructive hover:bg-destructive/5" onClick={() => onDelete(prop.id)} data-testid={`delete-property-${prop.id}`}>
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
        
        {/* Last Sync indicator */}
        {prop.last_ota_sync_at && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-2 pt-2 border-t">
            <Clock className="h-3 w-3" />
            <span>Last synced: {new Date(prop.last_ota_sync_at).toLocaleDateString()}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function Properties() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [properties, setProperties] = useState([]);
  const [cohosts, setCohosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastSyncInfo, setLastSyncInfo] = useState(null);

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const [propRes, cohostRes] = await Promise.all([
        fetch(`${API}/api/properties`, { credentials: "include" }),
        fetch(`${API}/api/staff/cohosts`, { credentials: "include" }),
      ]);
      if (propRes.ok) setProperties(await propRes.json());
      if (cohostRes.ok) setCohosts(await cohostRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };
  
  const fetchSyncStatus = async () => {
    try {
      const res = await fetch(`${API}/api/ota/sync-status`, { credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setLastSyncInfo(data);
        if (data.is_syncing) {
          setSyncing(true);
        }
      }
    } catch (err) { console.error(err); }
  };

  useEffect(() => { if (user?.company_id) { fetchData(); fetchSyncStatus(); } }, [user]); // eslint-disable-line

  const handleSave = async () => {
    setSaving(true);
    try {
      const method = editing ? "PUT" : "POST";
      const url = editing ? `${API}/api/properties/${editing}` : `${API}/api/properties`;
      const body = {
        ...form,
        units: parseInt(form.units) || 1,
        rooms: parseInt(form.rooms) || 0,
        suites: parseInt(form.suites) || 0,
        bathrooms: parseInt(form.bathrooms) || 0,
        assigned_cohost: form.assigned_cohost || null,
      };
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify(body) });
      if (res.ok) {
        toast.success(editing ? "Property updated" : "Property created");
        setDialogOpen(false); setForm(empty); setEditing(null); fetchData();
      } else { const err = await res.json(); toast.error(err.detail || "Failed to save"); }
    } catch (err) { toast.error("Error saving property"); } finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this property?")) return;
    try {
      const res = await fetch(`${API}/api/properties/${id}`, { method: "DELETE", credentials: "include" });
      if (res.ok) { toast.success("Property deleted"); fetchData(); }
    } catch (err) { toast.error("Error deleting property"); }
  };

  const handleOTASync = async () => {
    setSyncing(true);
    try {
      toast.info("Starting OTA sync...");
      const res = await fetch(`${API}/api/ota/sync`, { method: "POST", credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "no_feeds") {
          toast.warning("No OTA feeds configured. Go to OTA Settings to add feeds.");
        } else {
          toast.success(data.message);
          // Poll for completion
          const pollStatus = async () => {
            await new Promise(resolve => setTimeout(resolve, 2000));
            const statusRes = await fetch(`${API}/api/ota/sync-status`, { credentials: "include" });
            if (statusRes.ok) {
              const status = await statusRes.json();
              setLastSyncInfo(status);
              if (status.is_syncing) {
                pollStatus();
              } else {
                setSyncing(false);
                fetchData();
                if (status.latest_sync?.stats) {
                  const s = status.latest_sync.stats;
                  toast.success(`Sync complete: ${s.created} new, ${s.updated} updated bookings`);
                }
              }
            }
          };
          pollStatus();
        }
      } else {
        const err = await res.json();
        toast.error(err.detail || "Sync failed");
        setSyncing(false);
      }
    } catch (err) {
      toast.error("Sync failed");
      setSyncing(false);
    }
  };

  const openEdit = (prop) => {
    setForm({
      name: prop.name, address: prop.address, property_type: prop.property_type || "",
      rooms: prop.rooms || 0, suites: prop.suites || 0, bathrooms: prop.bathrooms || 0,
      city: prop.city || "", country: prop.country || "", notes: prop.notes || "",
      assigned_cohost: prop.assigned_cohost || "",
      owner_first_name: prop.owner_first_name, owner_last_name: prop.owner_last_name,
      owner_phone: prop.owner_phone, owner_email: prop.owner_email,
      units: prop.units, active: prop.active,
    });
    setEditing(prop.id); setDialogOpen(true);
  };

  const getCohostName = (id) => {
    const ch = cohosts.find(c => c.id === id);
    return ch ? `${ch.first_name} ${ch.last_name}` : null;
  };

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  const isAdmin = user?.role === "company_admin";
  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="properties-page">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="font-heading text-2xl font-bold">Properties</h1>
            <p className="text-sm text-muted-foreground mt-1">{properties.length} properties</p>
          </div>
          {isAdmin && (
            <div className="flex items-center gap-2 flex-wrap">
              <Button variant="outline" onClick={handleOTASync} disabled={syncing} data-testid="sync-ota-btn">
                <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
                {syncing ? "Syncing..." : "Sync from OTA"}
              </Button>
              <Button onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }} data-testid="add-property-btn">
                <Plus className="mr-2 h-4 w-4" /> Add Property
              </Button>
            </div>
          )}
        </div>
        
        {/* Last Sync Info */}
        {lastSyncInfo?.latest_sync && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>
              Last synced: {new Date(lastSyncInfo.latest_sync.created_at).toLocaleString()}
              {lastSyncInfo.feeds_count > 0 && ` • ${lastSyncInfo.feeds_count} feed(s) configured`}
            </span>
            <Button variant="link" size="sm" className="h-auto p-0 text-primary" onClick={() => navigate("/ota-settings")}>
              <Link2 className="h-3 w-3 mr-1" />
              Configure Feeds
            </Button>
          </div>
        )}
        
        {!lastSyncInfo?.latest_sync && lastSyncInfo?.feeds_count === 0 && isAdmin && (
          <Card className="border-dashed border-primary/30 bg-primary/5">
            <CardContent className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Link2 className="h-5 w-5 text-primary" />
                <div>
                  <p className="font-medium text-sm">No OTA feeds configured</p>
                  <p className="text-xs text-muted-foreground">Add iCal URLs from Airbnb, Booking.com, etc. to enable sync</p>
                </div>
              </div>
              <Button size="sm" onClick={() => navigate("/ota-settings")}>
                Configure OTA Feeds
              </Button>
            </CardContent>
          </Card>
        )}
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1,2,3].map(i => (
              <Card key={i} className="h-[280px]">
                <CardContent className="p-6 h-full animate-pulse bg-muted rounded-lg" />
              </Card>
            ))}
          </div>
        ) : properties.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="p-12 text-center">
              <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="font-heading font-semibold text-lg mb-1">No properties yet</h3>
              <p className="text-sm text-muted-foreground mb-4">Add your first property to get started</p>
              {isAdmin && (
                <Button onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }}>
                  <Plus className="mr-2 h-4 w-4" /> Add Property
                </Button>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {properties.map((prop) => (
              <PropertyCard 
                key={prop.id}
                prop={prop}
                isAdmin={isAdmin}
                onEdit={openEdit}
                onDelete={handleDelete}
                getCohostName={getCohostName}
              />
            ))}
          </div>
        )}

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
            <DialogHeader><DialogTitle className="font-heading">{editing ? "Edit Property" : "Add Property"}</DialogTitle></DialogHeader>
            <div className="grid gap-4 py-2">
              {/* Basic Info */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Property Name *</Label><Input data-testid="prop-name-input" value={form.name} onChange={e => set("name", e.target.value)} placeholder="Property name" /></div>
                <div className="space-y-2">
                  <Label>Property Type</Label>
                  <Select value={form.property_type} onValueChange={v => set("property_type", v)}>
                    <SelectTrigger data-testid="prop-type-select"><SelectValue placeholder="Select type..." /></SelectTrigger>
                    <SelectContent>{PROPERTY_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>
              {/* Rooms */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="space-y-2"><Label>Rooms</Label><Input data-testid="prop-rooms-input" type="number" min="0" value={form.rooms} onChange={e => set("rooms", e.target.value)} /></div>
                <div className="space-y-2"><Label>Suites</Label><Input data-testid="prop-suites-input" type="number" min="0" value={form.suites} onChange={e => set("suites", e.target.value)} /></div>
                <div className="space-y-2"><Label>Bathrooms</Label><Input data-testid="prop-bathrooms-input" type="number" min="0" value={form.bathrooms} onChange={e => set("bathrooms", e.target.value)} /></div>
                <div className="space-y-2"><Label>Units</Label><Input data-testid="prop-units-input" type="number" min="1" value={form.units} onChange={e => set("units", e.target.value)} /></div>
              </div>
              {/* Location */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2"><Label>City</Label><Input data-testid="prop-city-input" value={form.city} onChange={e => set("city", e.target.value)} placeholder="City" /></div>
                <div className="space-y-2">
                  <Label>Country</Label>
                  <Select value={form.country} onValueChange={v => set("country", v)}>
                    <SelectTrigger data-testid="prop-country-select"><SelectValue placeholder="Select country..." /></SelectTrigger>
                    <SelectContent>{COUNTRIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2"><Label>Address</Label><Input data-testid="prop-address-input" value={form.address} onChange={e => set("address", e.target.value)} placeholder="Full address" /></div>
              {/* Owner */}
              <p className="text-sm font-medium text-muted-foreground pt-2 border-t">Owner Details</p>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>First Name</Label><Input data-testid="prop-owner-fn-input" value={form.owner_first_name} onChange={e => set("owner_first_name", e.target.value)} /></div>
                <div className="space-y-2"><Label>Last Name</Label><Input data-testid="prop-owner-ln-input" value={form.owner_last_name} onChange={e => set("owner_last_name", e.target.value)} /></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Phone</Label><Input data-testid="prop-owner-phone-input" value={form.owner_phone} onChange={e => set("owner_phone", e.target.value)} /></div>
                <div className="space-y-2"><Label>Email</Label><Input data-testid="prop-owner-email-input" value={form.owner_email} onChange={e => set("owner_email", e.target.value)} /></div>
              </div>
              {/* Co-Host */}
              <div className="space-y-2">
                <Label>Assigned Co-Host</Label>
                <Select value={form.assigned_cohost} onValueChange={v => set("assigned_cohost", v)}>
                  <SelectTrigger data-testid="prop-cohost-select"><SelectValue placeholder="Select co-host..." /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No Co-Host</SelectItem>
                    {cohosts.map(ch => <SelectItem key={ch.id} value={ch.id}>{ch.first_name} {ch.last_name}</SelectItem>)}
                  </SelectContent>
                </Select>
                {cohosts.length === 0 && <p className="text-xs text-muted-foreground">No co-hosts available. Add staff with the Co-Host role first.</p>}
              </div>
              {/* Notes */}
              <div className="space-y-2">
                <Label>Notes</Label>
                <Textarea data-testid="prop-notes-input" value={form.notes} onChange={e => set("notes", e.target.value)} placeholder="Additional notes about the property..." rows={3} />
              </div>
              <div className="flex items-center gap-3">
                <Switch data-testid="prop-active-switch" checked={form.active} onCheckedChange={v => set("active", v)} />
                <Label>Active</Label>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSave} disabled={!form.name.trim() || saving} data-testid="save-property-btn">{saving ? "Saving..." : editing ? "Update" : "Create"}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
