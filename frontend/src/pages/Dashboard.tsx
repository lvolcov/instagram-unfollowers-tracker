import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listAccounts } from "@/services/api";

export function Dashboard() {
  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: listAccounts,
  });

  if (isLoading) return <p className="text-muted">Loading…</p>;

  if (accounts.length === 0) {
    return (
      <div className="text-center py-16">
        <h1 className="text-2xl font-semibold mb-2">No accounts tracked yet</h1>
        <p className="text-muted mb-6">Add your first Instagram account to get started.</p>
        <Link
          to="/accounts/add"
          className="inline-block px-5 py-2.5 bg-primary hover:bg-primary-hover rounded-lg font-medium"
        >
          Add Account
        </Link>
      </div>
    );
  }

  return (
    <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
      {accounts.map((a) => (
        <Link
          key={a.id}
          to={`/accounts/${a.id}`}
          className="bg-surface border border-border rounded-xl p-4 hover:bg-surface-hover transition"
        >
          <div className="font-semibold">@{a.username}</div>
          <div className="text-sm text-muted">
            {a.last_scan_at ? `Last scan: ${new Date(a.last_scan_at).toLocaleString()}` : "Never scanned"}
          </div>
          {a.session_status === "needs_relogin" && (
            <div className="text-sm text-danger mt-2">Session expired — re-login required</div>
          )}
        </Link>
      ))}
    </div>
  );
}
