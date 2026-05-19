import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle,
  RefreshCw,
  Send,
  Info,
  Plus,
  Trash2,
  Pencil,
  AlertTriangle,
} from "lucide-react";

import {
  createSchedule,
  deleteSchedule,
  getAppSettings,
  getSettings,
  listSchedules,
  listTrackedAccounts,
  testHealthWebhook,
  testWebhook,
  updateAppSettings,
  updateSchedule,
} from "@/services/api";
import { useTheme } from "@/contexts/ThemeContext";
import type {
  Schedule,
  ScheduleCreate,
  ScheduleMode,
  TrackedAccount,
} from "@/types/api";

// ── Helpers ────────────────────────────────────────────────────────────────

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function summarise(s: Schedule): string {
  if (s.mode === "daily_at") return `Daily at ${s.daily_time ?? "—"}`;
  if (s.mode === "weekly_on") {
    const day = s.weekly_day != null ? DAY_LABELS[s.weekly_day] : "?";
    return `Weekly on ${day} at ${s.daily_time ?? "—"}`;
  }
  if (s.mode === "interval_hours")
    return `Every ${s.interval_hours ?? "?"} hour${s.interval_hours === 1 ? "" : "s"}`;
  return s.mode;
}

function SettingRow({
  label,
  value,
}: {
  label: string;
  value: string | boolean | null | undefined;
}) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-border last:border-b-0">
      <span className="text-sm text-muted">{label}</span>
      <span className="text-sm font-medium">
        {typeof value === "boolean" ? (
          value ? (
            <span className="flex items-center gap-1 text-success">
              <CheckCircle size={13} /> Enabled
            </span>
          ) : (
            <span className="text-muted">Disabled</span>
          )
        ) : (
          value ?? <span className="text-muted italic">Not set</span>
        )}
      </span>
    </div>
  );
}

// ── Schedule editor modal ──────────────────────────────────────────────────

interface ScheduleFormProps {
  initial: Partial<Schedule> | null;
  tracked: TrackedAccount[];
  onCancel: () => void;
  onSave: (data: ScheduleCreate) => void;
  saving: boolean;
}

