<template>
  <div class="page">
    <div class="page-header">
      <router-link :to="`/workspaces/${workspaceId}`" class="back-link">← Back</router-link>
      <h1>Members</h1>
      <button v-if="canManage" class="btn btn-primary" @click="showInvite = true">+ Invite</button>
    </div>

    <div v-if="loading" class="loading">Loading…</div>

    <div v-else class="members-list">
      <div v-for="m in members" :key="m.id" class="member-card">
        <div class="member-info">
          <div class="member-email">{{ m.user.email }}</div>
          <div class="member-meta">
            <span class="role-badge" :class="m.role">{{ m.role }}</span>
            <span class="joined">joined {{ formatDate(m.joined_at) }}</span>
          </div>
        </div>
        <div v-if="canManage && m.role !== 'owner'" class="member-actions">
          <select :value="m.role" @change="updateRole(m, $event)">
            <option value="admin">Admin</option>
            <option value="member">Member</option>
            <option value="viewer">Viewer</option>
          </select>
          <button class="btn-icon" @click="removeMember(m)" title="Remove">🗑</button>
        </div>
      </div>
      <p v-if="!members.length" class="empty">No members yet.</p>
    </div>

    <Modal v-if="showInvite" @close="showInvite = false" title="Invite member">
      <input v-model="inviteEmail" type="email" placeholder="user@example.com" />
      <select v-model="inviteRole">
        <option value="admin">Admin</option>
        <option value="member">Member</option>
        <option value="viewer">Viewer</option>
      </select>
      <template #footer>
        <button class="btn btn-secondary" @click="showInvite = false">Cancel</button>
        <button class="btn btn-primary" @click="invite">Invite</button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { workspaces as wsApi } from "../api/client";
import { toast } from "../lib/toast";
import { useAuthStore } from "../stores/auth";
import Modal from "../components/Modal.vue";

const route = useRoute();
const workspaceId = Number(route.params.id);
const authStore = useAuthStore();

const members = ref<any[]>([]);
const loading = ref(true);
const showInvite = ref(false);
const inviteEmail = ref("");
const inviteRole = ref("member");

const me = computed(() => members.value.find((m) => m.user.id === authStore.user?.id));
const canManage = computed(() => me.value && ["owner", "admin"].includes(me.value.role));

onMounted(load);

// Fetch the workspace's members.
async function load() {
  loading.value = true;
  try {
    const { data } = await wsApi.members(workspaceId);
    members.value = data.data;
  } catch {
    toast.error("Failed to load members");
  } finally {
    loading.value = false;
  }
}

// Invite a user by email with the chosen role.
async function invite() {
  if (!inviteEmail.value.trim()) return;
  try {
    const { data } = await wsApi.inviteMember(workspaceId, inviteEmail.value, inviteRole.value);
    members.value.push(data.data);
    showInvite.value = false;
    inviteEmail.value = "";
    inviteRole.value = "member";
    toast.success("Member invited");
  } catch (err: any) {
    toast.error(err.response?.data?.errors?.[0]?.message || "Invite failed");
  }
}

// Change a member's role from the dropdown selection.
async function updateRole(m: any, e: Event) {
  const role = (e.target as HTMLSelectElement).value;
  try {
    const { data } = await wsApi.updateMember(workspaceId, m.id, role);
    Object.assign(m, data.data);
    toast.success("Role updated");
  } catch {
    toast.error("Update failed");
  }
}

// Remove a member (with confirmation).
async function removeMember(m: any) {
  if (!confirm(`Remove ${m.user.email}?`)) return;
  try {
    await wsApi.removeMember(workspaceId, m.id);
    members.value = members.value.filter((x) => x.id !== m.id);
    toast.success("Member removed");
  } catch {
    toast.error("Remove failed");
  }
}

// Format an ISO timestamp as a locale date (empty string if missing).
function formatDate(iso: string) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString();
}
</script>

<style scoped>
.page { max-width: 720px; margin: 0 auto; padding: 2rem 1rem; }
.page-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem; }
.back-link { color: var(--primary); text-decoration: none; font-size: 0.875rem; }
h1 { font-size: 1.5rem; font-weight: 700; margin: 0; flex: 1; }
.btn { padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.875rem; font-weight: 500; border: none; cursor: pointer; }
.btn-primary { background: var(--primary); color: var(--primary-fg); }
.btn-secondary { background: var(--bg-elevated); color: var(--text); border: 1px solid var(--border); }
.btn-icon { background: none; border: 1px solid var(--border); border-radius: 6px; padding: 0.35rem 0.5rem; cursor: pointer; color: var(--text-muted); }
.btn-icon:hover { color: var(--danger); border-color: var(--danger); }
.loading, .empty { text-align: center; color: var(--text-muted); padding: 2rem; }
.members-list { display: flex; flex-direction: column; gap: 0.75rem; }
.member-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 10px;
  gap: 1rem;
  flex-wrap: wrap;
}
.member-email { font-weight: 500; }
.member-meta { display: flex; gap: 0.5rem; align-items: center; margin-top: 0.25rem; font-size: 0.75rem; color: var(--text-muted); }
.role-badge { padding: 0.15rem 0.5rem; border-radius: 99px; font-weight: 600; text-transform: capitalize; font-size: 0.7rem; }
.role-badge.owner { background: #fef3c7; color: #92400e; }
.role-badge.admin { background: #dbeafe; color: #1e40af; }
.role-badge.member { background: #dcfce7; color: #166534; }
.role-badge.viewer { background: var(--bg-muted); color: var(--text-muted); }
[data-theme="dark"] .role-badge.owner { background: #713f12; color: #fef3c7; }
[data-theme="dark"] .role-badge.admin { background: #1e3a8a; color: #bfdbfe; }
[data-theme="dark"] .role-badge.member { background: #14532d; color: #bbf7d0; }
.member-actions { display: flex; gap: 0.5rem; align-items: center; }
.member-actions select {
  padding: 0.35rem 0.5rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text);
  font-size: 0.85rem;
}
</style>
