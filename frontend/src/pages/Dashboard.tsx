import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import {
  Plus,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  LogOut,
  Lock,
} from "lucide-react";

import {
  deleteLoginAccount,
  deleteTrackedAccount,
  getLoginAccount,
  listTrackedAccounts,
} from "@/services/api";
import { Avatar } from "@/components/common/Avatar";

export function Dashboard() {
  const qc = useQueryClient();
  const navigate = useNavigate();

  const { data: login, isLoading: loginLoading } = useQuery({
    queryKey: ["login-account"],
    queryFn: getLoginAccount,
  });
  const { data: tracked = [], isLoading: trackedLoading } = useQuery({
    queryKey: ["tracked-accounts"],
    queryFn: listTrackedAccounts,
    enabled: !!login,
  });

  const logoutMutation = useMutation({
    mutationFn: deleteLoginAccount,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["login-account"] });
      qc.invalidateQueries({ queryKey: ["tracked-accounts"] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (id: number) => deleteTrackedAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tracked-accounts"] }),
  });

  if (loginLoading) {
    return (
      <div className="flex items-center justify-center h-48 text-muted">
        <RefreshCw size={20} className="animate-spin mr-2" />
        Loading…
      </div>
    );
  }

  // No login → CTA
  if (!login) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
          <Lock size={28} className="text-primary" />
        </div>
        <h1 className="text-2xl font-bold mb-2">No login configured</h1>
        <p className="text-muted mb-6 max-w-sm">
          Log in with a secondary Instagram account. That session will be used to
          scan any tracked profile (e.g. your main account) without ever logging
          into the main itself.
        </p>
        <Link
          to="/login"
          className="px-5 py-2.5 bg-primary hover:bg-primary-hover text-white rounded-xl font-medium transition-colors cursor-pointer"
        >
          Log in
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Login banner */}
      <div className="bg-surface border border-border rounded-2xl p-4 flex items-center gap-3">
        <Avatar
          src={login.profile_pic_url}
          username={login.username}
          size={44}
        />
        <div className="flex-1 min-w-0">
          <p className="text-xs uppercase tracking-wider text-muted">
            Logged in as
          </p>
          <p className="font-semibold truncate">@{login.username}</p>
          {login.session_status === "needs_relogin" && (
            <p className="text-xs text-warning flex items-center gap-1">
              <AlertTriangle size={11} /> Session expired — please re-login
            </p>
          )}
        </div>
        <button
          onClick={() => {
            if (confirm("Log out and delete this session?")) {
              logoutMutation.mutate();
            }
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-danger hover:bg-danger/10 rounded-lg transition-colors cursor-pointer"
        >
          <LogOut size={14} /> Log out
        </button>
      </div>

      {/* Tracked accounts */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tracked accounts</h1>
          <p className="text-muted text-sm mt-0.5">
            {tracked.length} account{tracked.length !== 1 ? "s" : ""} being tracked
          </p>
        </div>
        <Link
          to="/tracked/add"
          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-sm font-medium transition-colors cursor-pointer"
        >
          <Plus size={16} /> Add tracked account
        </Link>
      </div>

      {trackedLoading ? (
        <div className="flex items-center gap-2 text-muted py-8 justify-center">
          <RefreshCw size={16} className="animate-spin" /> Loading…
        </div>
      ) : tracked.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center bg-surface border border-border rounded-2xl">
          <Plus size={28} className="text-muted mb-3" />
          <p className="font-medium mb-1">No tracked accounts yet</p>
          <p className="text-muted text-sm mb-4">
            Add a username to track its followers and unfollowers.
          </p>
          <Link
            to="/tracked/add"
            className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-sm font-medium cursor-pointer"
          >
            Add tracked account
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {tracked.map((t) => (
            <div
              key={t.id}
              className="bg-surface border border-border rounded-2xl p-4 hover:bg-surface-2 transition-colors group"
            >
              <button
                onClick={() => navigate(`/accounts/${t.id}?tab=overview`)}
                className="w-full text-left cursor-pointer"
              >
                <div className="flex items-start gap-3">
                  <Avatar
                    src={t.profile_pic_url}
                    username={t.username}
                    size={48}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold truncate">@{t.username}</p>
                    {t.display_name && (
                      <p className="text-sm text-muted truncate">
                        {t.display_name}
                      </p>
                    )}
                    {t.is_private && (
                      <p className="text-xs text-muted flex items-center gap-1 mt-0.5">
                        <Lock size={10} /> Private
                      </p>
                    )}
                  </div>
                </div>
              </button>

              <div className="mt-3 pt-3 border-t border-border flex items-center justify-between">
                <span className="text-xs text-muted">
                  {t.last_scan_at
                    ? `Scanned ${new Date(t.last_scan_at).toLocaleDateString()}`
                    : "Never scanned"}
                </span>
                {t.we_follow ? (
                  <span className="flex items-center gap-1 text-xs text-success">
                    <CheckCircle size={11} /> Following
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs text-warning">
                    <AlertTriangle size={11} /> Not following
                  </span>
                )}
              </div>

              <button
                onClick={() => {
                  if (confirm(`Remove @${t.username} from tracking?`)) {
                    removeMutation.mutate(t.id);
                  }
                }}
                className="mt-2 w-full text-xs text-muted hover:text-danger cursor-pointer"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
