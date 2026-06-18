<template>
  <div class="chat-layout">
    <aside class="sessions-sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-header">
        <h3>Conversations</h3>
        <button class="btn-new-chat" @click="newSession" title="New conversation">+</button>
      </div>
      <ul>
        <li
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === currentSessionId }"
          @click="loadSession(s.id)"
        >
          <span>{{ s.title || "New conversation" }}</span>
          <button class="btn-delete-session" @click.stop="deleteSession(s)" title="Delete">×</button>
        </li>
      </ul>

      <div v-if="collectionList.length" class="collection-filter">
        <label>Filter by collection</label>
        <select v-model="collectionId">
          <option :value="null">All collections</option>
          <option v-for="c in collectionList" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>

      <router-link :to="`/workspaces/${workspaceId}`" class="back-link">← Back to workspace</router-link>
    </aside>

    <div class="chat-main">
      <button class="mobile-toggle" @click="sidebarOpen = !sidebarOpen">☰</button>
      <div class="messages-area" ref="messagesEl" aria-live="polite" :aria-busy="streaming">
        <div v-if="!messages.length" class="welcome">
          <h2>Knowledge Base Chat</h2>
          <p>Ask questions about your uploaded documents. I'll answer based on the content and cite my sources.</p>
          <div class="example-questions">
            <p>Try asking:</p>
            <div class="chips">
              <span v-for="q in examples" :key="q" class="chip" @click="sendMessage(q)">{{ q }}</span>
            </div>
          </div>
        </div>

        <div
          v-for="(msg, idx) in messages"
          :key="msg.id || msg._key"
          class="message"
          :class="msg.role"
        >
          <div class="bubble">
            <span v-if="msg.role === 'user'">{{ msg.content }}</span>
            <template v-else>
              <div v-if="msg.streaming" class="streaming-text">
                <div v-html="renderMarkdown(msg.content)"></div>
                <span class="cursor">▋</span>
              </div>
              <div v-else v-html="renderMarkdown(msg.content)"></div>
            </template>
          </div>

          <div v-if="msg.citations?.length" class="citations">
            <p class="citations-label">Sources:</p>
            <div
              v-for="c in msg.citations"
              :key="`${c.document_id}-${c.chunk_index}`"
              class="citation"
              role="button"
              tabindex="0"
              :aria-label="`Source: ${c.document_name}, chunk ${c.chunk_index}`"
              @click="openCitation(c)"
              @keydown.enter="openCitation(c)"
              @keydown.space.prevent="openCitation(c)"
            >
              <span class="citation-source">📄 {{ c.document_name }} · chunk {{ c.chunk_index }}</span>
              <p class="citation-excerpt">{{ c.excerpt }}</p>
            </div>
          </div>

          <div v-if="msg.role === 'assistant' && !msg.streaming && msg.content" class="message-actions">
            <button @click="copyMessage(msg.content)" title="Copy">📋</button>
            <button v-if="idx === messages.length - 1" @click="regenerate" title="Regenerate">🔄</button>
          </div>
        </div>

        <div v-if="streaming && !messages.some(m => m.streaming)" class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </div>

      <div class="input-wrapper">
        <form class="input-area" @submit.prevent="sendMessage()">
          <textarea
            v-model="input"
            placeholder="Ask a question about your documents…"
            rows="1"
            @keydown.enter.exact.prevent="sendMessage()"
            @input="autoResize"
            ref="inputEl"
            :disabled="streaming"
          />
          <button v-if="streaming" type="button" class="stop-btn" @click="stopGeneration">Stop</button>
          <button v-else type="submit" :disabled="!input.trim()">Send</button>
        </form>
        <p class="input-hint">Press <kbd>Enter</kbd> to send · <kbd>Shift+Enter</kbd> for new line</p>
      </div>
    </div>

    <Modal v-if="confirmModal.show" @close="confirmModal.show = false" title="Confirm action">
      <p class="confirm-message">{{ confirmModal.message }}</p>
      <template #footer>
        <button class="btn btn-secondary" @click="confirmModal.show = false">Cancel</button>
        <button class="btn btn-danger" @click="doConfirm">Delete</button>
      </template>
    </Modal>

    <Modal v-if="citationModal" @close="citationModal = null" :title="citationModal.document_name">
      <p class="citation-modal-meta">Chunk {{ citationModal.chunk_index }}</p>
      <p class="citation-modal-text">{{ citationModal.excerpt }}</p>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from "vue";
