import { ref, watch } from "vue";

const STORAGE_KEY = "kb-theme";
type Theme = "light" | "dark";

/** Resolve the startup theme: stored preference, else the OS color scheme. */
function initial(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
  if (stored) return stored;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export const theme = ref<Theme>(initial());

/** Reflect the active theme onto the <html data-theme> attribute. */
function apply(t: Theme) {
  document.documentElement.dataset.theme = t;
}
apply(theme.value);

watch(theme, (t) => {
  localStorage.setItem(STORAGE_KEY, t);
  apply(t);
});

export function toggleTheme() {
  theme.value = theme.value === "dark" ? "light" : "dark";
}
