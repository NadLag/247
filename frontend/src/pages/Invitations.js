import { useState, useEffect } from "react";
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
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("staff");
  const [saving, setSaving] = useState(false);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);
  useEffect(() => { if (!authLoading && user && user.role !== "company_admin") navigate("/dashboard"); }, [user, authLoading, navigate]);

  const fetchInvitations = async () => {
    try {
      const res = await fetch(`${API}/api/invitations`, { credentials: "include" });
      if (res.ok) setInvitations(await res.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  useEffect(() => { if (user?.company_id) fetchInvitations(); }, [user]);

  const handleCreate = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/invitations`, {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify({ email, role }),
      });
      if (res.ok) {
        toast.success("Invitation created");
        setDialogOpen(false); setEmail(""); setRole("staff"); fetchInvitations();
      } else { const err = await res.json(); toast.error(err.detail || "Failed"); }
    } catch (err) { toast.error("Error"); } finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`${API}/api/invitations/${id}`, { method: "DELETE", credentials: "include" });
      if (res.ok) { toast.success("Invitation deleted"); fetchInvitations(); }
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
          <Button onClick={() => setDialogOpen(true)} data-testid="create-invitation-btn"><Plus className="mr-2 h-4 w-4" />Send Invitation</Button>
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
              <DialogDescription>The invited user will receive a link to join your organization.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-2">
              <div className="space-y-2"><Label>Email</Label><Input data-testid="invite-email-input" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="user@example.com" /></div>
              <div className="space-y-2">
                <Label>Role</Label>
                <Select value={role} onValueChange={setRole}>
                  <SelectTrigger data-testid="invite-role-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="owner">Owner (View Only)</SelectItem>
                    <SelectItem value="staff">Staff</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={!email.trim() || saving} data-testid="send-invitation-btn">{saving ? "Sending..." : "Send Invitation"}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