import { useRoute } from "vue-router";
import { chat, collections as colApi } from "../api/client";
import { renderMarkdown } from "../lib/markdown";
import { toast } from "../lib/toast";
import Modal from "../components/Modal.vue";

const route = useRoute();
const workspaceId = Number(route.params.id);

const sessions = ref<any[]>([]);
const currentSessionId = ref<number | null>(null);
const messages = ref<any[]>([]);
const collectionList = ref<any[]>([]);
const collectionId = ref<number | null>(null);
const input = ref("");
const streaming = ref(false);
const sidebarOpen = ref(false);
const messagesEl = ref<HTMLElement | null>(null);
const inputEl = ref<HTMLTextAreaElement | null>(null);
let abortCtrl: AbortController | null = null;

const confirmModal = ref<{ show: boolean; message: string; onConfirm: () => void }>({ show: false, message: "", onConfirm: () => {} });
const citationModal = ref<any | null>(null);

function askConfirm(message: string, onConfirm: () => void) {
  confirmModal.value = { show: true, message, onConfirm };
}

function doConfirm() {
  confirmModal.value.onConfirm();
  confirmModal.value.show = false;
}

const examples = [
  "Summarize the main policies",
  "What are the technical requirements?",
  "How does the onboarding process work?",
];

onMounted(async () => {
  try {
    const [{ data: sessData }, { data: colData }] = await Promise.all([
      chat.sessions(workspaceId),
      colApi.list(workspaceId),
    ]);
    sessions.value = sessData.data;
    collectionList.value = colData.data;
    if (sessions.value.length) loadSession(sessions.value[0].id);
  } catch {
    toast.error("Failed to load chat");
  }
});

async function newSession() {
  const { data } = await chat.createSession(workspaceId);
  sessions.value.unshift(data.data);
  currentSessionId.value = data.data.id;
  messages.value = [];
  sidebarOpen.value = false;
}

async function loadSession(sessionId: number) {
  currentSessionId.value = sessionId;
  const { data } = await chat.getSession(workspaceId, sessionId);
  messages.value = data.data.messages;
  sidebarOpen.value = false;
  scrollBottom();
}

function deleteSession(s: any) {
  askConfirm("Delete this conversation? This cannot be undone.", async () => {
    try {
      await chat.deleteSession(workspaceId, s.id);
      sessions.value = sessions.value.filter((x) => x.id !== s.id);
      if (currentSessionId.value === s.id) {
        currentSessionId.value = null;
        messages.value = [];
      }
      toast.success("Conversation deleted");
    } catch {
      toast.error("Failed to delete");
    }
  });
}

