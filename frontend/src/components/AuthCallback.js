import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

const API = process.env.REACT_APP_BACKEND_URL;

export default function AuthCallback() {
  const hasProcessed = useRef(false);
  const navigate = useNavigate();
  const { setUser } = useAuth();

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash;
    const sessionId = new URLSearchParams(hash.substring(1)).get("session_id");

    if (!sessionId) {
      navigate("/");
      return;
    }

    const invitationToken = sessionStorage.getItem("invitation_token");
    sessionStorage.removeItem("invitation_token");

    fetch(`${API}/api/auth/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ session_id: sessionId, invitation_token: invitationToken }),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Auth failed");
        return res.json();
      })
      .then((userData) => {
        setUser(userData);
        window.history.replaceState({}, "", "/dashboard");
        navigate("/dashboard", { state: { user: userData }, replace: true });
      })
      .catch((err) => {
        console.error("Auth callback error:", err);
        navigate("/");
      });
  }, [navigate, setUser]);

  return (
    <div className="h-screen flex items-center justify-center bg-background">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  );
}
