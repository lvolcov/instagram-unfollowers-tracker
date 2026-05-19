import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { AccountProvider } from "@/contexts/AccountContext";
import { Dashboard } from "@/pages/Dashboard";
import { AccountDetail } from "@/pages/AccountDetail";
import { Login } from "@/pages/Login";
import { AddTrackedAccount } from "@/pages/AddTrackedAccount";
import { Settings } from "@/pages/Settings";

export default function App() {
  return (
    <AccountProvider>
      <AppShell>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/login" element={<Login />} />
          <Route path="/tracked/add" element={<AddTrackedAccount />} />
          <Route path="/accounts/:id" element={<AccountDetail />} />
          {/* Legacy redirect */}
          <Route
            path="/accounts/add"
            element={<Navigate to="/login" replace />}
          />
          <Route
            path="/accounts/:id/unfollowers"
            element={<Navigate to="../?tab=history" relative="path" replace />}
          />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </AccountProvider>
  );
}
