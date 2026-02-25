import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
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
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Package, User, Building2, Phone, Mail } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v);

// Default service types - simplified list
const DEFAULT_SERVICE_TYPES = [
  "Housekeeping",
  "Maintenance",
  "Check-in",
  "Check-out",
  "Transport",
  "Breakfast",
  "Meal",
  "Excursion",
  "Airport Transfer",
  "Spa",
  "Laundry",
  "Concierge",
];

const priceTypes = [
  { value: "fixed", label: "Fixed Price" },
  { value: "per_person", label: "Per Person" },
  { value: "per_hour", label: "Per Hour" },
];

const empty = {
  name: "",
  custom_name: "",
  description: "",
  price: "",
  price_type: "fixed",
  provider_type: "internal",
  assigned_staff_id: "",
  external_provider_name: "",
  external_provider_phone: "",
  external_provider_email: "",
  active: true,
};

function ServiceCard({ service, staff, onEdit, onDelete, isAdmin, index = 0 }) {
  const assignedStaff = staff.find(s => s.id === service.assigned_staff_id);

  return (
    <Card 
      className="group hover:shadow-lg hover:-translate-y-1 transition-all duration-200 animate-fade-in opacity-0" 
      data-testid={`service-card-${service.id}`}
      style={{ animationDelay: `${0.05 + index * 0.03}s` }}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 transition-transform group-hover:scale-110">
              <Package className="h-5 w-5 text-primary" />
            </div>
            <div className="min-w-0">
              <h3 className="font-medium text-sm truncate text-foreground">{service.name}</h3>
              {service.description && (
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{service.description}</p>
              )}
            </div>
          </div>
          <Badge variant={service.active ? "default" : "secondary"} className={`shrink-0 ${service.active ? 'bg-primary/10 text-primary border-0' : ''}`}>
            {service.active ? "Active" : "Inactive"}
          </Badge>
        </div>

        <div className="flex items-center justify-between mt-4 pt-3 border-t">
          <div>
            <p className="text-lg font-bold font-heading tabular-nums text-foreground">{fmt(service.price)}</p>
            <p className="text-xs text-muted-foreground capitalize">{service.price_type?.replace("_", " ")}</p>
          </div>
          <div className="text-right">
            {service.provider_type === "internal" ? (
              <div className="flex items-center gap-1.5 text-sm">
                <User className="h-3.5 w-3.5 text-primary" />
                <span className="text-foreground">{assignedStaff ? `${assignedStaff.first_name} ${assignedStaff.last_name}` : "Unassigned"}</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-sm">
                <Building2 className="h-3.5 w-3.5 text-amber-500" />
                <span className="text-foreground">{service.external_provider_name || "External"}</span>
              </div>
            )}
          </div>
        </div>

        {isAdmin && (
          <div className="flex justify-end gap-1 mt-3 pt-3 border-t opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="ghost" size="sm" onClick={() => onEdit(service)} data-testid={`edit-service-${service.id}`} className="hover:bg-primary/10 hover:text-primary">
              <Pencil className="h-4 w-4 mr-1" /> Edit
            </Button>
            <Button variant="ghost" size="sm" className="text-destructive hover:bg-destructive/10" onClick={() => onDelete(service.id)} data-testid={`delete-service-${service.id}`}>
              <Trash2 className="h-4 w-4 mr-1" /> Delete
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function Services() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [services, setServices] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const [svcRes, staffRes] = await Promise.all([
        fetch(`${API}/api/services?active_only=false`, { credentials: "include" }),
        fetch(`${API}/api/staff`, { credentials: "include" }).catch(() => ({ ok: false })),
      ]);
      if (svcRes.ok) setServices(await svcRes.json());
      if (staffRes.ok) setStaff(await staffRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchData(); }, [user]); // eslint-disable-line

  // Build service name options - defaults + custom from existing services
  const serviceNameOptions = [...new Set([
    ...DEFAULT_SERVICE_TYPES,
    ...services.map(s => s.name).filter(n => !DEFAULT_SERVICE_TYPES.includes(n))
  ])].sort();

  const handleSave = async () => {
    const serviceName = form.name === "Other" ? form.custom_name : form.name;
    if (!serviceName?.trim()) { toast.error("Service name is required"); return; }
    setSaving(true);
    try {
      const method = editing ? "PUT" : "POST";
      const url = editing ? `${API}/api/services/${editing}` : `${API}/api/services`;
      const body = {
        name: serviceName.trim(),
        description: form.description,
        category: "other", // Simplified - no categories
        price: parseFloat(form.price) || 0,
        price_type: form.price_type,
        provider_type: form.provider_type,
        assigned_staff_id: form.provider_type === "internal" ? form.assigned_staff_id || null : null,
        external_provider_name: form.provider_type === "external" ? form.external_provider_name : null,
        external_provider_phone: form.provider_type === "external" ? form.external_provider_phone : null,
        external_provider_email: form.provider_type === "external" ? form.external_provider_email : null,
        active: form.active,
      };
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify(body) });
      if (res.ok) {
        toast.success(editing ? "Service updated" : "Service created");
        setDialogOpen(false); setForm(empty); setEditing(null); fetchData();
      } else { const err = await res.json(); toast.error(err.detail || "Failed"); }
    } catch (err) { toast.error("Error"); } finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this service?")) return;
    try {
      const res = await fetch(`${API}/api/services/${id}`, { method: "DELETE", credentials: "include" });
      if (res.ok) { toast.success("Service deleted"); fetchData(); }
    } catch (err) { toast.error("Error"); }
  };

  const openEdit = (s) => {
    const isDefault = DEFAULT_SERVICE_TYPES.includes(s.name);
    setForm({
      name: isDefault ? s.name : "Other",
      custom_name: isDefault ? "" : s.name,
      description: s.description || "",
      price: s.price,
      price_type: s.price_type,
      provider_type: s.provider_type,
      assigned_staff_id: s.assigned_staff_id || "",
      external_provider_name: s.external_provider_name || "",
      external_provider_phone: s.external_provider_phone || "",
      external_provider_email: s.external_provider_email || "",
      active: s.active,
    });
    setEditing(s.id); setDialogOpen(true);
  };

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  const isAdmin = user?.role === "company_admin";
  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="services-page">
        <div className="flex items-center justify-between animate-fade-in">
          <div>
            <h1 className="font-heading text-2xl font-bold text-foreground">Services</h1>
            <p className="text-sm text-muted-foreground mt-1">{services.length} services available</p>
          </div>
          {isAdmin && (
            <Button onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }} data-testid="add-service-btn" className="shadow-sm">
              <Plus className="mr-2 h-4 w-4" />Add Service
            </Button>
          )}
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <Card key={i}><CardContent className="p-6 h-40 animate-pulse bg-muted" /></Card>
            ))}
          </div>
        ) : services.length === 0 ? (
          <Card className="border-dashed"><CardContent className="p-12 text-center">
            <Package className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No services yet</p>
            {isAdmin && (
              <Button className="mt-4" onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }}>
                <Plus className="mr-2 h-4 w-4" />Add Your First Service
              </Button>
            )}
          </CardContent></Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {services.map((service, index) => (
              <ServiceCard 
                key={service.id} 
                service={service} 
                staff={staff}
                onEdit={openEdit} 
                onDelete={handleDelete}
                isAdmin={isAdmin}
                index={index}
              />
            ))}
          </div>
        )}

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-heading">{editing ? "Edit Service" : "Add Service"}</DialogTitle>
              <DialogDescription>Services will be available as task types.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="space-y-2">
                <Label>Service Type *</Label>
                <Select value={form.name} onValueChange={v => { set("name", v); if (v !== "Other") set("custom_name", ""); }}>
                  <SelectTrigger data-testid="service-name-select"><SelectValue placeholder="Select service type..." /></SelectTrigger>
                  <SelectContent>
                    {serviceNameOptions.map(name => (
                      <SelectItem key={name} value={name}>{name}</SelectItem>
                    ))}
                    <SelectItem value="Other">Other (Custom)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {form.name === "Other" && (
                <div className="space-y-2">
                  <Label>Custom Service Name *</Label>
                  <Input 
                    data-testid="service-custom-name-input" 
                    value={form.custom_name} 
                    onChange={e => set("custom_name", e.target.value)} 
                    placeholder="Enter custom service name" 
                  />
                </div>
              )}
              
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea data-testid="service-description-input" value={form.description} onChange={e => set("description", e.target.value)} placeholder="Describe this service..." rows={2} />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Price ($)</Label>
                  <Input data-testid="service-price-input" type="number" step="0.01" value={form.price} onChange={e => set("price", e.target.value)} placeholder="0.00" />
                </div>
                <div className="space-y-2">
                  <Label>Price Type</Label>
                  <Select value={form.price_type} onValueChange={v => set("price_type", v)}>
                    <SelectTrigger data-testid="service-pricetype-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {priceTypes.map(pt => (
                        <SelectItem key={pt.value} value={pt.value}>{pt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-3 pt-2 border-t">
                <Label className="text-base font-medium">Provider</Label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => set("provider_type", "internal")}
                    className={`p-3 rounded-lg border-2 text-left transition-all ${form.provider_type === "internal" ? "border-primary bg-primary/5" : "border-muted hover:border-muted-foreground/30"}`}
                    data-testid="provider-internal-btn"
                  >
                    <User className="h-5 w-5 mb-1" />
                    <p className="font-medium text-sm">Internal Staff</p>
                    <p className="text-xs text-muted-foreground">Assign to a team member</p>
                  </button>
                  <button
                    type="button"
                    onClick={() => set("provider_type", "external")}
                    className={`p-3 rounded-lg border-2 text-left transition-all ${form.provider_type === "external" ? "border-primary bg-primary/5" : "border-muted hover:border-muted-foreground/30"}`}
                    data-testid="provider-external-btn"
                  >
                    <Building2 className="h-5 w-5 mb-1" />
                    <p className="font-medium text-sm">External Provider</p>
                    <p className="text-xs text-muted-foreground">Third-party service</p>
                  </button>
                </div>

                {form.provider_type === "internal" ? (
                  <div className="space-y-2">
                    <Label>Assign Staff Member</Label>
                    <Select value={form.assigned_staff_id || "none"} onValueChange={v => set("assigned_staff_id", v === "none" ? "" : v)}>
                      <SelectTrigger data-testid="service-staff-select"><SelectValue placeholder="Select staff..." /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">No assignment</SelectItem>
                        {staff.filter(s => s.active).map(s => (
                          <SelectItem key={s.id} value={s.id}>{s.first_name} {s.last_name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label>Provider Name</Label>
                      <Input data-testid="provider-name-input" value={form.external_provider_name} onChange={e => set("external_provider_name", e.target.value)} placeholder="Company or person name" />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label className="flex items-center gap-1"><Phone className="h-3 w-3" /> Phone</Label>
                        <Input data-testid="provider-phone-input" value={form.external_provider_phone} onChange={e => set("external_provider_phone", e.target.value)} placeholder="+1..." />
                      </div>
                      <div className="space-y-2">
                        <Label className="flex items-center gap-1"><Mail className="h-3 w-3" /> Email</Label>
                        <Input data-testid="provider-email-input" type="email" value={form.external_provider_email} onChange={e => set("external_provider_email", e.target.value)} placeholder="email@..." />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between pt-2 border-t">
                <div>
                  <Label>Active</Label>
                  <p className="text-xs text-muted-foreground">Show this service to guests</p>
                </div>
                <Switch checked={form.active} onCheckedChange={v => set("active", v)} data-testid="service-active-switch" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSave} disabled={(!form.name || (form.name === "Other" && !form.custom_name?.trim())) || saving} data-testid="save-service-btn">
                {saving ? "Saving..." : editing ? "Update" : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
