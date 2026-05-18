import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { listUnfollowers } from "@/services/api";

export function UnfollowerHistory() {
  const { id } = useParams<{ id: string }>();
  const accountId = Number(id);

  const { data: unfollowers = [] } = useQuery({
    queryKey: ["unfollowers", accountId],
    queryFn: () => listUnfollowers(accountId),
    enabled: !!accountId,
  });

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Unfollower History</h1>
      {unfollowers.length === 0 ? (
        <p className="text-muted">No unfollowers detected yet.</p>
      ) : (
        <ul className="divide-y divide-border bg-surface border border-border rounded-xl">
          {unfollowers.map((u) => (
            <li key={u.id} className="p-3 flex items-center gap-3">
              {u.profile_pic_url && (
                <img src={u.profile_pic_url} alt={u.username} className="w-10 h-10 rounded-full" />
              )}
              <div className="flex-1">
                <a
                  href={`https://www.instagram.com/${u.username}`}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium hover:underline"
                >
                  @{u.username}
                </a>
                {u.full_name && <div className="text-sm text-muted">{u.full_name}</div>}
              </div>
              <div className="text-sm text-muted">{new Date(u.detected_at).toLocaleDateString()}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
