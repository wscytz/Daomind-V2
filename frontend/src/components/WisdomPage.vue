<template>
  <div class="wisdom-page">
    <div v-if="loading" class="wisdom-loading">
      <div class="loading-dots"><span></span><span></span><span></span></div>
    </div>

    <template v-else-if="data">
      <!-- 节气 -->
      <div class="term-card">
        <div class="term-header">
          <span class="term-name">{{ data.term.name }}</span>
          <span class="term-date">{{ data.term.date }}</span>
        </div>
        <div class="term-keyword">{{ data.term.keyword }}</div>
        <div class="term-desc">{{ data.term.description }}</div>
      </div>

      <!-- 智慧卡 -->
      <div v-if="data.passage" class="wisdom-card">
        <div class="wisdom-label">每日一签</div>
        <div class="wisdom-source">{{ data.passage.source_name }}<span v-if="data.passage.chapter"> · {{ data.passage.chapter }}</span></div>
        <div class="wisdom-original">{{ data.passage.original }}</div>
        <div v-if="data.passage.translation" class="wisdom-translation">{{ data.passage.translation }}</div>
        <button class="wisdom-discuss-btn" @click="discuss">
          就此讨论
        </button>
      </div>

      <div v-else class="wisdom-empty">暂无推荐</div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getWisdom } from '../api'
import { useChatStore } from '../stores/chat'

const emit = defineEmits(['navigate'])

const store = useChatStore()
const data = ref(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    data.value = await getWisdom()
  } catch (e) {
    console.warn('智慧卡加载失败:', e)
  } finally {
    loading.value = false
  }
}

function discuss() {
  if (!data.value?.passage) return
  const p = data.value.passage
  const text = p.original || p.content || ''
  const source = `${p.source_name}${p.chapter ? ' · ' + p.chapter : ''}`
  store.newConversation()
  store.send(`请解读这段经典：\n\n「${text}」\n\n—— ${source}`)
  emit('navigate', 'chat')
}

onMounted(load)
</script>
