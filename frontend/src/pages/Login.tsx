import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw, X, AlertTriangle } from "lucide-react";

import {
  cancelLogin,
  getLoginAccount,
  getLoginStatus,
  startLogin,
} from "@/services/api";

const STATUS_LABELS: Record<string, string> = {
  waiting: "Waiting for login…",
  pending: "Verifying…",
  logged_in: "Logged in — redirecting…",
  failed: "Login failed",
  expired: "Login timed out",
};

export function Login() {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [novncUrl, setNovncUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [error, setError] = useState<string | null>(null);

  const { data: existing } = useQuery({
    queryKey: ["login-account"],
    queryFn: getLoginAccount,
  });

  // Poll login status
  useEffect(() => {
    if (!sessionId) return;
    const id = setInterval(async () => {
      try {
        const result = await getLoginStatus(sessionId);
        setStatus(result.status);
        if (result.status === "logged_in") {
          clearInterval(id);
          navigate("/");
        }
        if (result.status === "failed" || result.status === "expired") {
          setError(result.error ?? STATUS_LABELS[result.status]);
          clearInterval(id);
        }
      } catch (e) {
        setError(String(e));
      }
    }, 2000);
    return () => clearInterval(id);
  }, [sessionId, navigate]);

  const handleStart = async () => {
    setError(null);
    try {
      const session = await startLogin();
      setSessionId(session.session_id);
      setNovncUrl(session.novnc_url);
      setStatus("waiting");
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? String(e);
      setError(detail);
    }
  };

  const handleCancel = async () => {
    if (sessionId) await cancelLogin(sessionId);
    navigate("/");
  };

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Log in to Instagram</h1>
        <p className="text-muted text-sm mt-1">
          This is the single account whose session will be used to scan all tracked
          profiles. Use a secondary account (not your main) — for example,{" "}
          <code className="text-foreground">trabalho_otimizado</code>.
        </p>
      </div>

      {existing && (
        <div className="flex items-start gap-2 p-3 bg-warning/10 border border-warning/30 rounded-xl text-sm text-warning">
          <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
          <span>
            Already logged in as <b>@{existing.username}</b>. Delete the current
            login from the dashboard before starting a new one.
          </span>
        </div>
      )}

      {!sessionId && !existing && (
        <div className="bg-surface border border-border rounded-2xl p-6 space-y-4">
          <div className="space-y-1.5">
            <p className="text-sm text-foreground">
              Clicking below opens an Instagram login window inside this container.
              Log in normally — 2FA and security challenges are handled by the real
              browser. The session is then saved (encrypted) and reused for all scans.
            </p>
            <ul className="text-sm text-muted list-disc list-inside space-y-0.5">
              <li>Use a throwaway/secondary account, never your main</li>
              <li>That account must follow each profile you want to track</li>
              <li>Session is Fernet-encrypted on disk; password is never stored</li>
            </ul>
          </div>
          <button
            onClick={handleStart}
            className="px-5 py-2.5 bg-primary hover:bg-primary-hover text-white rounded-xl font-medium transition-colors cursor-pointer"
          >
            Open Instagram login
          </button>
        </div>
      )}

      {sessionId && novncUrl && (
        <div className="bg-surface border border-border rounded-2xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 bg-surface-2 border-b border-border">
            <span className="text-sm flex items-center gap-2">
              {status === "waiting" || status === "pending" ? (
                <RefreshCw size={13} className="animate-spin text-primary" />
              ) : null}
              <span className="text-muted">{STATUS_LABELS[status] ?? status}</span>
            </span>
            <button
              onClick={handleCancel}
              className="flex items-center gap-1.5 text-sm text-danger hover:underline cursor-pointer"
            >
              <X size={14} />
              Cancel
            </button>
          </div>
          <iframe
            src={novncUrl}
            title="Instagram Login"
            className="w-full bg-black"
            style={{ height: "75vh", minHeight: 500 }}
          />
        </div>
      )}

      {error && (
        <div className="p-3 bg-danger/10 border border-danger/30 rounded-xl text-sm text-danger">
          {error}
        </div>
      )}
    </div>
  );
}
