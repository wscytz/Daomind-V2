<template>
  <div class="app">
    <div :class="['overlay', { show: showSidebar }]" @click="showSidebar = false"></div>

    <aside :class="['sidebar', { open: showSidebar }]" role="complementary" aria-label="侧边栏">
      <div class="sidebar-header">
        <div class="brand">
          <span class="brand-zh">道心</span>
          <span class="brand-en">DAO-MIND</span>
        </div>
        <p class="brand-desc">以古人之智，解今人之忧</p>
      </div>

      <!-- 对话列表 -->
      <div class="conv-section">
        <div class="conv-header">
          <span class="section-label">对话</span>
          <button class="conv-new-btn" @click="store.newConversation(); showSidebar = false"
            title="新建对话" aria-label="新建对话">+</button>
        </div>
        <div v-if="searchQuery" class="conv-search-info">
          搜索: "{{ searchQuery }}" ({{ filteredConvs.length }} 项)
        </div>
        <div class="conv-list" role="listbox" aria-label="对话列表">
          <div v-for="c in filteredConvs" :key="c.id"
            :class="['conv-item', { active: c.id === store.activeId }]"
            role="option" :aria-selected="c.id === store.activeId"
            @click="store.switchConversation(c.id); showSidebar = false">
            <span class="conv-title" @dblclick="startRename(c.id, c.title)">
              {{ renamingId === c.id ? '' : c.title }}
            </span>
            <input v-if="renamingId === c.id"
              class="conv-rename-input"
              v-model="renameValue"
              @keydown.enter="confirmRename"
              @keydown.escape="renamingId = null"
              @blur="confirmRename"
              ref="renameInput"
              aria-label="重命名对话" />
            <button class="conv-del-btn" @click.stop="store.deleteConversation(c.id)"
              title="删除对话" aria-label="删除对话">&times;</button>
          </div>
          <div v-if="filteredConvs.length === 0" class="conv-empty">
            {{ searchQuery ? '无匹配对话' : '暂无对话' }}
          </div>
        </div>
      </div>

      <div class="sidebar-body">
        <div class="section">
          <div class="section-label">人格</div>
          <div class="persona-grid">
            <button v-for="p in personas" :key="p.value"
              :class="['persona-btn', { active: store.persona === p.value }]"
              @click="store.setPersona(p.value); showSidebar = false"
              :aria-pressed="store.persona === p.value">
              <span class="persona-icon" aria-hidden="true">{{ p.icon }}</span>
              <span>{{ p.label }}</span>
            </button>
          </div>
        </div>

        <div class="section">
          <div class="section-label">深度</div>
          <div class="depth-row" role="radiogroup" aria-label="回复深度">
            <button v-for="d in depths" :key="d.value"
              :class="['depth-btn', { active: store.depth === d.value }]"
              @click="store.setDepth(d.value)"
              role="radio" :aria-checked="store.depth === d.value">
              {{ d.label }}
            </button>
          </div>
        </div>

        <div class="section">
          <div class="section-label">模型</div>
          <select :value="store.model" @change="store.setModel($event.target.value)"
            class="model-select" aria-label="选择模型">
            <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>

        <div class="section">
          <div class="section-label">经典检索</div>
          <div :class="['toggle-card', { active: store.ragMode }]"
            @click="store.ragMode = !store.ragMode"
            role="switch" :aria-checked="store.ragMode" tabindex="0"
            @keydown.enter="store.ragMode = !store.ragMode"
            @keydown.space.prevent="store.ragMode = !store.ragMode">
            <span class="toggle-label">{{ store.ragMode ? '已开启' : 'RAG 咨询' }}</span>
            <div class="toggle-switch" aria-hidden="true"></div>
          </div>
          <div v-if="store.ragMode" class="classic-select">
            <select v-model="store.classic" aria-label="选择经典">
              <option value="daodejing">道德经</option>
              <option value="lunyu">论语</option>
              <option value="zhuangzi">庄子</option>
              <option value="baijuyi">白居易诗集</option>
              <option value="daoist_therapy">道家认知疗法</option>
            </select>
          </div>
        </div>
      </div>

      <div class="sidebar-footer">
        <button class="btn-footer" @click="handleExport" :disabled="!store.messages.length"
          title="导出 Markdown" aria-label="导出对话">导出</button>
        <button class="btn-footer" @click="openSettings" aria-label="设置">设置</button>
        <button class="btn-footer danger" @click="store.clearChat()" :disabled="!store.messages.length"
          aria-label="清空当前对话">清空</button>
      </div>
    </aside>

    <main class="chat-area" role="main">
      <div class="topbar" role="banner">
        <div class="topbar-left">
          <button class="hamburger-btn" @click="showSidebar = !showSidebar"
            aria-label="打开侧边栏">&#9776;</button>
          <span class="topbar-title">{{ currentPersonaLabel }}</span>
        </div>
        <div class="topbar-right">
          <span v-if="store.ragMode" class="mode-chip rag">RAG</span>
          <span class="mode-chip persona">{{ depthLabel }}</span>
          <button class="theme-btn" @click="toggleTheme"
            :title="isDark ? '切换亮色' : '切换暗色'"
            :aria-label="isDark ? '切换亮色模式' : '切换暗色模式'">{{ isDark ? '☀' : '☾' }}</button>
          <button class="settings-btn" @click="openSettings" title="设置" aria-label="打开设置">&#9881;</button>
        </div>
      </div>
      <ChatWindow />
    </main>

    <!-- Settings Modal -->
    <div v-if="showSettings" class="modal-overlay" @click.self="showSettings = false"
      role="dialog" aria-modal="true" aria-label="API 配置">
      <div class="modal modal-wide">
        <div class="modal-header">
          <span class="modal-title">API 配置</span>
          <button class="modal-close" @click="showSettings = false" aria-label="关闭">&times;</button>
        </div>
        <div class="modal-body">
          <div v-if="saveMsg" :class="['save-toast', saveOk ? 'ok' : 'err']" role="status">{{ saveMsg }}</div>

          <div v-for="(p, i) in providerForms" :key="p.name" class="provider-section">
            <div class="provider-section-title">{{ p.label }}</div>
            <div class="setting-row">
              <label class="setting-label">接口地址</label>
              <input class="setting-input" v-model="p.base_url" placeholder="https://..."
                :aria-label="p.label + ' 接口地址'" />
            </div>
            <div class="setting-row">
              <label class="setting-label">API Key</label>
              <div class="key-row">
                <input :type="p.showKey ? 'text' : 'password'" class="setting-input"
                  v-model="p.api_key" placeholder="sk-..."
                  :aria-label="p.label + ' API Key'" />
                <button class="key-toggle" @click="p.showKey = !p.showKey" tabindex="-1"
                  :aria-label="p.showKey ? '隐藏密钥' : '显示密钥'">
                  {{ p.showKey ? '隐' : '显' }}
                </button>
              </div>
            </div>
          </div>

          <div class="provider-section">
            <div class="provider-section-title">Embedding（RAG 检索）</div>
            <div class="setting-row">
              <label class="setting-label">接口地址</label>
              <input class="setting-input" v-model="embeddingForm.base_url" placeholder="https://..."
                aria-label="Embedding 接口地址" />
            </div>
            <div class="setting-row">
              <label class="setting-label">API Key</label>
              <div class="key-row">
                <input :type="embeddingForm.showKey ? 'text' : 'password'" class="setting-input"
                  v-model="embeddingForm.api_key" placeholder="sk-..."
                  aria-label="Embedding API Key" />
                <button class="key-toggle" @click="embeddingForm.showKey = !embeddingForm.showKey" tabindex="-1"
                  :aria-label="embeddingForm.showKey ? '隐藏密钥' : '显示密钥'">
                  {{ embeddingForm.showKey ? '隐' : '显' }}
                </button>
              </div>
            </div>
            <div class="setting-row">
              <label class="setting-label">模型名</label>
              <input class="setting-input" v-model="embeddingForm.model" placeholder="embedding-3"
                aria-label="Embedding 模型名" />
            </div>
          </div>

          <div class="status-bar" role="status">
            <span :class="['status-dot', healthOk ? 'ok' : 'err']" aria-hidden="true"></span>
            <span class="status-text">{{ healthOk ? '服务正常' : '未连接' }}</span>
            <span v-if="ragCount" class="status-text dim">| RAG {{ ragCount }} 库</span>
            <span v-if="modelCount" class="status-text dim">| {{ modelCount }} 模型</span>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-modal" @click="showSettings = false">取消</button>
          <button class="btn-modal primary" @click="handleSave" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useChatStore } from './stores/chat'
