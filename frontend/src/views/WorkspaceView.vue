<template>
  <div class="layout" :class="{ 'sidebar-open': sidebarOpen }">
    <button class="hamburger" @click="sidebarOpen = !sidebarOpen" aria-label="Toggle menu">☰</button>

    <aside class="sidebar">
      <div class="brand">📚 Knowledge Base</div>
      <nav>
        <p class="nav-label">Workspaces</p>
        <ul>
          <li
            v-for="ws in workspaceList"
            :key="ws.id"
            class="ws-item"
            :class="{ active: ws.id === selected?.id }"
            @click="selectWorkspace(ws)"
          >
            <span class="ws-name">{{ ws.name }}</span>
            <span class="ws-role">{{ ws.my_role }}</span>
          </li>
        </ul>
        <button class="btn-new" @click="showCreate = true">+ New workspace</button>
      </nav>
      <div class="sidebar-footer">
        <span class="user-email">{{ authStore.user?.email }}</span>
        <div class="footer-actions">
          <button class="btn-icon" @click="toggleTheme" :title="theme === 'dark' ? 'Light mode' : 'Dark mode'">
            {{ theme === "dark" ? "☀️" : "🌙" }}
          </button>
          <button class="btn-logout" @click="logout">Logout</button>
        </div>
      </div>
    </aside>

    <main class="content">
      <div v-if="!selected" class="empty-state">
        <div class="empty-state-inner">
          <div class="empty-icon">📚</div>
          <h2>Welcome to Knowledge Base</h2>
          <p>Create your first workspace to start uploading documents and chatting with your knowledge base.</p>
          <button class="btn btn-primary" @click="showCreate = true">+ Create workspace</button>
        </div>
      </div>

      <template v-else>
        <div class="workspace-header">
          <h2>{{ selected.name }}</h2>
          <div class="header-actions">
            <router-link :to="`/workspaces/${selected.id}/members`" class="btn btn-secondary">👥 Members</router-link>
            <router-link :to="`/workspaces/${selected.id}/search`" class="btn btn-secondary">🔍 Search</router-link>
            <router-link :to="`/workspaces/${selected.id}/chat`" class="btn btn-primary">💬 Chat</router-link>
          </div>
        </div>

        <section class="section">
          <div class="section-header">
            <h3>Collections <span class="badge">{{ collectionList.length }}</span></h3>
            <button class="btn btn-secondary" @click="showCreateCollection = true" v-if="canManage">+ New collection</button>
          </div>
          <div v-if="collectionList.length" class="collection-list">
            <div
              v-for="col in collectionList"
              :key="col.id"
              class="collection-chip"
              :class="{ active: filterCollectionId === col.id }"
              @click="toggleCollectionFilter(col.id)"
            >
              {{ col.name }}
              <span class="col-count">{{ col.document_count ?? 0 }}</span>
              <button
                v-if="canManage"
                class="col-delete"
                @click.stop="removeCollection(col)"
                title="Delete collection"
              >×</button>
            </div>
          </div>
          <p v-else class="empty-docs">No collections yet.</p>
        </section>

        <section class="section">
          <div class="section-header">
            <h3>
              Documents <span class="badge">{{ documents.length }}</span>
              <span v-if="filterCollectionId" class="filter-pill">
                · filtered
                <button @click="filterCollectionId = null">×</button>
              </span>
            </h3>
            <label class="btn btn-secondary upload-btn">
              📄 Upload
              <input
                type="file"
                accept=".pdf,.docx,.txt,.md"
                multiple
                @change="onFileInput"
                hidden
              />
            </label>
          </div>

          <div v-if="collectionList.length" class="upload-collection-row">
            <label>Upload to collection:</label>
            <select v-model="uploadCollectionId">
              <option :value="null">No collection</option>
              <option v-for="c in collectionList" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>

          <div
            class="dropzone"
            :class="{ dragging: isDragging }"
            @dragover.prevent="isDragging = true"
            @dragenter.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="onDrop"
          >
            <p v-if="!isDragging">Drag & drop files here (PDF, DOCX, TXT, MD) or use the Upload button</p>
            <p v-else>Drop to upload</p>
          </div>

          <div v-if="uploadingCount" class="uploading-notice">
            Uploading {{ uploadingCount }} file{{ uploadingCount > 1 ? "s" : "" }}…
          </div>

          <div class="doc-list">
            <div v-for="doc in filteredDocs" :key="doc.id" class="doc-card">
              <div class="doc-info">
                <span class="doc-name">{{ doc.filename }}</span>
                <span class="doc-meta">
                  {{ doc.file_size_kb }} KB · {{ doc.chunk_count }} chunks
                  <span v-if="doc.collection"> · {{ doc.collection.name }}</span>
                </span>
              </div>
              <div class="doc-right">
                <span class="status-badge" :class="doc.status" :title="doc.error_message">
                  {{ doc.status }}
                  <span v-if="doc.status === 'processing' || doc.status === 'queued'" class="spin-icon">⟳</span>
                </span>
                <button
                  v-if="canManage || doc.uploaded_by?.id === authStore.user?.id"
                  class="btn-icon"
                  @click="removeDocument(doc)"
                  title="Delete"
                >🗑</button>
              </div>
            </div>
            <p v-if="filteredDocs.length === 0" class="empty-docs">
              No documents{{ filterCollectionId ? " in this collection" : "" }}. Upload to get started.
            </p>
          </div>
        </section>
      </template>
    </main>

    <Modal v-if="confirmModal.show" @close="confirmModal.show = false" title="Confirm action">
      <p class="confirm-message">{{ confirmModal.message }}</p>
      <template #footer>
        <button class="btn btn-secondary" @click="confirmModal.show = false">Cancel</button>
        <button class="btn btn-danger" @click="doConfirm">Delete</button>
      </template>
    </Modal>

    <Modal v-if="showCreate" @close="showCreate = false" title="New workspace">
      <input v-model="newName" placeholder="Workspace name" @keyup.enter="createWorkspace" />
      <template #footer>
        <button class="btn btn-secondary" @click="showCreate = false">Cancel</button>
        <button class="btn btn-primary" @click="createWorkspace">Create</button>
      </template>
    </Modal>

    <Modal v-if="showCreateCollection" @close="showCreateCollection = false" title="New collection">
      <input v-model="newCollectionName" placeholder="Collection name" @keyup.enter="createCollection" />
      <textarea v-model="newCollectionDescription" placeholder="Description (optional)" rows="3" />
      <template #footer>
        <button class="btn btn-secondary" @click="showCreateCollection = false">Cancel</button>
        <button class="btn btn-primary" @click="createCollection">Create</button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { workspaces as wsApi, documents as docApi, collections as colApi } from "../api/client";
