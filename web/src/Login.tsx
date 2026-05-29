import { useState } from "react";
import { api } from "./api";

interface MagicResp {
  sent: boolean;
  dev_link: string | null;
}

interface Props {
  onLoggedIn: () => void;
}

export default function Login({ onLoggedIn }: Props) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [orgType, setOrgType] = useState<"farmer" | "agronomist">("farmer");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [devLink, setDevLink] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setDevLink(null);
    try {
      const resp = await api.post<MagicResp>("/api/auth/magic", {
        email: email.trim(),
        org_type: orgType,
        name: name.trim() || null,
      });
      if (resp.dev_link) {
        // Dev mode — follow the link automatically.
        const url = new URL(resp.dev_link);
        const r = await fetch(url.pathname + url.search, { credentials: "include" });
        if (!r.ok) {
          const t = await r.text();
          throw new Error(`verify failed: ${t}`);
        }
        onLoggedIn();
      } else {
        setDevLink("sent");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="brand">
          <span className="dot" /> whorl
        </div>
        <p className="sub">crop-scouting dashboard · sign in with email</p>
        <form onSubmit={submit}>
          <label>
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
              autoFocus
            />
          </label>
          <label>
            <span>Your name (optional, used on first signup)</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Hartman Family Farm"
            />
          </label>
          <fieldset className="org-type">
            <legend>Account type (first signup only)</legend>
            <label className="radio">
              <input
                type="radio"
                name="org_type"
                value="farmer"
                checked={orgType === "farmer"}
                onChange={() => setOrgType("farmer")}
              />
              <span>
                <b>Farmer</b> — scouting my own fields
              </span>
            </label>
            <label className="radio">
              <input
                type="radio"
                name="org_type"
                value="agronomist"
                checked={orgType === "agronomist"}
                onChange={() => setOrgType("agronomist")}
              />
              <span>
                <b>Agronomist / crop consultant</b> — scouting client fields
              </span>
            </label>
          </fieldset>
          <button type="submit" disabled={busy}>
            {busy ? "Sending…" : "Send magic link"}
          </button>
        </form>
        {devLink === "sent" && (
          <div className="info">Check your email — magic link sent.</div>
        )}
        {error && <div className="error">{error}</div>}
        <p className="note">
          In dev mode, the link is auto-followed (no email is sent). Set{" "}
          <code>WHORL_DEV_AUTH=0</code> + a Resend key in production.
        </p>
      </div>
    </div>
  );
}