async function sendMessage(text?: string) {
  const content = text || input.value.trim();
  if (!content || streaming.value) return;
  if (!currentSessionId.value) await newSession();

  input.value = "";
  messages.value.push({ role: "user", content, _key: Date.now() });
  scrollBottom();

  const assistantMsg: any = {
    role: "assistant",
    content: "",
    citations: [],
    streaming: true,
    _key: Date.now() + 1,
  };
  messages.value.push(assistantMsg);
  streaming.value = true;
  abortCtrl = new AbortController();

  const token = sessionStorage.getItem("access_token");
  try {
    const response = await fetch(
      `/api/workspaces/${workspaceId}/chat/sessions/${currentSessionId.value}/messages/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ content, collection_id: collectionId.value }),
        signal: abortCtrl.signal,
      },
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === "token") {
            assistantMsg.content += data.token;
            scrollBottom();
          } else if (data.type === "done") {
            assistantMsg.citations = data.citations;
            assistantMsg.streaming = false;
          } else if (data.type === "error") {
            assistantMsg.content = data.message || "Error";
            assistantMsg.streaming = false;
            toast.error(data.message || "AI error");
          }
        } catch {
          /* ignore */
        }
      }
    }
  } catch (e: any) {
    if (e.name === "AbortError") {
      assistantMsg.content += "\n\n*(stopped)*";
    } else {
      assistantMsg.content = "Failed to get a response.";
      toast.error("Chat request failed");
    }
  } finally {
    assistantMsg.streaming = false;
    streaming.value = false;
    abortCtrl = null;
    const idx = sessions.value.findIndex((s) => s.id === currentSessionId.value);
    if (idx !== -1 && !sessions.value[idx].title) {
      sessions.value[idx].title = content.slice(0, 60);
    }
  }
}

function stopGeneration() {
  abortCtrl?.abort();
}

async function regenerate() {
  const lastUser = [...messages.value].reverse().find((m) => m.role === "user");
  if (!lastUser) return;
  messages.value.pop();
  await sendMessage(lastUser.content);
}

async function copyMessage(content: string) {
  try {
    await navigator.clipboard.writeText(content);
    toast.success("Copied");
  } catch {
    toast.error("Copy failed");
  }
}

function openCitation(c: any) {
  citationModal.value = c;
}

function scrollBottom() {
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
  });
}

function autoResize(e: Event) {
  const el = e.target as HTMLTextAreaElement;
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 160) + "px";
}
</script>

<style scoped>
.chat-layout { display: flex; height: 100vh; }
.sessions-sidebar {
  width: 260px;
  background: var(--bg-sidebar);
  color: var(--text-on-dark);
  display: flex;
  flex-direction: column;
  padding: 1rem;
  flex-shrink: 0;
}
.sidebar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.sidebar-header h3 { font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; margin: 0; }
.btn-new-chat { background: #334155; border: none; color: #e2e8f0; width: 28px; height: 28px; border-radius: 6px; cursor: pointer; font-size: 1.1rem; }
ul { list-style: none; flex: 1; overflow-y: auto; padding: 0; margin: 0; }
.session-item {
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.2rem;
}
.session-item:hover, .session-item.active { background: #334155; }
.session-item span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.btn-delete-session { background: none; border: none; color: #64748b; cursor: pointer; padding: 0 0.25rem; opacity: 0; }
.session-item:hover .btn-delete-session { opacity: 1; }
.btn-delete-session:hover { color: #f87171; }
.collection-filter { margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #334155; }
.collection-filter label { font-size: 0.7rem; text-transform: uppercase; color: #64748b; letter-spacing: 0.06em; }
.collection-filter select {
  width: 100%;
  margin-top: 0.35rem;
  padding: 0.4rem;
  background: #0f172a;
  color: #cbd5e1;
  border: 1px solid #334155;
  border-radius: 6px;
  font-size: 0.85rem;
}
.back-link { color: #64748b; text-decoration: none; font-size: 0.8rem; margin-top: 1rem; }
.chat-main { flex: 1; display: flex; flex-direction: column; background: var(--bg); position: relative; }
.mobile-toggle { display: none; position: absolute; top: 0.75rem; left: 0.75rem; z-index: 5; background: var(--bg-elevated); border: 1px solid var(--border); color: var(--text); width: 36px; height: 36px; border-radius: 8px; cursor: pointer; }
.messages-area { flex: 1; overflow-y: auto; padding: 2rem; display: flex; flex-direction: column; gap: 1.5rem; }
.welcome { text-align: center; margin: auto; max-width: 480px; color: var(--text-muted); }
.welcome h2 { font-size: 1.5rem; color: var(--text); margin-bottom: 0.5rem; }
.example-questions { margin-top: 1.5rem; }
.chips { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; margin-top: 0.75rem; }
.chip {
  padding: 0.4rem 0.875rem;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 99px;
  font-size: 0.875rem;
  cursor: pointer;
}
.chip:hover { border-color: var(--primary); color: var(--primary); }
.message { display: flex; flex-direction: column; max-width: 75%; }
.message.user { align-self: flex-end; align-items: flex-end; }
.message.assistant { align-self: flex-start; align-items: flex-start; }
.bubble {
  padding: 0.875rem 1.125rem;
  border-radius: 12px;
  font-size: 0.95rem;
  line-height: 1.65;
  word-wrap: break-word;
}
.message.user .bubble { background: var(--primary); color: var(--primary-fg); border-bottom-right-radius: 2px; white-space: pre-wrap; }
.message.assistant .bubble {
  background: var(--bg-elevated);
  color: var(--text);
  border: 1px solid var(--border);
  border-bottom-left-radius: 2px;
}
.message.assistant .bubble :deep(p) { margin: 0 0 0.5rem 0; }
.message.assistant .bubble :deep(p:last-child) { margin-bottom: 0; }
.message.assistant .bubble :deep(pre) {
  background: var(--bg-muted);
  padding: 0.75rem;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 0.85rem;
}
.message.assistant .bubble :deep(code) {
  background: var(--bg-muted);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-size: 0.85rem;
}
.message.assistant .bubble :deep(pre code) { background: none; padding: 0; }
.message.assistant .bubble :deep(ul),
.message.assistant .bubble :deep(ol) { padding-left: 1.25rem; margin: 0.5rem 0; }
.message.assistant .bubble :deep(blockquote) {
  border-left: 3px solid var(--border);
  padding-left: 0.75rem;
  margin: 0.5rem 0;
  color: var(--text-muted);
}
.cursor { animation: blink 0.7s infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.citations { margin-top: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem; width: 100%; }
.citations-label { font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; margin: 0; }
.citation {
  background: var(--bg-muted);
  border-left: 3px solid var(--primary);
  padding: 0.5rem 0.75rem;
  border-radius: 0 6px 6px 0;
  cursor: pointer;
  transition: background 0.15s;
}
.citation:hover { background: var(--border); }
.citation-source { font-size: 0.75rem; font-weight: 600; color: var(--primary); }
.citation-excerpt { font-size: 0.8rem; color: var(--text-muted); margin: 0.25rem 0 0; }
.message-actions { display: flex; gap: 0.25rem; margin-top: 0.25rem; opacity: 0.5; transition: opacity 0.15s; }
.message:hover .message-actions { opacity: 1; }
.message-actions button { background: none; border: 1px solid var(--border); border-radius: 6px; padding: 0.2rem 0.4rem; cursor: pointer; font-size: 0.8rem; }
.typing-indicator { display: flex; gap: 4px; padding: 0.75rem 1rem; background: var(--bg-elevated); border-radius: 12px; width: fit-content; border: 1px solid var(--border); }
.typing-indicator span { width: 7px; height: 7px; background: #94a3b8; border-radius: 50%; animation: bounce 0.8s infinite; }
.typing-indicator span:nth-child(2) { animation-delay: 0.15s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
.input-wrapper { display: flex; flex-direction: column; background: var(--bg-elevated); border-top: 1px solid var(--border); }
.input-area {
  display: flex;
  gap: 0.75rem;
  padding: 1rem 1.5rem 0.5rem;
}
.input-area textarea {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 0.95rem;
  resize: none;
  outline: none;
  font-family: inherit;
  background: var(--bg-input);
  color: var(--text);
}
.input-area textarea:focus { border-color: var(--primary); }
.input-area button {
  padding: 0.75rem 1.25rem;
  background: var(--primary);
  color: var(--primary-fg);
  border: none;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  align-self: flex-end;
}
.input-area button:disabled { opacity: 0.5; cursor: not-allowed; }
.input-area .stop-btn { background: var(--danger); color: white; }
.input-hint {
  font-size: 0.72rem;
  color: var(--text-muted);
  text-align: center;
  padding: 0 1rem 0.625rem;
  margin: 0;
}
.input-hint kbd {
  background: var(--bg-muted);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 0.05rem 0.3rem;
  font-size: 0.68rem;
  font-family: inherit;
}
.btn { padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.875rem; font-weight: 500; border: none; cursor: pointer; display: inline-flex; align-items: center; }
.btn-secondary { background: var(--bg-elevated); color: var(--text); border: 1px solid var(--border); }
.btn-danger { background: var(--danger); color: white; }
.confirm-message { margin: 0; color: var(--text); }
.citation-modal-meta {
  font-size: 0.72rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
  margin: 0 0 0.75rem;
}
.citation-modal-text {
  color: var(--text);
  font-size: 0.9rem;
  line-height: 1.7;
  margin: 0;
  white-space: pre-wrap;
}

@media (max-width: 768px) {
  .sessions-sidebar {
    position: absolute;
    inset: 0 auto 0 0;
    transform: translateX(-100%);
    transition: transform 0.2s;
    z-index: 10;
    width: 260px;
  }
  .sessions-sidebar.open { transform: translateX(0); }
  .mobile-toggle { display: block; }
  .messages-area { padding: 3.5rem 1rem 1rem; }
  .message { max-width: 92%; }
}
</style>
