import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Building2, Users, DollarSign, CheckCircle, ArrowRight, Plus, Globe, Home, Sparkles } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

const STEPS = [
  { id: 1, title: "Add Properties", description: "Add your first property or sync from Airbnb", icon: Building2 },
  { id: 2, title: "Invite Team", description: "Invite owners and staff to your team", icon: Users },
  { id: 3, title: "Financial Setup", description: "Configure your management fees", icon: DollarSign },
];

export default function OnboardingWizard({ onComplete }) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  
  // Step 1: Property
  const [propertyMethod, setPropertyMethod] = useState(null); // 'manual' or 'ota'
  const [propertyName, setPropertyName] = useState("");
  const [icalUrl, setIcalUrl] = useState("");
  const [propertiesAdded, setPropertiesAdded] = useState([]);
  
  // Step 2: Team
  const [inviteRole, setInviteRole] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [invitesSent, setInvitesSent] = useState([]);
  
  // Step 3: Fees
  const [feeModel, setFeeModel] = useState("percentage_revenue");
  const [feeAmount, setFeeAmount] = useState("15");

  const progress = ((step - 1) / 3) * 100;

  const handleAddProperty = async () => {
    if (propertyMethod === 'manual' && !propertyName.trim()) {
      toast.error("Please enter a property name");
      return;
    }
    if (propertyMethod === 'ota' && (!propertyName.trim() || !icalUrl.trim())) {
      toast.error("Please enter property name and iCal URL");
      return;
    }

    setLoading(true);
    try {
      let res;
      if (propertyMethod === 'ota') {
        res = await fetch(`${API}/api/ota/import-property`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ name: propertyName, source: "airbnb", ical_url: icalUrl }),
        });
      } else {
        res = await fetch(`${API}/api/properties`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ name: propertyName, property_type: "", active: true }),
        });
      }

      if (res.ok) {
        const data = await res.json();
        setPropertiesAdded([...propertiesAdded, { name: propertyName, type: propertyMethod }]);
        setPropertyName("");
        setIcalUrl("");
        setPropertyMethod(null);
        toast.success(`Property "${propertyName}" added!`);
      } else {
        const err = await res.json();
        toast.error(err.detail || "Failed to add property");
      }
    } catch (err) {
      toast.error("Error adding property");
    } finally {
      setLoading(false);
    }
  };

  const handleInvite = async () => {
    if (!inviteRole || !inviteEmail.trim() || !inviteName.trim()) {
      toast.error("Please fill all fields");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API}/api/invitations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ 
          email: inviteEmail, 
          role: inviteRole, 
          name: inviteName,
          assigned_properties: []
        }),
      });

      if (res.ok) {
        setInvitesSent([...invitesSent, { name: inviteName, role: inviteRole }]);
        setInviteEmail("");
        setInviteName("");
        setInviteRole("");
        toast.success(`Invitation sent to ${inviteName}!`);
      } else {
        const err = await res.json();
        toast.error(err.detail || "Failed to send invitation");
      }
    } catch (err) {
      toast.error("Error sending invitation");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveFees = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/companies/me`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ 
          management_fee_type: feeModel,
          management_fee_percent: parseFloat(feeAmount) || 15,
          onboarding_completed: true,
        }),
      });

      if (res.ok) {
        toast.success("Setup complete!");
        onComplete?.();
      } else {
        // Even if update fails, complete onboarding
        onComplete?.();
      }
    } catch (err) {
      onComplete?.();
    } finally {
      setLoading(false);
    }
  };

  const canProceed = () => {
    if (step === 1) return propertiesAdded.length > 0;
    if (step === 2) return true; // Optional
    return true;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl shadow-xl border-0">
        <CardHeader className="space-y-4 pb-6">
          <div className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            <span className="font-heading font-bold text-xl">Welcome to PropStack</span>
          </div>
          <Progress value={progress} className="h-2" />
          <div className="flex justify-between">
            {STEPS.map((s) => (
              <div 
                key={s.id} 
                className={`flex items-center gap-2 text-sm ${step >= s.id ? 'text-primary font-medium' : 'text-muted-foreground'}`}
              >
                <div className={`h-8 w-8 rounded-full flex items-center justify-center ${step > s.id ? 'bg-primary text-white' : step === s.id ? 'bg-primary/10 text-primary border-2 border-primary' : 'bg-muted'}`}>
                  {step > s.id ? <CheckCircle className="h-5 w-5" /> : <s.icon className="h-4 w-4" />}
                </div>
                <span className="hidden sm:inline">{s.title}</span>
              </div>
            ))}
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Step 1: Add Properties */}
          {step === 1 && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h2 className="text-xl font-bold font-heading">Add Your First Property</h2>
                <p className="text-muted-foreground mt-1">Choose how you'd like to add your property</p>
              </div>

              {!propertyMethod ? (
                <div className="grid grid-cols-2 gap-4">
                  <button
                    onClick={() => setPropertyMethod('manual')}
                    className="p-6 rounded-xl border-2 border-dashed hover:border-primary hover:bg-primary/5 transition-all text-left group"
                  >
                    <Home className="h-8 w-8 mb-3 text-muted-foreground group-hover:text-primary transition-colors" />
                    <p className="font-semibold">Add Manually</p>
                    <p className="text-sm text-muted-foreground mt-1">Enter property details yourself</p>
                  </button>
                  <button
                    onClick={() => setPropertyMethod('ota')}
                    className="p-6 rounded-xl border-2 border-dashed hover:border-primary hover:bg-primary/5 transition-all text-left group"
                  >
                    <Globe className="h-8 w-8 mb-3 text-muted-foreground group-hover:text-primary transition-colors" />
                    <p className="font-semibold">Sync from Airbnb</p>
                    <p className="text-sm text-muted-foreground mt-1">Import via iCal URL</p>
                  </button>
                </div>
              ) : (
                <div className="space-y-4 p-4 bg-muted/30 rounded-xl">
                  <div className="flex items-center justify-between">
                    <Badge variant={propertyMethod === 'ota' ? 'default' : 'secondary'}>
                      {propertyMethod === 'ota' ? 'Airbnb Sync' : 'Manual Entry'}
                    </Badge>
                    <Button variant="ghost" size="sm" onClick={() => setPropertyMethod(null)}>Change</Button>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <Label>Property Name *</Label>
                      <Input 
                        value={propertyName} 
                        onChange={e => setPropertyName(e.target.value)} 
                        placeholder="e.g., Beach Villa, Downtown Apartment"
                      />
                    </div>
                    {propertyMethod === 'ota' && (
                      <div>
                        <Label>iCal URL *</Label>
                        <Input 
                          value={icalUrl} 
                          onChange={e => setIcalUrl(e.target.value)} 
                          placeholder="https://www.airbnb.com/calendar/ical/..."
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Find this in your Airbnb listing → Availability → Export Calendar
                        </p>
                      </div>
                    )}
                    <Button onClick={handleAddProperty} disabled={loading} className="w-full">
                      {loading ? "Adding..." : "Add Property"}
                    </Button>
                  </div>
                </div>
              )}

              {propertiesAdded.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">Properties added:</p>
                  {propertiesAdded.map((p, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 bg-primary/5 rounded-lg">
                      <CheckCircle className="h-4 w-4 text-primary" />
                      <span className="font-medium">{p.name}</span>
                      <Badge variant="outline" className="ml-auto text-xs">
                        {p.type === 'ota' ? 'OTA Synced' : 'Manual'}
                      </Badge>
                    </div>
                  ))}
                  <Button variant="outline" size="sm" onClick={() => setPropertyMethod(null)} className="mt-2">
                    <Plus className="h-4 w-4 mr-1" /> Add Another
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Step 2: Invite Team */}
          {step === 2 && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h2 className="text-xl font-bold font-heading">Invite Your Team</h2>
                <p className="text-muted-foreground mt-1">Add property owners and staff members (optional)</p>
              </div>

              <div className="space-y-4 p-4 bg-muted/30 rounded-xl">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Role *</Label>
                    <Select value={inviteRole} onValueChange={setInviteRole}>
                      <SelectTrigger><SelectValue placeholder="Select role..." /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="owner">Property Owner</SelectItem>
                        <SelectItem value="staff">Housekeeper</SelectItem>
                        <SelectItem value="staff">Co-host</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Name *</Label>
                    <Input value={inviteName} onChange={e => setInviteName(e.target.value)} placeholder="John Doe" />
                  </div>
                </div>
                <div>
                  <Label>Email *</Label>
                  <Input type="email" value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} placeholder="john@example.com" />
                </div>
                <Button onClick={handleInvite} disabled={loading} className="w-full">
                  {loading ? "Sending..." : "Send Invitation"}
                </Button>
              </div>

              {invitesSent.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">Invitations sent:</p>
                  {invitesSent.map((inv, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 bg-primary/5 rounded-lg">
                      <CheckCircle className="h-4 w-4 text-primary" />
                      <span className="font-medium">{inv.name}</span>
                      <Badge variant="outline" className="ml-auto text-xs capitalize">{inv.role}</Badge>
                    </div>
                  ))}
                </div>
              )}

              <p className="text-sm text-muted-foreground text-center">
                You can always invite more team members later from Settings
              </p>
            </div>
          )}

          {/* Step 3: Financial Setup */}
          {step === 3 && (
            <div className="space-y-6 animate-fade-in">
              <div>
                <h2 className="text-xl font-bold font-heading">Set Up Management Fees</h2>
                <p className="text-muted-foreground mt-1">Configure how you calculate owner payouts</p>
              </div>

              <div className="space-y-4 p-4 bg-muted/30 rounded-xl">
                <div>
                  <Label>Fee Model</Label>
                  <Select value={feeModel} onValueChange={setFeeModel}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="percentage_revenue">% of Gross Revenue</SelectItem>
                      <SelectItem value="percentage_net">% of Net Revenue</SelectItem>
                      <SelectItem value="fixed">Fixed Amount per Booking</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>{feeModel === 'fixed' ? 'Fixed Fee ($)' : 'Fee Percentage (%)'}</Label>
                  <Input 
                    type="number" 
                    value={feeAmount} 
                    onChange={e => setFeeAmount(e.target.value)} 
                    placeholder={feeModel === 'fixed' ? '50' : '15'}
                  />
                </div>
                <div className="p-3 bg-primary/5 rounded-lg">
                  <p className="text-sm font-medium">Formula Preview:</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {feeModel === 'percentage_revenue' && `Owner Payout = Revenue - (Revenue × ${feeAmount}%) - Expenses`}
                    {feeModel === 'percentage_net' && `Owner Payout = (Revenue - Expenses) × (100% - ${feeAmount}%)`}
                    {feeModel === 'fixed' && `Owner Payout = Revenue - $${feeAmount} - Expenses`}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between pt-4 border-t">
            {step > 1 ? (
              <Button variant="outline" onClick={() => setStep(step - 1)}>Back</Button>
            ) : (
              <div />
            )}
            
            {step < 3 ? (
              <Button onClick={() => setStep(step + 1)} disabled={step === 1 && !canProceed()}>
                {step === 2 ? 'Skip & Continue' : 'Continue'} <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            ) : (
              <Button onClick={handleSaveFees} disabled={loading} className="bg-primary">
                {loading ? "Finishing..." : "Complete Setup"} <Sparkles className="h-4 w-4 ml-2" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
