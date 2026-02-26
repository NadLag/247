import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Building2, CheckCircle, Plus, Globe, Home, Sparkles, ArrowRight } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

export default function OnboardingWizard({ onComplete }) {
  const [loading, setLoading] = useState(false);
  const [propertyMethod, setPropertyMethod] = useState(null); // 'manual' or 'ota'
  const [propertyName, setPropertyName] = useState("");
  const [icalUrl, setIcalUrl] = useState("");
  const [propertiesAdded, setPropertiesAdded] = useState([]);

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
          body: JSON.stringify({ 
            name: propertyName, 
            address: "",
            property_type: "", 
            owner_first_name: "",
            owner_last_name: "",
            owner_phone: "",
            owner_email: "",
            units: 1,
            active: true 
          }),
        });
      }

      if (res.ok) {
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

  const handleComplete = async () => {
    setLoading(true);
    try {
      await fetch(`${API}/api/companies/me`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ onboarding_completed: true }),
      });
      onComplete?.();
    } catch (err) {
      onComplete?.();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <Card className="w-full max-w-xl shadow-xl border-0">
        <CardHeader className="space-y-2 pb-4 text-center">
          <div className="flex items-center justify-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            <span className="font-heading font-bold text-xl">Welcome to PropStack</span>
          </div>
          <p className="text-muted-foreground text-sm">Let's get you started by adding your first property</p>
        </CardHeader>

        <CardContent className="space-y-6">
          <div className="space-y-6 animate-fade-in">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                <Building2 className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h2 className="text-lg font-bold font-heading">Add / Sync Property</h2>
                <p className="text-sm text-muted-foreground">Choose how you'd like to add your property</p>
              </div>
            </div>

            {!propertyMethod ? (
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => setPropertyMethod('manual')}
                  className="p-5 rounded-xl border-2 border-dashed hover:border-primary hover:bg-primary/5 transition-all text-left group"
                  data-testid="onboard-manual-btn"
                >
                  <Home className="h-7 w-7 mb-2 text-muted-foreground group-hover:text-primary transition-colors" />
                  <p className="font-semibold text-sm">Add Manually</p>
                  <p className="text-xs text-muted-foreground mt-1">Enter property details yourself</p>
                </button>
                <button
                  onClick={() => setPropertyMethod('ota')}
                  className="p-5 rounded-xl border-2 border-dashed hover:border-primary hover:bg-primary/5 transition-all text-left group"
                  data-testid="onboard-ota-btn"
                >
                  <Globe className="h-7 w-7 mb-2 text-muted-foreground group-hover:text-primary transition-colors" />
                  <p className="font-semibold text-sm">Sync from OTA</p>
                  <p className="text-xs text-muted-foreground mt-1">Import via iCal URL</p>
                </button>
              </div>
            ) : (
              <div className="space-y-4 p-4 bg-muted/30 rounded-xl">
                <div className="flex items-center justify-between">
                  <Badge variant={propertyMethod === 'ota' ? 'default' : 'secondary'}>
                    {propertyMethod === 'ota' ? 'OTA Sync (iCal)' : 'Manual Entry'}
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
                      data-testid="onboard-prop-name"
                    />
                  </div>
                  {propertyMethod === 'ota' && (
                    <div>
                      <Label>iCal URL *</Label>
                      <Input 
                        value={icalUrl} 
                        onChange={e => setIcalUrl(e.target.value)} 
                        placeholder="https://www.airbnb.com/calendar/ical/..."
                        data-testid="onboard-ical-url"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Find this in your Airbnb/Booking.com listing → Calendar → Export
                      </p>
                    </div>
                  )}
                  <Button onClick={handleAddProperty} disabled={loading} className="w-full" data-testid="onboard-add-btn">
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
                    <span className="font-medium text-sm">{p.name}</span>
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

          {/* Complete Setup Button */}
          <div className="pt-4 border-t">
            <Button 
              onClick={handleComplete} 
              disabled={propertiesAdded.length === 0 || loading} 
              className="w-full"
              data-testid="onboard-complete-btn"
            >
              {loading ? "Setting up..." : "Get Started"} 
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
            {propertiesAdded.length === 0 && (
              <p className="text-xs text-muted-foreground text-center mt-2">
                Add at least one property to continue
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
