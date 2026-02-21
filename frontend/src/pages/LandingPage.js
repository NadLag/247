import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Building2, DollarSign, Users, BarChart3, Shield, Zap } from "lucide-react";

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
  const { login, user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) navigate("/dashboard");
  }, [user, navigate]);

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
            <Button variant="ghost" onClick={login} data-testid="nav-signin-btn" className="text-sm">
              Sign In
            </Button>
            <Button onClick={login} data-testid="nav-signup-btn" className="text-sm">
              Get Started
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-28 sm:pt-36 pb-16 sm:pb-24 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          <div className="space-y-8 animate-fade-in-up">
            <div className="space-y-4">
              <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.1]" data-testid="hero-headline">
                Smart Property Operations.{" "}
                <span className="text-muted-foreground">Financial Clarity in Real Time.</span>
              </h1>
              <p className="text-base sm:text-lg text-muted-foreground max-w-lg leading-relaxed">
                Track revenue. Control expenses. Manage staff. Analyze performance — all from one unified platform built for hospitality.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button size="lg" onClick={login} data-testid="hero-signup-btn" className="h-12 px-6 text-sm font-semibold">
                Sign Up with Google
              </Button>
              <Button size="lg" variant="outline" onClick={login} data-testid="hero-signin-btn" className="h-12 px-6 text-sm font-semibold">
                Sign In with Google
              </Button>
            </div>
            <div className="flex items-center gap-6 text-sm text-muted-foreground pt-2">
              <span className="flex items-center gap-1.5"><Shield className="h-4 w-4" /> Secure & Encrypted</span>
              <span className="flex items-center gap-1.5"><Zap className="h-4 w-4" /> Real-time Data</span>
            </div>
          </div>
          <div className="animate-fade-in-up delay-300 relative">
            <div className="rounded-xl overflow-hidden shadow-2xl border bg-muted">
              <img src={HERO_IMAGE} alt="Modern luxury hotel architecture" className="w-full h-[300px] sm:h-[420px] object-cover" />
            </div>
            <div className="absolute -bottom-4 -left-4 bg-card border rounded-lg p-3 shadow-lg hidden lg:block">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-emerald-500" />
                <span className="text-xs font-medium">4 properties active</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 sm:py-24 bg-muted/30 border-t">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center space-y-3 mb-12 sm:mb-16">
            <h2 className="font-heading text-2xl sm:text-3xl font-bold" data-testid="features-heading">
              Everything You Need to Manage Properties
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto text-sm sm:text-base">
              From revenue tracking to staff management, PropStack gives you complete operational control.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {features.map((f, i) => (
              <Card key={f.title} className={`animate-fade-in-up delay-${(i + 1) * 100} border bg-card hover:shadow-md transition-shadow`}>
                <CardContent className="p-5 sm:p-6 space-y-3">
                  <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <f.icon className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="font-heading text-base font-semibold">{f.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{f.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 sm:py-24 border-t">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center space-y-6">
          <h2 className="font-heading text-2xl sm:text-3xl font-bold">Ready to streamline your operations?</h2>
          <p className="text-muted-foreground">Join property managers who trust PropStack for financial clarity.</p>
          <Button size="lg" onClick={login} data-testid="cta-signup-btn" className="h-12 px-8">
            Get Started Free
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <span className="font-heading font-semibold text-foreground">PropStack</span>
          <span>Multi-Tenant Property & Hospitality Management</span>
        </div>
      </footer>
    </div>
  );
}