import { checkHealth, getSettings, saveSettings } from './api'
import ChatWindow from './components/ChatWindow.vue'

const store = useChatStore()
const showSidebar = ref(false)
const showSettings = ref(false)
const isDark = ref(document.documentElement.getAttribute('data-theme') === 'dark')
const models = ref(['glm-4-flash', 'glm-4.7', 'glm-5', 'emohaa', 'seed', 'seed-lite'])
const healthOk = ref(false)
const ragCount = ref(0)
const modelCount = ref(0)
const saving = ref(false)
const saveMsg = ref('')
const saveOk = ref(true)

// 对话管理
const searchQuery = ref('')
const renamingId = ref(null)
const renameValue = ref('')
const renameInput = ref(null)

const providerForms = ref([
  { name: 'zhipu', label: '智谱 AI (GLM / Emohaa)', base_url: '', api_key: '', showKey: false },
  { name: 'doubao', label: '豆包 (Doubao Seed)', base_url: '', api_key: '', showKey: false },
])
const embeddingForm = ref({ base_url: '', api_key: '', model: 'embedding-3', showKey: false })

const filteredConvs = computed(() => {
  if (!searchQuery.value) return store.conversations
  return store.searchConversations(searchQuery.value)
})

async function loadSettings() {
  try {
    const s = await getSettings()
    for (const pf of providerForms.value) {
      const saved = s.providers.find(p => p.name === pf.name)
      if (saved) {
        pf.base_url = saved.base_url || ''
        pf.api_key = saved.api_key || ''
      }
    }
    if (s.embedding) {
      embeddingForm.value.base_url = s.embedding.base_url || ''
      embeddingForm.value.api_key = s.embedding.api_key || ''
      embeddingForm.value.model = s.embedding.model || 'embedding-3'
    }
  } catch (e) {
    console.warn('加载设置失败:', e)
  }
}

