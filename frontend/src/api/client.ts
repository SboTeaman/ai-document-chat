import axios from "axios";
import { toast } from "../lib/toast";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// Request interceptor: attach the bearer access token to every outgoing call.
// NOTE: sessionStorage clears on tab/window close; for production use HttpOnly cookies instead.
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let isRefreshing = false;
let refreshWaiters: ((token: string | null) => void)[] = [];

// Response interceptor: on 401, transparently rotate the refresh token once and
// replay the original request; coalesces concurrent refreshes behind one call.
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const status = error.response?.status;
    const original = error.config;

    if (status === 401 && !original?._retry) {
      const refresh = sessionStorage.getItem("refresh_token");
      if (!refresh) {
        forceLogout();
        return Promise.reject(error);
      }
      original._retry = true;

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshWaiters.push((token) => {
            if (!token) return reject(error);
            original.headers.Authorization = `Bearer ${token}`;
            resolve(api.request(original));
          });
        });
      }

      isRefreshing = true;
      try {
        const { data } = await axios.post("/api/auth/token/refresh/", { refresh_token: refresh });
        const access = data.data.access_token;
        sessionStorage.setItem("access_token", access);
        sessionStorage.setItem("refresh_token", data.data.refresh_token);
        refreshWaiters.forEach((cb) => cb(access));
        refreshWaiters = [];
        original.headers.Authorization = `Bearer ${access}`;
        return api.request(original);
      } catch {
        refreshWaiters.forEach((cb) => cb(null));
        refreshWaiters = [];
        forceLogout();
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

    if (status === 429) {
      toast.error("Rate limit reached. Please wait a moment.");
    } else if (status >= 500) {
      toast.error("Server error. Try again later.");
    } else if (status === 403) {
      toast.error("You don't have permission for this action.");
    }
    return Promise.reject(error);
  }
);

/** Clear the session and redirect to /login (used when refresh fails). */
function forceLogout() {
  sessionStorage.clear();
  if (!window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
}

export default api;

/** Authentication endpoints (register, login, logout, current user). */
export const auth = {
  register: (data: object) => api.post("/auth/register/", data),
  login: (email: string, password: string) => api.post("/auth/login/", { email, password }),
  logout: (refresh_token: string) => api.post("/auth/logout/", { refresh_token }),
  me: () => api.get("/auth/me/"),
};

/** Workspace and member-management endpoints. */
export const workspaces = {
  list: () => api.get("/workspaces/"),
  create: (name: string) => api.post("/workspaces/", { name }),
  remove: (id: number) => api.delete(`/workspaces/${id}/`),
  members: (id: number) => api.get(`/workspaces/${id}/members/`),
  inviteMember: (id: number, email: string, role: string) =>
    api.post(`/workspaces/${id}/members/`, { email, role }),
  updateMember: (id: number, memberId: number, role: string) =>
    api.patch(`/workspaces/${id}/members/${memberId}/`, { role }),
  removeMember: (id: number, memberId: number) =>
    api.delete(`/workspaces/${id}/members/${memberId}/`),
};

/** Collection CRUD endpoints, scoped to a workspace. */
export const collections = {
  list: (workspaceId: number) => api.get(`/workspaces/${workspaceId}/collections/`),
  create: (workspaceId: number, data: { name: string; description?: string }) =>
    api.post(`/workspaces/${workspaceId}/collections/`, data),
  update: (workspaceId: number, collectionId: number, data: object) =>
    api.patch(`/workspaces/${workspaceId}/collections/${collectionId}/`, data),
  remove: (workspaceId: number, collectionId: number) =>
    api.delete(`/workspaces/${workspaceId}/collections/${collectionId}/`),
};

/** Document endpoints: list, upload, fetch, presigned download, delete. */
export const documents = {
  list: (workspaceId: number, params?: object) =>
    api.get(`/workspaces/${workspaceId}/documents/`, { params }),
  upload: (workspaceId: number, formData: FormData) =>
    api.post(`/workspaces/${workspaceId}/documents/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  get: (workspaceId: number, docId: number) =>
    api.get(`/workspaces/${workspaceId}/documents/${docId}/`),
  download: (workspaceId: number, docId: number) =>
    api.get(`/workspaces/${workspaceId}/documents/${docId}/download/`),
  delete: (workspaceId: number, docId: number) =>
    api.delete(`/workspaces/${workspaceId}/documents/${docId}/`),
};

/** Hybrid search endpoint. */
export const search = {
  query: (workspaceId: number, query: string, collectionId?: number | null, limit = 10) =>
    api.post(`/workspaces/${workspaceId}/search/`, { query, collection_id: collectionId, limit }),
};

/** Chat-session endpoints (message streaming is done via fetch in ChatView). */
export const chat = {
  sessions: (workspaceId: number) => api.get(`/workspaces/${workspaceId}/chat/sessions/`),
  createSession: (workspaceId: number) => api.post(`/workspaces/${workspaceId}/chat/sessions/`),
  getSession: (workspaceId: number, sessionId: number) =>
    api.get(`/workspaces/${workspaceId}/chat/sessions/${sessionId}/`),
  deleteSession: (workspaceId: number, sessionId: number) =>
    api.delete(`/workspaces/${workspaceId}/chat/sessions/${sessionId}/`),
};
