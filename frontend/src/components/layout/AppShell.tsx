import { useState } from "react";
import {
  Link,
  useMatch,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Users,
  UserCheck,
  UserX,
  Star,
  Clock,
  Plus,
  Settings,
  Sun,
  Moon,
  Menu,
  X,
  UserMinus,
  LogIn,
} from "lucide-react";
import type { ReactNode } from "react";

import {
  getLoginAccount,
  listTrackedAccounts,
} from "@/services/api";
import { useTheme } from "@/contexts/ThemeContext";
import { Avatar } from "@/components/common/Avatar";
import type { LoginAccount, TrackedAccount } from "@/types/api";

const NAV_ITEMS = [
  { tab: "overview", label: "Overview", icon: LayoutDashboard },
  { tab: "followers", label: "Followers", icon: UserCheck },
  { tab: "following", label: "Following", icon: Users },
  { tab: "non-followers", label: "Not following back", icon: UserX },
  { tab: "not-following", label: "Doesn't follow back", icon: UserMinus },
  { tab: "whitelist", label: "Whitelist", icon: Star },
  { tab: "history", label: "Unfollower history", icon: Clock },
];

interface SidebarProps {
  login: LoginAccount | null;
  tracked: TrackedAccount[];
  currentAccountId: number | null;
  activeTab: string;
  onClose?: () => void;
}

function Sidebar({
  login,
  tracked,
  currentAccountId,
  activeTab,
  onClose,
}: SidebarProps) {
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();

  const handleClick = (id: number) => {
    navigate(`/accounts/${id}?tab=overview`);
    onClose?.();
  };

  const handleNavClick = (tab: string) => {
    if (currentAccountId) {
      navigate(`/accounts/${currentAccountId}?tab=${tab}`);
    }
    onClose?.();
  };

  return (
    <div className="flex flex-col h-full bg-surface border-r border-border">
      <div className="flex items-center justify-between px-4 h-14 border-b border-border flex-shrink-0">
        <Link
          to="/"
          className="flex items-center gap-2 font-bold text-foreground"
          onClick={onClose}
        >
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
            <UserX size={14} className="text-white" />
          </div>
          <span className="text-sm">Unfollowers</span>
        </Link>
        <div className="flex items-center gap-1">
          <button
            onClick={toggle}
            className="p-1.5 rounded-lg hover:bg-surface-2 transition-colors cursor-pointer text-muted hover:text-foreground"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-surface-2 transition-colors cursor-pointer text-muted md:hidden"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin py-2">
        {/* Login account */}
        <div className="px-3 mb-1">
          <p className="text-xs font-semibold text-muted uppercase tracking-wider px-2 py-1.5">
            Logged in as
          </p>
          {login ? (
            <div className="flex items-center gap-2 px-2 py-2 rounded-lg bg-surface-2">
              <Avatar
                src={login.profile_pic_url}
                username={login.username}
                size={28}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">@{login.username}</p>
              </div>
            </div>
          ) : (
            <Link
              to="/login"
              onClick={onClose}
              className="flex items-center gap-2 px-2 py-2 rounded-lg text-muted hover:bg-surface-2 hover:text-foreground transition-colors cursor-pointer text-sm"
            >
              <LogIn size={14} /> Log in
            </Link>
          )}
        </div>

        {/* Tracked accounts */}
        <div className="px-3 mt-3">
          <p className="text-xs font-semibold text-muted uppercase tracking-wider px-2 py-1.5">
            Tracked accounts
          </p>
          <div className="space-y-0.5">
            {tracked.map((t) => {
              const isActive = t.id === currentAccountId;
              return (
                <button
                  key={t.id}
                  onClick={() => handleClick(t.id)}
                  className={`w-full flex items-center gap-3 px-2 py-2 rounded-lg text-left transition-colors cursor-pointer ${
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "hover:bg-surface-2 text-foreground"
                  }`}
                >
                  <Avatar
                    src={t.profile_pic_url}
                    username={t.username}
                    size={28}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">@{t.username}</p>
                    {!t.we_follow && (
                      <p className="text-xs text-warning truncate">
                        Not following
                      </p>
                    )}
                  </div>
                </button>
              );
            })}

            {login && (
              <Link
                to="/tracked/add"
                onClick={onClose}
                className="flex items-center gap-3 px-2 py-2 rounded-lg text-muted hover:bg-surface-2 hover:text-foreground transition-colors cursor-pointer"
              >
                <div className="w-7 h-7 rounded-full border-2 border-dashed border-border flex items-center justify-center">
                  <Plus size={12} />
                </div>
                <span className="text-sm">Add tracked account</span>
              </Link>
            )}
          </div>
        </div>

        {currentAccountId && (
          <div className="px-3 mt-3">
            <p className="text-xs font-semibold text-muted uppercase tracking-wider px-2 py-1.5">
              Navigate
            </p>
            <div className="space-y-0.5">
              {NAV_ITEMS.map(({ tab, label, icon: Icon }) => {
                const isActive = activeTab === tab;
                return (
                  <button
                    key={tab}
                    onClick={() => handleNavClick(tab)}
                    className={`w-full flex items-center gap-2.5 px-2 py-2 rounded-lg text-left text-sm transition-colors cursor-pointer ${
                      isActive
                        ? "bg-primary/10 text-primary font-medium"
                        : "text-muted hover:bg-surface-2 hover:text-foreground"
                    }`}
                  >
                    <Icon size={16} />
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <div className="px-3 py-3 border-t border-border flex-shrink-0">
        <Link
          to="/settings"
          onClick={onClose}
          className="flex items-center gap-2.5 px-2 py-2 rounded-lg text-sm text-muted hover:bg-surface-2 hover:text-foreground transition-colors cursor-pointer"
        >
          <Settings size={16} />
          Settings
        </Link>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") ?? "overview";

  const accountMatch = useMatch("/accounts/:id");
  const currentAccountId = accountMatch?.params?.id
    ? Number(accountMatch.params.id)
    : null;

  const { data: login = null } = useQuery({
    queryKey: ["login-account"],
    queryFn: getLoginAccount,
  });
  const { data: tracked = [] } = useQuery({
    queryKey: ["tracked-accounts"],
    queryFn: listTrackedAccounts,
    enabled: !!login,
  });

  const currentAccount = tracked.find((a) => a.id === currentAccountId) ?? null;

  return (
    <div className="flex h-full bg-bg">
      <div className="hidden md:flex w-[260px] flex-col flex-shrink-0 h-full fixed left-0 top-0 z-20">
        <Sidebar
          login={login}
          tracked={tracked}
          currentAccountId={currentAccountId}
          activeTab={activeTab}
        />
      </div>

      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 z-40 flex">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="relative w-[280px] h-full z-10">
            <Sidebar
              login={login}
              tracked={tracked}
              currentAccountId={currentAccountId}
              activeTab={activeTab}
              onClose={() => setSidebarOpen(false)}
            />
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col md:ml-[260px] min-h-full">
        <div className="md:hidden flex items-center justify-between px-4 h-14 bg-surface border-b border-border flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-surface-2 transition-colors cursor-pointer"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <span className="font-semibold text-sm">
            {currentAccount ? `@${currentAccount.username}` : "Unfollowers Tracker"}
          </span>
          <div className="w-9" />
        </div>

        <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-6">
          {children}
        </main>
      </div>
    </div>
  );
}