import { toast } from "../lib/toast";
import { theme, toggleTheme } from "../lib/theme";
import Modal from "../components/Modal.vue";

const router = useRouter();
const authStore = useAuthStore();
const workspaceList = ref<any[]>([]);
const selected = ref<any>(null);
const documents = ref<any[]>([]);
const collectionList = ref<any[]>([]);
const filterCollectionId = ref<number | null>(null);
const showCreate = ref(false);
const showCreateCollection = ref(false);
const newName = ref("");
const newCollectionName = ref("");
const newCollectionDescription = ref("");
const uploadingCount = ref(0);
const isDragging = ref(false);
const sidebarOpen = ref(false);
const uploadCollectionId = ref<number | null>(null);
const confirmModal = ref<{ show: boolean; message: string; onConfirm: () => void }>({ show: false, message: "", onConfirm: () => {} });

const canManage = computed(() => ["owner", "admin"].includes(selected.value?.my_role));
const filteredDocs = computed(() =>
  filterCollectionId.value
    ? documents.value.filter((d) => d.collection?.id === filterCollectionId.value)
    : documents.value,
);

function askConfirm(message: string, onConfirm: () => void) {
  confirmModal.value = { show: true, message, onConfirm };
}

function doConfirm() {
  confirmModal.value.onConfirm();
  confirmModal.value.show = false;
}

onMounted(async () => {
  try {
    const { data } = await wsApi.list();
    workspaceList.value = data.data;
    if (workspaceList.value.length) selectWorkspace(workspaceList.value[0]);
  } catch {
    toast.error("Failed to load workspaces");
  }
});

async function selectWorkspace(ws: any) {
  selected.value = ws;
  filterCollectionId.value = null;
  sidebarOpen.value = false;
  await Promise.all([loadDocuments(), loadCollections()]);
  schedulePoll();
}

async function loadDocuments() {
  try {
    const { data } = await docApi.list(selected.value.id);
    documents.value = data.data;
  } catch {
    toast.error("Failed to load documents");
  }
}

async function loadCollections() {
  try {
    const { data } = await colApi.list(selected.value.id);
    collectionList.value = data.data;
  } catch {
    /* silent */
  }
}

let pollTimer: ReturnType<typeof setTimeout> | null = null;
let pollDelay = 2000;
function schedulePoll() {
  if (pollTimer) clearTimeout(pollTimer);
  const processing = documents.value.filter((d) => ["queued", "processing"].includes(d.status));
  if (!processing.length) {
    pollDelay = 2000;
    return;
  }
  pollTimer = setTimeout(async () => {
    await loadDocuments();
    pollDelay = Math.min(pollDelay * 1.5, 15000);
    schedulePoll();
  }, pollDelay);
}

onUnmounted(() => {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
})

function toggleCollectionFilter(id: number) {
  filterCollectionId.value = filterCollectionId.value === id ? null : id;
}

