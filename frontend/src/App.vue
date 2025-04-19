<template>
  <router-view />
  <Toaster />
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useAuthStore } from "./stores/auth";
import Toaster from "./components/Toaster.vue";
import "./lib/theme";

const authStore = useAuthStore();
onMounted(() => authStore.loadUser());
</script>

<style>
:root {
  --bg: #f8fafc;
  --bg-elevated: #ffffff;
  --bg-sidebar: #1e293b;
  --bg-input: #ffffff;
  --bg-muted: #f1f5f9;
  --border: #e2e8f0;
  --text: #1e293b;
  --text-muted: #64748b;
  --text-on-dark: #cbd5e1;
  --primary: #6366f1;
  --primary-fg: #ffffff;
  --danger: #dc2626;
  --success: #16a34a;
  --warning: #f59e0b;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  color-scheme: light;
}

[data-theme="dark"] {
  --bg: #0f172a;
  --bg-elevated: #1e293b;
  --bg-sidebar: #0b1220;
  --bg-input: #1e293b;
  --bg-muted: #1e293b;
  --border: #334155;
  --text: #e2e8f0;
  --text-muted: #94a3b8;
  --text-on-dark: #cbd5e1;
  --primary: #818cf8;
  --primary-fg: #0b1220;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
  color-scheme: dark;
}

html, body, #app { height: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  transition: background-color 0.15s, color 0.15s;
}
* { box-sizing: border-box; }
a { color: var(--primary); }
mark {
  background: #fde68a;
  color: inherit;
  padding: 0 2px;
  border-radius: 2px;
}
[data-theme="dark"] mark { background: #78350f; color: #fde68a; }
</style>
