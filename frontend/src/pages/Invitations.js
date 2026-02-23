import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { Plus, Mail, Copy, Check, Send, RefreshCw, XCircle, Filter, UserPlus, Shield, Building2, Clock, CheckCircle } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const statusConfig = {
  pending: { label: "Pending", className: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-200" },
  accepted: { label: "Accepted", className: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200" },
  expired: { label: "Expired", className: "bg-red-500/10 text-red-500 dark:text-red-400 border-red-200" },
  cancelled: { label: "Cancelled", className: "bg-slate-500/10 text-slate-500 dark:text-slate-400 border-slate-200" },
};

export default function Invitations() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [invitations, setInvitations] = useState([]);
  const [staff, setStaff] = useState([]);
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [copiedId, setCopiedId] = useState(null);
  const [resendingId, setResendingId] = useState(null);

  // Form state
  const [form, setForm] = useState({
    role: "staff",
    selectedPerson: "",
    manualEmail: "",
    name: "",
    assignedProperties: [],
    permissions: { view_financials: false, manage_bookings: true, manage_tasks: true },
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);
  useEffect(() => { if (!authLoading && user && user.role !== "company_admin") navigate("/dashboard"); }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const [invRes, staffRes, propRes] = await Promise.all([
        fetch(`${API}/api/invitations`, { credentials: "include" }),
        fetch(`${API}/api/staff`, { credentials: "include" }),
        fetch(`${API}/api/properties`, { credentials: "include" }),
      ]);
      if (invRes.ok) setInvitations(await invRes.json());
      if (staffRes.ok) setStaff(await staffRes.json());
      if (propRes.ok) setProperties(await propRes.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchData(); }, [user]); // eslint-disable-line

  // Build unique owners from properties
  const owners = useMemo(() => {
    const map = new Map();
    properties.forEach(p => {
      if (p.owner_email) {
        const key = p.owner_email;
        if (!map.has(key)) {
          map.set(key, { email: p.owner_email, name: `${p.owner_first_name || ""} ${p.owner_last_name || ""}`.trim(), properties: [p.name] });
        } else {
          map.get(key).properties.push(p.name);
        }
      }
    });
    return Array.from(map.values());
  }, [properties]);

  // People list based on role
  const people = useMemo(() => {
    if (form.role === "staff") {
      return staff.map(s => ({ id: s.id, name: `${s.first_name} ${s.last_name}`, email: s.email, detail: s.staff_role?.replace("_", " ") || "" }));
    }
    return owners.map((o, i) => ({ id: `owner_${i}`, name: o.name, email: o.email, detail: o.properties.join(", ") }));
  }, [form.role, staff, owners]);

  const resolvedEmail = useMemo(() => {
    if (form.selectedPerson && form.selectedPerson !== "manual") {
      const person = people.find(p => p.id === form.selectedPerson);
      return person?.email || "";
    }
    return form.manualEmail;
  }, [form.selectedPerson, form.manualEmail, people]);

  const resolvedName = useMemo(() => {
    if (form.name) return form.name;
    if (form.selectedPerson && form.selectedPerson !== "manual") {
      const person = people.find(p => p.id === form.selectedPerson);
      return person?.name || "";
    }
    return "";
  }, [form.name, form.selectedPerson, people]);

  const resetForm = () => setForm({
    role: "staff", selectedPerson: "", manualEmail: "", name: "",
    assignedProperties: [], permissions: { view_financials: false, manage_bookings: true, manage_tasks: true },
  });

  const handleCreate = async () => {
    if (!resolvedEmail) { toast.error("Email is required"); return; }
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/invitations`, {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify({
          email: resolvedEmail,
          role: form.role,
          name: resolvedName,
          assigned_properties: form.assignedProperties,
          permissions: form.role === "staff" ? form.permissions : {},
        }),
      });
      if (res.ok) {
        toast.success("Invitation sent!");
        setDialogOpen(false);
        resetForm();
        fetchData();
      } else { const err = await res.json(); toast.error(err.detail || "Failed"); }
    } catch (err) { toast.error("Error sending invitation"); } finally { setSaving(false); }
  };

  const handleCancel = async (id) => {
    try {
      const res = await fetch(`${API}/api/invitations/${id}/cancel`, { method: "PUT", credentials: "include" });
      if (res.ok) { toast.success("Invitation cancelled"); fetchData(); }
      else { const err = await res.json(); toast.error(err.detail || "Failed"); }
    } catch (err) { toast.error("Error"); }
  };

  const handleResend = async (id) => {
    setResendingId(id);
    try {
      const res = await fetch(`${API}/api/invitations/${id}/resend`, { method: "POST", credentials: "include" });
      if (res.ok) {
        toast.success("New invitation sent! Previous link invalidated.");
        fetchData();
      } else { const err = await res.json(); toast.error(err.detail || "Failed"); }
    } catch (err) { toast.error("Error"); } finally { setResendingId(null); }
  };

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`${API}/api/invitations/${id}`, { method: "DELETE", credentials: "include" });
      if (res.ok) { toast.success("Invitation removed"); fetchData(); }
    } catch (err) { toast.error("Error"); }
  };

  const copyLink = (token) => {
    if (!token) { toast.error("No active link for this invitation"); return; }
    const link = `${window.location.origin}/invite/${token}`;
    navigator.clipboard.writeText(link);
    setCopiedId(token);
    toast.success("Link copied!");
    setTimeout(() => setCopiedId(null), 2000);
  };

  const toggleProperty = (propId) => {
    setForm(prev => ({
      ...prev,
      assignedProperties: prev.assignedProperties.includes(propId)
        ? prev.assignedProperties.filter(id => id !== propId)
        : [...prev.assignedProperties, propId],
    }));
  };

  const togglePermission = (key) => {
    setForm(prev => ({ ...prev, permissions: { ...prev.permissions, [key]: !prev.permissions[key] } }));
  };

  const filteredInvitations = useMemo(() => {
    if (statusFilter === "all") return invitations;
    return invitations.filter(inv => inv.status === statusFilter);
  }, [invitations, statusFilter]);

  const getPropNames = (ids) => {
    if (!ids || ids.length === 0) return "All";
    return ids.map(id => properties.find(p => p.id === id)?.name || id).join(", ");
  };

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="invite-page">
        {/* Header */}
        <div className="flex items-center justify-between animate-fade-in">
          <div>
            <h1 className="font-heading text-2xl font-bold text-foreground">Invite</h1>
            <p className="text-sm text-muted-foreground mt-1">Invite owners and staff to your organization</p>
          </div>
          <Button onClick={() => { resetForm(); setDialogOpen(true); }} data-testid="send-invitation-btn" className="shadow-sm">
            <UserPlus className="mr-2 h-4 w-4" />Send Invitation
          </Button>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-2" data-testid="invite-status-filter">
          {["all", "pending", "accepted", "expired", "cancelled"].map(s => (
            <Button
              key={s}
              variant={statusFilter === s ? "default" : "outline"}
              size="sm"
              className="capitalize h-8"
              onClick={() => setStatusFilter(s)}
            >
              {s === "all" ? "All" : statusConfig[s]?.label || s}
              {s !== "all" && (
                <Badge variant="secondary" className="ml-1.5 h-5 px-1.5 text-[10px]">
                  {invitations.filter(i => i.status === s).length}
                </Badge>
              )}
            </Button>
          ))}
        </div>

        {/* Invitations Table */}
        {loading ? (
          <Card><CardContent className="p-6 h-32 animate-pulse bg-muted" /></Card>
        ) : filteredInvitations.length === 0 ? (
          <Card className="border-dashed"><CardContent className="p-12 text-center">
            <Mail className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">{statusFilter !== "all" ? `No ${statusFilter} invitations` : "No invitations sent yet"}</p>
          </CardContent></Card>
        ) : (
          <Card>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Properties</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Sent</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredInvitations.map((inv) => {
                    const sc = statusConfig[inv.status] || statusConfig.pending;
                    const canResend = inv.status === "pending" || inv.status === "expired";
                    const canCancel = inv.status === "pending" || inv.status === "expired";

                    return (
                      <TableRow key={inv.id} data-testid={`invitation-row-${inv.id}`}>
                        <TableCell className="font-medium">{inv.name || "-"}</TableCell>
                        <TableCell className="text-sm">{inv.email}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="capitalize">
                            {inv.role === "owner" ? <Building2 className="h-3 w-3 mr-1" /> : <Shield className="h-3 w-3 mr-1" />}
                            {inv.role}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground max-w-[200px] truncate">
                          {getPropNames(inv.assigned_properties)}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            <Badge variant="outline" className={sc.className}>{sc.label}</Badge>
                            {inv.email_delivery_status === 'sent' && (
                              <span className="text-[10px] text-emerald-500">Email delivered</span>
                            )}
                            {inv.email_delivery_status === 'failed' && (
                              <span className="text-[10px] text-red-400">Email failed — use copy link</span>
                            )}
                            {!inv.email_delivery_status && inv.email_sent && (
                              <span className="text-[10px] text-emerald-500">Email sent</span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {inv.created_at?.slice(0, 10)}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {inv.expires_at?.slice(0, 10) || "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            {canResend && (
                              <Button
                                variant="ghost" size="icon"
                                onClick={() => handleResend(inv.id)}
                                disabled={resendingId === inv.id}
                                title="Resend (invalidates old link)"
                                data-testid={`resend-btn-${inv.id}`}
                              >
                                {resendingId === inv.id ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                              </Button>
                            )}
                            {inv.token && !inv.used && (
                              <Button variant="ghost" size="icon" onClick={() => copyLink(inv.token)} title="Copy link" data-testid={`copy-link-${inv.id}`}>
                                {copiedId === inv.token ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
                              </Button>
                            )}
                            {canCancel && (
                              <Button variant="ghost" size="icon" onClick={() => handleCancel(inv.id)} className="text-destructive" title="Cancel invitation" data-testid={`cancel-btn-${inv.id}`}>
                                <XCircle className="h-4 w-4" />
                              </Button>
                            )}
                            {(inv.status === "cancelled" || inv.status === "accepted") && (
                              <Button variant="ghost" size="icon" onClick={() => handleDelete(inv.id)} className="text-muted-foreground" title="Remove" data-testid={`delete-btn-${inv.id}`}>
                                <XCircle className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </Card>
        )}

        {/* Send Invitation Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-heading flex items-center gap-2">
                <UserPlus className="h-5 w-5" />
                Send Invitation
              </DialogTitle>
              <DialogDescription>
                Invite an owner or staff member. An email will be sent with a secure registration link.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-2">
              {/* Role */}
              <div className="space-y-2">
                <Label>Role *</Label>
                <Select value={form.role} onValueChange={(v) => setForm(prev => ({ ...prev, role: v, selectedPerson: "" }))}>
                  <SelectTrigger data-testid="invite-role-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="owner">Owner (Property Owner)</SelectItem>
                    <SelectItem value="staff">Staff</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Person Picker (from existing records) */}
              <div className="space-y-2">
                <Label>Select {form.role === "staff" ? "Staff Member" : "Property Owner"}</Label>
                <Select value={form.selectedPerson} onValueChange={v => setForm(prev => ({ ...prev, selectedPerson: v }))}>
                  <SelectTrigger data-testid="invite-person-select"><SelectValue placeholder={`Pick a ${form.role}...`} /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Enter details manually</SelectItem>
                    {people.map(p => (
                      <SelectItem key={p.id} value={p.id}>
                        <span>{p.name}</span>
                        <span className="text-xs text-muted-foreground ml-2">{p.email}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Name & Email */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Full Name</Label>
                  <Input
                    data-testid="invite-name-input"
                    value={form.selectedPerson && form.selectedPerson !== "manual" ? (people.find(p => p.id === form.selectedPerson)?.name || "") : form.name}
                    onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="John Doe"
                    disabled={form.selectedPerson && form.selectedPerson !== "manual"}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Email Address *</Label>
                  <Input
                    data-testid="invite-email-input"
                    type="email"
                    value={form.selectedPerson && form.selectedPerson !== "manual" ? resolvedEmail : form.manualEmail}
                    onChange={e => setForm(prev => ({ ...prev, manualEmail: e.target.value }))}
                    placeholder="user@example.com"
                    disabled={form.selectedPerson && form.selectedPerson !== "manual"}
                  />
                </div>
              </div>

              {/* Assign Properties */}
              <div className="space-y-2">
                <Label>Assign Properties</Label>
                <div className="border rounded-lg p-3 max-h-[140px] overflow-y-auto space-y-2" data-testid="invite-properties-list">
                  {properties.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No properties yet</p>
                  ) : properties.map(p => (
                    <div key={p.id} className="flex items-center gap-2">
                      <Checkbox
                        id={`prop-${p.id}`}
                        checked={form.assignedProperties.includes(p.id)}
                        onCheckedChange={() => toggleProperty(p.id)}
                        data-testid={`assign-prop-${p.id}`}
                      />
                      <label htmlFor={`prop-${p.id}`} className="text-sm cursor-pointer flex-1">{p.name}</label>
                    </div>
                  ))}
                </div>
                {form.assignedProperties.length === 0 && (
                  <p className="text-xs text-muted-foreground">Leave empty to grant access to all properties</p>
                )}
              </div>

              {/* Staff Permissions */}
              {form.role === "staff" && (
                <div className="space-y-2">
                  <Label>Permissions</Label>
                  <div className="border rounded-lg p-3 space-y-2" data-testid="invite-permissions">
                    {[
                      { key: "view_financials", label: "View Financial Data" },
                      { key: "manage_bookings", label: "Manage Bookings" },
                      { key: "manage_tasks", label: "Manage Tasks" },
                    ].map(perm => (
                      <div key={perm.key} className="flex items-center gap-2">
                        <Checkbox
                          id={`perm-${perm.key}`}
                          checked={form.permissions[perm.key] || false}
                          onCheckedChange={() => togglePermission(perm.key)}
                          data-testid={`perm-${perm.key}`}
                        />
                        <label htmlFor={`perm-${perm.key}`} className="text-sm cursor-pointer">{perm.label}</label>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Info */}
              <div className="flex items-start gap-2 bg-blue-500/5 rounded-lg p-3 border border-blue-500/10">
                <Mail className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                <p className="text-xs text-muted-foreground">
                  A secure invitation email will be sent with a registration link that expires in 48 hours. Resending invalidates previous links.
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={!resolvedEmail || saving} data-testid="confirm-send-invitation-btn">
                <Send className="mr-2 h-4 w-4" />
                {saving ? "Sending..." : "Send Invitation"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
