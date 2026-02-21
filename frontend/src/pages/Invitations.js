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
import { toast } from "sonner";
import { Plus, Trash2, Mail, Copy, Check } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

export default function Invitations() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [invitations, setInvitations] = useState([]);
  const [staff, setStaff] = useState([]);
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [role, setRole] = useState("staff");
  const [selectedPerson, setSelectedPerson] = useState("");
  const [manualEmail, setManualEmail] = useState("");
  const [saving, setSaving] = useState(false);
  const [copiedId, setCopiedId] = useState(null);

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
          map.set(key, { email: p.owner_email, name: `${p.owner_first_name} ${p.owner_last_name}`, properties: [p.name] });
        } else {
          map.get(key).properties.push(p.name);
        }
      }
    });
    return Array.from(map.values());
  }, [properties]);

  // People list based on role
  const people = useMemo(() => {
    if (role === "staff") {
      return staff.map(s => ({ id: s.id, name: `${s.first_name} ${s.last_name}`, email: s.email, detail: s.staff_role?.replace("_", " ") || "" }));
    }
    return owners.map((o, i) => ({ id: `owner_${i}`, name: o.name, email: o.email, detail: o.properties.join(", ") }));
  }, [role, staff, owners]);

  const resolvedEmail = useMemo(() => {
    if (selectedPerson && selectedPerson !== "manual") {
      const person = people.find(p => p.id === selectedPerson);
      return person?.email || "";
    }
    return manualEmail;
  }, [selectedPerson, manualEmail, people]);

  const handleCreate = async () => {
    if (!resolvedEmail) { toast.error("Email is required"); return; }
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/invitations`, {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify({ email: resolvedEmail, role }),
      });
      if (res.ok) {
        toast.success("Invitation created");
        setDialogOpen(false); setSelectedPerson(""); setManualEmail(""); setRole("staff"); fetchData();
      } else { const err = await res.json(); toast.error(err.detail || "Failed"); }
    } catch (err) { toast.error("Error"); } finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`${API}/api/invitations/${id}`, { method: "DELETE", credentials: "include" });
      if (res.ok) { toast.success("Invitation deleted"); fetchData(); }
    } catch (err) { toast.error("Error"); }
  };

  const copyLink = (token) => {
    const link = `${window.location.origin}/invite/${token}`;
    navigator.clipboard.writeText(link);
    setCopiedId(token);
    toast.success("Link copied!");
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;

  return (
    <Layout>
      <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="invitations-page">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold">Invitations</h1>
            <p className="text-sm text-muted-foreground mt-1">Invite owners and staff to your organization</p>
          </div>
          <Button onClick={() => { setSelectedPerson(""); setManualEmail(""); setRole("staff"); setDialogOpen(true); }} data-testid="create-invitation-btn"><Plus className="mr-2 h-4 w-4" />Send Invitation</Button>
        </div>

        {loading ? (
          <Card><CardContent className="p-6 h-32 animate-pulse bg-muted" /></Card>
        ) : invitations.length === 0 ? (
          <Card className="border-dashed"><CardContent className="p-12 text-center">
            <Mail className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No invitations sent yet</p>
          </CardContent></Card>
        ) : (
          <Card>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invitations.map((inv) => (
                    <TableRow key={inv.id} data-testid={`invitation-row-${inv.id}`}>
                      <TableCell className="font-medium">{inv.email}</TableCell>
                      <TableCell><Badge variant="outline" className="capitalize">{inv.role}</Badge></TableCell>
                      <TableCell>
                        {inv.used ? (
                          <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-0">Accepted</Badge>
                        ) : (
                          <Badge variant="secondary">Pending</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{inv.created_at?.slice(0, 10)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          {!inv.used && (
                            <Button variant="ghost" size="icon" onClick={() => copyLink(inv.token)} data-testid={`copy-link-${inv.id}`}>
                              {copiedId === inv.token ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
                            </Button>
                          )}
                          <Button variant="ghost" size="icon" onClick={() => handleDelete(inv.id)} className="text-destructive" data-testid={`delete-invitation-${inv.id}`}><Trash2 className="h-4 w-4" /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>
        )}

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="font-heading">Send Invitation</DialogTitle>
              <DialogDescription>Pick a staff member or owner from your existing records, or enter an email manually.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-2">
              {/* Role */}
              <div className="space-y-2">
                <Label>Role</Label>
                <Select value={role} onValueChange={(v) => { setRole(v); setSelectedPerson(""); }}>
                  <SelectTrigger data-testid="invite-role-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="owner">Owner (View Only)</SelectItem>
                    <SelectItem value="staff">Staff</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {/* Person Picker */}
              <div className="space-y-2">
                <Label>Select {role === "staff" ? "Staff Member" : "Property Owner"}</Label>
                <Select value={selectedPerson} onValueChange={setSelectedPerson}>
                  <SelectTrigger data-testid="invite-person-select"><SelectValue placeholder={`Pick a ${role}...`} /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Enter email manually</SelectItem>
                    {people.map(p => (
                      <SelectItem key={p.id} value={p.id}>
                        <div className="flex flex-col">
                          <span>{p.name}</span>
                          <span className="text-xs text-muted-foreground">{p.email}{p.detail ? ` - ${p.detail}` : ""}</span>
                        </div>
                      </SelectItem>
                    ))}
                    {people.length === 0 && (
                      <SelectItem value="manual" disabled>
                        No {role === "staff" ? "staff members" : "property owners"} found
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>
              {/* Manual email or resolved display */}
              {selectedPerson === "manual" ? (
                <div className="space-y-2">
                  <Label>Email Address</Label>
                  <Input data-testid="invite-email-input" type="email" value={manualEmail} onChange={e => setManualEmail(e.target.value)} placeholder="user@example.com" />
                </div>
              ) : selectedPerson ? (
                <div className="bg-muted/50 rounded-lg p-3 border">
                  <p className="text-sm"><span className="font-medium">Will send to:</span> {resolvedEmail}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {people.find(p => p.id === selectedPerson)?.name} — {people.find(p => p.id === selectedPerson)?.detail}
                  </p>
                </div>
              ) : null}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={!resolvedEmail || saving} data-testid="send-invitation-btn">
                {saving ? "Sending..." : "Send Invitation"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
