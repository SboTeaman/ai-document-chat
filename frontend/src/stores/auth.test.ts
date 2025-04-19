import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";

// Mock the API layer so the store is tested in isolation (no network).
vi.mock("../api/client", () => ({
  auth: {
    login: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    me: vi.fn(),
  },
}));

import { auth } from "../api/client";
import { useAuthStore } from "./auth";

const mockedLogin = vi.mocked(auth.login);
const mockedLogout = vi.mocked(auth.logout);

describe("auth store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it("stores tokens and user on successful login", async () => {
    mockedLogin.mockResolvedValue({
      data: {
        data: {
          access_token: "acc",
          refresh_token: "ref",
          user: { id: 1, email: "a@b.com", full_name: "A B", created_at: "" },
        },
      },
    } as any);

    const store = useAuthStore();
    await store.login("a@b.com", "secret");

    expect(sessionStorage.getItem("access_token")).toBe("acc");
    expect(sessionStorage.getItem("refresh_token")).toBe("ref");
    expect(store.isAuthenticated).toBe(true);
    expect(store.user?.email).toBe("a@b.com");
  });

  it("clears session and state on logout", async () => {
    sessionStorage.setItem("access_token", "acc");
    sessionStorage.setItem("refresh_token", "ref");

    const store = useAuthStore();
    await store.logout();

    expect(mockedLogout).toHaveBeenCalledWith("ref");
    expect(sessionStorage.getItem("access_token")).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(store.user).toBeNull();
  });

  it("swallows logout API errors but still clears the session", async () => {
    sessionStorage.setItem("access_token", "acc");
    mockedLogout.mockRejectedValueOnce(new Error("network"));

    const store = useAuthStore();
    await store.logout();

    expect(sessionStorage.getItem("access_token")).toBeNull();
    expect(store.isAuthenticated).toBe(false);
  });
});