function ScheduleForm({ initial, tracked, onCancel, onSave, saving }: ScheduleFormProps) {
  const [trackedId, setTrackedId] = useState<number>(
    initial?.tracked_account_id ?? tracked[0]?.id ?? 0
  );
  const [name, setName] = useState(initial?.name ?? "");
  const [mode, setMode] = useState<ScheduleMode>((initial?.mode as ScheduleMode) ?? "daily_at");
  const [dailyTime, setDailyTime] = useState(initial?.daily_time ?? "09:00");
  const [weeklyDay, setWeeklyDay] = useState<number>(initial?.weekly_day ?? 0);
  const [intervalHours, setIntervalHours] = useState<number>(initial?.interval_hours ?? 6);
  const [webhookUrl, setWebhookUrl] = useState(initial?.webhook_url ?? "");
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      tracked_account_id: trackedId,
      name,
      mode,
      daily_time: mode === "daily_at" || mode === "weekly_on" ? dailyTime : null,
      weekly_day: mode === "weekly_on" ? weeklyDay : null,
      interval_hours: mode === "interval_hours" ? intervalHours : null,
      webhook_url: webhookUrl.trim() || null,
      enabled,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={onCancel}
    >
      <form
        onSubmit={submit}
        onClick={(e) => e.stopPropagation()}
        className="bg-surface border border-border rounded-2xl w-full max-w-md space-y-4 p-5"
      >
        <h3 className="font-semibold text-lg">
          {initial?.id ? "Edit schedule" : "New schedule"}
        </h3>

        <label className="block">
          <span className="text-sm text-muted">Name (optional)</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Morning check"
            className="mt-1 w-full bg-surface-2 border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </label>

        <label className="block">
          <span className="text-sm text-muted">Tracked account</span>
          <select
            value={trackedId}
            onChange={(e) => setTrackedId(Number(e.target.value))}
            className="mt-1 w-full bg-surface-2 border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            {tracked.map((t) => (
              <option key={t.id} value={t.id}>
                @{t.username}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-sm text-muted">Frequency</span>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as ScheduleMode)}
            className="mt-1 w-full bg-surface-2 border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            <option value="daily_at">Daily at specific time</option>
            <option value="weekly_on">Weekly on day + time</option>
            <option value="interval_hours">Every N hours</option>
          </select>
        </label>

        {(mode === "daily_at" || mode === "weekly_on") && (
          <label className="block">
            <span className="text-sm text-muted">Time (HH:MM, container timezone)</span>
            <input
              type="time"
              value={dailyTime}
              onChange={(e) => setDailyTime(e.target.value)}
              className="mt-1 w-full bg-surface-2 border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </label>
        )}

        {mode === "weekly_on" && (
          <label className="block">
            <span className="text-sm text-muted">Day of week</span>
            <select
              value={weeklyDay}
              onChange={(e) => setWeeklyDay(Number(e.target.value))}
              className="mt-1 w-full bg-surface-2 border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              {DAY_LABELS.map((d, i) => (
                <option key={d} value={i}>
                  {d}
                </option>
              ))}
            </select>
          </label>
        )}

        {mode === "interval_hours" && (
          <label className="block">
            <span className="text-sm text-muted">Interval (hours)</span>
            <input
              type="number"
              min={1}
              value={intervalHours}
              onChange={(e) => setIntervalHours(Number(e.target.value))}
              className="mt-1 w-full bg-surface-2 border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </label>
        )}

        <label className="block">
          <span className="text-sm text-muted">
            Webhook URL (optional override)
          </span>
          <input
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://homeassistant.local:8123/api/webhook/..."
            className="mt-1 w-full bg-surface-2 border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
          <span className="text-xs text-muted mt-1 block">
            Leave blank to use the default HA webhook from <code>.env</code>.
          </span>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="h-4 w-4 accent-primary"
          />
          Enabled
        </label>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded-xl text-sm text-muted hover:bg-surface-2 cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving || !trackedId}
            className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-sm font-medium disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export function Settings() {
  const qc = useQueryClient();
  const { theme, toggle } = useTheme();

  const { data: settings, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
  });
  const { data: appSettings } = useQuery({
    queryKey: ["app-settings"],
    queryFn: getAppSettings,
  });
  const { data: tracked = [] } = useQuery({
    queryKey: ["tracked-accounts"],
    queryFn: listTrackedAccounts,
  });
  const { data: schedules = [], isLoading: schedLoading } = useQuery({
    queryKey: ["schedules"],
    queryFn: listSchedules,
  });

  const [healthUrl, setHealthUrl] = useState("");
  useEffect(() => {
    if (appSettings?.health_webhook_url != null) setHealthUrl(appSettings.health_webhook_url);
  }, [appSettings?.health_webhook_url]);

  const testMutation = useMutation({ mutationFn: () => testWebhook() });
  const saveHealth = useMutation({
    mutationFn: (url: string) => updateAppSettings({ health_webhook_url: url }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["app-settings"] }),
  });
  const testHealth = useMutation({ mutationFn: testHealthWebhook });

  const [editing, setEditing] = useState<Partial<Schedule> | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const createMut = useMutation({
    mutationFn: (data: ScheduleCreate) => createSchedule(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["schedules"] });
      setModalOpen(false);
    },
  });
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: ScheduleCreate }) =>
      updateSchedule(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["schedules"] });
      setModalOpen(false);
    },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteSchedule(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules"] }),
  });
  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      updateSchedule(id, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules"] }),
  });

  const trackedById = new Map(tracked.map((t) => [t.id, t]));

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted text-sm mt-1">Configuration and preferences</p>
      </div>

      {/* Appearance */}
      <section className="bg-surface border border-border rounded-2xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border">
          <h2 className="font-semibold text-sm">Appearance</h2>
        </div>
        <div className="px-5 py-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Theme</p>
            <p className="text-xs text-muted mt-0.5">Switch between dark and light mode</p>
          </div>
          <button
            onClick={toggle}
            className={`relative inline-flex items-center w-12 h-6 rounded-full transition-colors cursor-pointer border ${
              theme === "dark"
                ? "bg-primary border-primary"
                : "bg-surface-2 border-border"
            }`}
            aria-label="Toggle theme"
          >
            <span
              className={`inline-block w-5 h-5 rounded-full shadow transition-transform duration-200 bg-white ${
                theme === "dark" ? "translate-x-6" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>
      </section>

      {/* Schedules */}
      <section className="bg-surface border border-border rounded-2xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border flex items-center justify-between">
          <h2 className="font-semibold text-sm">Schedules</h2>
          <button
            onClick={() => {
              if (tracked.length === 0) {
                alert("Add a tracked account first.");
                return;
              }
              setEditing(null);
              setModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary-hover text-white rounded-lg text-sm font-medium cursor-pointer"
          >
            <Plus size={14} /> New schedule
          </button>
        </div>

        {schedLoading ? (
          <div className="px-5 py-6 text-muted flex items-center gap-2">
            <RefreshCw size={14} className="animate-spin" /> Loading…
          </div>
        ) : schedules.length === 0 ? (
          <p className="px-5 py-6 text-muted text-sm">
            No schedules yet. Add one to scan an account automatically.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {schedules.map((s) => {
              const t = trackedById.get(s.tracked_account_id);
              return (
                <li key={s.id} className="px-5 py-3 flex items-center gap-3 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">
                      @{t?.username ?? `tracked#${s.tracked_account_id}`}
                      {s.name && (
                        <span className="text-muted font-normal"> — {s.name}</span>
                      )}
                    </p>
                    <p className="text-xs text-muted">{summarise(s)}</p>
                    {s.webhook_url && (
                      <p className="text-xs text-muted truncate">
                        Webhook: {s.webhook_url}
                      </p>
                    )}
                    {s.next_run_at && s.enabled && (
                      <p className="text-xs text-muted">
                        Next: {new Date(s.next_run_at).toLocaleString()}
                      </p>
                    )}
                    {s.last_run_at && (
                      <p className="text-xs text-muted">
                        Last: {new Date(s.last_run_at).toLocaleString()} (
                        {s.last_run_status ?? "—"})
                      </p>
                    )}
                  </div>

                  <label className="flex items-center gap-1.5 text-xs text-muted cursor-pointer">
                    <input
                      type="checkbox"
                      checked={s.enabled}
                      onChange={(e) =>
                        toggleMut.mutate({ id: s.id, enabled: e.target.checked })
                      }
                      className="h-4 w-4 accent-primary"
                    />
                    Enabled
                  </label>

                  <button
                    onClick={() => {
                      setEditing(s);
                      setModalOpen(true);
                    }}
                    className="p-1.5 rounded-lg text-muted hover:text-foreground hover:bg-surface-2 cursor-pointer"
                    title="Edit"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm("Delete this schedule?")) deleteMut.mutate(s.id);
                    }}
                    className="p-1.5 rounded-lg text-muted hover:text-danger hover:bg-danger/10 cursor-pointer"
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* Health monitoring */}
      <section className="bg-surface border border-border rounded-2xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border">
          <h2 className="font-semibold text-sm">Health monitoring</h2>
        </div>
        <div className="px-5 py-4 space-y-3">
          <p className="text-sm text-muted">
            Webhook fired when something needs your attention — currently, when
            the logged-in account's session expires and a re-login is required.
            Payload: <code>{`{event: "session_expired", login_account, message}`}</code>.
          </p>
          <input
            value={healthUrl}
            onChange={(e) => setHealthUrl(e.target.value)}
            placeholder="https://homeassistant.local:8123/api/webhook/instagram_tracker_health"
            className="w-full bg-surface-2 border border-border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => saveHealth.mutate(healthUrl)}
              disabled={saveHealth.isPending}
              className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-sm font-medium disabled:opacity-60 cursor-pointer"
            >
              {saveHealth.isPending ? "Saving…" : "Save"}
            </button>
            <button
              onClick={() => testHealth.mutate()}
              disabled={testHealth.isPending || !appSettings?.health_webhook_url}
              className="flex items-center gap-1.5 px-3 py-2 bg-surface-2 hover:bg-surface text-foreground border border-border rounded-xl text-sm font-medium cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {testHealth.isPending ? (
                <RefreshCw size={13} className="animate-spin" />
              ) : (
                <Send size={13} />
              )}
              Send test
            </button>
            {saveHealth.isSuccess && (
              <span className="flex items-center gap-1 text-sm text-success">
                <CheckCircle size={13} /> Saved
              </span>
            )}
            {testHealth.data?.sent === false && (
              <span className="flex items-center gap-1 text-sm text-danger">
                <AlertTriangle size={13} /> {testHealth.data.error ?? "Send failed"}
              </span>
            )}
            {testHealth.data?.sent === true && (
              <span className="flex items-center gap-1 text-sm text-success">
                <CheckCircle size={13} /> Sent
              </span>
            )}
          </div>
        </div>
      </section>

      {/* Default Home Assistant Webhook (env) */}
      <section className="bg-surface border border-border rounded-2xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border">
          <h2 className="font-semibold text-sm">Default scan webhook</h2>
        </div>
        <div className="px-5 py-2">
          {isLoading ? (
            <div className="flex items-center gap-2 text-muted py-4">
              <RefreshCw size={14} className="animate-spin" /> Loading…
            </div>
          ) : settings ? (
            <>
              <SettingRow label="Base URL" value={settings.ha_webhook_url} />
              <SettingRow label="Webhook ID" value={settings.ha_webhook_id} />
              <SettingRow label="Enabled" value={settings.ha_webhook_enabled} />
            </>
          ) : (
            <p className="text-muted text-sm py-4">Could not load settings.</p>
          )}
        </div>
        <div className="px-5 py-4 border-t border-border flex items-center gap-3 flex-wrap">
          <button
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
          >
            {testMutation.isPending ? (
              <RefreshCw size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
            Send test webhook
          </button>
          {testMutation.isSuccess && (
            <span className="flex items-center gap-1 text-sm text-success">
              <CheckCircle size={13} /> Sent
            </span>
          )}
        </div>
        <div className="px-5 py-3 border-t border-border bg-surface-2">
          <p className="text-xs text-muted flex items-center gap-1.5">
            <Info size={12} />
            These defaults come from <code className="bg-bg px-1 rounded">.env</code>.
            Each schedule above can override the URL.
          </p>
        </div>
      </section>

      {/* About */}
      <section className="bg-surface border border-border rounded-2xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border">
          <h2 className="font-semibold text-sm">About</h2>
        </div>
        <div className="px-5 py-2">
          <SettingRow label="App" value="Instagram Unfollowers Tracker" />
          <SettingRow label="Version" value="0.1.0" />
          <SettingRow label="Backend" value="FastAPI + SQLite + APScheduler" />
          <SettingRow label="Login" value="Playwright + noVNC (real browser)" />
        </div>
      </section>

      {modalOpen && (
        <ScheduleForm
          initial={editing}
          tracked={tracked}
          onCancel={() => setModalOpen(false)}
          saving={createMut.isPending || updateMut.isPending}
          onSave={(data) => {
            if (editing?.id) {
              updateMut.mutate({ id: editing.id, data });
            } else {
              createMut.mutate(data);
            }
          }}
        />
      )}
    </div>
  );
}