async function createWorkspace() {
  if (!newName.value.trim()) return;
  try {
    const { data } = await wsApi.create(newName.value);
    workspaceList.value.push(data.data);
    showCreate.value = false;
    newName.value = "";
    await selectWorkspace(data.data);
    toast.success("Workspace created");
  } catch {
    toast.error("Failed to create workspace");
  }
}

async function createCollection() {
  if (!newCollectionName.value.trim()) return;
  try {
    const { data } = await colApi.create(selected.value.id, {
      name: newCollectionName.value,
      description: newCollectionDescription.value || undefined,
    });
    collectionList.value.unshift(data.data);
    showCreateCollection.value = false;
    newCollectionName.value = "";
    newCollectionDescription.value = "";
    toast.success("Collection created");
  } catch {
    toast.error("Failed to create collection");
  }
}

function removeCollection(col: any) {
  askConfirm(`Delete collection "${col.name}"? This cannot be undone.`, async () => {
    try {
      await colApi.remove(selected.value.id, col.id);
      collectionList.value = collectionList.value.filter((c) => c.id !== col.id);
      if (filterCollectionId.value === col.id) filterCollectionId.value = null;
      toast.success("Collection deleted");
    } catch {
      toast.error("Failed to delete collection");
    }
  });
}

function removeDocument(doc: any) {
  askConfirm(`Delete "${doc.filename}"? This cannot be undone.`, async () => {
    try {
      await docApi.delete(selected.value.id, doc.id);
      documents.value = documents.value.filter((d) => d.id !== doc.id);
      toast.success("Document deleted");
    } catch {
      toast.error("Failed to delete document");
    }
  });
}

function onFileInput(e: Event) {
  const files = (e.target as HTMLInputElement).files;
  if (files) uploadFiles(Array.from(files));
  (e.target as HTMLInputElement).value = "";
}

function onDrop(e: DragEvent) {
  isDragging.value = false;
  const files = e.dataTransfer?.files;
  if (files) uploadFiles(Array.from(files));
}

async function uploadFiles(files: File[]) {
  if (!selected.value) return;
  uploadingCount.value += files.length;
  const targetCollection = uploadCollectionId.value ?? filterCollectionId.value;
  for (const file of files) {
    const fd = new FormData();
    fd.append("file", file);
    if (targetCollection) fd.append("collection_id", String(targetCollection));
    try {
      const { data } = await docApi.upload(selected.value.id, fd);
      documents.value.unshift(data.data);
      schedulePoll();
    } catch (err: any) {
      const msg = err.response?.data?.errors?.[0]?.message || `Upload failed: ${file.name}`;
      toast.error(msg);
    } finally {
      uploadingCount.value--;
    }
  }
}

async function logout() {
  await authStore.logout();
  router.push("/login");
}
</script>