async function refreshHealth() {
  try {
    const h = await checkHealth()
    healthOk.value = h.status === 'ok'
    ragCount.value = h.rag_loaded || 0
    modelCount.value = (h.models && h.models.length) || 0
    if (h.models && h.models.length) models.value = h.models
  } catch (e) {
    console.warn('健康检查失败:', e)
    healthOk.value = false
  }
}

function openSettings() {
  saveMsg.value = ''
  loadSettings()
  showSettings.value = true
}

function toggleTheme() {
  isDark.value = !isDark.value
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  localStorage.setItem('daomind-theme', isDark.value ? 'dark' : 'light')
}

async function handleSave() {
  saving.value = true
  saveMsg.value = ''
  try {
    const providers = providerForms.value.map(p => ({
      name: p.name, base_url: p.base_url, api_key: p.api_key,
    }))
    const embedding = {
      base_url: embeddingForm.value.base_url,
      api_key: embeddingForm.value.api_key,
      model: embeddingForm.value.model,
    }
    const result = await saveSettings({ providers, embedding })
    saveOk.value = true
    saveMsg.value = `已保存 | ${result.models?.length || 0} 模型可用 | RAG ${result.rag_loaded || 0} 库`
    if (result.models && result.models.length) models.value = result.models
    healthOk.value = true
    ragCount.value = result.rag_loaded || 0
    modelCount.value = (result.models && result.models.length) || 0
  } catch (e) {
    saveOk.value = false
    saveMsg.value = e.response?.data?.detail || e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

function startRename(id, title) {
  renamingId.value = id
  renameValue.value = title
  nextTick(() => {
    if (renameInput.value) renameInput.value[0]?.focus()
  })
}

function confirmRename() {
  if (renamingId.value && renameValue.value.trim()) {
    store.renameConversation(renamingId.value, renameValue.value.trim())
  }
  renamingId.value = null
}

function handleExport() {
  const md = store.exportMarkdown()
  if (!md) return
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${store.activeConv?.title || '对话'}.md`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(refreshHealth)

const personas = [
  { value: 'standard', label: '现代心理咨询', icon: '☯' },
  { value: 'baijuyi', label: '白居易诗疗', icon: '诗' },
  { value: 'daoist', label: '道家疗愈', icon: '道' },
]

const depths = [
  { value: 'brief', label: '简短' },
  { value: 'standard', label: '标准' },
  { value: 'deep', label: '深入' },
]

const currentPersonaLabel = computed(() => {
  const p = personas.find(p => p.value === store.persona)
  return p ? p.label : '对话'
})

const depthLabel = computed(() => {
  const d = depths.find(d => d.value === store.depth)
  return d ? d.label : ''
})
</script>
