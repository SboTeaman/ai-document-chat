import { defineStore } from "pinia";
import { ref } from "vue";
import { auth } from "../api/client";

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  created_at: string;
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<AuthUser | null>(null);
  const isAuthenticated = ref(!!sessionStorage.getItem("access_token"));

  /** Authenticate, store the JWT pair in sessionStorage, and load the user. */
  async function login(email: string, password: string) {
    const { data } = await auth.login(email, password);
    sessionStorage.setItem("access_token", data.data.access_token);
    sessionStorage.setItem("refresh_token", data.data.refresh_token);
    user.value = data.data.user;
    isAuthenticated.value = true;
  }

  /** Revoke the refresh token server-side (best-effort) and clear local state. */
  async function logout() {
    const refresh = sessionStorage.getItem("refresh_token") || "";
    await auth.logout(refresh).catch(() => {});
    sessionStorage.clear();
    user.value = null;
    isAuthenticated.value = false;
  }

  /** Hydrate the current user from /me when an access token is present. */
  async function loadUser() {
    if (!sessionStorage.getItem("access_token")) return;
    try {
      const { data } = await auth.me();
      user.value = data.data;
      isAuthenticated.value = true;
    } catch {
      sessionStorage.clear();
      isAuthenticated.value = false;
    }
  }

  return { user, isAuthenticated, login, logout, loadUser };
});
