<template>
  <div class="app-shell">
    <aside class="sidebar">
      <section class="brand-block">
        <img class="brand-logo" src="/sparkle-ignis-logo.svg" alt="Sparkle Ignis logo" />
        <div>
          <p class="eyebrow">Sparkle AI Series</p>
          <h1>Sparkle Ignis</h1>
          <p class="generation">第一代 · LLM 技术研究 Agent</p>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <span>Agent 路由</span>
          <strong>{{ routeLabel }}</strong>
        </div>
        <select v-model="selectedAgent" aria-label="选择 Agent">
          <option value="auto">自动判定</option>
          <option value="all">多 Agent 综合</option>
          <option v-for="agent in agents" :key="agent.id" :value="agent.id">
            {{ agent.name }} · {{ agent.pdf_count }} PDFs
          </option>
        </select>
      </section>

      <section class="panel">
        <div class="panel-head">
          <span>文档索引</span>
          <strong :class="{ ready: indexReady }">{{ indexReady ? '就绪' : '待处理' }}</strong>
        </div>
        <p class="status-line">{{ indexText }}</p>
        <button class="secondary-button" :disabled="busy" @click="rebuildIndex">重建元数据索引</button>
      </section>

      <section class="agent-grid" aria-label="可用 Agent">
        <button
          v-for="agent in agents"
          :key="agent.id"
          class="agent-card"
          :class="{ active: selectedAgent === agent.id }"
          @click="selectedAgent = agent.id"
        >
          <span>{{ agent.name }}</span>
          <small>{{ agent.pdf_count }} PDFs</small>
        </button>
      </section>
    </aside>

    <main class="workspace">
      <header class="topbar">
        <div>
          <p class="eyebrow">Research Console</p>
          <h2>面向 LLM 技术报告的多级 Agent 问答</h2>
        </div>
        <div class="topbar-meta">
          <span>RAG</span>
          <span>DeepSeek Ready</span>
          <span>Evidence Audit</span>
        </div>
      </header>

      <section ref="messagesEl" class="messages">
        <article v-for="message in messages" :key="message.id" class="message" :class="message.role">
          <div class="avatar">{{ message.role === 'user' ? '你' : 'Ignis' }}</div>
          <div class="bubble">
            <template v-if="message.role === 'assistant' && message.payload">
              <details v-if="message.payload.thinking?.length" class="thinking" open>
                <summary>思考摘要</summary>
                <ul>
                  <li v-for="item in message.payload.thinking" :key="item">{{ item }}</li>
                </ul>
              </details>
              <div class="answer" v-html="formatAnswer(message.payload.answer)"></div>
              <div v-if="message.payload.evidence?.length" class="evidence-list">
                <span v-for="item in message.payload.evidence.slice(0, 8)" :key="item.chunk_id">
                  {{ item.agent_name }} · {{ item.title }} p.{{ item.page }}
                </span>
              </div>
            </template>
            <template v-else>
              <div class="answer" v-html="formatAnswer(message.text)"></div>
            </template>
          </div>
        </article>
      </section>

      <form class="composer" @submit.prevent="sendQuestion">
        <textarea
          v-model="question"
          :disabled="busy"
          rows="1"
          placeholder="输入问题，例如：我想知道 KimiAI 框架的演进过程"
          @keydown.enter.exact.prevent="sendQuestion"
        />
        <button :disabled="busy || !question.trim()" type="submit" aria-label="发送">↑</button>
      </form>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'

const agents = ref([])
const selectedAgent = ref('auto')
const indexStatus = ref({})
const busy = ref(false)
const question = ref('')
const messages = ref([
  {
    id: crypto.randomUUID(),
    role: 'assistant',
    text: '这里是 Sparkle Ignis 第一代。你可以指定某个 LLM Agent，也可以让系统自动判断是否需要多 Agent 综合。',
  },
])
const messagesEl = ref(null)

const indexReady = computed(() => indexStatus.value.built && !indexStatus.value.stale)
const indexText = computed(() => {
  if (!indexStatus.value.built) return '尚未构建元数据索引。首次提问会自动构建。'
  const chunks = indexStatus.value.chunk_count ?? 0
  const agentIndexes = indexStatus.value.agent_index_count ?? 0
  return `${chunks} 条文档元数据，${agentIndexes} 个 Agent 全文索引已缓存。`
})
const routeLabel = computed(() => {
  if (selectedAgent.value === 'auto') return '自动'
  if (selectedAgent.value === 'all') return '综合'
  return agents.value.find((agent) => agent.id === selectedAgent.value)?.name ?? selectedAgent.value
})

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || data.answer || '请求失败')
  return data
}

async function loadAgents() {
  const data = await api('/api/agents')
  agents.value = data.agents || []
}

async function loadIndexStatus() {
  indexStatus.value = await api('/api/index/status')
}

async function rebuildIndex() {
  busy.value = true
  try {
    indexStatus.value = await api('/api/index/rebuild', { method: 'POST', body: '{}' })
    appendAssistant({
      answer: '元数据索引已重建。目标 Agent 的全文索引会在首次命中时按需构建。',
      thinking: [
        `文档数：${indexStatus.value.document_count ?? 0}`,
        `元数据片段：${indexStatus.value.chunk_count ?? 0}`,
      ],
      evidence: [],
    })
  } catch (error) {
    appendText('assistant', `索引重建失败：${error.message}`)
  } finally {
    busy.value = false
  }
}

async function sendQuestion() {
  const text = question.value.trim()
  if (!text || busy.value) return
  question.value = ''
  appendText('user', text)
  busy.value = true
  const pendingId = appendAssistant({
    answer: '正在检索文档、判断意图并调度 Agent...',
    thinking: ['相关性审查', '意图路由', 'RAG 检索', '答案审核'],
    evidence: [],
  })

  const agentIds =
    selectedAgent.value === 'auto'
      ? []
      : selectedAgent.value === 'all'
        ? agents.value.map((agent) => agent.id)
        : [selectedAgent.value]

  try {
    const result = await api('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ question: text, agent_ids: agentIds }),
    })
    replaceMessage(pendingId, { id: pendingId, role: 'assistant', payload: result })
    await loadIndexStatus()
  } catch (error) {
    replaceMessage(pendingId, { id: pendingId, role: 'assistant', text: `处理失败：${error.message}` })
  } finally {
    busy.value = false
  }
}

function appendText(role, text) {
  const id = crypto.randomUUID()
  messages.value.push({ id, role, text })
  scrollToBottom()
  return id
}

function appendAssistant(payload) {
  const id = crypto.randomUUID()
  messages.value.push({ id, role: 'assistant', payload })
  scrollToBottom()
  return id
}

function replaceMessage(id, message) {
  const index = messages.value.findIndex((item) => item.id === id)
  if (index >= 0) messages.value[index] = message
  scrollToBottom()
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

function formatAnswer(text = '') {
  return String(text)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replace(/^### (.*)$/gm, '<strong>$1</strong>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br />')
}

onMounted(async () => {
  try {
    await Promise.all([loadAgents(), loadIndexStatus()])
  } catch (error) {
    appendText('assistant', `初始化失败：${error.message}`)
  }
})
</script>
