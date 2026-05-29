<template>
  <div class="messages-wrap" role="log" aria-label="对话内容" aria-live="polite">
    <div class="messages" ref="msgContainer">
      <div v-if="store.messages.length === 0 && !store.isLoading" class="empty-state">
        <div class="empty-glyph" aria-hidden="true">道</div>
        <div class="empty-title">道法自然，心安即归处</div>
        <div class="empty-sub">以古人之智，解今人之忧</div>
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
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import MessageBubble from './MessageBubble.vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const store = useChatStore()
const inputText = ref('')
const msgContainer = ref(null)

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
