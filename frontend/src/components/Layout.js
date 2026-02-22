import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/components/ThemeProvider";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { LayoutDashboard, Building2, Users, Receipt, CalendarDays, Mail, CreditCard, Settings, Sun, Moon, Menu, LogOut, ChevronRight, Package, BarChart3, ClipboardList, Link2 } from "lucide-react";

const navConfig = {
  company_admin: [
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    { name: "Properties", path: "/properties", icon: Building2 },
    { name: "Staff", path: "/staff", icon: Users },
    { name: "Bookings", path: "/bookings", icon: CalendarDays },
    { name: "Tasks", path: "/tasks", icon: ClipboardList },
    { name: "Services", path: "/services", icon: Package },
    { name: "Expenses", path: "/expenses", icon: Receipt },
    { name: "Analytics", path: "/analytics", icon: BarChart3 },
    { name: "OTA Settings", path: "/ota-settings", icon: Link2 },
    { name: "Invitations", path: "/invitations", icon: Mail },
    { name: "Billing", path: "/billing", icon: CreditCard },
    { name: "Settings", path: "/settings", icon: Settings },
  ],
  owner: [
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    { name: "Properties", path: "/properties", icon: Building2 },
    { name: "Bookings", path: "/bookings", icon: CalendarDays },
    { name: "Analytics", path: "/analytics", icon: BarChart3 },
    { name: "Settings", path: "/settings", icon: Settings },
  ],
  staff: [
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    { name: "Tasks", path: "/tasks", icon: ClipboardList },
    { name: "Bookings", path: "/bookings", icon: CalendarDays },
    { name: "Settings", path: "/settings", icon: Settings },
  ],
};

function NavItems({ items, currentPath, onNavigate }) {
  return (
    <nav className="flex-1 p-3 space-y-1">
      {items.map((item) => {
        const isActive = currentPath === item.path;
        return (
          <button
            key={item.path}
            data-testid={`nav-${item.name.toLowerCase()}`}
            onClick={() => onNavigate(item.path)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all duration-200 ${
              isActive
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            }`}
          >
            <item.icon className="h-4 w-4 shrink-0" />
            <span>{item.name}</span>
            {isActive && <ChevronRight className="h-3 w-3 ml-auto" />}
          </button>
        );
      })}
    </nav>
  );
}

export default function Layout({ children }) {
  const { user, logout, setupCompany } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [companyName, setCompanyName] = useState("");
  const [settingUp, setSettingUp] = useState(false);

  const navItems = navConfig[user?.role] || navConfig.staff;

  const handleNavigate = (path) => {
    navigate(path);
    setMobileOpen(false);
  };

  const handleSetup = async () => {
    if (!companyName.trim()) return;
    setSettingUp(true);
    try {
      await setupCompany(companyName.trim());
      toast.success("Company created successfully!");
    } catch (err) {
      toast.error("Failed to create company");
    } finally {
      setSettingUp(false);
    }
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex w-60 border-r bg-card flex-col shrink-0">
        <div className="h-14 flex items-center px-5 border-b">
          <span className="font-heading font-bold text-lg tracking-tight" data-testid="app-logo">
            PropStack
          </span>
        </div>
        <NavItems items={navItems} currentPath={location.pathname} onNavigate={handleNavigate} />
        <Separator />
        <div className="p-3">
          <div className="flex items-center gap-3 px-3 py-2 rounded-md bg-muted/50">
            <Avatar className="h-8 w-8">
              <AvatarImage src={user?.picture} alt={user?.name} />
              <AvatarFallback className="text-xs">{user?.name?.[0]}</AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.role?.replace("_", " ")}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-14 border-b bg-card flex items-center justify-between px-4 md:px-6 shrink-0">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setMobileOpen(true)} data-testid="mobile-menu-btn">
              <Menu className="h-5 w-5" />
            </Button>
            <h2 className="font-heading text-base md:text-lg font-semibold" data-testid="header-greeting">
              Hey, {user?.first_name || user?.name?.split(" ")[0] || "there"}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            {user?.role && (
              <Badge 
                variant="secondary" 
                className="hidden sm:flex text-xs" 
                data-testid="role-badge"
              >
                {user.role === "company_admin" ? "Admin" : user.role === "owner" ? "Owner" : "Staff"}
              </Badge>
            )}
            <Button variant="ghost" size="icon" onClick={toggleTheme} data-testid="theme-toggle-btn">
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="rounded-full" data-testid="user-menu-btn">
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user?.picture} alt={user?.name} />
                    <AvatarFallback className="text-xs">{user?.name?.[0]}</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem onClick={() => navigate("/settings")} data-testid="menu-settings">
                  <Settings className="mr-2 h-4 w-4" /> Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} data-testid="menu-logout">
                  <LogOut className="mr-2 h-4 w-4" /> Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-4 md:p-6">{children}</main>
      </div>

      {/* Mobile Sidebar */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-60 p-0">
          <div className="h-14 flex items-center px-5 border-b">
            <span className="font-heading font-bold text-lg">PropStack</span>
          </div>
          <NavItems items={navItems} currentPath={location.pathname} onNavigate={handleNavigate} />
        </SheetContent>
      </Sheet>

      {/* Company Setup Dialog */}
      {user && !user.company_id && (
        <Dialog open={true}>
          <DialogContent className="sm:max-w-md" onPointerDownOutside={(e) => e.preventDefault()}>
            <DialogHeader>
              <DialogTitle className="font-heading">Welcome to PropStack</DialogTitle>
              <DialogDescription>Set up your company to get started managing your properties.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="company-name">Company Name</Label>
                <Input
                  id="company-name"
                  data-testid="company-name-input"
                  placeholder="Enter your company name"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSetup()}
                />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleSetup} disabled={!companyName.trim() || settingUp} data-testid="create-company-btn">
                {settingUp ? "Creating..." : "Create Company"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
