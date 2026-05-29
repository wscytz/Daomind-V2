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
        <div class="conv-list" role="listbox" aria-label="对话列表">
          <div v-for="c in store.conversations" :key="c.id"
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
          <div v-if="store.conversations.length === 0" class="conv-empty">暂无对话</div>
        </div>
      </div>

      <div class="sidebar-body">
        <!-- 页面切换 -->
        <div class="section">
          <div class="page-tabs">
            <button :class="['page-tab', { active: currentPage === 'chat' }]" @click="currentPage = 'chat'">对话</button>
            <button :class="['page-tab', { active: currentPage === 'wisdom' }]" @click="currentPage = 'wisdom'">智慧</button>
          </div>
        </div>

        <!-- 人格（= 模式，决定 RAG 路由） -->
        <div class="section">
          <div class="section-label">模式</div>
          <div class="persona-grid">
            <button v-for="p in personas" :key="p.value"
              :class="['persona-btn', { active: store.persona === p.value }]"
              @click="store.setPersona(p.value); showSidebar = false"
              :aria-pressed="store.persona === p.value">
              <span class="persona-icon" aria-hidden="true">{{ p.icon }}</span>
              <div class="persona-text">
                <span class="persona-name">{{ p.label }}</span>
                <span class="persona-hint">{{ p.hint }}</span>
              </div>
            </button>
          </div>
        </div>

        <!-- 深度 -->
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

        <!-- 模型（按 provider 分组） -->
        <div class="section">
          <div class="section-label">模型</div>
          <select :value="store.model" @change="store.setModel($event.target.value)"
            class="model-select" aria-label="选择模型">
            <optgroup v-for="group in modelGroups" :key="group.provider" :label="group.provider">
              <option v-for="m in group.models" :key="m.id" :value="m.id">
                {{ m.label }}{{ m.tag ? ` (${m.tag})` : '' }}
              </option>
            </optgroup>
          </select>
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
          <span class="topbar-title">{{ currentPage === 'chat' ? currentPersonaLabel : '每日智慧' }}</span>
        </div>
        <div class="topbar-right">
          <span v-if="activePersonaRag" class="mode-chip rag">{{ activePersonaRag }}</span>
          <span class="mode-chip persona">{{ depthLabel }}</span>
          <button class="theme-btn" @click="toggleTheme"
            :title="isDark ? '切换亮色' : '切换暗色'"
            :aria-label="isDark ? '切换亮色模式' : '切换暗色模式'">{{ isDark ? '☀' : '☾' }}</button>
          <button class="settings-btn" @click="openSettings" title="设置" aria-label="打开设置">&#9881;</button>
        </div>
      </div>
      <ChatWindow v-if="currentPage === 'chat'" />
      <WisdomPage v-else-if="currentPage === 'wisdom'" @navigate="currentPage = $event" />
    </main>

    <!-- Settings Modal -->
    <div v-if="showSettings" class="modal-overlay" @click.self="showSettings = false"
      role="dialog" aria-modal="true" aria-label="设置">
      <div class="modal modal-wide">
        <div class="modal-header">
          <span class="modal-title">设置</span>
          <button class="modal-close" @click="showSettings = false" aria-label="关闭">&times;</button>
        </div>
        <div class="modal-body">
          <div v-if="saveMsg" :class="['save-toast', saveOk ? 'ok' : 'err']" role="status">{{ saveMsg }}</div>

          <!-- Provider 列表 -->
          <div v-for="(p, pi) in providerForms" :key="pi" class="provider-section">
            <div class="provider-section-header">
              <input class="provider-name-input" v-model="p.name" placeholder="服务商名称" />
              <button class="provider-del-btn" @click="providerForms.splice(pi, 1)" title="删除服务商">&times;</button>
            </div>
            <div class="setting-row">
              <label class="setting-label">接口地址</label>
              <input class="setting-input" v-model="p.base_url" placeholder="https://..." />
            </div>
            <div class="setting-row">
              <label class="setting-label">API Key</label>
              <div class="key-row">
                <input :type="p.showKey ? 'text' : 'password'" class="setting-input"
                  v-model="p.api_key" placeholder="sk-..." />
                <button class="key-toggle" @click="p.showKey = !p.showKey" tabindex="-1">
                  {{ p.showKey ? '隐' : '显' }}
                </button>
              </div>
            </div>
            <!-- 模型列表 -->
            <div class="setting-row">
              <label class="setting-label">模型</label>
              <div class="model-list">
                <div v-for="(m, mi) in p.models" :key="mi" class="model-entry">
                  <input class="model-id-input" v-model="m.id" placeholder="model-id" />
                  <input class="model-label-input" v-model="m.label" placeholder="显示名" />
                  <input class="model-tag-input" v-model="m.tag" placeholder="标签" />
                  <button class="model-del-btn" @click="p.models.splice(mi, 1)">&times;</button>
                </div>
                <button class="model-add-btn" @click="p.models.push({ id: '', label: '', tag: '', api_model: '' })">+ 添加模型</button>
              </div>
            </div>
          </div>

          <button class="provider-add-btn" @click="addProvider">+ 添加服务商</button>

          <!-- Embedding -->
          <div class="provider-section">
            <div class="provider-section-title">Embedding（RAG 检索）</div>
            <div class="setting-row">
              <label class="setting-label">接口地址</label>
              <input class="setting-input" v-model="embeddingForm.base_url" placeholder="https://..." />
            </div>
            <div class="setting-row">
              <label class="setting-label">API Key</label>
              <div class="key-row">
                <input :type="embeddingForm.showKey ? 'text' : 'password'" class="setting-input"
                  v-model="embeddingForm.api_key" placeholder="sk-..." />
                <button class="key-toggle" @click="embeddingForm.showKey = !embeddingForm.showKey" tabindex="-1">
                  {{ embeddingForm.showKey ? '隐' : '显' }}
                </button>
              </div>
            </div>
            <div class="setting-row">
              <label class="setting-label">模型名</label>
              <input class="setting-input" v-model="embeddingForm.model" placeholder="embedding-3" />
            </div>
          </div>

          <!-- 状态 -->
          <div class="status-bar" role="status">
            <span :class="['status-dot', healthOk ? 'ok' : 'err']" aria-hidden="true"></span>
            <span class="status-text">{{ healthOk ? '服务正常' : '未连接' }}</span>
            <span v-if="ragCount" class="status-text dim">| RAG {{ ragCount }} 库</span>
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
import WisdomPage from './components/WisdomPage.vue'

