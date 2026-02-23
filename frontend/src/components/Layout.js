import { useState, useEffect, useCallback } from "react";
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
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";
import { LayoutDashboard, Building2, Users, Receipt, CalendarDays, Mail, CreditCard, Settings, Sun, Moon, Menu, LogOut, ChevronRight, Package, BarChart3, ClipboardList, Bell, AlertTriangle, ExternalLink } from "lucide-react";

const navConfig = {
  company_admin: [
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    { name: "Properties", path: "/properties", icon: Building2 },
    { name: "Bookings", path: "/bookings", icon: CalendarDays },
    { name: "Staff", path: "/staff", icon: Users },
    { name: "Tasks", path: "/tasks", icon: ClipboardList },
    { name: "Expenses", path: "/expenses", icon: Receipt },
    { name: "Services", path: "/services", icon: Package },
    { name: "Analytics", path: "/analytics", icon: BarChart3 },
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
      {items.map((item, index) => {
        const isActive = currentPath === item.path;
        return (
          <button
            key={item.path}
            data-testid={`nav-${item.name.toLowerCase()}`}
            onClick={() => onNavigate(item.path)}
            style={{ animationDelay: `${index * 0.03}s` }}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 animate-fade-in opacity-0 ${
              isActive
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground hover:translate-x-0.5"
            }`}
          >
            <item.icon className={`h-4 w-4 shrink-0 transition-transform duration-200 ${isActive ? '' : 'group-hover:scale-110'}`} />
            <span>{item.name}</span>
            {isActive && <ChevronRight className="h-3 w-3 ml-auto animate-slide-in" />}
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
      <aside className="hidden md:flex w-60 border-r bg-card/50 backdrop-blur-sm flex-col shrink-0">
        <div className="h-14 flex items-center px-5 border-b bg-card">
          <span className="font-heading font-bold text-lg tracking-tight text-gradient" data-testid="app-logo">
            PropStack
          </span>
        </div>
        <NavItems items={navItems} currentPath={location.pathname} onNavigate={handleNavigate} />
        <Separator />
        <div className="p-3">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-muted/50 hover:bg-muted transition-colors">
            <Avatar className="h-8 w-8 ring-2 ring-background">
              <AvatarImage src={user?.picture} alt={user?.name} />
              <AvatarFallback className="text-xs bg-primary/10 text-primary">{user?.name?.[0]}</AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground truncate capitalize">{user?.role?.replace("_", " ")}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-14 border-b bg-card/80 backdrop-blur-sm flex items-center justify-between px-4 md:px-6 shrink-0 sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="md:hidden hover:bg-accent" onClick={() => setMobileOpen(true)} data-testid="mobile-menu-btn">
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
                className="hidden sm:flex text-xs bg-primary/10 text-primary border-0" 
                data-testid="role-badge"
              >
                {user.role === "company_admin" ? "Admin" : user.role === "owner" ? "Owner" : "Staff"}
              </Badge>
            )}
            <Button variant="ghost" size="icon" onClick={toggleTheme} className="hover:bg-accent" data-testid="theme-toggle-btn">
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="rounded-full hover:ring-2 hover:ring-primary/20" data-testid="user-menu-btn">
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user?.picture} alt={user?.name} />
                    <AvatarFallback className="text-xs bg-primary/10 text-primary">{user?.name?.[0]}</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48 animate-scale-in">
                <DropdownMenuItem onClick={() => navigate("/settings")} data-testid="menu-settings" className="cursor-pointer">
                  <Settings className="mr-2 h-4 w-4" /> Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} data-testid="menu-logout" className="cursor-pointer text-destructive focus:text-destructive">
                  <LogOut className="mr-2 h-4 w-4" /> Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-4 md:p-6 lg:p-8">{children}</main>
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
