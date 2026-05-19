import { createContext, useContext, useState, type ReactNode } from "react";

import type { TrackedAccount } from "@/types/api";

interface AccountContextValue {
  selectedAccount: TrackedAccount | null;
  setSelectedAccount: (account: TrackedAccount | null) => void;
}

const AccountContext = createContext<AccountContextValue | undefined>(undefined);

export function AccountProvider({ children }: { children: ReactNode }) {
  const [selectedAccount, setSelectedAccount] = useState<TrackedAccount | null>(null);

  return (
    <AccountContext.Provider value={{ selectedAccount, setSelectedAccount }}>
      {children}
    </AccountContext.Provider>
  );
}

export function useSelectedAccount() {
  const ctx = useContext(AccountContext);
  if (!ctx) throw new Error("useSelectedAccount must be used inside AccountProvider");
  return ctx;
}
