import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export async function sendMessage({ message, model = 'glm-4-flash', persona = 'standard', depth = 'standard', history = [] }) {
  const { data } = await api.post('/chat', { message, model, persona, depth, history })
  return data
}

export async function sendRagMessage({ message, classic = 'daodejing', persona = 'daoist', depth = 'standard', model = 'glm-4-flash', history = [] }) {
  const { data } = await api.post('/rag/counseling', { message, classic, persona, depth, model, history })
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
 * @param {Object} params
 * @param {function} onToken - 收到内容 token 时调用 (text: string)
 * @param {function} onThinking - 收到思考内容时调用 (text: string)
 * @param {function} onMeta - 收到元数据时调用 (meta: object)
 * @param {function} onUsage - 收到 token 用量时调用 (usage: object)
 * @param {function} onDone - 流结束时调用 ()
 * @param {function} onError - 出错时调用 (error: string)
 */
export function streamChat({
  message, model = 'glm-4-flash', persona = 'standard', depth = 'standard',
  ragMode = false, classic = 'daodejing', history = [],
  onToken, onThinking, onMeta, onUsage, onDone, onError,
}) {
  const body = { message, model, persona, depth, history, rag_mode: ragMode, classic }

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