<style scoped>
.layout { display: flex; min-height: 100vh; }
.hamburger {
  display: none;
  position: fixed;
  top: 0.75rem;
  left: 0.75rem;
  z-index: 20;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  color: var(--text);
  width: 36px;
  height: 36px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.1rem;
}
.sidebar {
  width: 260px;
  background: var(--bg-sidebar);
  color: var(--text-on-dark);
  display: flex;
  flex-direction: column;
  padding: 1.5rem 1rem;
  flex-shrink: 0;
}
.brand { font-size: 1.1rem; font-weight: 700; color: white; margin-bottom: 2rem; }
.nav-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin-bottom: 0.5rem; }
ul { list-style: none; padding: 0; margin: 0; }
.ws-item { padding: 0.5rem 0.75rem; border-radius: 6px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem; }
.ws-item:hover, .ws-item.active { background: #334155; }
.ws-name { font-size: 0.9rem; }
.ws-role { font-size: 0.7rem; background: #475569; padding: 0.15rem 0.4rem; border-radius: 4px; }
.btn-new { width: 100%; margin-top: 0.75rem; padding: 0.5rem; background: transparent; border: 1px dashed #475569; color: #94a3b8; border-radius: 6px; cursor: pointer; }
.sidebar-footer { margin-top: auto; border-top: 1px solid #334155; padding-top: 1rem; font-size: 0.8rem; display: flex; flex-direction: column; gap: 0.5rem; }
.user-email { color: var(--text-on-dark); overflow: hidden; text-overflow: ellipsis; }
.footer-actions { display: flex; justify-content: space-between; align-items: center; }
.btn-icon { background: none; border: none; color: var(--text-on-dark); cursor: pointer; font-size: 1rem; padding: 0.25rem; border-radius: 4px; }
.btn-icon:hover { background: #334155; }
.btn-logout { background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 0.8rem; }
.content { flex: 1; padding: 2rem; overflow-y: auto; }
.workspace-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem; }
.workspace-header h2 { font-size: 1.5rem; font-weight: 700; margin: 0; }
.header-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.btn { padding: 0.5rem 1rem; border-radius: 8px; text-decoration: none; font-size: 0.875rem; font-weight: 500; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 0.375rem; }
.btn-primary { background: var(--primary); color: var(--primary-fg); }
.btn-secondary { background: var(--bg-elevated); color: var(--text); border: 1px solid var(--border); }
.btn-danger { background: var(--danger); color: white; }
.section { background: var(--bg-elevated); border-radius: 12px; padding: 1.5rem; box-shadow: var(--shadow); margin-bottom: 1.5rem; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.5rem; }
.section-header h3 { font-size: 1rem; font-weight: 600; margin: 0; }
.badge { background: var(--bg-muted); color: var(--text-muted); padding: 0.1rem 0.5rem; border-radius: 99px; font-size: 0.75rem; margin-left: 0.5rem; }
.filter-pill { font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem; }
.filter-pill button { background: none; border: none; cursor: pointer; color: var(--text-muted); font-size: 0.9rem; }
.upload-btn { cursor: pointer; }
.upload-collection-row {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}
.upload-collection-row select {
  padding: 0.35rem 0.6rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text);
  font-size: 0.875rem;
  outline: none;
}
.upload-collection-row select:focus { border-color: var(--primary); }
.dropzone {
  border: 2px dashed var(--border);
  border-radius: 10px;
  padding: 1.5rem;
  text-align: center;
  color: var(--text-muted);
  margin-bottom: 1rem;
  transition: all 0.15s;
}
.dropzone.dragging { border-color: var(--primary); background: var(--bg-muted); color: var(--primary); }
.uploading-notice { background: #eff6ff; color: #1d4ed8; padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem; font-size: 0.875rem; }
[data-theme="dark"] .uploading-notice { background: #1e3a8a; color: #bfdbfe; }
.doc-list { display: flex; flex-direction: column; gap: 0.75rem; }
.doc-card { display: flex; justify-content: space-between; align-items: center; padding: 0.875rem 1rem; border: 1px solid var(--border); border-radius: 8px; }
.doc-name { font-weight: 500; font-size: 0.9rem; display: block; }
.doc-meta { color: var(--text-muted); font-size: 0.75rem; margin-top: 0.1rem; }
.doc-right { display: flex; gap: 0.5rem; align-items: center; }
.doc-right .btn-icon { color: var(--text-muted); }
.doc-right .btn-icon:hover { background: var(--bg-muted); color: var(--danger); }
.status-badge { font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 99px; font-weight: 500; display: inline-flex; align-items: center; gap: 0.3rem; }
.status-badge.ready { background: #dcfce7; color: #166534; }
.status-badge.processing, .status-badge.queued { background: #fef9c3; color: #854d0e; }
.status-badge.failed { background: #fee2e2; color: #991b1b; cursor: help; }
[data-theme="dark"] .status-badge.ready { background: #14532d; color: #bbf7d0; }
[data-theme="dark"] .status-badge.processing, [data-theme="dark"] .status-badge.queued { background: #713f12; color: #fef3c7; }
[data-theme="dark"] .status-badge.failed { background: #7f1d1d; color: #fecaca; }
.spin-icon { display: inline-block; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-docs { color: var(--text-muted); text-align: center; padding: 2rem; }
.empty-state { display: flex; align-items: center; justify-content: center; height: 100%; min-height: 60vh; }
.empty-state-inner { text-align: center; max-width: 380px; padding: 2rem; }
.empty-icon { font-size: 3.5rem; margin-bottom: 1rem; }
.empty-state-inner h2 { font-size: 1.5rem; font-weight: 700; margin: 0 0 0.75rem; color: var(--text); }
.empty-state-inner p { color: var(--text-muted); margin: 0 0 1.5rem; line-height: 1.6; }
.confirm-message { margin: 0; color: var(--text); }
.collection-list { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.collection-chip {
  background: var(--bg-muted);
  border: 1px solid var(--border);
  border-radius: 99px;
  padding: 0.35rem 0.875rem;
  font-size: 0.85rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.collection-chip:hover { border-color: var(--primary); }
.collection-chip.active { background: var(--primary); color: var(--primary-fg); border-color: var(--primary); }
.col-count { font-size: 0.7rem; opacity: 0.7; }
.col-delete { background: none; border: none; color: inherit; cursor: pointer; padding: 0 0 0 0.25rem; opacity: 0.6; }
.col-delete:hover { opacity: 1; }

@media (max-width: 768px) {
  .hamburger { display: block; }
  .sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    transform: translateX(-100%);
    transition: transform 0.2s;
    z-index: 15;
    width: 280px;
  }
  .layout.sidebar-open .sidebar { transform: translateX(0); }
  .content { padding: 3.5rem 1rem 1rem; }
}
</style>
