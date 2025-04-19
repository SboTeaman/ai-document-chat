import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: () => import("../views/LoginView.vue") },
    { path: "/", redirect: "/workspaces" },
    {
      path: "/workspaces",
      component: () => import("../views/WorkspaceView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/workspaces/:id/search",
      component: () => import("../views/SearchView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/workspaces/:id/chat",
      component: () => import("../views/ChatView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/workspaces/:id/members",
      component: () => import("../views/MembersView.vue"),
      meta: { requiresAuth: true },
    },
  ],
});

// Global guard: redirect to /login for protected routes when unauthenticated.
router.beforeEach((to) => {
  const token = sessionStorage.getItem("access_token");
  if (to.meta.requiresAuth && !token) return "/login";
});

export default router;
