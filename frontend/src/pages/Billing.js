import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { CreditCard, Check, Loader2, Building2, Zap, Crown } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const plans = [
  { id: "starter", name: "Starter", price: 29, properties: "5", icon: Building2, features: ["Up to 5 properties", "2 staff members", "Basic analytics", "Email support"] },
  { id: "professional", name: "Professional", price: 79, properties: "20", icon: Zap, popular: true, features: ["Up to 20 properties", "Unlimited staff", "Advanced analytics", "Priority support", "OTA sync"] },
  { id: "enterprise", name: "Enterprise", price: 199, properties: "Unlimited", icon: Crown, features: ["Unlimited properties", "Unlimited staff", "Custom analytics", "Dedicated support", "OTA sync", "API access"] },
];

export default function Billing() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [checkingOut, setCheckingOut] = useState(null);
  const [polling, setPolling] = useState(false);

  useEffect(() => { if (!authLoading && !user) navigate("/"); }, [user, authLoading, navigate]);

  useEffect(() => {
    if (!user?.company_id) return;
    const fetchSub = async () => {
      try {
        const res = await fetch(`${API}/api/subscription/current`, { credentials: "include" });
        if (res.ok) setSubscription(await res.json());
      } catch (err) { console.error(err); } finally { setLoading(false); }
    };
    fetchSub();
  }, [user]);

  // Poll payment status after Stripe redirect
  useEffect(() => {
    const sessionId = searchParams.get("session_id");
    if (!sessionId || !user) return;

    const pollStatus = async (attempts = 0) => {
      if (attempts >= 5) {
        toast.error("Payment status check timed out");
        setPolling(false);
        return;
      }
      setPolling(true);
      try {
        const res = await fetch(`${API}/api/subscription/status/${sessionId}`, { credentials: "include" });
        if (res.ok) {
          const data = await res.json();
          if (data.payment_status === "paid") {
            toast.success("Payment successful! Subscription activated.");
            setPolling(false);
            // Refresh subscription
            const subRes = await fetch(`${API}/api/subscription/current`, { credentials: "include" });
            if (subRes.ok) setSubscription(await subRes.json());
            // Clean URL
            window.history.replaceState({}, "", "/billing");
            return;
          } else if (data.status === "expired") {
            toast.error("Payment session expired");
            setPolling(false);
            return;
          }
        }
        setTimeout(() => pollStatus(attempts + 1), 2000);
      } catch (err) {
        console.error(err);
        setTimeout(() => pollStatus(attempts + 1), 2000);
      }
    };
    pollStatus();
  }, [searchParams, user]);

  const handleCheckout = async (planId) => {
    setCheckingOut(planId);
    try {
      const res = await fetch(`${API}/api/subscription/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ plan: planId, origin_url: window.location.origin }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.url) window.location.href = data.url;
      } else {
        const err = await res.json();
        toast.error(err.detail || "Failed to create checkout");
      }
    } catch (err) {
      toast.error("Error creating checkout session");
    } finally {
      setCheckingOut(null);
    }
  };

  if (authLoading || !user) return <div className="h-screen flex items-center justify-center bg-background"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;

  return (
    <Layout>
      <div className="space-y-8 max-w-[1100px] mx-auto" data-testid="billing-page">
        <div>
          <h1 className="font-heading text-2xl font-bold">Billing & Subscription</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage your subscription plan</p>
        </div>

        {/* Current Plan */}
        {subscription && (
          <Card data-testid="current-plan-card">
            <CardContent className="p-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <CreditCard className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium">Current Plan</p>
                  <p className="text-lg font-bold font-heading capitalize">
                    {subscription.subscription_plan || "No plan"}{" "}
                    <Badge variant={subscription.subscription_status === "active" ? "default" : "secondary"} className="ml-2">
                      {subscription.subscription_status}
                    </Badge>
                  </p>
                </div>
              </div>
              {polling && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Verifying payment...
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Plans */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plans.map((plan) => {
            const isCurrent = subscription?.subscription_plan === plan.id;
            return (
              <Card key={plan.id} className={`relative overflow-hidden transition-shadow hover:shadow-md ${plan.popular ? "border-primary shadow-md" : ""}`} data-testid={`plan-card-${plan.id}`}>
                {plan.popular && (
                  <div className="absolute top-0 right-0 bg-primary text-primary-foreground text-xs font-semibold px-3 py-1 rounded-bl-lg">Popular</div>
                )}
                <CardHeader className="pb-4">
                  <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center mb-2">
                    <plan.icon className="h-5 w-5 text-primary" />
                  </div>
                  <CardTitle className="font-heading text-lg">{plan.name}</CardTitle>
                  <CardDescription>Up to {plan.properties} properties</CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold font-data">${plan.price}</span>
                    <span className="text-sm text-muted-foreground">/month</span>
                  </div>
                  <ul className="space-y-2">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-center gap-2 text-sm">
                        <Check className="h-4 w-4 text-emerald-500 shrink-0" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="w-full"
                    variant={isCurrent ? "secondary" : plan.popular ? "default" : "outline"}
                    disabled={isCurrent || checkingOut !== null}
                    onClick={() => handleCheckout(plan.id)}
                    data-testid={`subscribe-${plan.id}-btn`}
                  >
                    {checkingOut === plan.id ? (
                      <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Processing...</>
                    ) : isCurrent ? (
                      "Current Plan"
                    ) : (
                      `Subscribe to ${plan.name}`
                    )}
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </Layout>
  );
}
