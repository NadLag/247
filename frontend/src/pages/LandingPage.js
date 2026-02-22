import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { Building2, DollarSign, Users, BarChart3, Shield, Zap, Mail, Lock, Loader2, Eye, EyeOff } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;
const HERO_IMAGE = "https://images.unsplash.com/photo-1768223933860-6d62bc5b2ff3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NTN8MHwxfHNlYXJjaHwyfHxtb2Rlcm4lMjBsdXh1cnklMjBob3RlbCUyMGFyY2hpdGVjdHVyZSUyMG1pbmltYWxpc3R8ZW58MHx8fHwxNzcxNjk1Mzc4fDA&ixlib=rb-4.1.0&q=85";

const features = [
  { icon: DollarSign, title: "Revenue Tracking", description: "Real-time revenue monitoring with MTD comparisons and trend analysis across all properties." },
  { icon: Building2, title: "Property Management", description: "Centralized control over all your properties with owner details, units, and activity status." },
  { icon: Users, title: "Staff Operations", description: "Manage staff assignments, track salaries, and handle payroll across your portfolio." },
  { icon: BarChart3, title: "Performance Analytics", description: "KPIs including ADR, RevPAN, occupancy rates, and net income at your fingertips." },
  { icon: Shield, title: "Role-Based Access", description: "Granular permissions for admins, property owners, and staff with secure isolation." },
  { icon: Zap, title: "Expense Control", description: "Track fixed and variable expenses per property with recurring payment automation." },
];

export default function LandingPage() {
  const { login, user, loading, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [showLogin, setShowLogin] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loggingIn, setLoggingIn] = useState(false);

  useEffect(() => {
    if (user) navigate("/dashboard");
  }, [user, navigate]);

  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    if (!email || !password) return;
    
    setLoggingIn(true);
    try {
      const res = await fetch(`${API}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      
      if (res.ok) {
        toast.success("Welcome back!");
        await checkAuth();
        navigate("/dashboard");
      } else {
        const err = await res.json();
        toast.error(err.detail || "Invalid email or password");
      }
    } catch (err) {
      toast.error("Login failed");
    } finally {
      setLoggingIn(false);
    }
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b bg-background/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <span className="font-heading font-bold text-lg tracking-tight" data-testid="landing-logo">PropStack</span>
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => setShowLogin(true)} data-testid="nav-signin-btn" className="text-sm">
              Sign In
            </Button>
            <Button onClick={login} data-testid="nav-signup-btn" className="text-sm">
              Get Started
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-28 pb-16 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <h1 className="font-heading text-4xl sm:text-5xl lg:text-[3.5rem] font-bold leading-tight tracking-tight" data-testid="hero-title">
              Smart Property Operations.{" "}
              <span className="text-primary">Financial Clarity in Real Time.</span>
            </h1>
            <p className="text-muted-foreground text-base sm:text-lg max-w-xl">
              Track revenue. Control expenses. Manage staff. Analyze performance — all from one unified platform built for hospitality.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Button size="lg" onClick={login} data-testid="hero-signup-btn" className="h-12 px-6">
                Sign Up with Google
              </Button>
              <Button size="lg" variant="outline" onClick={() => setShowLogin(true)} data-testid="hero-signin-btn" className="h-12 px-6">
                Sign In with Google
              </Button>
            </div>
            <div className="flex items-center gap-6 pt-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-2"><Shield className="h-4 w-4" /> Secure & Encrypted</div>
              <div className="flex items-center gap-2"><Zap className="h-4 w-4" /> Real-time Data</div>
            </div>
          </div>
          <div className="relative hidden lg:block">
            <div className="absolute inset-0 bg-gradient-to-tr from-primary/20 to-transparent rounded-2xl" />
            <img src={HERO_IMAGE} alt="Modern hotel" className="rounded-2xl shadow-2xl object-cover aspect-[4/3]" />
            <div className="absolute bottom-6 left-6 bg-background/90 backdrop-blur-sm rounded-lg px-4 py-2 shadow-lg flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span className="text-sm font-medium">4 properties active</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 px-4 sm:px-6 border-t">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="font-heading text-2xl sm:text-3xl font-bold mb-3">Everything You Need to Manage Properties</h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">From revenue tracking to staff management, PropStack gives you complete operational control.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <Card key={i} className="group hover:shadow-lg transition-shadow">
                <CardContent className="p-6">
                  <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                    <f.icon className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="font-heading font-semibold mb-2">{f.title}</h3>
                  <p className="text-sm text-muted-foreground">{f.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="font-heading text-2xl sm:text-3xl font-bold mb-4">Ready to Transform Your Property Operations?</h2>
          <p className="text-muted-foreground mb-8">Join property managers who trust PropStack for their daily operations.</p>
          <Button size="lg" onClick={login} data-testid="cta-signup-btn" className="h-12 px-8">
            Start Free Today
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-6 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <span>© {new Date().getFullYear()} PropStack. All rights reserved.</span>
          <div className="flex gap-6">
            <a href="#" className="hover:text-foreground transition-colors">Privacy</a>
            <a href="#" className="hover:text-foreground transition-colors">Terms</a>
            <a href="#" className="hover:text-foreground transition-colors">Contact</a>
          </div>
        </div>
      </footer>

      {/* Login Dialog */}
      <Dialog open={showLogin} onOpenChange={setShowLogin}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading text-center">Sign In to PropStack</DialogTitle>
            <DialogDescription className="text-center">Choose your sign-in method</DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 pt-4">
            {/* Google Auth */}
            <Button 
              variant="outline" 
              className="w-full h-12 text-base gap-3" 
              onClick={() => { setShowLogin(false); login(); }}
              data-testid="login-google-btn"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </Button>

            <div className="relative">
              <Separator />
              <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-background px-3 text-xs text-muted-foreground">
                or sign in with email
              </span>
            </div>

            {/* Email/Password Form */}
            <form onSubmit={handlePasswordLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="login-email">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input 
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    className="pl-10"
                    placeholder="you@example.com"
                    required
                    data-testid="login-email-input"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="login-password">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input 
                    id="login-password"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    className="pl-10 pr-10"
                    placeholder="Your password"
                    required
                    data-testid="login-password-input"
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
              <Button 
                type="submit" 
                className="w-full h-11"
                disabled={loggingIn}
                data-testid="login-submit-btn"
              >
                {loggingIn ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Signing in...</>
                ) : (
                  "Sign In"
                )}
              </Button>
            </form>

            <p className="text-xs text-center text-muted-foreground">
              Don't have an account? <button onClick={() => { setShowLogin(false); login(); }} className="text-primary underline">Sign up with Google</button>
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
