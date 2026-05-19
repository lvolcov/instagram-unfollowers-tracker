import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle, RefreshCw, Send, Info } from "lucide-react";

import { getSettings, testWebhook } from "@/services/api";
import { useTheme } from "@/contexts/ThemeContext";

function SettingRow({ label, value }: { label: string; value: string | boolean | null | undefined }) {
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

export function Settings() {
  const { data: settings, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
  });
  const testMutation = useMutation({ mutationFn: testWebhook });
  const { theme, toggle } = useTheme();

  return (
    <div className="max-w-2xl space-y-6">
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
            className={`relative w-12 h-6 rounded-full transition-colors cursor-pointer ${
              theme === "dark" ? "bg-primary" : "bg-surface-2 border border-border"
            }`}
            aria-label="Toggle theme"
          >
            <span
              className={`absolute top-0.5 w-5 h-5 rounded-full shadow transition-transform ${
                theme === "dark"
                  ? "translate-x-6 bg-white"
                  : "translate-x-0.5 bg-foreground"
              }`}
            />
          </button>
        </div>
      </section>

      {/* Home Assistant Webhook */}
      <section className="bg-surface border border-border rounded-2xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border">
          <h2 className="font-semibold text-sm">Home Assistant Webhook</h2>
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
        {testMutation.data && (
          <div className="px-5 pb-4">
            <pre className="p-3 bg-bg border border-border rounded-xl text-xs overflow-auto text-muted">
              {JSON.stringify(testMutation.data, null, 2)}
            </pre>
          </div>
        )}
        <div className="px-5 py-3 border-t border-border bg-surface-2">
          <p className="text-xs text-muted flex items-center gap-1.5">
            <Info size={12} />
            To change these values, edit the <code className="bg-bg px-1 rounded">.env</code> file and restart the container.
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
          <SettingRow label="Backend" value="FastAPI + SQLite" />
          <SettingRow label="Login" value="Playwright + noVNC (real browser)" />
        </div>
      </section>
    </div>
  );
}
