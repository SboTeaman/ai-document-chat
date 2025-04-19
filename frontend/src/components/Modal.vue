<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal" role="dialog" aria-modal="true">
      <div v-if="title" class="modal-header">
        <h3>{{ title }}</h3>
        <button class="close" @click="$emit('close')" aria-label="Close">×</button>
      </div>
      <div class="modal-body">
        <slot />
      </div>
      <div v-if="$slots.footer" class="modal-footer">
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title?: string }>();
defineEmits(["close"]);
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 1rem;
}
.modal {
  background: var(--bg-elevated);
  color: var(--text);
  border-radius: 12px;
  width: 100%;
  max-width: 460px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}
.modal-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-header h3 { margin: 0; font-size: 1rem; font-weight: 600; }
.close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--text-muted);
  line-height: 1;
}
.modal-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow-y: auto;
}
.modal-body :deep(input),
.modal-body :deep(textarea),
.modal-body :deep(select) {
  width: 100%;
  padding: 0.625rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 0.9rem;
  font-family: inherit;
  background: var(--bg-input);
  color: var(--text);
  outline: none;
}
.modal-body :deep(input:focus),
.modal-body :deep(textarea:focus),
.modal-body :deep(select:focus) {
  border-color: var(--primary);
}
.modal-footer {
  padding: 1rem 1.25rem;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
