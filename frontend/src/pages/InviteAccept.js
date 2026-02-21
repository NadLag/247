import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, Building2, UserCheck } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

export default function InviteAccept() {
  const { token } = useParams();
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [invitation, setInvitation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (user) { navigate("/dashboard"); return; }
    const validate = async () => {
      try {
        const res = await fetch(`${API}/api/invitations/validate/${token}`);
        if (res.ok) {
          setInvitation(await res.json());
        } else {
          const err = await res.json();
          setError(err.detail || "Invalid invitation");
        }
      } catch (err) {
        setError("Failed to validate invitation");
      } finally {
        setLoading(false);
      }
    };
    validate();
  }, [token, user, navigate]);

  const handleAccept = () => {
    login(token);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md" data-testid="invite-accept-card">
        {error ? (
          <CardContent className="p-8 text-center space-y-4">
            <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center mx-auto">
              <span className="text-destructive text-xl">!</span>
            </div>
            <h2 className="font-heading text-xl font-bold">Invalid Invitation</h2>
            <p className="text-sm text-muted-foreground">{error}</p>
            <Button variant="outline" onClick={() => navigate("/")} data-testid="back-to-home-btn">Back to Home</Button>
          </CardContent>
        ) : invitation && (
          <>
            <CardHeader className="text-center pb-2">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-2">
                <UserCheck className="h-6 w-6 text-primary" />
              </div>
              <CardTitle className="font-heading text-xl">You're Invited!</CardTitle>
              <CardDescription>You've been invited to join an organization on PropStack</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="bg-muted rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Organization</span>
                  <span className="font-medium flex items-center gap-1.5"><Building2 className="h-4 w-4" />{invitation.company_name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Role</span>
                  <Badge variant="outline" className="capitalize">{invitation.role}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Email</span>
                  <span className="text-sm">{invitation.email}</span>
                </div>
              </div>
              <Button className="w-full h-11" onClick={handleAccept} data-testid="accept-invite-btn">
                Accept & Sign in with Google
              </Button>
              <p className="text-xs text-center text-muted-foreground">
                By accepting, you'll join {invitation.company_name} as a {invitation.role}.
              </p>
            </CardContent>
          </>
        )}
      </Card>
    </div>
  );
}
