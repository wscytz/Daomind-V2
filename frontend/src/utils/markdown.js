import { marked } from 'marked'
import DOMPurify from 'dompurify'

/**
 * 渲染 Markdown，返回安全的 HTML
 * DOMPurify 防止 XSS，marked 做 Markdown 解析
 */
export function renderMd(text) {
  if (!text) return ''
  return DOMPurify.sanitize(marked(text))
}
