import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";

import { listAccounts } from "@/services/api";
import { useSelectedAccount } from "@/contexts/AccountContext";

export function AccountSwitcher() {
  const { data: accounts = [] } = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const { selectedAccount, setSelectedAccount } = useSelectedAccount();

  return (
    <div className="flex items-center gap-2">
      <select
        className="bg-surface border border-border rounded-lg px-2 py-1.5 text-sm"
        value={selectedAccount?.id ?? ""}
        onChange={(e) => {
          const id = Number(e.target.value);
          setSelectedAccount(accounts.find((a) => a.id === id) ?? null);
        }}
      >
        <option value="">Select account…</option>
        {accounts.map((a) => (
          <option key={a.id} value={a.id}>
            @{a.username}
          </option>
        ))}
      </select>
      <Link
        to="/accounts/add"
        className="p-1.5 bg-primary hover:bg-primary-hover rounded-lg"
        aria-label="Add account"
      >
        <Plus size={16} />
      </Link>
    </div>
  );
}
