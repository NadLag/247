import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Plus, Trash2, RefreshCw, Link2, CheckCircle, XCircle, Clock, Building2 } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const OTA_SOURCES = [
  { value: "airbnb", label: "Airbnb" },
  { value: "booking.com", label: "Booking.com" },
  { value: "vrbo", label: "VRBO" },
  { value: "expedia", label: "Expedia" },
  { value: "other", label: "Other" },
];

const emptyFeed = {
  property_id: "",
  source: "",
  ical_url: "",
  name: "",
};

export default function OTASettings() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [feeds, setFeeds] = useState([]);
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState(emptyFeed);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) navigate("/");
    if (!authLoading && user?.role !== "company_admin") navigate("/dashboard");
  }, [user, authLoading, navigate]);

  const fetchData = async () => {
    try {
      const [feedsRes, propsRes] = await Promise.all([
        fetch(`${API}/api/ota/feeds`, { credentials: "include" }),
        fetch(`${API}/api/properties`, { credentials: "include" }),
      ]);
      if (feedsRes.ok) setFeeds(await feedsRes.json());
      if (propsRes.ok) setProperties(await propsRes.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.company_id) fetchData();
  }, [user]); // eslint-disable-line

  const handleSave = async () => {
    if (!form.property_id || !form.source || !form.ical_url) {
      toast.error("Please fill in all required fields");
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${API}/api/ota/feeds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(form),
      });

      if (res.ok) {
        toast.success("OTA feed added successfully");
        setDialogOpen(false);
        setForm(emptyFeed);
        fetchData();
      } else {
        const err = await res.json();
        toast.error(err.detail || "Failed to add feed");
      }
    } catch (err) {
      toast.error("Error adding feed");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (feedId) => {
    if (!window.confirm("Remove this OTA feed?")) return;

    try {
      const res = await fetch(`${API}/api/ota/feeds/${feedId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (res.ok) {
        toast.success("Feed removed");
        fetchData();
      } else {
        toast.error("Failed to remove feed");
      }
    } catch (err) {
      toast.error("Error removing feed");
    }
  };

  const handleToggleActive = async (feed) => {
    try {
      const res = await fetch(`${API}/api/ota/feeds/${feed.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ active: !feed.active }),
      });
      if (res.ok) {
        fetchData();
        toast.success(feed.active ? "Feed disabled" : "Feed enabled");
      }
    } catch (err) {
      toast.error("Failed to update feed");
    }
  };

  const generateMockUrl = () => {
    if (!form.property_id || !form.source) {
      toast.error("Select a property and source first");
      return;
    }
    const prop = properties.find((p) => p.id === form.property_id);
    const propName = prop?.name?.replace(/\s+/g, "_") || "Property";
    setForm((prev) => ({
      ...prev,
      ical_url: `mock://${form.source}/${propName}`,
    }));
    toast.info("Mock URL generated for testing");
  };

  const set = (k, v) => setForm((p) => ({ ...p, [k]: v }));

  if (authLoading || !user) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  const getStatusBadge = (feed) => {
    if (!feed.last_sync_status) {
      return <Badge variant="outline"><Clock className="h-3 w-3 mr-1" />Never synced</Badge>;
    }
    if (feed.last_sync_status === "success") {
      return <Badge variant="default" className="bg-emerald-500"><CheckCircle className="h-3 w-3 mr-1" />Success</Badge>;
    }
    return <Badge variant="destructive"><XCircle className="h-3 w-3 mr-1" />Error</Badge>;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleString();
  };

  return (
    <Layout>
      <div className="space-y-6 max-w-[1200px] mx-auto" data-testid="ota-settings-page">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold">OTA Settings</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Configure iCal feeds from Airbnb, Booking.com, VRBO, and other OTAs
            </p>
          </div>
          <Button onClick={() => { setForm(emptyFeed); setDialogOpen(true); }} data-testid="add-feed-btn">
            <Plus className="mr-2 h-4 w-4" /> Add OTA Feed
          </Button>
        </div>

        {/* Info Card */}
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <Link2 className="h-5 w-5 text-primary mt-0.5 shrink-0" />
              <div className="text-sm">
                <p className="font-medium text-foreground">How iCal Sync Works</p>
                <p className="text-muted-foreground mt-1">
                  Add iCal URLs from your OTA platforms. When you click "Sync from OTA" on the Properties page,
                  the system will fetch all calendar data and automatically create or update bookings.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Feeds Table */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Configured Feeds</CardTitle>
            <CardDescription>{feeds.length} feed(s) configured</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="h-32 flex items-center justify-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
              </div>
            ) : feeds.length === 0 ? (
              <div className="text-center py-12 border-2 border-dashed rounded-lg">
                <RefreshCw className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                <h3 className="font-semibold mb-1">No OTA feeds configured</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Add iCal URLs from your OTA platforms to enable sync
                </p>
                <Button onClick={() => setDialogOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" /> Add First Feed
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Property</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Sync</TableHead>
                    <TableHead>Active</TableHead>
                    <TableHead className="w-[80px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {feeds.map((feed) => (
                    <TableRow key={feed.id} data-testid={`feed-row-${feed.id}`}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Building2 className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{feed.property_name}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">
                          {feed.source}
                        </Badge>
                      </TableCell>
                      <TableCell>{getStatusBadge(feed)}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(feed.last_sync_at)}
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={feed.active}
                          onCheckedChange={() => handleToggleActive(feed)}
                          data-testid={`toggle-feed-${feed.id}`}
                        />
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                          onClick={() => handleDelete(feed.id)}
                          data-testid={`delete-feed-${feed.id}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Add Feed Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-heading">Add OTA Feed</DialogTitle>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label>Property *</Label>
                <Select value={form.property_id} onValueChange={(v) => set("property_id", v)}>
                  <SelectTrigger data-testid="feed-property-select">
                    <SelectValue placeholder="Select property..." />
                  </SelectTrigger>
                  <SelectContent>
                    {properties.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>OTA Source *</Label>
                <Select value={form.source} onValueChange={(v) => set("source", v)}>
                  <SelectTrigger data-testid="feed-source-select">
                    <SelectValue placeholder="Select OTA..." />
                  </SelectTrigger>
                  <SelectContent>
                    {OTA_SOURCES.map((s) => (
                      <SelectItem key={s.value} value={s.value}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>iCal URL *</Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={generateMockUrl}
                  >
                    Generate Mock URL
                  </Button>
                </div>
                <Input
                  value={form.ical_url}
                  onChange={(e) => set("ical_url", e.target.value)}
                  placeholder="https://www.airbnb.com/calendar/ical/..."
                  data-testid="feed-url-input"
                />
                <p className="text-xs text-muted-foreground">
                  Find the iCal export URL in your OTA platform settings
                </p>
              </div>

              <div className="space-y-2">
                <Label>Display Name (optional)</Label>
                <Input
                  value={form.name}
                  onChange={(e) => set("name", e.target.value)}
                  placeholder="e.g., Beach House - Airbnb"
                  data-testid="feed-name-input"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={saving} data-testid="save-feed-btn">
                {saving ? "Saving..." : "Add Feed"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
