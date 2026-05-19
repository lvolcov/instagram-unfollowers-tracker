import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  RefreshCw,
  ExternalLink,
  Star,
  ShieldCheck,
  Lock,
  Search,
  X,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
} from "lucide-react";

import {
  getTrackedAccount,
  getScanJob,
  listFollowers,
  listFollowersNotFollowingBack,
  listFollowing,
  listNonFollowers,
  listUnfollowers,
  listWhitelist,
  addToWhitelist,
  removeFromWhitelist,
  triggerScan,
} from "@/services/api";
import { Avatar } from "@/components/common/Avatar";
import type { IGUser, ScanJob, Unfollower, WhitelistEntry } from "@/types/api";

// ── Stat card ──────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <div className="bg-surface border border-border rounded-2xl p-4">
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm font-medium mt-0.5">{label}</p>
      {sub && <p className="text-xs text-muted mt-0.5">{sub}</p>}
    </div>
  );
}

// ── User row ───────────────────────────────────────────────────────────────

interface UserRowProps {
  user: IGUser & { relationship?: string };
  whitelistEntry?: WhitelistEntry;
  isWhitelisted?: boolean;
  onWhitelist?: () => void;
  onUnwhitelist?: () => void;
}

function UserRow({ user, isWhitelisted, whitelistEntry, onWhitelist, onUnwhitelist }: UserRowProps) {
  return (
    <li className="flex items-center gap-3 py-2.5 group">
      <Avatar src={user.profile_pic_url} username={user.username} size={36} />
      <div className="flex-1 min-w-0">
        <a
          href={`https://www.instagram.com/${user.username}`}
          target="_blank"
          rel="noreferrer"
          className="font-medium hover:text-primary transition-colors flex items-center gap-1 cursor-pointer"
        >
          @{user.username}
          <ExternalLink size={11} className="text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
        </a>
        {user.full_name && (
          <p className="text-xs text-muted truncate">{user.full_name}</p>
        )}
      </div>
      <div className="flex items-center gap-1.5 flex-shrink-0">
        {user.is_verified && (
          <ShieldCheck size={14} className="text-primary" aria-label="Verified" />
        )}
        {user.is_private && (
          <Lock size={13} className="text-muted" aria-label="Private" />
        )}
        {(onWhitelist || onUnwhitelist) && (
          <button
            onClick={() =>
              isWhitelisted && whitelistEntry
                ? onUnwhitelist?.()
                : onWhitelist?.()
            }
            title={isWhitelisted ? "Remove from whitelist" : "Add to whitelist"}
            className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
              isWhitelisted
                ? "text-warning bg-warning/10 hover:bg-warning/20"
                : "text-muted hover:text-foreground hover:bg-surface-2"
            }`}
          >
            <Star size={14} fill={isWhitelisted ? "currentColor" : "none"} />
          </button>
        )}
      </div>
    </li>
  );
}

// ── Paginated user list ────────────────────────────────────────────────────

interface UserListProps {
  accountId: number;
  queryKey: string[];
  queryFn: (page: number, search: string) => Promise<{ users: IGUser[]; total: number }>;
  emptyMessage: string;
  showWhitelistToggle?: boolean;
}

function UserList({ accountId, queryKey, queryFn, emptyMessage, showWhitelistToggle }: UserListProps) {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearchChange = (val: string) => {
    setSearch(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(val);
      setPage(1);
    }, 300);
  };

  const { data, isLoading } = useQuery({
    queryKey: [...queryKey, page, debouncedSearch],
    queryFn: () => queryFn(page, debouncedSearch),
  });

  const { data: whitelist = [] } = useQuery({
    queryKey: ["whitelist", accountId],
    queryFn: () => listWhitelist(accountId),
    enabled: showWhitelistToggle,
  });

  const whitelistedIds = new Set(whitelist.map((w) => w.instagram_user_id));

  const whitelistMutation = useMutation({
    mutationFn: ({ igId, username }: { igId: string; username: string }) =>
      addToWhitelist(accountId, { instagram_user_id: igId, username }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["whitelist", accountId] }),
  });

  const unwhitelistMutation = useMutation({
    mutationFn: (entryId: number) => removeFromWhitelist(accountId, entryId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["whitelist", accountId] }),
  });

  const users: (IGUser & { relationship?: string })[] = data?.users ?? [];
  const total: number = data?.total ?? 0;
  const pageSize = 50;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="relative">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
        <input
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="Search by username…"
          className="w-full bg-surface-2 border border-border rounded-xl pl-9 pr-8 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 placeholder:text-muted"
        />
        {search && (
          <button
            onClick={() => handleSearchChange("")}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-foreground cursor-pointer"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* Count + pagination */}
      {!isLoading && (
        <div className="flex items-center justify-between text-sm text-muted">
          <span>{total.toLocaleString()} {total === 1 ? "person" : "people"}</span>
          {totalPages > 1 && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1 rounded hover:bg-surface-2 disabled:opacity-30 cursor-pointer disabled:cursor-default"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="px-1">{page} / {totalPages}</span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-1 rounded hover:bg-surface-2 disabled:opacity-30 cursor-pointer disabled:cursor-default"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          )}
        </div>
      )}

      {/* List */}
      {isLoading ? (
        <div className="flex items-center gap-2 text-muted py-8 justify-center">
          <RefreshCw size={16} className="animate-spin" />
          Loading…
        </div>
      ) : users.length === 0 ? (
        <p className="text-muted text-sm py-8 text-center">{emptyMessage}</p>
      ) : (
        <ul className="divide-y divide-border">
          {users.map((u) => {
            const isWL = whitelistedIds.has(u.instagram_user_id);
            const wlEntry = whitelist.find((w) => w.instagram_user_id === u.instagram_user_id);
            return (
              <UserRow
                key={u.instagram_user_id}
                user={u}
                isWhitelisted={isWL}
                whitelistEntry={wlEntry}
                onWhitelist={
                  showWhitelistToggle
                    ? () => whitelistMutation.mutate({ igId: u.instagram_user_id, username: u.username })
                    : undefined
                }
                onUnwhitelist={
                  showWhitelistToggle && wlEntry
                    ? () => unwhitelistMutation.mutate(wlEntry.id)
                    : undefined
                }
              />
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ── Overview tab ───────────────────────────────────────────────────────────

function OverviewTab({ accountId }: { accountId: number }) {
  const { data: followers } = useQuery({
    queryKey: ["followers", accountId, 1, ""],
    queryFn: () => listFollowers(accountId, 1, ""),
  });
  const { data: following } = useQuery({
    queryKey: ["following", accountId, 1, ""],
    queryFn: () => listFollowing(accountId, 1, ""),
  });
  const { data: nonFollowers } = useQuery({
    queryKey: ["non-followers", accountId, false, 1, ""],
    queryFn: () => listNonFollowers(accountId, false, 1, ""),
  });
  const { data: notFollowing } = useQuery({
    queryKey: ["not-following", accountId, 1, ""],
    queryFn: () => listFollowersNotFollowingBack(accountId, 1, ""),
  });
  const { data: unfollowers = [] } = useQuery({
    queryKey: ["unfollowers", accountId],
    queryFn: () => listUnfollowers(accountId),
  });

  const recent = unfollowers.slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Followers" value={followers?.total ?? "—"} />
        <StatCard label="Following" value={following?.total ?? "—"} />
        <StatCard
          label="Not following back"
          value={nonFollowers?.total ?? "—"}
          sub="You follow → they don't"
        />
        <StatCard
          label="Doesn't follow back"
          value={notFollowing?.total ?? "—"}
          sub="They follow → you don't"
        />
      </div>

      {recent.length > 0 && (
        <div className="bg-surface border border-border rounded-2xl p-4">
          <h3 className="font-semibold mb-3 text-sm">Recent unfollowers</h3>
          <ul className="divide-y divide-border">
            {recent.map((u: Unfollower) => (
              <li key={u.id} className="flex items-center gap-3 py-2.5 group">
                <Avatar src={u.profile_pic_url} username={u.username} size={32} />
                <div className="flex-1 min-w-0">
                  <a
                    href={`https://www.instagram.com/${u.username}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm font-medium hover:text-primary transition-colors flex items-center gap-1 cursor-pointer"
                  >
                    @{u.username}
                    <ExternalLink size={10} className="text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                  </a>
                </div>
                <span className="text-xs text-muted flex-shrink-0">
                  {new Date(u.detected_at).toLocaleDateString()}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Whitelist tab ──────────────────────────────────────────────────────────

function WhitelistTab({ accountId }: { accountId: number }) {
  const qc = useQueryClient();
  const { data: whitelist = [], isLoading } = useQuery({
    queryKey: ["whitelist", accountId],
    queryFn: () => listWhitelist(accountId),
  });

  const removeMutation = useMutation({
    mutationFn: (id: number) => removeFromWhitelist(accountId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["whitelist", accountId] }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-muted py-8 justify-center">
        <RefreshCw size={16} className="animate-spin" /> Loading…
      </div>
    );
  }

  if (whitelist.length === 0) {
    return (
      <p className="text-muted text-sm py-8 text-center">
        No whitelist entries. Star users in the "Not following back" tab to add them here.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-muted">{whitelist.length} whitelisted user{whitelist.length !== 1 ? "s" : ""}</p>
      <ul className="divide-y divide-border">
        {whitelist.map((entry: WhitelistEntry) => (
          <li key={entry.id} className="flex items-center gap-3 py-2.5">
            <div className="w-8 h-8 rounded-full bg-warning/10 flex items-center justify-center flex-shrink-0">
              <Star size={14} className="text-warning" fill="currentColor" />
            </div>
            <div className="flex-1 min-w-0">
              <a
                href={`https://www.instagram.com/${entry.username}`}
                target="_blank"
                rel="noreferrer"
                className="text-sm font-medium hover:text-primary transition-colors cursor-pointer"
              >
                @{entry.username}
              </a>
              {entry.note && <p className="text-xs text-muted">{entry.note}</p>}
            </div>
            <span className="text-xs text-muted flex-shrink-0">
              {new Date(entry.added_at).toLocaleDateString()}
            </span>
            <button
              onClick={() => removeMutation.mutate(entry.id)}
              className="p-1.5 rounded-lg text-muted hover:text-danger hover:bg-danger/10 transition-colors cursor-pointer"
              title="Remove from whitelist"
            >
              <X size={14} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── History tab ────────────────────────────────────────────────────────────

function HistoryTab({ accountId }: { accountId: number }) {
  const { data: unfollowers = [], isLoading } = useQuery({
    queryKey: ["unfollowers", accountId],
    queryFn: () => listUnfollowers(accountId),
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-muted py-8 justify-center">
        <RefreshCw size={16} className="animate-spin" /> Loading…
      </div>
    );
  }

  if (unfollowers.length === 0) {
    return <p className="text-muted text-sm py-8 text-center">No unfollowers detected yet.</p>;
  }

  return (
    <ul className="divide-y divide-border">
      {unfollowers.map((u: Unfollower) => (
        <li key={u.id} className="flex items-center gap-3 py-2.5 group">
          <Avatar src={u.profile_pic_url} username={u.username} size={36} />
          <div className="flex-1 min-w-0">
            <a
              href={`https://www.instagram.com/${u.username}`}
              target="_blank"
              rel="noreferrer"
              className="font-medium hover:text-primary transition-colors flex items-center gap-1 cursor-pointer"
            >
              @{u.username}
              <ExternalLink size={11} className="text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>
            {u.full_name && <p className="text-xs text-muted">{u.full_name}</p>}
          </div>
          <span className="text-xs text-muted flex-shrink-0">
            {new Date(u.detected_at).toLocaleDateString()}
          </span>
        </li>
      ))}
    </ul>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

const TAB_LABELS: Record<string, string> = {
  overview: "Overview",
  followers: "Followers",
  following: "Following",
  "non-followers": "Not following back",
  "not-following": "Doesn't follow back",
  whitelist: "Whitelist",
  history: "Unfollower history",
};

export function AccountDetail() {
  const { id } = useParams<{ id: string }>();
  const accountId = Number(id);
  const qc = useQueryClient();
  const [searchParams] = useSearchParams();
  const tab = searchParams.get("tab") ?? "overview";

  const [activeScan, setActiveScan] = useState<ScanJob | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { data: account } = useQuery({
    queryKey: ["tracked-account", accountId],
    queryFn: () => getTrackedAccount(accountId),
    enabled: !!accountId,
  });

  // Poll active scan
  useEffect(() => {
    if (!activeScan || activeScan.status === "completed" || activeScan.status === "failed") {
      if (pollRef.current) clearInterval(pollRef.current);
      if (activeScan?.status === "completed") {
        qc.invalidateQueries({ queryKey: ["tracked-account", accountId] });
        qc.invalidateQueries({ queryKey: ["followers", accountId] });
        qc.invalidateQueries({ queryKey: ["following", accountId] });
        qc.invalidateQueries({ queryKey: ["non-followers", accountId] });
        qc.invalidateQueries({ queryKey: ["not-following", accountId] });
        qc.invalidateQueries({ queryKey: ["unfollowers", accountId] });
      }
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const job = await getScanJob(accountId, activeScan.job_id);
        setActiveScan(job);
      } catch { /* ignore */ }
    }, 2000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [activeScan?.status, activeScan?.job_id, accountId, qc]);

  const scanMutation = useMutation({
    mutationFn: () => triggerScan(accountId),
    onSuccess: (job) => setActiveScan(job),
  });

  if (!account) {
    return (
      <div className="flex items-center gap-2 text-muted py-12 justify-center">
        <RefreshCw size={18} className="animate-spin" /> Loading account…
      </div>
    );
  }

  const isScanning = activeScan?.status === "queued" || activeScan?.status === "running";

  return (
    <div className="space-y-5">
      {/* Account header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <Avatar src={account.profile_pic_url} username={account.username} size={48} />
          <div>
            <h1 className="text-xl font-bold">@{account.username}</h1>
            {account.display_name && (
              <p className="text-sm text-muted">{account.display_name}</p>
            )}
            <p className="text-xs text-muted mt-0.5">
              {account.last_scan_at
                ? `Last scan: ${new Date(account.last_scan_at).toLocaleString()}`
                : "Never scanned"}
            </p>
          </div>
        </div>

        <button
          onClick={() => scanMutation.mutate()}
          disabled={isScanning}
          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
        >
          <RefreshCw size={15} className={isScanning ? "animate-spin" : ""} />
          {isScanning
            ? activeScan?.progress?.phase
              ? `${activeScan.progress.phase} (${activeScan.progress.current})`
              : "Scanning…"
            : "Scan now"}
        </button>
      </div>

      {/* Banners */}
      {activeScan?.status === "completed" && activeScan.result && (
        <>
          <div className="flex items-center gap-2 p-3 bg-success/10 border border-success/30 rounded-xl text-sm text-success">
            Scan complete — {activeScan.result.new_unfollowers} new unfollower
            {activeScan.result.new_unfollowers !== 1 ? "s" : ""} detected.
          </div>
          {activeScan.result.warning && (
            <div className="flex items-start gap-2 p-3 bg-warning/10 border border-warning/30 rounded-xl text-sm text-warning">
              <AlertTriangle size={15} className="flex-shrink-0 mt-0.5" />
              <span>{activeScan.result.warning}</span>
            </div>
          )}
        </>
      )}
      {activeScan?.status === "failed" && (
        <div className="p-3 bg-danger/10 border border-danger/30 rounded-xl text-sm text-danger">
          Scan failed: {activeScan.error}
        </div>
      )}
      {!account.we_follow && (
        <div className="flex items-center gap-2 p-3 bg-warning/10 border border-warning/30 rounded-xl text-sm text-warning">
          <AlertTriangle size={15} />
          The logged-in account does not follow @{account.username}. Follow them
          from the logged-in profile, then retry the scan.
        </div>
      )}

      {/* Section title */}
      <div className="border-b border-border pb-2">
        <h2 className="font-semibold text-foreground">{TAB_LABELS[tab] ?? tab}</h2>
      </div>

      {/* Tab content */}
      <div>
        {tab === "overview" && <OverviewTab accountId={accountId} />}

        {tab === "followers" && (
          <UserList
            accountId={accountId}
            queryKey={["followers", String(accountId)]}
            queryFn={(page, search) => listFollowers(accountId, page, search)}
            emptyMessage="No followers found. Run a scan first."
          />
        )}

        {tab === "following" && (
          <UserList
            accountId={accountId}
            queryKey={["following", String(accountId)]}
            queryFn={(page, search) => listFollowing(accountId, page, search)}
            emptyMessage="Not following anyone. Run a scan first."
          />
        )}

        {tab === "non-followers" && (
          <UserList
            accountId={accountId}
            queryKey={["non-followers", String(accountId)]}
            queryFn={(page, search) => listNonFollowers(accountId, false, page, search)}
            emptyMessage="Everyone you follow also follows you back."
            showWhitelistToggle
          />
        )}

        {tab === "not-following" && (
          <UserList
            accountId={accountId}
            queryKey={["not-following", String(accountId)]}
            queryFn={(page, search) => listFollowersNotFollowingBack(accountId, page, search)}
            emptyMessage="You follow everyone who follows you."
          />
        )}

        {tab === "whitelist" && <WhitelistTab accountId={accountId} />}

        {tab === "history" && <HistoryTab accountId={accountId} />}
      </div>
    </div>
  );
}
