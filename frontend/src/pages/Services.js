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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Plane, Utensils, Map, Sparkles, Car, Package, User, Building2, Phone, Mail } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const fmt = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v);

const categories = [
  { value: "airport_transfer", label: "Airport Transfer", icon: Plane },
  { value: "meals", label: "Meals & Dining", icon: Utensils },
  { value: "excursions", label: "Excursions & Tours", icon: Map },
  { value: "spa", label: "Spa & Wellness", icon: Sparkles },
  { value: "transport", label: "Transportation", icon: Car },
  { value: "other", label: "Other Services", icon: Package },
];

const priceTypes = [
  { value: "fixed", label: "Fixed Price" },
  { value: "per_person", label: "Per Person" },
  { value: "per_hour", label: "Per Hour" },
];

const empty = {
  name: "",
  description: "",
  category: "other",
  price: "",
  price_type: "fixed",
  provider_type: "internal",
  assigned_staff_id: "",
  external_provider_name: "",
  external_provider_phone: "",
  external_provider_email: "",
  active: true,
};

function ServiceCard({ service, staff, onEdit, onDelete, isAdmin }) {
  const category = categories.find(c => c.value === service.category) || categories[5];
  const IconComponent = category.icon;
  const assignedStaff = staff.find(s => s.id === service.assigned_staff_id);

  return (
    <Card className="group hover:shadow-md transition-shadow" data-testid={`service-card-${service.id}`}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className={`h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0`}>
              <IconComponent className="h-5 w-5 text-primary" />
            </div>
            <div className="min-w-0">
              <h3 className="font-medium text-sm truncate">{service.name}</h3>
              <p className="text-xs text-muted-foreground mt-0.5">{category.label}</p>
            </div>
          </div>
          <Badge variant={service.active ? "default" : "secondary"} className="shrink-0">
            {service.active ? "Active" : "Inactive"}
          </Badge>
        </div>

        {service.description && (
          <p className="text-sm text-muted-foreground mt-3 line-clamp-2">{service.description}</p>
        )}

        <div className="flex items-center justify-between mt-4 pt-3 border-t">
          <div>
            <p className="text-lg font-bold font-data">{fmt(service.price)}</p>
            <p className="text-xs text-muted-foreground capitalize">{service.price_type?.replace("_", " ")}</p>
          </div>
          <div className="text-right">
            {service.provider_type === "internal" ? (
              <div className="flex items-center gap-1.5 text-sm">
                <User className="h-3.5 w-3.5 text-primary" />
                <span>{assignedStaff ? `${assignedStaff.first_name} ${assignedStaff.last_name}` : "Unassigned"}</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-sm">
                <Building2 className="h-3.5 w-3.5 text-amber-500" />
                <span>{service.external_provider_name || "External"}</span>
              </div>
            )}
          </div>
        </div>

        {isAdmin && (
          <div className="flex justify-end gap-1 mt-3 pt-3 border-t opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="ghost" size="sm" onClick={() => onEdit(service)} data-testid={`edit-service-${service.id}`}>
              <Pencil className="h-4 w-4 mr-1" /> Edit
            </Button>
            <Button variant="ghost" size="sm" className="text-destructive" onClick={() => onDelete(service.id)} data-testid={`delete-service-${service.id}`}>
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
  const [activeCategory, setActiveCategory] = useState("all");

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const [svcRes, staffRes] = await Promise.all([
        fetch(`${API}/api/services?active_only=false`, { credentials: "include" }),
        fetch(`${API}/api/staff`, { credentials: "include" }),
      ]);
      if (svcRes.ok) setServices(await svcRes.json());
      if (staffRes.ok) setStaff(await staffRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchData(); }, [user]); // eslint-disable-line

  const handleSave = async () => {
    if (!form.name.trim()) { toast.error("Service name is required"); return; }
    setSaving(true);
    try {
      const method = editing ? "PUT" : "POST";
      const url = editing ? `${API}/api/services/${editing}` : `${API}/api/services`;
      const body = {
        ...form,
        price: parseFloat(form.price) || 0,
        assigned_staff_id: form.provider_type === "internal" ? form.assigned_staff_id || null : null,
        external_provider_name: form.provider_type === "external" ? form.external_provider_name : null,
        external_provider_phone: form.provider_type === "external" ? form.external_provider_phone : null,
        external_provider_email: form.provider_type === "external" ? form.external_provider_email : null,
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
    setForm({
      name: s.name,
      description: s.description || "",
      category: s.category,
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

  const filteredServices = activeCategory === "all" 
    ? services 
    : services.filter(s => s.category === activeCategory);

  // Group services by category for display
  const categoryCounts = categories.reduce((acc, cat) => {
    acc[cat.value] = services.filter(s => s.category === cat.value).length;
    return acc;
  }, {});

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="services-page">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold">Services</h1>
            <p className="text-sm text-muted-foreground mt-1">{services.length} services available</p>
          </div>
          {isAdmin && (
            <Button onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }} data-testid="add-service-btn">
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
          <>
            <Tabs value={activeCategory} onValueChange={setActiveCategory}>
              <TabsList className="flex-wrap h-auto gap-1 p-1" data-testid="service-category-tabs">
                <TabsTrigger value="all" className="gap-1.5">
                  All <Badge variant="secondary" className="h-5 px-1.5">{services.length}</Badge>
                </TabsTrigger>
                {categories.map(cat => {
                  const count = categoryCounts[cat.value] || 0;
                  if (count === 0) return null;
                  return (
                    <TabsTrigger key={cat.value} value={cat.value} className="gap-1.5">
                      <cat.icon className="h-3.5 w-3.5" />
                      <span className="hidden sm:inline">{cat.label}</span>
                      <Badge variant="secondary" className="h-5 px-1.5">{count}</Badge>
                    </TabsTrigger>
                  );
                })}
              </TabsList>
            </Tabs>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredServices.map(service => (
                <ServiceCard 
                  key={service.id} 
                  service={service} 
                  staff={staff}
                  onEdit={openEdit} 
                  onDelete={handleDelete}
                  isAdmin={isAdmin}
                />
              ))}
            </div>
          </>
        )}

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-heading">{editing ? "Edit Service" : "Add Service"}</DialogTitle>
              <DialogDescription>Create services that can be offered to guests as add-ons.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="space-y-2">
                <Label>Service Name *</Label>
                <Input data-testid="service-name-input" value={form.name} onChange={e => set("name", e.target.value)} placeholder="e.g., Airport Pickup" />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea data-testid="service-description-input" value={form.description} onChange={e => set("description", e.target.value)} placeholder="Describe this service..." rows={2} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Select value={form.category} onValueChange={v => set("category", v)}>
                    <SelectTrigger data-testid="service-category-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {categories.map(cat => (
                        <SelectItem key={cat.value} value={cat.value}>
                          <div className="flex items-center gap-2">
                            <cat.icon className="h-4 w-4" />
                            {cat.label}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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
              <div className="space-y-2">
                <Label>Price ($)</Label>
                <Input data-testid="service-price-input" type="number" step="0.01" value={form.price} onChange={e => set("price", e.target.value)} placeholder="0.00" />
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
              <Button onClick={handleSave} disabled={!form.name.trim() || saving} data-testid="save-service-btn">
                {saving ? "Saving..." : editing ? "Update" : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
