import { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Star, ExternalLink, RefreshCw } from "lucide-react";

import {
  getAccount,
  getScanJob,
  listNonFollowers,
  triggerScan,
  addToWhitelist,
  removeFromWhitelist,
  listWhitelist,
} from "@/services/api";
import type { ScanJob } from "@/types/api";

export function AccountDetail() {
  const { id } = useParams<{ id: string }>();
  const accountId = Number(id);
  const qc = useQueryClient();

  const [hideWhitelisted, setHideWhitelisted] = useState(true);
  const [search, setSearch] = useState("");
  const [activeScan, setActiveScan] = useState<ScanJob | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { data: account } = useQuery({
    queryKey: ["account", accountId],
    queryFn: () => getAccount(accountId),
    enabled: !!accountId,
    refetchInterval: activeScan ? 3000 : false,
  });

  const { data: nonFollowersData, refetch: refetchNonFollowers } = useQuery({
    queryKey: ["non-followers", accountId, hideWhitelisted, search],
    queryFn: () => listNonFollowers(accountId, !hideWhitelisted, 1, search),
    enabled: !!accountId,
  });

  const { data: whitelist = [] } = useQuery({
    queryKey: ["whitelist", accountId],
    queryFn: () => listWhitelist(accountId),
    enabled: !!accountId,
  });

  const whitelistedIds = new Set(whitelist.map((w) => w.instagram_user_id));

  // Poll active scan job until done
  useEffect(() => {
    if (!activeScan || activeScan.status === "completed" || activeScan.status === "failed") {
      if (pollRef.current) clearInterval(pollRef.current);
      if (activeScan?.status === "completed") {
        qc.invalidateQueries({ queryKey: ["account", accountId] });
        qc.invalidateQueries({ queryKey: ["non-followers", accountId] });
      }
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const job = await getScanJob(accountId, activeScan.job_id);
        setActiveScan(job);
      } catch {
        /* ignore */
      }
    }, 2000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [activeScan?.status, activeScan?.job_id, accountId, qc]);

  const scanMutation = useMutation({
    mutationFn: () => triggerScan(accountId),
    onSuccess: (job) => setActiveScan(job),
  });

  const whitelistMutation = useMutation({
    mutationFn: ({ igId, username }: { igId: string; username: string }) =>
      addToWhitelist(accountId, { instagram_user_id: igId, username }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["whitelist", accountId] });
      qc.invalidateQueries({ queryKey: ["non-followers", accountId] });
    },
  });

  const unwhitelistMutation = useMutation({
    mutationFn: (entryId: number) => removeFromWhitelist(accountId, entryId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["whitelist", accountId] });
      qc.invalidateQueries({ queryKey: ["non-followers", accountId] });
    },
  });

  if (!account) return <p className="text-muted">Loading…</p>;

  const isScanning = activeScan?.status === "queued" || activeScan?.status === "running";
  const scanPhase = activeScan?.progress?.phase;
  const scanCount = activeScan?.progress?.current ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          {account.profile_pic_url && (
            <img src={account.profile_pic_url} alt={account.username} className="w-12 h-12 rounded-full" />
          )}
          <div>
            <h1 className="text-2xl font-semibold">@{account.username}</h1>
            {account.display_name && <p className="text-muted text-sm">{account.display_name}</p>}
            <p className="text-muted text-xs">
              {account.last_scan_at
                ? `Last scan: ${new Date(account.last_scan_at).toLocaleString()}`
                : "Never scanned"}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => scanMutation.mutate()}
            disabled={isScanning}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg disabled:opacity-50"
          >
            <RefreshCw size={16} className={isScanning ? "animate-spin" : ""} />
            {isScanning ? (scanPhase ? `${scanPhase} (${scanCount})` : "Queued…") : "Scan now"}
          </button>
          <Link
            to={`/accounts/${accountId}/unfollowers`}
            className="px-4 py-2 bg-surface hover:bg-surface-hover border border-border rounded-lg"
          >
            Unfollower history
          </Link>
        </div>
      </div>

      {/* Scan status banner */}
      {activeScan?.status === "completed" && activeScan.result && (
        <div className="p-3 bg-green-900/30 border border-green-700 rounded-xl text-sm">
          Scan complete — {activeScan.result.new_unfollowers} new unfollower
          {activeScan.result.new_unfollowers !== 1 ? "s" : ""} detected.
        </div>
      )}
      {activeScan?.status === "failed" && (
        <div className="p-3 bg-danger/20 border border-danger rounded-xl text-sm">
          Scan failed: {activeScan.error}
        </div>
      )}
      {account.session_status === "needs_relogin" && (
        <div className="p-3 bg-yellow-900/30 border border-yellow-700 rounded-xl text-sm">
          Session expired — <Link to="/accounts/add" className="underline">re-login</Link> to resume scanning.
        </div>
      )}

      {/* Non-followers panel */}
      <div className="bg-surface border border-border rounded-xl p-4">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search…"
            className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm min-w-40"
          />
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={hideWhitelisted}
              onChange={(e) => setHideWhitelisted(e.target.checked)}
            />
            Hide whitelisted
          </label>
          <button onClick={() => refetchNonFollowers()} className="text-muted hover:text-foreground">
            <RefreshCw size={14} />
          </button>
        </div>

        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">
            Non-followers
            {nonFollowersData?.total != null && (
              <span className="ml-2 text-sm text-muted font-normal">
                ({nonFollowersData.total})
              </span>
            )}
          </h2>
        </div>

        {!nonFollowersData?.users?.length ? (
          <p className="text-muted text-sm">
            {nonFollowersData === undefined
              ? "Loading…"
              : account.last_scan_at
              ? "Everyone you follow also follows you back."
              : "Run a scan to see who isn't following you back."}
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {nonFollowersData.users.map((u: any) => {
              const isWL = whitelistedIds.has(u.instagram_user_id);
              const wlEntry = whitelist.find((w) => w.instagram_user_id === u.instagram_user_id);
              return (
                <li key={u.instagram_user_id} className="py-2.5 flex items-center gap-3">
                  {u.profile_pic_url ? (
                    <img src={u.profile_pic_url} alt={u.username} className="w-9 h-9 rounded-full flex-shrink-0" />
                  ) : (
                    <div className="w-9 h-9 rounded-full bg-surface-hover flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <a
                      href={`https://www.instagram.com/${u.username}`}
                      target="_blank"
                      rel="noreferrer"
                      className="font-medium hover:underline flex items-center gap-1"
                    >
                      @{u.username}
                      <ExternalLink size={12} className="text-muted" />
                    </a>
                    {u.full_name && <div className="text-xs text-muted truncate">{u.full_name}</div>}
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {u.is_verified && <span className="text-xs text-blue-400">✓</span>}
                    {u.is_private && <span className="text-xs text-muted">🔒</span>}
                    <button
                      onClick={() =>
                        isWL
                          ? wlEntry && unwhitelistMutation.mutate(wlEntry.id)
                          : whitelistMutation.mutate({ igId: u.instagram_user_id, username: u.username })
                      }
                      title={isWL ? "Remove from whitelist" : "Whitelist (ignore)"}
                      className={`p-1.5 rounded-lg transition ${
                        isWL
                          ? "text-yellow-400 bg-yellow-900/30 hover:bg-yellow-900/50"
                          : "text-muted hover:text-foreground hover:bg-surface-hover"
                      }`}
                    >
                      <Star size={14} fill={isWL ? "currentColor" : "none"} />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
