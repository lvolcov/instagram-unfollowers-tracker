import { createContext, useContext, useState, type ReactNode } from "react";

import type { Account } from "@/types/api";

interface AccountContextValue {
  selectedAccount: Account | null;
  setSelectedAccount: (account: Account | null) => void;
}

const AccountContext = createContext<AccountContextValue | undefined>(undefined);

export function AccountProvider({ children }: { children: ReactNode }) {
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);

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
