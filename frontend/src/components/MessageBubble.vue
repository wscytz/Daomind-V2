<template>
  <div class="msg-assistant-inner">
    <div class="msg-avatar">
      <span class="msg-avatar-dot" aria-hidden="true"></span>
      {{ avatarLabel }}
    </div>

    <div class="md-content" v-html="renderedContent"></div>

    <div v-if="message.thinking" class="think-block">
      <span class="think-toggle" @click="showThink = !showThink">
        {{ showThink ? '收起思路' : '展开思路' }}
      </span>
      <div v-if="showThink" class="think-content">{{ message.thinking }}</div>
    </div>

    <!-- RAG 引用面板 -->
    <div v-if="message.ragDetails && message.ragDetails.length" class="citation-block">
      <span class="citation-toggle" @click="showCitations = !showCitations">
        {{ showCitations ? '收起出处' : `经典出处 (${message.ragDetails.length})` }}
      </span>
      <div v-if="showCitations" class="citation-list">
        <div v-for="(c, i) in message.ragDetails" :key="i" class="citation-item">
          <div class="citation-header">
            <span class="citation-source">{{ c.source_name }}</span>
            <span v-if="c.chapter" class="citation-chapter">{{ c.chapter }}</span>
            <span v-if="c.title" class="citation-chapter">《{{ c.title }}》</span>
            <span class="citation-sim" :title="`相关度 ${((c.similarity || 0) * 100).toFixed(0)}%`">
              <span class="sim-bar"><span class="sim-fill" :style="{ width: Math.max((c.similarity || 0) * 100, 10) + '%' }"></span></span>
            </span>
          </div>
          <div v-if="c.original" class="citation-original">{{ c.original }}</div>
          <div v-if="c.translation" class="citation-translation">{{ c.translation }}</div>
        </div>
      </div>
    </div>

    <!-- 旧格式兼容 -->
    <div v-else-if="message.sources && message.sources.length" class="sources-row">
      <span v-for="s in message.sources" :key="s" class="source-chip">{{ sourceName(s) }}</span>
    </div>

    <div v-if="message.safetyWarning || message.safety_warning" class="safety-box">
      {{ getSafetyMessage() }}
    </div>

    <div class="msg-footer">
      <span v-if="tokenLabel" class="msg-tokens" :title="tokenTitle">{{ tokenLabel }}</span>
      <span v-if="message.inferenceTime" class="msg-duration">{{ message.inferenceTime }}ms</span>
      <span class="msg-time">{{ fmtTime(message.time) }}</span>
      <button v-if="message.content" class="copy-btn" @click="copy">
        {{ copied ? '&#10003;' : '复制' }}
      </button>
      <button v-if="isLast" class="copy-btn" @click="$emit('retry')" title="重新生成">重试</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { renderMd } from '../utils/markdown'

const props = defineProps({
  message: Object,
  isLast: { type: Boolean, default: false },
})
defineEmits(['retry'])

const showThink = ref(false)
const showCitations = ref(false)
const copied = ref(false)

const avatarLabel = computed(() => {
  if (props.message.ragDetails?.length || props.message.sources?.length) return '经典释读'
  return '道心'
})

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  return DOMPurify.sanitize(marked(props.message.content))
})

const tokenLabel = computed(() => {
  const u = props.message.usage
  if (!u) return ''
  return u.total_tokens ? `${u.total_tokens}t` : ''
})

const tokenTitle = computed(() => {
  const u = props.message.usage
  if (!u) return ''
  const parts = []
  if (u.prompt_tokens) parts.push(`输入: ${u.prompt_tokens}`)
  if (u.completion_tokens) parts.push(`输出: ${u.completion_tokens}`)
  if (u.total_tokens) parts.push(`合计: ${u.total_tokens}`)
  return parts.join(' | ') || ''
})

function sourceName(s) {
  const m = { daodejing: '道德经', lunyu: '论语', zhuangzi: '庄子',
              poem: '白居易', poem_outer: '白居易', daoist_therapy: '道家疗法' }
  return m[s] || s
}

function fmtTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function getSafetyMessage() {
  return '您的感受很重要，如果您有困扰，建议寻求专业心理帮助。'
}

async function copy() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    copied.value = true
    setTimeout(() => copied.value = false, 1200)
  } catch (e) {
    console.warn('复制失败:', e)
  }
}
</script>
