import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { cancelLogin, getLoginStatus, startLogin } from "@/services/api";

export function AddAccount() {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [novncUrl, setNovncUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    const id = setInterval(async () => {
      try {
        const result = await getLoginStatus(sessionId);
        setStatus(result.status);
        if (result.status === "logged_in" && result.account) {
          clearInterval(id);
          navigate(`/accounts/${result.account.id}`);
        }
        if (result.status === "failed") {
          setError(result.error ?? "Login failed");
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
    const session = await startLogin();
    setSessionId(session.session_id);
    setNovncUrl(session.novnc_url);
    setStatus("waiting");
  };

  const handleCancel = async () => {
    if (sessionId) await cancelLogin(sessionId);
    navigate("/");
  };

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Add Instagram Account</h1>

      {!sessionId && (
        <div className="bg-surface border border-border rounded-xl p-6">
          <p className="text-muted mb-4">
            Clicking the button below opens an Instagram login window inside this container. Log
            in normally — including 2FA or security challenges. Once you complete login, the
            container will save your session and start tracking your followers.
          </p>
          <button
            onClick={handleStart}
            className="px-5 py-2.5 bg-primary hover:bg-primary-hover rounded-lg font-medium"
          >
            Open Instagram Login
          </button>
        </div>
      )}

      {sessionId && novncUrl && (
        <div className="bg-surface border border-border rounded-xl overflow-hidden">
          <div className="flex items-center justify-between p-3 bg-surface-hover border-b border-border">
            <span className="text-sm text-muted">Status: {status}</span>
            <button onClick={handleCancel} className="text-sm text-danger hover:underline">
              Cancel
            </button>
          </div>
          <iframe
            src={novncUrl}
            title="Instagram Login"
            className="w-full h-[640px] bg-black"
          />
        </div>
      )}

      {error && <div className="mt-4 p-3 bg-danger/20 border border-danger rounded-lg">{error}</div>}
    </div>
  );
}
