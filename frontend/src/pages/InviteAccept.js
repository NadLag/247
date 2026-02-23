import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Eye, EyeOff, Building2, Shield, AlertTriangle, CheckCircle, Loader2 } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

export default function InviteAccept() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { user, checkAuth } = useAuth();
  
  const [invitation, setInvitation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [registering, setRegistering] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [acceptTerms, setAcceptTerms] = useState(false);
  
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    password: "",
    confirm_password: "",
  });

  useEffect(() => {
    const validateToken = async () => {
      try {
        const res = await fetch(`${API}/api/invitations/validate/${token}`);
        if (res.ok) {
          const data = await res.json();
          setInvitation(data);
          // Pre-fill form with data from invitation
          setForm(prev => ({
            ...prev,
            first_name: data.first_name || "",
            last_name: data.last_name || "",
            phone: data.phone || "",
          }));
        } else {
          const err = await res.json();
          setError(err.detail || "Invalid invitation link");
        }
      } catch (err) {
        setError("Failed to validate invitation. Please check the link and try again.");
      } finally {
        setLoading(false);
      }
    };
    validateToken();
  }, [token]);

  // If already logged in and invitation is valid, redirect
  useEffect(() => {
    if (user && invitation && !invitation.used) {
      navigate("/dashboard");
    }
  }, [user, invitation, navigate]);

  const handleGoogleAuth = () => {
    // Store invitation token in sessionStorage so it persists through OAuth redirect
    sessionStorage.setItem("invitation_token", token);
    // Use the standard Emergent Auth flow - token will be retrieved in AuthCallback
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const handlePasswordRegister = async (e) => {
    e.preventDefault();
    
    if (!form.first_name.trim()) {
      toast.error("First name is required");
      return;
    }
    if (form.password.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }
    if (form.password !== form.confirm_password) {
      toast.error("Passwords do not match");
      return;
    }
    if (!acceptTerms) {
      toast.error("Please accept the terms and conditions");
      return;
    }
    
    setRegistering(true);
    try {
      const res = await fetch(`${API}/api/auth/register-with-invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          token,
          first_name: form.first_name.trim(),
          last_name: form.last_name.trim(),
          email: invitation.email,
          phone: form.phone.trim(),
          password: form.password,
        }),
      });
      
      if (res.ok) {
        toast.success("Account created successfully! Redirecting...");
        await checkAuth();
        navigate("/dashboard");
      } else {
        const err = await res.json();
        toast.error(err.detail || "Registration failed. Please try again.");
      }
    } catch (err) {
      toast.error("Registration failed. Please check your connection and try again.");
    } finally {
      setRegistering(false);
    }
  };

  const set = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/30 flex items-center justify-center p-4">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Validating invitation...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/30 flex items-center justify-center p-4">
        <Card className="max-w-md w-full" data-testid="invite-error">
          <CardContent className="p-8 text-center space-y-4">
            <AlertTriangle className="h-12 w-12 mx-auto text-red-500" />
            <div>
              <h2 className="text-lg font-semibold text-foreground">Invalid Invitation</h2>
              <p className="text-sm text-muted-foreground mt-2">{error}</p>
            </div>
            <div className="space-y-2 text-xs text-muted-foreground">
              <p>This could happen because:</p>
              <ul className="list-disc text-left pl-4 space-y-1">
                <li>The invitation link has expired (48-hour validity)</li>
                <li>The invitation was cancelled by admin</li>
                <li>A new invitation was sent (old link invalidated)</li>
                <li>The link was already used to register</li>
              </ul>
            </div>
            <Button onClick={() => navigate("/")} variant="outline">Go to Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (invitation?.used) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/30 flex items-center justify-center p-4">
        <Card className="max-w-md w-full" data-testid="invite-already-used">
          <CardContent className="p-8 text-center space-y-4">
            <CheckCircle className="h-12 w-12 mx-auto text-emerald-500" />
            <div>
              <h2 className="text-lg font-semibold text-foreground">Already Registered</h2>
              <p className="text-sm text-muted-foreground mt-2">This invitation has already been accepted. You can sign in with your credentials.</p>
            </div>
            <Button onClick={() => navigate("/")} data-testid="go-to-login-btn">Sign In</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/30 flex items-center justify-center p-4">
      <Card className="max-w-md w-full shadow-lg" data-testid="invite-accept-card">
        <CardHeader className="space-y-2 text-center pb-3">
          <div className="flex justify-center">
            <Badge variant="outline" className="text-primary border-primary/30">
              {invitation?.role === "owner" ? <Building2 className="h-3 w-3 mr-1" /> : <Shield className="h-3 w-3 mr-1" />}
              {invitation?.role === "owner" ? "Property Owner" : "Staff Member"}
            </Badge>
          </div>
          <CardTitle className="font-heading text-xl">Join {invitation?.company_name}</CardTitle>
          <CardDescription>
            You've been invited as a <strong className="text-foreground">{invitation?.role === "owner" ? "Property Owner" : "Staff Member"}</strong>.
            Create your account to get started.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Invitation for</p>
            <p className="text-sm font-medium">{invitation?.email}</p>
          </div>

          <Separator />

          {/* Google Auth Option */}
          <Button variant="outline" className="w-full" onClick={handleGoogleAuth} data-testid="google-register-btn">
            <svg className="h-4 w-4 mr-2" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
            Continue with Google
          </Button>

          <div className="relative"><div className="absolute inset-0 flex items-center"><Separator /></div><div className="relative flex justify-center text-xs uppercase"><span className="bg-card px-2 text-muted-foreground">or create password</span></div></div>

          {/* Password Registration Form */}
          <form onSubmit={handlePasswordRegister} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">First Name *</Label>
                <Input data-testid="register-firstname" value={form.first_name} onChange={e => set("first_name", e.target.value)} placeholder="John" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Last Name</Label>
                <Input data-testid="register-lastname" value={form.last_name} onChange={e => set("last_name", e.target.value)} placeholder="Doe" />
              </div>
            </div>
            
            <div className="space-y-1">
              <Label className="text-xs">Phone</Label>
              <Input data-testid="register-phone" value={form.phone} onChange={e => set("phone", e.target.value)} placeholder="+1 234 567 8900" />
            </div>
            
            <div className="space-y-1">
              <Label className="text-xs">Password *</Label>
              <div className="relative">
                <Input data-testid="register-password" type={showPassword ? "text" : "password"} value={form.password} onChange={e => set("password", e.target.value)} placeholder="Min 8 characters" />
                <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" onClick={() => setShowPassword(!showPassword)}>
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            
            <div className="space-y-1">
              <Label className="text-xs">Confirm Password *</Label>
              <Input data-testid="register-confirm-password" type="password" value={form.confirm_password} onChange={e => set("confirm_password", e.target.value)} placeholder="Re-enter password" />
            </div>
            
            <div className="flex items-start gap-2 pt-1">
              <Checkbox id="terms" checked={acceptTerms} onCheckedChange={setAcceptTerms} data-testid="accept-terms" />
              <label htmlFor="terms" className="text-xs text-muted-foreground cursor-pointer leading-relaxed">
                I accept the Terms of Service and Privacy Policy
              </label>
            </div>
            
            <Button type="submit" className="w-full" disabled={registering} data-testid="register-submit-btn">
              {registering ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Creating Account...</> : "Create Account"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
