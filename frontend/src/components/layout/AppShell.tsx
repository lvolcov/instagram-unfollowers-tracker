import { Link } from "react-router-dom";
import { Settings, Users } from "lucide-react";
import type { ReactNode } from "react";

import { AccountSwitcher } from "@/components/accounts/AccountSwitcher";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="h-14 bg-surface/70 backdrop-blur border-b border-border flex items-center justify-between px-4">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <Users size={20} />
          Unfollowers Tracker
        </Link>

        <div className="flex items-center gap-3">
          <AccountSwitcher />
          <Link to="/settings" className="p-2 hover:bg-surface-hover rounded-lg" aria-label="Settings">
            <Settings size={18} />
          </Link>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
