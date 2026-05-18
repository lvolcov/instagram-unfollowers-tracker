import { useMutation, useQuery } from "@tanstack/react-query";

import { getSettings, testWebhook } from "@/services/api";

export function Settings() {
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: getSettings });
  const testMutation = useMutation({ mutationFn: testWebhook });

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <section className="bg-surface border border-border rounded-xl p-4">
        <h2 className="font-semibold mb-3">Home Assistant Webhook</h2>
        {settings && (
          <dl className="text-sm space-y-1">
            <div className="flex justify-between">
              <dt className="text-muted">Base URL</dt>
              <dd>{settings.ha_webhook_url}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Webhook ID</dt>
              <dd>{settings.ha_webhook_id}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Enabled</dt>
              <dd>{settings.ha_webhook_enabled ? "Yes" : "No"}</dd>
            </div>
          </dl>
        )}
        <button
          onClick={() => testMutation.mutate()}
          className="mt-4 px-4 py-2 bg-primary hover:bg-primary-hover rounded-lg"
        >
          Send test webhook
        </button>
        {testMutation.data && (
          <pre className="mt-3 p-3 bg-background border border-border rounded-lg text-xs overflow-auto">
            {JSON.stringify(testMutation.data, null, 2)}
          </pre>
        )}
        <p className="mt-3 text-sm text-muted">
          To change these values, edit the <code>.env</code> file and restart the container.
        </p>
      </section>
    </div>
  );
}