const store = useChatStore()
const showSidebar = ref(false)
const showSettings = ref(false)
const currentPage = ref('chat')  // 'chat' | 'wisdom'
const isDark = ref(document.documentElement.getAttribute('data-theme') === 'dark')
const healthOk = ref(false)
const ragCount = ref(0)
const saving = ref(false)
const saveMsg = ref('')
const saveOk = ref(true)

const renamingId = ref(null)
const renameValue = ref('')
const renameInput = ref(null)

// Provider 表单（动态）
const providerForms = ref([])
const embeddingForm = ref({ base_url: '', api_key: '', model: 'embedding-3', showKey: false })

// 人格定义（= 模式，含 RAG 说明）
const personas = [
  { value: 'standard', label: '心理咨询', icon: '☯', hint: '纯对话' },
  { value: 'baijuyi', label: '诗疗', icon: '诗', hint: '白居易诗集' },
  { value: 'daoist', label: '道疗', icon: '道', hint: '道德经·庄子·道家疗法' },
]

const depths = [
  { value: 'brief', label: '简短' },
  { value: 'standard', label: '标准' },
  { value: 'deep', label: '深入' },
]

// 当前人格对应的 RAG 提示
const activePersonaRag = computed(() => {
  const p = personas.find(p => p.value === store.persona)
  return p && p.hint !== '纯对话' ? p.hint : ''
})

// 模型按 provider 分组
const modelGroups = computed(() => {
  const groups = {}
  for (const p of providerForms.value) {
    if (!p.models.length) continue
    const models = p.models
      .filter(m => m.id)
      .map(m => ({ id: m.id, label: m.label || m.id, tag: m.tag || '' }))
    if (models.length) {
      groups[p.name] = { provider: p.name || '自定义', models }
    }
  }
  return Object.values(groups)
})

const currentPersonaLabel = computed(() => {
  const p = personas.find(p => p.value === store.persona)
  return p ? p.label : '对话'
})

const depthLabel = computed(() => {
  const d = depths.find(d => d.value === store.depth)
  return d ? d.label : ''
})

// ── Settings ──

async function loadSettings() {
  try {
    const s = await getSettings()
    // 从后端 provider 列表构建表单
    providerForms.value = (s.providers || []).map(p => ({
      name: p.name || '自定义',
      base_url: p.base_url || '',
      api_key: p.api_key || '',
      showKey: false,
      models: Object.entries(p.models || {}).map(([id, info]) => ({
        id,
        api_model: typeof info === 'string' ? info : (info.api_model || id),
        label: typeof info === 'string' ? id : (info.label || id),
        tag: typeof info === 'string' ? '' : (info.tag || ''),
      })),
    }))
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
    // models 现在是 { id: {provider, label, tag, ...} } 格式
    if (h.models && typeof h.models === 'object') {
      const modelObjs = h.models
      // 如果没有 providerForms（首次加载），从 health 构建模型分组
      if (!providerForms.value.length) {
        const byProvider = {}
        for (const [id, info] of Object.entries(modelObjs)) {
          const pname = info.provider || '自定义'
          if (!byProvider[pname]) byProvider[pname] = { name: pname, base_url: '', api_key: '', showKey: false, models: [] }
          byProvider[pname].models.push({ id, api_model: info.api_model || id, label: info.label || id, tag: info.tag || '' })
        }
        providerForms.value = Object.values(byProvider)
      }
    }
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

function addProvider() {
  providerForms.value.push({
    name: '', base_url: '', api_key: '', showKey: false,
    models: [{ id: '', api_model: '', label: '', tag: '' }],
  })
}

async function handleSave() {
  saving.value = true
  saveMsg.value = ''
  try {
    const providers = providerForms.value.map(p => {
      const models = {}
      for (const m of p.models) {
        if (m.id) {
          models[m.id] = {
            api_model: m.api_model || m.id,
            label: m.label || m.id,
            tag: m.tag || '',
          }
        }
      }
      return { name: p.name || '自定义', base_url: p.base_url, api_key: p.api_key, models }
    }).filter(p => p.base_url)

    const embedding = {
      base_url: embeddingForm.value.base_url,
      api_key: embeddingForm.value.api_key,
      model: embeddingForm.value.model,
    }

    const result = await saveSettings({ providers, embedding })
    saveOk.value = true

    const modelCount = result.models ? Object.keys(result.models).length : 0
    saveMsg.value = `已保存 | ${providers.length} 服务商 | ${modelCount} 模型 | RAG ${result.rag_loaded || 0} 库`
    healthOk.value = true
    ragCount.value = result.rag_loaded || 0
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
</script>
