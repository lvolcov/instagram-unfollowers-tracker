export interface Account {
  id: number;
  instagram_user_id: string;
  username: string;
  display_name: string | null;
  profile_pic_url: string | null;
  session_status: "active" | "needs_relogin" | "expired" | "scanning";
  created_at: string;
  last_scan_at: string | null;
}

export interface IGUser {
  instagram_user_id: string;
  username: string;
  full_name: string | null;
  profile_pic_url: string | null;
  is_verified: boolean;
  is_private: boolean;
}

export interface Unfollower {
  id: number;
  account_id: number;
  instagram_user_id: string;
  username: string;
  full_name: string | null;
  profile_pic_url: string | null;
  detected_at: string;
  first_seen_at: string | null;
  notified: boolean;
}

export interface WhitelistEntry {
  id: number;
  account_id: number;
  instagram_user_id: string;
  username: string;
  note: string | null;
  added_at: string;
}

export type ScheduleMode = "daily_at" | "interval_hours" | "manual_only";

export interface Schedule {
  id: number;
  account_id: number;
  mode: ScheduleMode;
  daily_time: string | null;
  interval_hours: number | null;
  enabled: boolean;
  next_run_at: string | null;
}

export interface ScheduleUpdate {
  mode: ScheduleMode;
  daily_time?: string | null;
  interval_hours?: number | null;
  enabled: boolean;
}

export interface ScanJob {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  progress?: { phase: string; current: number; total: number };
  result?: { snapshot_id: number; new_unfollowers: number };
  error?: string;
}
