import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { toast } from "sonner";
import { User, Building2, Shield, Mail } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

export default function Settings() {
  const { user, logout, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [company, setCompany] = useState(null);

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  useEffect(() => {
    if (!user?.company_id) return;
    fetch(`${API}/api/companies/me`, { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setCompany(data); })
      .catch(console.error);
  }, [user]);

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;

  return (
    <Layout>
      <div className="space-y-6 max-w-[800px] mx-auto" data-testid="settings-page">
        <div>
          <h1 className="font-heading text-2xl font-bold">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage your account and preferences</p>
        </div>

        {/* Profile */}
        <Card data-testid="profile-card">
          <CardHeader><CardTitle className="font-heading text-base flex items-center gap-2"><User className="h-4 w-4" />Profile</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16">
                <AvatarImage src={user.picture} alt={user.name} />
                <AvatarFallback className="text-lg">{user.name?.[0]}</AvatarFallback>
              </Avatar>
              <div>
                <h3 className="font-heading font-semibold text-lg">{user.name}</h3>
                <p className="text-sm text-muted-foreground flex items-center gap-1"><Mail className="h-3.5 w-3.5" />{user.email}</p>
              </div>
            </div>
            <Separator />
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Role</p>
                <Badge variant="outline" className="mt-1 capitalize">{user.role?.replace("_", " ") || "No role"}</Badge>
              </div>
              <div>
                <p className="text-muted-foreground">User ID</p>
                <p className="font-data text-xs mt-1">{user.user_id}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Company */}
        {company && (
          <Card data-testid="company-card">
            <CardHeader><CardTitle className="font-heading text-base flex items-center gap-2"><Building2 className="h-4 w-4" />Company</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Name</p>
                  <p className="font-medium mt-1">{company.name}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Subscription</p>
                  <Badge variant={company.subscription_status === "active" ? "default" : "secondary"} className="mt-1 capitalize">
                    {company.subscription_status} {company.subscription_plan ? `(${company.subscription_plan})` : ""}
                  </Badge>
                </div>
                <div>
                  <p className="text-muted-foreground">Company ID</p>
                  <p className="font-data text-xs mt-1">{company.company_id}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Created</p>
                  <p className="text-xs mt-1">{company.created_at?.slice(0, 10)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Security */}
        <Card data-testid="security-card">
          <CardHeader><CardTitle className="font-heading text-base flex items-center gap-2"><Shield className="h-4 w-4" />Security</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">Authentication is managed via Google OAuth. Your session expires after 7 days.</p>
            <Button variant="destructive" onClick={logout} data-testid="logout-btn">Sign Out</Button>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
