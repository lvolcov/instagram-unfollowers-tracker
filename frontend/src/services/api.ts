import axios from "axios";

import type {
  Account,
  ScanJob,
  Schedule,
  ScheduleUpdate,
  Unfollower,
  WhitelistEntry,
} from "@/types/api";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
});

// ----- Accounts -----
export const listAccounts = () => api.get<Account[]>("/accounts").then((r) => r.data);
export const getAccount = (id: number) => api.get<Account>(`/accounts/${id}`).then((r) => r.data);
export const deleteAccount = (id: number) => api.delete(`/accounts/${id}`).then((r) => r.data);

// ----- Auth (login flow) -----
export const startLogin = () =>
  api.post<{ session_id: string; novnc_url: string; expires_in: number }>("/auth/login/start").then((r) => r.data);
export const getLoginStatus = (sessionId: string) =>
  api.get<{ status: string; account: Account | null; error: string | null }>(`/auth/login/status/${sessionId}`).then((r) => r.data);
export const cancelLogin = (sessionId: string) =>
  api.post(`/auth/login/cancel/${sessionId}`).then((r) => r.data);

// ----- Scans -----
export const triggerScan = (accountId: number) =>
  api.post<ScanJob>(`/accounts/${accountId}/scan`).then((r) => r.data);
export const getScanJob = (accountId: number, jobId: string) =>
  api.get<ScanJob>(`/accounts/${accountId}/scan/${jobId}`).then((r) => r.data);

// ----- Followers / Non-followers -----
export const listFollowers = (accountId: number, page = 1, search = "") =>
  api.get(`/accounts/${accountId}/followers`, { params: { page, search } }).then((r) => r.data);
export const listNonFollowers = (
  accountId: number,
  includeWhitelisted = false,
  page = 1,
  search = ""
) =>
  api
    .get(`/accounts/${accountId}/non-followers`, {
      params: { include_whitelisted: includeWhitelisted, page, search },
    })
    .then((r) => r.data);

// ----- Unfollowers -----
export const listUnfollowers = (accountId: number, page = 1) =>
  api.get<Unfollower[]>(`/accounts/${accountId}/unfollowers`, { params: { page } }).then((r) => r.data);

// ----- Whitelist -----
export const listWhitelist = (accountId: number) =>
  api.get<WhitelistEntry[]>(`/accounts/${accountId}/whitelist`).then((r) => r.data);
export const addToWhitelist = (
  accountId: number,
  data: { instagram_user_id: string; username: string; note?: string }
) => api.post<WhitelistEntry>(`/accounts/${accountId}/whitelist`, data).then((r) => r.data);
export const removeFromWhitelist = (accountId: number, entryId: number) =>
  api.delete(`/accounts/${accountId}/whitelist/${entryId}`).then((r) => r.data);

// ----- Schedule -----
export const getSchedule = (accountId: number) =>
  api.get<Schedule>(`/accounts/${accountId}/schedule`).then((r) => r.data);
export const updateSchedule = (accountId: number, data: ScheduleUpdate) =>
  api.put<Schedule>(`/accounts/${accountId}/schedule`, data).then((r) => r.data);

// ----- Settings -----
export const getSettings = () => api.get("/settings").then((r) => r.data);
export const testWebhook = () => api.post("/settings/webhook/test").then((r) => r.data);

export default api;
