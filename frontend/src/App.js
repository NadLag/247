import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ThemeProvider } from "@/components/ThemeProvider";
import AuthCallback from "@/components/AuthCallback";
import LandingPage from "@/pages/LandingPage";
import Dashboard from "@/pages/Dashboard";
import Properties from "@/pages/Properties";
import StaffPage from "@/pages/Staff";
import Expenses from "@/pages/Expenses";
import Invitations from "@/pages/Invitations";
import Billing from "@/pages/Billing";
import Settings from "@/pages/Settings";
import Bookings from "@/pages/Bookings";
import Services from "@/pages/Services";
import Analytics from "@/pages/Analytics";
import Tasks from "@/pages/Tasks";
import InviteAccept from "@/pages/InviteAccept";
import Reports from "@/pages/Reports";
import { Toaster } from "@/components/ui/sonner";

function AppRouter() {
  const location = useLocation();

  // CRITICAL: Check URL fragment for session_id synchronously during render
  // This prevents race conditions by processing new session_id FIRST
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/properties" element={<Properties />} />
      <Route path="/staff" element={<StaffPage />} />
      <Route path="/expenses" element={<Expenses />} />
      <Route path="/bookings" element={<Bookings />} />
      <Route path="/services" element={<Services />} />
      <Route path="/analytics" element={<Analytics />} />
      <Route path="/tasks" element={<Tasks />} />
      <Route path="/reports" element={<Reports />} />
      <Route path="/invitations" element={<Invitations />} />
      <Route path="/billing" element={<Billing />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/invite/:token" element={<InviteAccept />} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster richColors position="top-right" />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
