import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export async function sendMessage({ message, model = 'glm-4-flash', persona = 'standard', depth = 'standard', history = [] }) {
  const { data } = await api.post('/chat', { message, model, persona, depth, history })
  return data
}

export async function sendRagMessage({ message, persona = 'daoist', depth = 'standard', model = 'glm-4-flash', history = [] }) {
  const { data } = await api.post('/rag/counseling', { message, persona, depth, model, history })
  return data
}

export async function checkHealth() {
  const { data } = await api.get('/health')
  return data
}

export async function getSettings() {
  const { data } = await api.get('/settings')
  return data
}

export async function saveSettings({ providers, embedding }) {
  const { data } = await api.post('/settings', { providers, embedding })
  return data
}

/**
 * SSE 流式对话
 */
export function streamChat({
  message, model = 'glm-4-flash', persona = 'standard', depth = 'standard',
  history = [],
  onToken, onThinking, onMeta, onUsage, onDone, onError,
}) {
  const body = { message, model, persona, depth, history }

  const controller = new AbortController()

  fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (resp) => {
      if (!resp.ok) {
        onError && onError(`HTTP ${resp.status}`)
        return
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6)
          if (data === '[DONE]') {
            onDone && onDone()
            return
          }
          try {
            const parsed = JSON.parse(data)
            if (parsed.type === 'content') onToken && onToken(parsed.content)
            else if (parsed.type === 'thinking') onThinking && onThinking(parsed.content)
            else if (parsed.type === 'meta') onMeta && onMeta(parsed)
            else if (parsed.type === 'usage') onUsage && onUsage(parsed.content)
          } catch (e) {
            console.warn('SSE 数据解析失败:', e, data)
          }
        }
      }
      onDone && onDone()
    })
    .catch((e) => {
      if (e.name !== 'AbortError') onError && onError(e.message)
    })

  return () => controller.abort()
}
