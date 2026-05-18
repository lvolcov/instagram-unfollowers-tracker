import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";

import { getAccount, listNonFollowers, triggerScan } from "@/services/api";

export function AccountDetail() {
  const { id } = useParams<{ id: string }>();
  const accountId = Number(id);
  const [hideWhitelisted, setHideWhitelisted] = useState(true);
  const [search, setSearch] = useState("");

  const { data: account } = useQuery({
    queryKey: ["account", accountId],
    queryFn: () => getAccount(accountId),
    enabled: !!accountId,
  });

  const { data: nonFollowers } = useQuery({
    queryKey: ["non-followers", accountId, hideWhitelisted, search],
    queryFn: () => listNonFollowers(accountId, !hideWhitelisted, 1, search),
    enabled: !!accountId,
  });

  const scanMutation = useMutation({
    mutationFn: () => triggerScan(accountId),
  });

  if (!account) return <p className="text-muted">Loading…</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">@{account.username}</h1>
        <div className="flex gap-2">
          <button
            onClick={() => scanMutation.mutate()}
            disabled={scanMutation.isPending}
            className="px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg disabled:opacity-50"
          >
            {scanMutation.isPending ? "Starting…" : "Scan now"}
          </button>
          <Link
            to={`/accounts/${accountId}/unfollowers`}
            className="px-4 py-2 bg-surface hover:bg-surface-hover border border-border rounded-lg"
          >
            History
          </Link>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-xl p-4">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search…"
            className="flex-1 bg-background border border-border rounded-lg px-3 py-2"
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={hideWhitelisted}
              onChange={(e) => setHideWhitelisted(e.target.checked)}
            />
            Hide whitelisted
          </label>
        </div>

        <h2 className="font-semibold mb-2">Non-followers</h2>
        {nonFollowers?.users?.length ? (
          <ul className="divide-y divide-border">
            {/* TODO: render rows with whitelist star button */}
          </ul>
        ) : (
          <p className="text-muted text-sm">
            No non-followers found. Run a scan if this is your first time.
          </p>
        )}
      </div>
    </div>
  );
}
