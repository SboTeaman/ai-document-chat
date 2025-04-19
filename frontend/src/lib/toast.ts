import { reactive } from "vue";

export type ToastKind = "info" | "success" | "error";

export interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
}

const state = reactive<{ items: ToastItem[] }>({ items: [] });
let nextId = 1;

/** Add a toast and auto-dismiss it after `timeout` ms. */
function push(kind: ToastKind, message: string, timeout = 4000) {
  const id = nextId++;
  state.items.push({ id, kind, message });
  setTimeout(() => dismiss(id), timeout);
}

function dismiss(id: number) {
  const idx = state.items.findIndex((t) => t.id === id);
  if (idx !== -1) state.items.splice(idx, 1);
}

export const toast = {
  info: (m: string) => push("info", m),
  success: (m: string) => push("success", m),
  error: (m: string) => push("error", m, 6000),
  dismiss,
};

export function useToasts() {
  return state;
}
