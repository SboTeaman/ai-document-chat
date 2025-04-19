<template>
  <div class="page">
    <div class="page-header">
      <router-link :to="`/workspaces/${workspaceId}`" class="back-link">← Back</router-link>
      <h1>Search</h1>
    </div>

    <div class="search-controls">
      <div class="search-box">
        <input
          v-model="query"
          type="text"
          placeholder="Ask anything about your documents…"
          @keyup.enter="runSearch"
          autofocus
        />
        <button @click="runSearch" :disabled="loading || !query.trim()">
          {{ loading ? "Searching…" : "Search" }}
        </button>
      </div>
      <select v-if="collectionList.length" v-model="collectionId" class="collection-select">
        <option :value="null">All collections</option>
        <option v-for="c in collectionList" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
    </div>

    <div v-if="!results.length && !loading && !searched" class="suggestions">
      <p>Try one of these:</p>
      <div class="chips">
        <span v-for="s in suggestions" :key="s" class="chip" @click="query = s; runSearch()">{{ s }}</span>
      </div>
    </div>

    <div v-if="loading" class="results">
      <div v-for="i in 3" :key="i" class="skeleton-card">
        <div class="skeleton-line w-40" />
        <div class="skeleton-line w-100" />
        <div class="skeleton-line w-80" />
      </div>
    </div>

    <div v-if="searched && !loading && results.length === 0" class="no-results">
      No results found for "{{ lastQuery }}". Try different keywords.
    </div>

    <div v-if="results.length && !loading" class="results">
      <p class="results-meta">{{ results.length }} results for "<strong>{{ lastQuery }}</strong>"</p>
      <div v-for="result in results" :key="result.chunk_id" class="result-card">
        <div class="result-header">
          <span class="doc-name">📄 {{ result.document_name }}</span>
          <span class="score">{{ (result.similarity_score * 100).toFixed(0) }}% match</span>
        </div>
        <p class="result-content" v-html="highlight(result.content, lastQuery)"></p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { search, collections as colApi } from "../api/client";
import { highlight } from "../lib/markdown";
import { toast } from "../lib/toast";

const route = useRoute();
const workspaceId = Number(route.params.id);
const query = ref("");
const collectionId = ref<number | null>(null);
const collectionList = ref<any[]>([]);
const results = ref<any[]>([]);
const loading = ref(false);
const searched = ref(false);
const lastQuery = ref("");

const suggestions = [
  "What are the refund policies?",
  "How to configure the API?",
  "Security requirements",
  "Onboarding process",
];

onMounted(async () => {
  try {
    const { data } = await colApi.list(workspaceId);
    collectionList.value = data.data;
  } catch {
    /* silent */
  }
});

// Run a hybrid search for the current query and render the results.
async function runSearch() {
  if (!query.value.trim()) return;
  loading.value = true;
  searched.value = false;
  lastQuery.value = query.value;
  try {
    const { data } = await search.query(workspaceId, query.value, collectionId.value);
    results.value = data.data;
  } catch {
    results.value = [];
    toast.error("Search failed");
  } finally {
    loading.value = false;
    searched.value = true;
  }
}
</script>

<style scoped>
.page { max-width: 800px; margin: 0 auto; padding: 2rem 1rem; }
.page-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem; }
.back-link { color: var(--primary); text-decoration: none; font-size: 0.875rem; }
h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
.search-controls { display: flex; gap: 0.75rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.search-box { display: flex; gap: 0.75rem; flex: 1; min-width: 240px; }
.search-box input {
  flex: 1;
  padding: 0.875rem 1rem;
  border: 2px solid var(--border);
  border-radius: 10px;
  font-size: 1rem;
  outline: none;
  background: var(--bg-input);
  color: var(--text);
  transition: border-color 0.15s;
}
.search-box input:focus { border-color: var(--primary); }
.search-box button {
  padding: 0.875rem 1.5rem;
  background: var(--primary);
  color: var(--primary-fg);
  border: none;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.search-box button:disabled { opacity: 0.6; cursor: not-allowed; }
.collection-select {
  padding: 0.75rem;
  border: 2px solid var(--border);
  border-radius: 10px;
  background: var(--bg-input);
  color: var(--text);
  font-size: 0.9rem;
  min-width: 180px;
}
.suggestions p { color: var(--text-muted); font-size: 0.875rem; margin-bottom: 0.75rem; }
.chips { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.chip {
  padding: 0.4rem 0.875rem;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 99px;
  font-size: 0.875rem;
  cursor: pointer;
  color: var(--text);
}
.chip:hover { border-color: var(--primary); color: var(--primary); }
.no-results { text-align: center; color: var(--text-muted); padding: 3rem; }
.results-meta { color: var(--text-muted); font-size: 0.875rem; margin-bottom: 1rem; }
.results { display: flex; flex-direction: column; gap: 1rem; }
.result-card { background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
.doc-name { font-weight: 600; font-size: 0.875rem; color: var(--text); }
.score {
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 0.75rem;
  padding: 0.2rem 0.6rem;
  border-radius: 99px;
  font-weight: 600;
}
[data-theme="dark"] .score { background: #1e3a8a; color: #bfdbfe; }
.result-content { color: var(--text-muted); font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap; margin: 0; }
.skeleton-card {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.skeleton-line {
  height: 12px;
  background: linear-gradient(90deg, var(--bg-muted) 0%, var(--border) 50%, var(--bg-muted) 100%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
  border-radius: 4px;
}
.w-40 { width: 40%; }
.w-80 { width: 80%; }
.w-100 { width: 100%; }
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
