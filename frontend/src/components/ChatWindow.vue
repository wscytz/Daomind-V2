<template>
  <!-- AI Disclaimer Modal -->
  <div v-if="showDisclaimer" class="disclaimer-overlay" role="dialog" aria-modal="true" aria-label="AI身份声明">
    <div class="disclaimer-card">
      <div class="disclaimer-title">温馨提示</div>
      <div class="disclaimer-body">
        <p>道心是人工智能辅助工具，不是医疗机构，不能替代专业心理咨询或医疗诊断。</p>
        <p>如果您正在经历严重的心理困扰，请联系专业机构：</p>
        <ul class="disclaimer-hotlines">
          <li>全国24小时心理援助热线：400-161-9995</li>
          <li>北京心理危机研究与干预中心：010-82951332</li>
        </ul>
      </div>
      <button class="disclaimer-btn" @click="acceptDisclaimer">我已了解，继续使用</button>
    </div>
  </div>

  <div class="messages-wrap" role="log" aria-label="对话内容" aria-live="polite">
    <div class="messages" ref="msgContainer">
      <div v-if="store.messages.length === 0 && !store.isLoading" class="empty-state">
        <template v-if="!healthOk">
          <div class="welcome-card">
            <div class="welcome-icon" aria-hidden="true">道</div>
            <div class="welcome-title">欢迎使用道心</div>
            <div class="welcome-desc">请先点击右上角齿轮图标，配置您的 AI 服务商接口</div>
            <button class="welcome-btn" @click="emit('openSettings')">打开设置</button>
          </div>
        </template>
        <template v-else>
          <div class="empty-glyph" aria-hidden="true">道</div>
          <div class="empty-title">道法自然，心安即归处</div>
          <div class="empty-sub">以古人之智，解今人之忧</div>
        </template>
      </div>

      <template v-for="(msg, i) in store.messages" :key="i">
        <!-- User -->
        <div v-if="msg.role === 'user'" class="msg-user">
          <div class="msg-user-inner">{{ msg.content }}</div>
        </div>
        <!-- Assistant -->
        <div v-else class="msg-assistant">
          <MessageBubble
            :message="msg"
            :isLast="i === store.messages.length - 1 && msg.role === 'assistant'"
            @retry="store.retryLast()"
          />
        </div>
      </template>

      <!-- Streaming -->
      <div v-if="store.streamingText" class="msg-assistant">
        <div class="msg-assistant-inner">
          <div class="msg-avatar"><span class="msg-avatar-dot" aria-hidden="true"></span> 道心</div>
          <div class="md-content" v-html="renderMd(store.streamingText)"></div>
          <span class="streaming-cursor" aria-hidden="true"></span>
        </div>
      </div>

      <!-- Loading -->
      <div v-else-if="store.isLoading && !store.streamingText" class="loading-row" role="status" aria-label="正在生成回复">
        <div class="loading-card">
          <div class="loading-dots" aria-hidden="true"><span></span><span></span><span></span></div>
          <span class="loading-text">正在思考</span>
        </div>
      </div>

      <!-- Error -->
      <div v-if="store.error" class="error-banner" role="alert" @click="store.error = null">
        {{ store.error }}
      </div>
    </div>
  </div>

  <div class="input-area">
    <div class="input-container">
      <div class="input-wrap">
        <input class="input-field" v-model="inputText"
          @keydown.enter.exact="handleSend"
          placeholder="说点什么..."
          :disabled="store.isLoading && !store.streamingText"
          aria-label="输入消息"
          autocomplete="off" />
      </div>
      <button v-if="store.streamingText" class="send-btn stop" @click="store.stopStream()"
        title="停止生成" aria-label="停止生成">&#9632;</button>
      <button v-else class="send-btn" @click="handleSend"
        :disabled="store.isLoading || !inputText.trim()"
        title="发送" aria-label="发送消息">&#8593;</button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted } from 'vue'
import { useChatStore } from '../stores/chat'
import MessageBubble from './MessageBubble.vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  healthOk: { type: Boolean, default: true },
})
const emit = defineEmits(['open-settings'])
const store = useChatStore()
const inputText = ref('')
const msgContainer = ref(null)
const showDisclaimer = ref(false)

onMounted(() => {
  if (!localStorage.getItem('daomind-disclaimer-accepted')) {
    showDisclaimer.value = true
  }
})

function acceptDisclaimer() {
  localStorage.setItem('daomind-disclaimer-accepted', '1')
  showDisclaimer.value = false
}

function renderMd(text) { return DOMPurify.sanitize(marked(text)) }

function handleSend() {
  const text = inputText.value.trim()
  if (!text || store.isLoading) return
  inputText.value = ''
  store.send(text)
}

watch(() => [store.messages.length, store.streamingText], async () => {
  await nextTick()
  if (msgContainer.value) msgContainer.value.scrollTop = msgContainer.value.scrollHeight
})
</script>

<style scoped>
.disclaimer-overlay {
  position: fixed;
  inset: 0;
  z-index: 600;
  background: rgba(0,0,0,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.2s var(--ease);
}

.disclaimer-card {
  width: 400px;
  max-width: 90vw;
  background: var(--snow);
  border-radius: 12px;
  padding: 32px 28px 24px;
  text-align: center;
  box-shadow: 0 24px 64px rgba(0,0,0,0.08);
  animation: modalIn 0.25s var(--spring);
}

.disclaimer-title {
  font-family: var(--font-serif);
  font-size: 17px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: 3px;
  margin-bottom: 20px;
}

.disclaimer-body {
  font-family: var(--font-serif);
  font-size: 13.5px;
  color: var(--stone);
  line-height: 1.9;
  text-align: left;
}

.disclaimer-body p {
  margin: 0 0 10px 0;
}

.disclaimer-hotlines {
  list-style: none;
  margin: 6px 0 0;
  padding: 0;
}

.disclaimer-hotlines li {
  padding: 3px 0;
  font-size: 13px;
  color: var(--gold-dim);
  letter-spacing: 0.3px;
}

.disclaimer-hotlines li::before {
  content: '\2022';
  margin-right: 8px;
  color: var(--gold-dim);
}

.disclaimer-btn {
  margin-top: 24px;
  padding: 10px 32px;
  border: none;
  border-radius: 20px;
  background: var(--ink);
  color: var(--snow);
  font-family: var(--font-serif);
  font-size: 13px;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.15s var(--ease);
}

.disclaimer-btn:hover {
  background: var(--gold-dim);
}
</style>
