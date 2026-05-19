export interface LoginAccount {
  id: number;
  instagram_user_id: string;
  username: string;
  display_name: string | null;
  profile_pic_url: string | null;
  session_status: "active" | "needs_relogin" | "expired" | "scanning";
  created_at: string;
  last_active_at: string | null;
}

export interface TrackedAccount {
  id: number;
  instagram_user_id: string;
  username: string;
  display_name: string | null;
  profile_pic_url: string | null;
  is_private: boolean;
  follows_us: boolean;
  we_follow: boolean;
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
  tracked_account_id: number;
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
  tracked_account_id: number;
  instagram_user_id: string;
  username: string;
  note: string | null;
  added_at: string;
}

export type ScheduleMode = "daily_at" | "weekly_on" | "interval_hours";

export interface Schedule {
  id: number;
  tracked_account_id: number;
  name: string;
  mode: ScheduleMode;
  daily_time: string | null;       // "HH:MM"
  weekly_day: number | null;       // 0=Mon..6=Sun
  interval_hours: number | null;
  webhook_url: string | null;
  enabled: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  last_run_status: string | null;
}

export interface ScheduleCreate {
  tracked_account_id: number;
  name?: string;
  mode: ScheduleMode;
  daily_time?: string | null;
  weekly_day?: number | null;
  interval_hours?: number | null;
  webhook_url?: string | null;
  enabled?: boolean;
}

export interface ScheduleUpdate {
  name?: string;
  mode?: ScheduleMode;
  daily_time?: string | null;
  weekly_day?: number | null;
  interval_hours?: number | null;
  webhook_url?: string | null;
  enabled?: boolean;
}

export interface AppSettings {
  health_webhook_url: string | null;
}

export interface ScanJob {
  job_id: string;
  tracked_account_id: number;
  status: "queued" | "running" | "completed" | "failed";
  progress?: { phase: string; current: number; total: number };
  result?: { snapshot_id: number; new_unfollowers: number; warning?: string | null };
  error?: string;
}
