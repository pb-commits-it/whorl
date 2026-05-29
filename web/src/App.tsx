import { useCallback, useEffect, useState } from "react";
import { api, type Me } from "./api";
import Dashboard from "./Dashboard";
import Login from "./Login";

type Status = "loading" | "anon" | "authed";

export default function App() {
  const [status, setStatus] = useState<Status>("loading");
  const [me, setMe] = useState<Me | null>(null);

  const refresh = useCallback(async () => {
    try {
      const m = await api.get<Me>("/api/me");
      setMe(m);
      setStatus("authed");
    } catch {
      setMe(null);
      setStatus("anon");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (status === "loading") {
    return (
      <div className="boot">
        <span className="dot" /> whorl
      </div>
    );
  }
  if (status === "anon" || !me) {
    return <Login onLoggedIn={refresh} />;
  }
  return <Dashboard me={me} onLogout={refresh} />;
}
