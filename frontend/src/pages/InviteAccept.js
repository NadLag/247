import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { Building2, Mail, Lock, User, Phone, Loader2, CheckCircle, XCircle, Shield, Eye, EyeOff } from "lucide-react";

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
    email: "",
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
          // Pre-fill all user info from invitation (read-only fields)
          setForm(prev => ({
            ...prev,
            email: data.email || "",
            first_name: data.first_name || "",
            last_name: data.last_name || "",
            phone: data.phone || "",
          }));
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
    validateToken();
  }, [token]);

  // If already logged in and invitation is valid, show option to link account
  useEffect(() => {
    if (user && invitation && !invitation.used) {
      // User already logged in via Google - could auto-accept
      navigate("/dashboard");
    }
  }, [user, invitation, navigate]);

  const handleGoogleAuth = () => {
    // Redirect to Google OAuth with invitation token
    window.location.href = `${API}/api/auth/google?invitation_token=${token}`;
  };

  const handlePasswordRegister = async (e) => {
    e.preventDefault();
    
    if (form.password !== form.confirm_password) {
      toast.error("Passwords do not match");
      return;
    }
    
    if (form.password.length < 8) {
      toast.error("Password must be at least 8 characters");
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
          first_name: form.first_name,
          last_name: form.last_name,
          email: form.email,
          phone: form.phone,
          password: form.password,
        }),
      });
      
      if (res.ok) {
        toast.success("Account created successfully!");
        await checkAuth();
        navigate("/dashboard");
      } else {
        const err = await res.json();
        toast.error(err.detail || "Registration failed");
      }
    } catch (err) {
      toast.error("Registration failed");
    } finally {
      setRegistering(false);
    }
  };

  const set = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/30 flex items-center justify-center p-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error || !invitation) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/30 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="p-8 text-center">
            <XCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
            <h2 className="font-heading text-xl font-semibold mb-2">Invalid Invitation</h2>
            <p className="text-muted-foreground mb-6">{error || "This invitation link is invalid or has expired."}</p>
            <Button onClick={() => navigate("/")} variant="outline">Go to Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (invitation.used) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/30 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="p-8 text-center">
            <CheckCircle className="h-12 w-12 mx-auto text-emerald-500 mb-4" />
            <h2 className="font-heading text-xl font-semibold mb-2">Invitation Already Used</h2>
            <p className="text-muted-foreground mb-6">This invitation has already been accepted. Please sign in.</p>
            <Button onClick={() => navigate("/")} data-testid="go-signin-btn">Sign In</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const roleDisplay = invitation.role === "owner" ? "Property Owner" : "Staff Member";

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/30 flex items-center justify-center p-4">
      <Card className="w-full max-w-lg" data-testid="invite-register-card">
        <CardHeader className="text-center pb-2">
          <div className="flex justify-center mb-4">
            <div className="h-14 w-14 rounded-xl bg-primary/10 flex items-center justify-center">
              <Building2 className="h-7 w-7 text-primary" />
            </div>
          </div>
          <CardTitle className="font-heading text-2xl">Join PropStack</CardTitle>
          <CardDescription className="mt-2">
            You've been invited to join as a <Badge variant="secondary" className="ml-1">{roleDisplay}</Badge>
          </CardDescription>
        </CardHeader>
        
        <CardContent className="p-6 pt-2">
          {/* Invitation Details */}
          <div className="bg-muted/50 rounded-lg p-4 mb-6 border">
            <div className="flex items-center gap-3">
              <Mail className="h-5 w-5 text-muted-foreground shrink-0" />
              <div>
                <p className="text-sm font-medium">Invitation for</p>
                <p className="text-sm text-muted-foreground">{invitation.email}</p>
              </div>
            </div>
          </div>

          {/* Google Auth Option */}
          <Button 
            variant="outline" 
            className="w-full h-12 text-base gap-3" 
            onClick={handleGoogleAuth}
            data-testid="google-register-btn"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </Button>

          <div className="relative my-6">
            <Separator />
            <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-background px-3 text-xs text-muted-foreground">
              or register with email
            </span>
          </div>

          {/* Registration Form */}
          <form onSubmit={handlePasswordRegister} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="first_name">First Name *</Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input 
                    id="first_name"
                    value={form.first_name}
                    onChange={e => set("first_name", e.target.value)}
                    className="pl-10"
                    placeholder="John"
                    required
                    data-testid="register-firstname"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="last_name">Last Name *</Label>
                <Input 
                  id="last_name"
                  value={form.last_name}
                  onChange={e => set("last_name", e.target.value)}
                  placeholder="Doe"
                  required
                  data-testid="register-lastname"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email *</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={e => set("email", e.target.value)}
                  className="pl-10"
                  placeholder="john@example.com"
                  required
                  disabled
                  data-testid="register-email"
                />
              </div>
              <p className="text-xs text-muted-foreground">Email is set from your invitation</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Phone Number *</Label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  id="phone"
                  type="tel"
                  value={form.phone}
                  onChange={e => set("phone", e.target.value)}
                  className="pl-10"
                  placeholder="+1 (555) 000-0000"
                  required
                  data-testid="register-phone"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password *</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={form.password}
                  onChange={e => set("password", e.target.value)}
                  className="pl-10 pr-10"
                  placeholder="Min. 8 characters"
                  required
                  minLength={8}
                  data-testid="register-password"
                />
                <button 
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm_password">Confirm Password *</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  id="confirm_password"
                  type={showPassword ? "text" : "password"}
                  value={form.confirm_password}
                  onChange={e => set("confirm_password", e.target.value)}
                  className="pl-10"
                  placeholder="Repeat password"
                  required
                  data-testid="register-confirm-password"
                />
              </div>
            </div>

            <div className="flex items-start gap-3 pt-2">
              <Checkbox 
                id="terms" 
                checked={acceptTerms}
                onCheckedChange={setAcceptTerms}
                data-testid="accept-terms"
              />
              <label htmlFor="terms" className="text-sm text-muted-foreground leading-snug cursor-pointer">
                I accept the <a href="#" className="text-primary underline">Terms of Service</a> and <a href="#" className="text-primary underline">Privacy Policy</a>
              </label>
            </div>

            <Button 
              type="submit" 
              className="w-full h-12 text-base"
              disabled={registering || !acceptTerms}
              data-testid="register-submit-btn"
            >
              {registering ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating Account...</>
              ) : (
                <><Shield className="mr-2 h-4 w-4" /> Create Account</>
              )}
            </Button>
          </form>

          <p className="text-xs text-center text-muted-foreground mt-6">
            Already have an account? <a href="/" className="text-primary underline">Sign in</a>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
