<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>Knowledge Base</h1>
      <p class="subtitle">{{ isRegister ? "Create account" : "Sign in to your workspace" }}</p>

      <form @submit.prevent="submit">
        <div v-if="isRegister" class="field">
          <label>Full name</label>
          <input v-model="form.full_name" type="text" required placeholder="Jane Smith" />
        </div>
        <div class="field">
          <label>Email</label>
          <input v-model="form.email" type="email" required placeholder="you@example.com" />
        </div>
        <div class="field">
          <label>Password</label>
          <input v-model="form.password" type="password" required placeholder="••••••••" />
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <button type="submit" :disabled="loading">
          {{ loading ? "Please wait…" : isRegister ? "Create account" : "Sign in" }}
        </button>
      </form>

      <p class="toggle">
        {{ isRegister ? "Already have an account?" : "No account yet?" }}
        <a @click="isRegister = !isRegister">{{ isRegister ? "Sign in" : "Register" }}</a>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { auth } from "../api/client";

const router = useRouter();
const authStore = useAuthStore();
const isRegister = ref(false);
const loading = ref(false);
const error = ref("");
const form = ref({ email: "", password: "", full_name: "" });

// Submit the auth form (login or register) and redirect on success.
async function submit() {
  loading.value = true;
  error.value = "";
  try {
    if (isRegister.value) {
      await auth.register(form.value);
    }
    await authStore.login(form.value.email, form.value.password);
    router.push("/workspaces");
  } catch (e: any) {
    const errors = e.response?.data?.errors;
    error.value = errors?.[0]?.message || "Something went wrong.";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg); padding: 1rem; }
.auth-card { background: var(--bg-elevated); padding: 2.5rem; border-radius: 12px; width: 100%; max-width: 420px; box-shadow: 0 4px 24px rgba(0,0,0,.08); }
h1 { font-size: 1.75rem; font-weight: 700; color: var(--text); margin: 0; }
.subtitle { color: var(--text-muted); margin: .5rem 0 2rem; }
.field { margin-bottom: 1.25rem; }
label { display: block; font-size: .875rem; font-weight: 500; color: var(--text); margin-bottom: .375rem; }
input { width: 100%; padding: .625rem .875rem; border: 1px solid var(--border); border-radius: 8px; font-size: 1rem; outline: none; background: var(--bg-input); color: var(--text); transition: border-color .15s; }
input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(99,102,241,.15); }
button { width: 100%; padding: .75rem; background: var(--primary); color: var(--primary-fg); border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; margin-top: .5rem; }
button:disabled { opacity: .6; cursor: not-allowed; }
.error { color: var(--danger); font-size: .875rem; margin: .5rem 0; }
.toggle { text-align: center; margin-top: 1.5rem; font-size: .875rem; color: var(--text-muted); }
.toggle a { color: var(--primary); cursor: pointer; font-weight: 500; margin-left: .25rem; }
</style>
