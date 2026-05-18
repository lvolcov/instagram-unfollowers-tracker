import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { AccountProvider } from "@/contexts/AccountContext";
import { Dashboard } from "@/pages/Dashboard";
import { AccountDetail } from "@/pages/AccountDetail";
import { AddAccount } from "@/pages/AddAccount";
import { UnfollowerHistory } from "@/pages/UnfollowerHistory";
import { Settings } from "@/pages/Settings";

export default function App() {
  return (
    <AccountProvider>
      <AppShell>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/accounts/add" element={<AddAccount />} />
          <Route path="/accounts/:id" element={<AccountDetail />} />
          <Route path="/accounts/:id/unfollowers" element={<UnfollowerHistory />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </AccountProvider>
  );
}
