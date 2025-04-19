<template>
  <div class="toaster">
    <div
      v-for="t in toasts.items"
      :key="t.id"
      class="toast"
      :class="t.kind"
      role="status"
      @click="dismiss(t.id)"
    >
      {{ t.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { useToasts, toast } from "../lib/toast";
const toasts = useToasts();
const dismiss = toast.dismiss;
</script>

<style scoped>
.toaster {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  pointer-events: none;
}
.toast {
  pointer-events: auto;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  color: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  max-width: 360px;
  cursor: pointer;
  animation: slide-in 0.2s ease;
}
.toast.info { background: #475569; }
.toast.success { background: #16a34a; }
.toast.error { background: #dc2626; }
@keyframes slide-in {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
</style>
