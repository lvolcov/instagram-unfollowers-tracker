import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AtSign, ArrowRight, AlertTriangle, RefreshCw } from "lucide-react";

import { addTrackedAccount, getLoginAccount } from "@/services/api";

export function AddTrackedAccount() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [username, setUsername] = useState("");

  const { data: login, isLoading: loginLoading } = useQuery({
    queryKey: ["login-account"],
    queryFn: getLoginAccount,
  });

  const mutation = useMutation({
    mutationFn: (u: string) => addTrackedAccount(u),
    onSuccess: (tracked) => {
      qc.invalidateQueries({ queryKey: ["tracked-accounts"] });
      navigate(`/accounts/${tracked.id}?tab=overview`);
    },
  });

  const errorDetail =
    (mutation.error as { response?: { data?: { detail?: string } } } | null)
      ?.response?.data?.detail ?? (mutation.error ? String(mutation.error) : null);

  if (loginLoading) {
    return (
      <div className="flex items-center gap-2 text-muted py-12 justify-center">
        <RefreshCw size={18} className="animate-spin" /> Loading…
      </div>
    );
  }

  if (!login) {
    return (
      <div className="max-w-xl mx-auto space-y-4">
        <div className="flex items-start gap-2 p-3 bg-warning/10 border border-warning/30 rounded-xl text-sm text-warning">
          <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
          <span>
            You need to log in first. Tracked accounts are scanned through the
            single LoginAccount's session.
          </span>
        </div>
        <button
          onClick={() => navigate("/login")}
          className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-sm font-medium cursor-pointer"
        >
          Go to login
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Add tracked account</h1>
        <p className="text-muted text-sm mt-1">
          Logged in as <b>@{login.username}</b>. Add an Instagram username to track
          its followers / following. <b>@{login.username}</b> must follow the
          account, otherwise scans will be rejected.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (username.trim()) mutation.mutate(username.trim());
        }}
        className="bg-surface border border-border rounded-2xl p-5 space-y-4"
      >
        <label className="block">
          <span className="block text-sm font-medium mb-1.5">Instagram username</span>
          <div className="relative">
            <AtSign
              size={15}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none"
            />
            <input
              autoFocus
              value={username}
              onChange={(e) =>
                setUsername(e.target.value.replace(/^@/, "").toLowerCase())
              }
              placeholder="lvolcov"
              className="w-full bg-surface-2 border border-border rounded-xl pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 placeholder:text-muted"
            />
          </div>
        </label>

        <button
          type="submit"
          disabled={!username.trim() || mutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-sm font-medium disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
        >
          {mutation.isPending ? (
            <>
              <RefreshCw size={15} className="animate-spin" /> Checking…
            </>
          ) : (
            <>
              Add <ArrowRight size={15} />
            </>
          )}
        </button>

        {errorDetail && (
          <div className="p-3 bg-danger/10 border border-danger/30 rounded-xl text-sm text-danger">
            {errorDetail}
          </div>
        )}
      </form>
    </div>
  );
}
