import { useState } from "react";

const GRADIENTS = [
  ["#6366F1", "#8B5CF6"],
  ["#EC4899", "#F43F5E"],
  ["#0EA5E9", "#6366F1"],
  ["#10B981", "#0EA5E9"],
  ["#F59E0B", "#EF4444"],
  ["#8B5CF6", "#EC4899"],
];

function getGradient(username: string): [string, string] {
  const n = username.split("").reduce((s, c) => s + c.charCodeAt(0), 0);
  return GRADIENTS[n % GRADIENTS.length] as [string, string];
}

interface AvatarProps {
  src?: string | null;
  username: string;
  size?: number;
  className?: string;
}

export function Avatar({ src, username, size = 36, className = "" }: AvatarProps) {
  const [failed, setFailed] = useState(false);
  const [from, to] = getGradient(username);
  const letter = (username[0] ?? "?").toUpperCase();

  if (!src || failed) {
    return (
      <div
        className={`rounded-full flex items-center justify-center text-white font-semibold flex-shrink-0 select-none ${className}`}
        style={{
          width: size,
          height: size,
          fontSize: Math.round(size * 0.4),
          background: `linear-gradient(135deg, ${from}, ${to})`,
        }}
        aria-label={username}
      >
        {letter}
      </div>
    );
  }

  return (
    <img
      src={`/api/v1/proxy/avatar?url=${encodeURIComponent(src)}`}
      alt={username}
      onError={() => setFailed(true)}
      className={`rounded-full object-cover flex-shrink-0 ${className}`}
      style={{ width: size, height: size }}
    />
  );
}
