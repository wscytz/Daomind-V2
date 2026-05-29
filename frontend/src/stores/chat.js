import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { sendMessage, sendRagMessage, streamChat } from '../api'

const CONV_KEY = 'daomind-conversations'
const ACTIVE_KEY = 'daomind-active-id'
const PREFS_KEY = 'daomind-prefs'

function genId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
}

function loadConversations() {
  try {
    const raw = localStorage.getItem(CONV_KEY)
    return raw ? JSON.parse(raw) : []
  } catch (e) {
    console.warn('对话加载失败:', e)
    return []
  }
}

function saveConversations(convs) {
  try {
    localStorage.setItem(CONV_KEY, JSON.stringify(convs))
  } catch (e) {
    console.warn('对话保存失败:', e)
  }
}

function loadPrefs() {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch { return {} }
}

function savePrefs(prefs) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
  } catch { /* ignore */ }
}

export const useChatStore = defineStore('chat', () => {
  // 对话列表
  const conversations = ref(loadConversations())
  const activeId = ref(localStorage.getItem(ACTIVE_KEY) || null)

  // 当前偏好
  const prefs = loadPrefs()
  const persona = ref(prefs.persona || 'standard')
  const depth = ref(prefs.depth || 'standard')
  const model = ref(prefs.model || 'glm-4-flash')
  const ragMode = ref(false)
  const classic = ref('daodejing')

  // UI 状态
  const isLoading = ref(false)
  const error = ref(null)
  const streamingText = ref('')

  // 当前对话消息
  const activeConv = computed(() =>
    conversations.value.find(c => c.id === activeId.value) || null
  )
  const messages = computed(() =>
    activeConv.value ? activeConv.value.messages : []
  )

  const history = computed(() =>
    messages.value
      .filter(m => m.role !== 'system')
      .slice(-10)
      .map(m => ({ role: m.role, content: m.content }))
  )

  let abortStream = null

  function _persist() {
    saveConversations(conversations.value)
    if (activeId.value) localStorage.setItem(ACTIVE_KEY, activeId.value)
  }

  function _updateConv(id, patch) {
    const idx = conversations.value.findIndex(c => c.id === id)
    if (idx >= 0) {
      Object.assign(conversations.value[idx], patch, { updatedAt: Date.now() })
      _persist()
    }
  }

  function _autoTitle(msg) {
    const t = msg.trim().slice(0, 24)
    return t.length < msg.trim().length ? t + '...' : t
  }

  // ── 对话管理 ──
  function newConversation() {
    const conv = {
      id: genId(),
      title: '新对话',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }
    conversations.value.unshift(conv)
    activeId.value = conv.id
    _persist()
    return conv.id
  }

  function switchConversation(id) {
    if (isLoading.value) return
    activeId.value = id
    error.value = null
    streamingText.value = ''
    localStorage.setItem(ACTIVE_KEY, id)
  }

  function deleteConversation(id) {
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (activeId.value === id) {
      activeId.value = conversations.value.length > 0 ? conversations.value[0].id : null
    }
    _persist()
  }

  function renameConversation(id, title) {
    _updateConv(id, { title })
  }

  function clearChat() {
    if (activeId.value) {
      _updateConv(activeId.value, { messages: [] })
    }
    error.value = null
  }

  function searchConversations(query) {
    const q = query.toLowerCase()
    return conversations.value.filter(c =>
      c.title.toLowerCase().includes(q) ||
      c.messages.some(m => m.content.toLowerCase().includes(q))
    )
  }

  // ── 发送消息 ──
  async function send(text) {
    if (!text.trim() || isLoading.value) return
    error.value = null
    streamingText.value = ''

    // 自动创建对话
    if (!activeId.value || !conversations.value.find(c => c.id === activeId.value)) {
      newConversation()
    }

    const userMsg = { role: 'user', content: text, time: Date.now() }
    _updateConv(activeId.value, {
      messages: [...(activeConv.value?.messages || []), userMsg],
      title: activeConv.value?.messages?.length === 0 ? _autoTitle(text) : activeConv.value?.title,
    })

    isLoading.value = true

    let fullText = ''
    let thinkingText = ''
    let meta = {}

    abortStream = streamChat({
      message: text, model: model.value, persona: persona.value,
      depth: depth.value, ragMode: ragMode.value, classic: classic.value,
      history: history.value.slice(0, -1),
      onToken: (token) => {
        fullText += token
        streamingText.value = fullText
      },
      onThinking: (t) => { thinkingText += t },
      onMeta: (m) => { meta = m },
      onUsage: (u) => { meta.usage = u },
      onDone: () => {
        _pushAssistant(fullText || '（无回复）', thinkingText, meta)
        streamingText.value = ''
        isLoading.value = false
        abortStream = null
      },
      onError: () => {
        _fallbackSend(text)
      },
    })
  }

  function _pushAssistant(content, thinking, meta) {
    const msg = {
      role: 'assistant',
      content,
      thinking: thinking || null,
      sources: meta.sources || [],
      principle: meta.principle || null,
      inferenceTime: meta.inference_time_ms,
      usage: meta.usage || null,
      time: Date.now(),
    }
    if (activeId.value && activeConv.value) {
      _updateConv(activeId.value, {
        messages: [...activeConv.value.messages, msg],
      })
    }
  }

  async function _fallbackSend(text) {
    try {
      let data
      if (ragMode.value) {
        data = await sendRagMessage({
          message: text, classic: classic.value, persona: persona.value,
          depth: depth.value, model: model.value, history: history.value.slice(0, -1),
        })
      } else {
        data = await sendMessage({
          message: text, model: model.value, persona: persona.value,
          depth: depth.value, history: history.value.slice(0, -1),
        })
      }
      _pushAssistant(data.response, data.thinking, data)
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      _pushAssistant('请求失败，请稍后重试。', null, {})
    } finally {
      isLoading.value = false
      streamingText.value = ''
    }
  }

  // ── 重试最后一条 ──
  function retryLast() {
    if (!activeConv.value || isLoading.value) return
    const msgs = activeConv.value.messages
    const lastUser = [...msgs].reverse().find(m => m.role === 'user')
    if (!lastUser) return
    // 移除最后的 assistant 消息
    const updated = msgs.slice(0, -1)
    _updateConv(activeId.value, { messages: updated })
    send(lastUser.content)
  }

  function stopStream() {
    if (abortStream) {
      abortStream()
      abortStream = null
    }
    if (streamingText.value) {
      _pushAssistant(streamingText.value, null, {})
      streamingText.value = ''
    }
    isLoading.value = false
  }

  // ── 导出 Markdown ──
  function exportMarkdown() {
    if (!activeConv.value || !messages.value.length) return null
    const conv = activeConv.value
    const title = conv.title
    const date = new Date(conv.updatedAt).toLocaleString('zh-CN')
    let md = `# ${title}\n\n> 导出时间：${date}\n\n---\n\n`
    for (const msg of messages.value) {
      const time = msg.time ? new Date(msg.time).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : ''
      if (msg.role === 'user') {
        md += `**我** (${time})：\n\n${msg.content}\n\n`
      } else {
        md += `**道心** (${time})：\n\n${msg.content}\n\n`
        if (msg.sources?.length) {
          md += `> 引用：${msg.sources.join('、')}\n\n`
        }
      }
    }
    return md
  }

  // ── 偏好持久化 ──
  function setPersona(v) { persona.value = v; savePrefs({ ...loadPrefs(), persona: v }) }
  function setDepth(v) { depth.value = v; savePrefs({ ...loadPrefs(), depth: v }) }
  function setModel(v) { model.value = v; savePrefs({ ...loadPrefs(), model: v }) }

  // 初始化：如果没有活跃对话，不自动创建（等用户发消息时创建）
  // 但如果已有活跃ID但对话列表为空，清除
  if (activeId.value && !conversations.value.find(c => c.id === activeId.value)) {
    activeId.value = conversations.value.length > 0 ? conversations.value[0].id : null
  }

  return {
    messages, conversations, activeId, persona, depth, model,
    ragMode, classic, isLoading, error, history, streamingText,
    send, clearChat, stopStream, retryLast, exportMarkdown,
    newConversation, switchConversation, deleteConversation,
    renameConversation, searchConversations,
    setPersona, setDepth, setModel,
  }
})
