import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Building2, MapPin, User, RefreshCw, Clock, Globe, FileEdit, Loader2, CheckCircle, Eye } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const PROPERTY_TYPES = ["Apartment", "Villa", "Hotel", "Resort", "Cabin", "Townhouse", "Condo", "House", "Studio", "Penthouse"];
const COUNTRIES = ["United States", "United Kingdom", "Canada", "Australia", "France", "Germany", "Spain", "Italy", "Portugal", "Greece", "Turkey", "UAE", "Thailand", "Mexico", "Brazil", "Japan", "Indonesia", "South Africa", "Morocco", "Egypt", "Saudi Arabia", "Switzerland", "Netherlands", "Austria", "Sweden"];
const OTA_SOURCES = [
  { value: "airbnb", label: "Airbnb" },
  { value: "booking.com", label: "Booking.com" },
  { value: "vrbo", label: "VRBO" },
  { value: "expedia", label: "Expedia" },
  { value: "other", label: "Other" },
];

const empty = {
  name: "", address: "", property_type: "", rooms: 1, suites: 0, bathrooms: 1,
  city: "", country: "", notes: "", assigned_cohost: "",
  owner_first_name: "", owner_last_name: "", owner_phone: "", owner_email: "",
  units: 1, active: true,
};

function PropertyCard({ prop, isAdmin, onEdit, onDelete, onQuickView, index = 0 }) {
  const ownerName = [prop.owner_first_name, prop.owner_last_name].filter(Boolean).join(" ") || "No owner";
  const location = prop.city && prop.country ? `${prop.city}, ${prop.country}` : prop.address || "No address";
  
  return (
    <Card 
      className="group hover:shadow-lg hover:-translate-y-1 transition-all duration-200 border-border/60 animate-fade-in opacity-0" 
      data-testid={`property-card-${prop.id}`}
      style={{ animationDelay: `${0.05 + index * 0.03}s` }}
    >
      <CardContent className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <h3 className="font-semibold text-sm leading-tight line-clamp-2 text-foreground">{prop.name}</h3>
          <Badge 
            variant={prop.active ? "default" : "secondary"} 
            className={`shrink-0 text-[10px] px-1.5 py-0 ${prop.active ? 'bg-primary/10 text-primary border-primary/20' : ''}`}
          >
            {prop.active ? "Active" : "Inactive"}
          </Badge>
        </div>

        {/* Details */}
        <div className="space-y-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <MapPin className="h-3 w-3 shrink-0 text-primary/60" />
            <span className="truncate">{location}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <User className="h-3 w-3 shrink-0 text-primary/60" />
            <span className="truncate">{ownerName}</span>
          </div>
          {prop.last_ota_sync_at && (
            <div className="flex items-center gap-1.5">
              <Clock className="h-3 w-3 shrink-0 text-primary/60" />
              <span>Synced {new Date(prop.last_ota_sync_at).toLocaleDateString()}</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 mt-4 pt-3 border-t border-border/50">
          <Button 
            variant="outline" 
            size="sm" 
            className="flex-1 h-8 text-xs hover:bg-primary/5 hover:border-primary/30 hover:text-primary transition-colors"
            onClick={() => onQuickView(prop)}
            data-testid={`view-property-${prop.id}`}
          >
            <Eye className="h-3 w-3 mr-1.5" />
            Quick View
          </Button>
          {isAdmin && (
            <>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0 hover:bg-primary/10 hover:text-primary" onClick={() => onEdit(prop)} data-testid={`edit-property-${prop.id}`}>
                <Pencil className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10" onClick={() => onDelete(prop.id)} data-testid={`delete-property-${prop.id}`}>
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </>
          )}
        </div>
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
  
  // Dialog states
  const [choiceDialogOpen, setChoiceDialogOpen] = useState(false);
  const [otaDialogOpen, setOtaDialogOpen] = useState(false);
  const [manualDialogOpen, setManualDialogOpen] = useState(false);
  const [quickViewProp, setQuickViewProp] = useState(null);
  
  // Form states
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  
  // OTA sync states
  const [syncing, setSyncing] = useState(false);
  const [lastSyncInfo, setLastSyncInfo] = useState(null);
  
  // OTA import states
  const [otaForm, setOtaForm] = useState({ name: "", source: "", ical_url: "" });
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);

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
        setManualDialogOpen(false); setForm(empty); setEditing(null); fetchData();
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

  // OTA Import - Create new property from iCal
  const handleOTAImport = async () => {
    if (!otaForm.name.trim()) {
      toast.error("Please enter a property name");
      return;
    }
    if (!otaForm.source) {
      toast.error("Please select an OTA source");
      return;
    }
    if (!otaForm.ical_url.trim()) {
      toast.error("Please enter an iCal URL");
      return;
    }
    
    setImporting(true);
    setImportResult(null);
    
    try {
      const res = await fetch(`${API}/api/ota/import-property`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          name: otaForm.name.trim(),
          source: otaForm.source,
          ical_url: otaForm.ical_url.trim(),
        }),
      });
      
      if (res.ok) {
        const data = await res.json();
        toast.success(`Property "${data.property_name}" created with ${data.bookings_imported} booking(s)!`);
        fetchData();
        fetchSyncStatus();
        // Close dialog and reset form
        setOtaDialogOpen(false);
        setOtaForm({ name: "", source: "", ical_url: "" });
        setImportResult(null);
      } else {
        const err = await res.json();
        toast.error(err.detail || "Failed to import property");
      }
    } catch (err) {
      toast.error("Error importing property");
    } finally {
      setImporting(false);
    }
  };

  // Global OTA Sync for all configured feeds
  const handleOTASync = async () => {
    setSyncing(true);
    try {
      toast.info("Starting OTA sync...");
      const res = await fetch(`${API}/api/ota/sync`, { method: "POST", credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "no_feeds") {
          toast.warning("No OTA feeds configured. Add a property via OTA to enable sync.");
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
      owner_first_name: prop.owner_first_name || "", owner_last_name: prop.owner_last_name || "",
      owner_phone: prop.owner_phone || "", owner_email: prop.owner_email || "",
      units: prop.units || 1, active: prop.active ?? true,
    });
    setEditing(prop.id);
    setManualDialogOpen(true);
  };

  const openAddChoice = () => {
    setChoiceDialogOpen(true);
  };

  const selectAddManual = () => {
    setChoiceDialogOpen(false);
    setForm(empty);
    setEditing(null);
    setManualDialogOpen(true);
  };

  const selectAddOTA = () => {
    setChoiceDialogOpen(false);
    setOtaForm({ name: "", source: "", ical_url: "" });
    setImportResult(null);
    setOtaDialogOpen(true);
  };

  const generateMockUrl = () => {
    if (!otaForm.source || !otaForm.name) {
      toast.error("Enter property name and select source first");
      return;
    }
    const propName = otaForm.name.trim().replace(/\s+/g, "_");
    setOtaForm(prev => ({ ...prev, ical_url: `mock://${otaForm.source}/${propName}` }));
    toast.info("Mock URL generated for testing");
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
      <div className="space-y-6" data-testid="properties-page">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-4 animate-fade-in">
          <div>
            <h1 className="text-xl font-semibold font-heading text-foreground">Properties</h1>
            <p className="text-sm text-muted-foreground">{properties.length} total</p>
          </div>
          {isAdmin && (
            <div className="flex items-center gap-2">
              {lastSyncInfo?.feeds_count > 0 && (
                <Button variant="outline" size="sm" onClick={handleOTASync} disabled={syncing} data-testid="refresh-btn" className="hover:bg-primary/5 hover:border-primary/30 hover:text-primary">
                  <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
                  {syncing ? "Refreshing..." : "Refresh"}
                </Button>
              )}
              <Button size="sm" onClick={openAddChoice} data-testid="add-property-btn" className="shadow-sm">
                <Plus className="mr-2 h-4 w-4" /> Add Property
              </Button>
            </div>
          )}
        </div>

        {/* Grid - 6 columns desktop, 3 tablet, 1 mobile */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
            {[1,2,3,4,5,6].map(i => (
              <Card key={i} className="h-[180px]">
                <CardContent className="p-4 h-full animate-pulse bg-muted/50 rounded-lg" />
              </Card>
            ))}
          </div>
        ) : properties.length === 0 ? (
          <Card className="border-dashed border-2">
            <CardContent className="py-16 text-center">
              <Building2 className="h-10 w-10 mx-auto text-muted-foreground/50 mb-4" />
              <h3 className="font-medium text-base mb-1">No properties yet</h3>
              <p className="text-sm text-muted-foreground mb-4">Add your first property to get started</p>
              {isAdmin && (
                <Button size="sm" onClick={openAddChoice}>
                  <Plus className="mr-2 h-4 w-4" /> Add Property
                </Button>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
            {properties.map((prop, index) => (
              <PropertyCard 
                key={prop.id}
                prop={prop}
                isAdmin={isAdmin}
                onEdit={openEdit}
                onDelete={handleDelete}
                onQuickView={setQuickViewProp}
                getCohostName={getCohostName}
                index={index}
              />
            ))}
          </div>
        )}

        {/* Quick View Dialog */}
        <Dialog open={!!quickViewProp} onOpenChange={() => setQuickViewProp(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>{quickViewProp?.name}</DialogTitle>
            </DialogHeader>
            {quickViewProp && (
              <div className="space-y-4 py-2">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground text-xs mb-1">Address</p>
                    <p>{quickViewProp.address || quickViewProp.city || "Not set"}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs mb-1">Status</p>
                    <Badge variant={quickViewProp.active ? "default" : "secondary"}>
                      {quickViewProp.active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs mb-1">Owner</p>
                    <p>{[quickViewProp.owner_first_name, quickViewProp.owner_last_name].filter(Boolean).join(" ") || "Not set"}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs mb-1">Units</p>
                    <p>{quickViewProp.units || 1}</p>
                  </div>
                  {quickViewProp.last_ota_sync_at && (
                    <div className="col-span-2">
                      <p className="text-muted-foreground text-xs mb-1">Last Synced</p>
                      <p>{new Date(quickViewProp.last_ota_sync_at).toLocaleString()}</p>
                    </div>
                  )}
                </div>
                {isAdmin && (
                  <div className="flex gap-2 pt-4 border-t">
                    <Button className="flex-1" onClick={() => { setQuickViewProp(null); openEdit(quickViewProp); }}>
                      <Pencil className="mr-2 h-4 w-4" /> Edit Property
                    </Button>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Choice Dialog - Add Property Options */}
        <Dialog open={choiceDialogOpen} onOpenChange={setChoiceDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="font-heading">Add Property</DialogTitle>
              <DialogDescription>Choose how you'd like to add a new property</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <Card 
                className="cursor-pointer hover:border-primary hover:bg-primary/5 transition-colors"
                onClick={selectAddOTA}
                data-testid="add-from-ota-choice"
              >
                <CardContent className="p-4 flex items-start gap-4">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                    <Globe className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Sync from OTA</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Import property & bookings from Airbnb, Booking.com, etc. using iCal
                    </p>
                  </div>
                </CardContent>
              </Card>
              
              <Card 
                className="cursor-pointer hover:border-primary hover:bg-primary/5 transition-colors"
                onClick={selectAddManual}
                data-testid="add-manual-choice"
              >
                <CardContent className="p-4 flex items-start gap-4">
                  <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center shrink-0">
                    <FileEdit className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Add Manually</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Enter property details manually without OTA connection
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </DialogContent>
        </Dialog>

        {/* OTA Import Dialog */}
        <Dialog open={otaDialogOpen} onOpenChange={setOtaDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-heading flex items-center gap-2">
                <Globe className="h-5 w-5" /> Sync from OTA
              </DialogTitle>
              <DialogDescription>
                Enter the iCal URL from your OTA platform to import property and bookings
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label>Property Name *</Label>
                <Input 
                  value={otaForm.name}
                  onChange={e => setOtaForm(p => ({ ...p, name: e.target.value }))}
                  placeholder="e.g., Beach House"
                  data-testid="ota-property-name"
                />
                <p className="text-xs text-muted-foreground">Give your property a name for easy identification</p>
              </div>
              
              <div className="space-y-2">
                <Label>OTA Source *</Label>
                <Select value={otaForm.source} onValueChange={v => setOtaForm(p => ({ ...p, source: v }))}>
                  <SelectTrigger data-testid="ota-source-select">
                    <SelectValue placeholder="Select OTA platform..." />
                  </SelectTrigger>
                  <SelectContent>
                    {OTA_SOURCES.map(s => (
                      <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>iCal URL *</Label>
                  <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={generateMockUrl}>
                    Generate Mock URL
                  </Button>
                </div>
                <Input 
                  value={otaForm.ical_url}
                  onChange={e => setOtaForm(p => ({ ...p, ical_url: e.target.value }))}
                  placeholder="https://www.airbnb.com/calendar/ical/..."
                  data-testid="ota-ical-url"
                />
                <p className="text-xs text-muted-foreground">
                  Find the iCal export URL in your OTA platform settings
                </p>
              </div>
              
              {importResult && (
                <Card className="bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800">
                  <CardContent className="p-3 flex items-center gap-3">
                    <CheckCircle className="h-5 w-5 text-emerald-600" />
                    <div className="text-sm">
                      <p className="font-medium text-emerald-800 dark:text-emerald-400">Property imported!</p>
                      <p className="text-emerald-700 dark:text-emerald-500">
                        {importResult.bookings_imported} booking(s) created
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOtaDialogOpen(false)}>Cancel</Button>
              <Button 
                onClick={handleOTAImport} 
                disabled={importing || !otaForm.name.trim() || !otaForm.source || !otaForm.ical_url.trim()}
                data-testid="import-ota-btn"
              >
                {importing ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Importing...</>
                ) : (
                  <><RefreshCw className="mr-2 h-4 w-4" /> Import Property</>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Manual Add/Edit Dialog */}
        <Dialog open={manualDialogOpen} onOpenChange={setManualDialogOpen}>
          <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
            <DialogHeader><DialogTitle className="font-heading">{editing ? "Edit Property" : "Add Property Manually"}</DialogTitle></DialogHeader>
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
              <Button variant="outline" onClick={() => setManualDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSave} disabled={!form.name.trim() || saving} data-testid="save-property-btn">{saving ? "Saving..." : editing ? "Update" : "Create"}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
