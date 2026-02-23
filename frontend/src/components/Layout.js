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
import { LayoutDashboard, Building2, Users, Receipt, CalendarDays, Mail, CreditCard, Settings, Sun, Moon, Menu, LogOut, ChevronRight, ChevronLeft, Package, BarChart3, ClipboardList, Bell, AlertTriangle, ExternalLink, PanelLeftClose, PanelLeft, FileText } from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

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
    { name: "Invite", path: "/invitations", icon: Mail },
    { name: "Billing", path: "/billing", icon: CreditCard },
    { name: "Settings", path: "/settings", icon: Settings },
  ],
  owner: [
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    { name: "Properties", path: "/properties", icon: Building2 },
    { name: "Bookings", path: "/bookings", icon: CalendarDays },
    { name: "Reports", path: "/reports", icon: FileText },
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

function NavItems({ items, currentPath, onNavigate, collapsed = false }) {
  return (
    <nav className={`flex-1 space-y-1 ${collapsed ? 'p-2' : 'p-3'}`}>
      {items.map((item, index) => {
        const isActive = currentPath === item.path;
        return (
          <button
            key={item.path}
            data-testid={`nav-${item.name.toLowerCase()}`}
            onClick={() => onNavigate(item.path)}
            title={collapsed ? item.name : undefined}
            style={{ animationDelay: `${index * 0.03}s` }}
            className={`w-full flex items-center ${collapsed ? 'justify-center' : 'gap-3'} ${collapsed ? 'px-0 py-2.5' : 'px-3 py-2.5'} rounded-lg text-sm font-medium transition-all duration-200 animate-fade-in opacity-0 ${
              isActive
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground hover:translate-x-0.5"
            }`}
          >
            <item.icon className={`h-4 w-4 shrink-0 transition-transform duration-200 ${isActive ? '' : 'group-hover:scale-110'}`} />
            {!collapsed && <span>{item.name}</span>}
            {!collapsed && isActive && <ChevronRight className="h-3 w-3 ml-auto animate-slide-in" />}
          </button>
        );
      })}
    </nav>
  );
}

function NotificationBell() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      const [notifRes, countRes] = await Promise.all([
        fetch(`${API}/api/notifications`, { credentials: "include" }),
        fetch(`${API}/api/notifications/unread-count`, { credentials: "include" }),
      ]);
      if (notifRes.ok) setNotifications(await notifRes.json());
      if (countRes.ok) {
        const data = await countRes.json();
        setUnreadCount(data.count);
      }
    } catch (err) { console.error(err); }
  }, []);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  const handleAction = async (notif) => {
    // Mark as read
    await fetch(`${API}/api/notifications/${notif.id}/read`, {
      method: "PUT", credentials: "include",
    });
    setOpen(false);
    fetchNotifications();
    if (notif.action_url) navigate(notif.action_url);
  };

  const markAllRead = async () => {
    await fetch(`${API}/api/notifications/read-all`, {
      method: "PUT", credentials: "include",
    });
    fetchNotifications();
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative hover:bg-accent" data-testid="notification-bell">
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 h-4 min-w-[16px] rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center px-1" data-testid="notification-badge">
              {unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 animate-scale-in" data-testid="notification-dropdown">
        <div className="flex items-center justify-between px-3 py-2 border-b">
          <span className="text-sm font-semibold">Notifications</span>
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" className="text-xs h-7 text-primary" onClick={markAllRead}>
              Mark all read
            </Button>
          )}
        </div>
        <ScrollArea className="max-h-[320px]">
          {notifications.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No notifications
            </div>
          ) : (
            notifications.map(notif => (
              <DropdownMenuItem
                key={notif.id}
                className={`flex flex-col items-start gap-1 px-3 py-3 cursor-pointer ${!notif.read ? 'bg-primary/5' : ''}`}
                onClick={() => handleAction(notif)}
                data-testid={`notification-item-${notif.id}`}
              >
                <div className="flex items-center gap-2 w-full">
                  <AlertTriangle className={`h-4 w-4 shrink-0 ${!notif.read ? 'text-amber-500' : 'text-muted-foreground'}`} />
                  <span className={`text-sm font-medium flex-1 ${!notif.read ? 'text-foreground' : 'text-muted-foreground'}`}>
                    {notif.title}
                  </span>
                  {!notif.read && <div className="h-2 w-2 rounded-full bg-primary shrink-0" />}
                </div>
                <p className="text-xs text-muted-foreground pl-6">{notif.message}</p>
                {notif.action_url && (
                  <span className="text-xs text-primary font-medium pl-6 flex items-center gap-1">
                    Review Bookings <ExternalLink className="h-3 w-3" />
                  </span>
                )}
              </DropdownMenuItem>
            ))
          )}
        </ScrollArea>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function Layout({ children }) {
  const { user, logout, setupCompany } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem("sidebar_collapsed") === "true"; } catch { return false; }
  });
  const [companyName, setCompanyName] = useState("");
  const [settingUp, setSettingUp] = useState(false);

  const navItems = navConfig[user?.role] || navConfig.staff;

  const toggleSidebar = () => {
    setCollapsed(prev => {
      const next = !prev;
      try { localStorage.setItem("sidebar_collapsed", String(next)); } catch {}
      return next;
    });
  };

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
      <aside className={`hidden md:flex ${collapsed ? 'w-16' : 'w-60'} border-r bg-card/50 backdrop-blur-sm flex-col shrink-0 transition-all duration-300`}>
        <div className={`h-14 flex items-center ${collapsed ? 'justify-center px-2' : 'justify-between px-5'} border-b bg-card`}>
          {!collapsed && (
            <span className="font-heading font-bold text-lg tracking-tight text-gradient" data-testid="app-logo">
              PropStack
            </span>
          )}
          <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-accent shrink-0" onClick={toggleSidebar} data-testid="sidebar-toggle-btn">
            {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          </Button>
        </div>
        <NavItems items={navItems} currentPath={location.pathname} onNavigate={handleNavigate} collapsed={collapsed} />
        <Separator />
        <div className={collapsed ? "p-2" : "p-3"}>
          {collapsed ? (
            <div className="flex justify-center">
              <Avatar className="h-8 w-8 ring-2 ring-background">
                <AvatarImage src={user?.picture} alt={user?.name} />
                <AvatarFallback className="text-xs bg-primary/10 text-primary">{user?.name?.[0]}</AvatarFallback>
              </Avatar>
            </div>
          ) : (
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
          )}
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
            <NotificationBell />
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
