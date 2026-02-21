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
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Building2, MapPin, User, Phone, Mail } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const empty = { name: "", address: "", owner_first_name: "", owner_last_name: "", owner_phone: "", owner_email: "", units: 1, active: true };

export default function Properties() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  const fetchProperties = async () => {
    try {
      const res = await fetch(`${API}/api/properties`, { credentials: "include" });
      if (res.ok) setProperties(await res.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchProperties(); }, [user]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const method = editing ? "PUT" : "POST";
      const url = editing ? `${API}/api/properties/${editing}` : `${API}/api/properties`;
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify({ ...form, units: parseInt(form.units) || 1 }) });
      if (res.ok) {
        toast.success(editing ? "Property updated" : "Property created");
        setDialogOpen(false);
        setForm(empty);
        setEditing(null);
        fetchProperties();
      } else {
        const err = await res.json();
        toast.error(err.detail || "Failed to save");
      }
    } catch (err) { toast.error("Error saving property"); } finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this property?")) return;
    try {
      const res = await fetch(`${API}/api/properties/${id}`, { method: "DELETE", credentials: "include" });
      if (res.ok) { toast.success("Property deleted"); fetchProperties(); }
    } catch (err) { toast.error("Error deleting property"); }
  };

  const openEdit = (prop) => {
    setForm({ name: prop.name, address: prop.address, owner_first_name: prop.owner_first_name, owner_last_name: prop.owner_last_name, owner_phone: prop.owner_phone, owner_email: prop.owner_email, units: prop.units, active: prop.active });
    setEditing(prop.id);
    setDialogOpen(true);
  };

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  const isAdmin = user?.role === "company_admin";

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="properties-page">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold">Properties</h1>
            <p className="text-sm text-muted-foreground mt-1">{properties.length} properties</p>
          </div>
          {isAdmin && (
            <Button onClick={() => { setForm(empty); setEditing(null); setDialogOpen(true); }} data-testid="add-property-btn">
              <Plus className="mr-2 h-4 w-4" /> Add Property
            </Button>
          )}
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1,2,3].map(i => <Card key={i}><CardContent className="p-6 h-48 animate-pulse bg-muted" /></Card>)}
          </div>
        ) : properties.length === 0 ? (
          <Card className="border-dashed"><CardContent className="p-12 text-center">
            <Building2 className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No properties yet</p>
          </CardContent></Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {properties.map((prop) => (
              <Card key={prop.id} className="overflow-hidden hover:shadow-md transition-shadow" data-testid={`property-card-${prop.id}`}>
                <div className="h-3 bg-primary" />
                <CardContent className="p-5 space-y-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-heading font-semibold text-base">{prop.name}</h3>
                      <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1"><MapPin className="h-3 w-3" />{prop.address}</p>
                    </div>
                    <Badge variant={prop.active ? "default" : "secondary"}>{prop.active ? "Active" : "Inactive"}</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex items-center gap-1.5 text-muted-foreground"><User className="h-3.5 w-3.5" />{prop.owner_first_name} {prop.owner_last_name}</div>
                    <div className="flex items-center gap-1.5 text-muted-foreground"><Building2 className="h-3.5 w-3.5" />{prop.units} units</div>
                    <div className="flex items-center gap-1.5 text-muted-foreground"><Phone className="h-3.5 w-3.5" /><span className="truncate">{prop.owner_phone}</span></div>
                    <div className="flex items-center gap-1.5 text-muted-foreground"><Mail className="h-3.5 w-3.5" /><span className="truncate">{prop.owner_email}</span></div>
                  </div>
                  {isAdmin && (
                    <div className="flex gap-2 pt-2 border-t">
                      <Button variant="outline" size="sm" onClick={() => openEdit(prop)} data-testid={`edit-property-${prop.id}`}><Pencil className="h-3.5 w-3.5 mr-1" />Edit</Button>
                      <Button variant="outline" size="sm" onClick={() => handleDelete(prop.id)} className="text-destructive hover:text-destructive" data-testid={`delete-property-${prop.id}`}><Trash2 className="h-3.5 w-3.5 mr-1" />Delete</Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader><DialogTitle className="font-heading">{editing ? "Edit Property" : "Add Property"}</DialogTitle></DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Property Name</Label><Input data-testid="prop-name-input" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="Property name" /></div>
                <div className="space-y-2"><Label>Units</Label><Input data-testid="prop-units-input" type="number" min="1" value={form.units} onChange={e => setForm(p => ({ ...p, units: e.target.value }))} /></div>
              </div>
              <div className="space-y-2"><Label>Address</Label><Input data-testid="prop-address-input" value={form.address} onChange={e => setForm(p => ({ ...p, address: e.target.value }))} placeholder="Full address" /></div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Owner First Name</Label><Input data-testid="prop-owner-fn-input" value={form.owner_first_name} onChange={e => setForm(p => ({ ...p, owner_first_name: e.target.value }))} /></div>
                <div className="space-y-2"><Label>Owner Last Name</Label><Input data-testid="prop-owner-ln-input" value={form.owner_last_name} onChange={e => setForm(p => ({ ...p, owner_last_name: e.target.value }))} /></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Owner Phone</Label><Input data-testid="prop-owner-phone-input" value={form.owner_phone} onChange={e => setForm(p => ({ ...p, owner_phone: e.target.value }))} /></div>
                <div className="space-y-2"><Label>Owner Email</Label><Input data-testid="prop-owner-email-input" value={form.owner_email} onChange={e => setForm(p => ({ ...p, owner_email: e.target.value }))} /></div>
              </div>
              <div className="flex items-center gap-3">
                <Switch data-testid="prop-active-switch" checked={form.active} onCheckedChange={v => setForm(p => ({ ...p, active: v }))} />
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
