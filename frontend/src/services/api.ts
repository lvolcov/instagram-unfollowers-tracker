import axios from "axios";

import type {
  LoginAccount,
  ScanJob,
  Schedule,
  ScheduleUpdate,
  TrackedAccount,
  Unfollower,
  WhitelistEntry,
} from "@/types/api";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
});

// ----- Login account (singleton) -----
export const getLoginAccount = () =>
  api.get<LoginAccount | null>("/login-account").then((r) => r.data);
export const deleteLoginAccount = () =>
  api.delete("/login-account").then((r) => r.data);

// ----- Auth (login flow) -----
export const startLogin = () =>
  api
    .post<{ session_id: string; novnc_url: string; expires_in: number }>(
      "/auth/login/start"
    )
    .then((r) => r.data);
export const getLoginStatus = (sessionId: string) =>
  api
    .get<{
      status: string;
      account: { id: number; username: string } | null;
      error: string | null;
    }>(`/auth/login/status/${sessionId}`)
    .then((r) => r.data);
export const cancelLogin = (sessionId: string) =>
  api.post(`/auth/login/cancel/${sessionId}`).then((r) => r.data);

// ----- Tracked accounts -----
export const listTrackedAccounts = () =>
  api.get<TrackedAccount[]>("/tracked-accounts").then((r) => r.data);
export const getTrackedAccount = (id: number) =>
  api.get<TrackedAccount>(`/tracked-accounts/${id}`).then((r) => r.data);
export const addTrackedAccount = (username: string) =>
  api
    .post<TrackedAccount>("/tracked-accounts", { username })
    .then((r) => r.data);
export const deleteTrackedAccount = (id: number) =>
  api.delete(`/tracked-accounts/${id}`).then((r) => r.data);

// ----- Scans -----
export const triggerScan = (id: number) =>
  api.post<ScanJob>(`/tracked-accounts/${id}/scan`).then((r) => r.data);
export const getScanJob = (id: number, jobId: string) =>
  api.get<ScanJob>(`/tracked-accounts/${id}/scan/${jobId}`).then((r) => r.data);

// ----- Followers / Non-followers -----
export const listFollowers = (id: number, page = 1, search = "") =>
  api
    .get(`/tracked-accounts/${id}/followers`, { params: { page, search } })
    .then((r) => r.data);

export const listFollowersNotFollowingBack = (id: number, page = 1, search = "") =>
  api
    .get(`/tracked-accounts/${id}/followers`, {
      params: { page, search, only_not_following_back: true },
    })
    .then((r) => r.data);

export const listFollowing = (id: number, page = 1, search = "") =>
  api
    .get(`/tracked-accounts/${id}/following`, { params: { page, search } })
    .then((r) => r.data);

export const listNonFollowers = (
  id: number,
  includeWhitelisted = false,
  page = 1,
  search = ""
) =>
  api
    .get(`/tracked-accounts/${id}/non-followers`, {
      params: { include_whitelisted: includeWhitelisted, page, search },
    })
    .then((r) => r.data);

// ----- Unfollowers -----
export const listUnfollowers = (id: number, page = 1) =>
  api
    .get<Unfollower[]>(`/tracked-accounts/${id}/unfollowers`, { params: { page } })
    .then((r) => r.data);

// ----- Whitelist -----
export const listWhitelist = (id: number) =>
  api
    .get<WhitelistEntry[]>(`/tracked-accounts/${id}/whitelist`)
    .then((r) => r.data);
export const addToWhitelist = (
  id: number,
  data: { instagram_user_id: string; username: string; note?: string }
) =>
  api
    .post<WhitelistEntry>(`/tracked-accounts/${id}/whitelist`, data)
    .then((r) => r.data);
export const removeFromWhitelist = (id: number, entryId: number) =>
  api.delete(`/tracked-accounts/${id}/whitelist/${entryId}`).then((r) => r.data);

// ----- Schedule -----
export const getSchedule = (id: number) =>
  api.get<Schedule>(`/tracked-accounts/${id}/schedule`).then((r) => r.data);
export const updateSchedule = (id: number, data: ScheduleUpdate) =>
  api.put<Schedule>(`/tracked-accounts/${id}/schedule`, data).then((r) => r.data);

// ----- Settings -----
export const getSettings = () => api.get("/settings").then((r) => r.data);
export const testWebhook = () => api.post("/settings/webhook/test").then((r) => r.data);

export default api;
