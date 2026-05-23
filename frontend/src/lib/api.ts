import axios from "axios";

// 回测默认日期：今天往前一年
export function defaultBacktestDates() {
  const today = new Date();
  const yearAgo = new Date(today);
  yearAgo.setFullYear(yearAgo.getFullYear() - 1);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  return { start_date: fmt(yearAgo), end_date: fmt(today) };
}

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    // 增强错误提示
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") {
      err.friendlyMessage = detail;
    } else if (Array.isArray(detail)) {
      // Pydantic 验证错误
      err.friendlyMessage = detail.map((d: any) => {
        const field = d.loc?.join(".") || "未知字段";
        return `${field}: ${d.msg}`;
      }).join("; ");
    } else if (err.message) {
      err.friendlyMessage = err.message;
    } else {
      err.friendlyMessage = "网络错误，请稍后重试";
    }
    return Promise.reject(err);
  }
);

// ---- Auth ----
export const authAPI = {
  sendCode: (email: string) => api.post("/api/auth/send-code", { email }),
  register: (email: string, password: string, code: string) =>
    api.post("/api/auth/register", { email, password, code }),
  login: (email: string, password: string) =>
    api.post("/api/auth/login", { email, password }),
};

// ---- Strategies ----
export const strategyAPI = {
  list: (page = 1) => api.get(`/api/strategies?page=${page}`),
  get: (id: string) => api.get(`/api/strategies/${id}`),
  create: (name: string, config: any) => api.post("/api/strategies", { name, config }),
  update: (id: string, data: any) => api.put(`/api/strategies/${id}`, data),
  delete: (id: string) => api.delete(`/api/strategies/${id}`),
  versions: (id: string) => api.get(`/api/strategies/${id}/versions`),
};

// ---- Backtest ----
export const backtestAPI = {
  run: (strategyId: string, params: any) =>
    api.post(`/api/strategies/${strategyId}/backtest`, params),
  get: (taskId: string) => api.get(`/api/backtest/${taskId}`),
  trades: (taskId: string) => api.get(`/api/backtest/${taskId}/trades`),
  nav: (taskId: string) => api.get(`/api/backtest/${taskId}/nav`),
  list: () => api.get("/api/backtests"),
};

// ---- WFA ----
export const wfaAPI = {
  run: (strategyId: string, params: any) =>
    api.post(`/api/strategies/${strategyId}/wfa`, params),
  get: (wfaId: string) => api.get(`/api/wfa/${wfaId}`),
};

// ---- Optimize ----
export const optimizeAPI = {
  run: (strategyId: string, params: any) =>
    api.post(`/api/strategies/${strategyId}/optimize`, params),
};

// ---- AI ----
export const aiAPI = {
  generate: (prompt: string) => api.post("/api/ai/generate-strategy", { prompt }),
  diagnose: (strategyId: string) =>
    api.post(`/api/ai/diagnose-strategy/${strategyId}`, { strategy_id: strategyId }),
};

// ---- User ----
export const userAPI = {
  getAISettings: () => api.get("/api/user/ai-settings"),
  updateAISettings: (data: { ai_api_key?: string | null; ai_provider?: string | null }) =>
    api.put("/api/user/ai-settings", data),
  upgrade: (plan: string) => api.post("/api/user/upgrade", { plan }),
};

// ---- Scorecard ----
export const scorecardAPI = {
  get: (strategyId: string) => api.get(`/api/strategies/${strategyId}/scorecard`),
};

// ---- QMT Export ----
export const qmtAPI = {
  exportScript: (strategyId: string) =>
    api.get(`/api/strategies/${strategyId}/export/qmt`, { responseType: "blob" }),
};

// ---- Agent Tokens ----
export const agentAPI = {
  list: () => api.get("/api/agent-tokens"),
  create: (data: any) => api.post("/api/agent-tokens", data),
  revoke: (id: string) => api.delete(`/api/agent-tokens/${id}`),
};

// ---- Data ----
export const dataAPI = {
  factors: () => api.get("/api/data/factors"),
  symbols: (q = "") => api.get(`/api/data/symbols?q=${q}`),
};

// ---- Admin ----
export const adminAPI = {
  stats: () => api.get("/api/admin/stats"),
  users: () => api.get("/api/admin/users"),
  deleteUser: (id: string) => api.delete(`/api/admin/users/${id}`),
  strategies: () => api.get("/api/admin/strategies"),
  deleteStrategy: (id: string) => api.delete(`/api/admin/strategies/${id}`),
  backtests: () => api.get("/api/admin/backtests"),
  deleteBacktest: (id: string) => api.delete(`/api/admin/backtests/${id}`),
  agentTokens: () => api.get("/api/admin/agent-tokens"),
  revokeAgentToken: (id: string) => api.delete(`/api/admin/agent-tokens/${id}`),
};

// ---- Sync ----
export const syncAPI = {
  status: (syncType = "market_daily") => api.get(`/api/admin/sync/status?sync_type=${syncType}`),
  triggerMarketDaily: () => api.post("/api/admin/sync/market-daily"),
  triggerFactors: () => api.post("/api/admin/sync/factors"),
};
