<template>
  <div class="messages-view">
    <header class="page-head">
      <div>
        <p class="eyebrow">互动消息</p>
        <h1>消息中心</h1>
        <p class="page-sub">按点赞、回复与 @ 分类查看与你账号相关的互动。</p>
      </div>
      <div class="head-actions">
        <span v-if="unreadCount > 0" class="unread-pill">未读 {{ unreadCount }}</span>
        <button type="button" class="refresh-btn" :disabled="loading" @click="load(false)">
          <span v-if="loading" class="tiny-spinner" aria-hidden="true"></span>
          <span>{{ loading ? '加载中…' : '刷新' }}</span>
        </button>
      </div>
    </header>

    <section class="panel messages-panel" aria-labelledby="messages-heading">
      <div class="messages-head">
        <div class="tabs" role="tablist" aria-label="消息分类">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="tab"
            :class="{ active: activeType === tab.key }"
            role="tab"
            :aria-selected="activeType === tab.key ? 'true' : 'false'"
            @click="switchTab(tab.key)"
          >
            {{ tab.label }}
          </button>
        </div>
        <p class="list-total" aria-live="polite">
          <template v-if="loading && !list.length">正在加载…</template>
          <template v-else>共 {{ total }} 条</template>
          <span v-if="loading && list.length" class="loading-note">正在更新</span>
        </p>
      </div>

      <div v-if="error" class="list-alert" role="alert">
        <div>
          <strong>消息加载失败</strong>
          <p>{{ error }}</p>
        </div>
        <button type="button" class="retry-btn" :disabled="loading" @click="load(false)">重试</button>
      </div>

      <div v-if="loading && !list.length" class="skeleton-list" aria-live="polite">
        <span class="sr-only">正在加载消息</span>
        <div v-for="index in 4" :key="index" class="skeleton-row">
          <span class="skeleton-avatar"></span>
          <div class="skeleton-copy">
            <span class="skeleton-line wide"></span>
            <span class="skeleton-line"></span>
            <span class="skeleton-line short"></span>
          </div>
        </div>
      </div>

      <div v-else-if="!list.length && !error" class="empty-state">
        <div class="empty-mark" aria-hidden="true">信</div>
        <h2>{{ emptyTitle }}</h2>
        <p>{{ emptyCopy }}</p>
      </div>

      <div v-else class="message-list" :class="{ refreshing: loading }" :aria-busy="loading ? 'true' : 'false'">
        <button
          v-for="message in list"
          :key="message.id"
          type="button"
          class="message-item"
          :class="{ clickable: message.postId != null, unread: message.unread }"
          :disabled="message.postId == null"
          :aria-label="message.postId != null ? `查看帖子：${message.postTitle || message.content || ''}` : undefined"
          @click="openMessage(message)"
        >
          <span class="message-avatar" aria-hidden="true">
            <span class="avatar-letter">{{ initialOf(message.name) }}</span>
            <img
              v-if="message.avatar"
              :src="imageUrl(message.avatar)"
              alt=""
              @error="hideBrokenAvatar"
            />
            <span v-if="message.unread" class="unread-dot" title="未读"></span>
          </span>

          <span class="message-body">
            <span class="message-title">
              <strong>{{ message.name || '社区用户' }}</strong>
              <span>{{ message.action || typeLabel(message.type) }}</span>
              <span class="message-kind">{{ typeLabel(message.type) }}</span>
            </span>

            <span v-if="message.content" class="message-content">{{ message.content }}</span>
            <span v-if="message.postTitle && message.postTitle !== message.content" class="message-post">
              帖子：{{ message.postTitle }}
            </span>

            <span class="message-time">{{ message.time || '' }}</span>
          </span>

          <span v-if="message.postId != null" class="message-arrow" aria-hidden="true">›</span>
        </button>
      </div>

      <footer v-if="total > 0" class="pager">
        <span class="pager-info">第 {{ page }} / {{ totalPages }} 页</span>
        <div class="pager-actions">
          <button type="button" class="pager-btn" :disabled="page <= 1 || loading" @click="goPage(page - 1)">
            上一页
          </button>
          <button
            type="button"
            class="pager-btn"
            :disabled="page >= totalPages || loading || !hasMore"
            @click="goPage(page + 1)"
          >
            下一页
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, imageUrl } from '../api'
import { session } from '../session'

const PAGE_SIZE = 10

const tabs = [
  { key: 'all', label: '全部' },
  { key: 'like', label: '点赞' },
  { key: 'reply', label: '回复' },
  { key: 'mention', label: '@我的' }
]

const route = useRoute()
const router = useRouter()

const activeType = ref('all')
const list = ref([])
const page = ref(1)
const total = ref(0)
const totalPages = ref(1)
const hasMore = ref(false)
const unreadCount = ref(0)
const loading = ref(Boolean(session.token))
const error = ref('')

const readMarked = ref(false)
let markingRead = false
let requestSeq = 0
let disposed = false

const emptyTitle = computed(() => {
  if (activeType.value === 'like') return '还没有收到点赞'
  if (activeType.value === 'reply') return '还没有收到回复'
  if (activeType.value === 'mention') return '还没有 @ 你的消息'
  return '暂时没有互动消息'
})

const emptyCopy = computed(() => {
  if (activeType.value === 'all') return '当其他用户与你的帖子互动时，消息会出现在这里。'
  return '切换其他分类，或稍后刷新查看新的互动。'
})

function typeLabel(type) {
  if (type === 'like') return '点赞'
  if (type === 'reply') return '回复'
  if (type === 'mention') return '@我的'
  return '互动'
}

function initialOf(name) {
  const source = String(name || '友').trim()
  return Array.from(source)[0] || '友'
}

function hideBrokenAvatar(event) {
  if (event && event.currentTarget) event.currentTarget.style.display = 'none'
}

function errorText(err, fallback) {
  const text = err && typeof err.message === 'string' ? err.message.trim() : ''
  if (text && !/failed to fetch|networkerror|load failed|fetch failed/i.test(text)) return text
  const status = err && (err.status || err.code)
  if (status === 401) return '登录状态已失效，请重新登录'
  if (status === 403) return '当前账号无权查看互动消息'
  if (status === 429) return '加载过于频繁，请稍后再试'
  if (status >= 500) return '服务器暂时不可用，请稍后重试'
  return fallback
}

function goLogin() {
  router.replace({ path: '/login', query: { redirect: route.fullPath } })
}

async function markRead() {
  if (readMarked.value || markingRead || !session.token) return
  markingRead = true
  try {
    const data = await api.readNotifications()
    window.dispatchEvent(new Event('bbs:notifications-read'))
    if (disposed) return
    readMarked.value = true
    unreadCount.value = data && typeof data.unreadCount === 'number' ? data.unreadCount : 0
    list.value = list.value.map((message) => (message.unread ? { ...message, unread: false } : message))
  } catch (err) {
    /* 已读状态不是关键路径，失败时保留未读标记，下次加载再试 */
  } finally {
    markingRead = false
  }
}

async function load(reset) {
  if (!session.token) {
    goLogin()
    return
  }

  if (reset) {
    page.value = 1
    list.value = []
  }

  const current = ++requestSeq
  const requestedPage = page.value
  loading.value = true
  error.value = ''

  try {
    const data = await api.notifications(activeType.value, {
      page: requestedPage,
      pageSize: PAGE_SIZE
    })

    if (disposed || current !== requestSeq) return

    const items = data && Array.isArray(data.list) ? data.list : []
    const nextTotal = data && Number.isFinite(Number(data.total)) ? Number(data.total) : items.length
    const computedPages = PAGE_SIZE > 0 ? Math.ceil(nextTotal / PAGE_SIZE) : 1
    const nextPages =
      data && Number.isFinite(Number(data.totalPages)) && Number(data.totalPages) > 0
        ? Number(data.totalPages)
        : Math.max(1, computedPages)

    // 当前页因数据减少而越界时，自动回到最后一页重新取数
    if (!items.length && nextTotal > 0 && requestedPage > nextPages) {
      page.value = nextPages
      await load(false)
      return
    }

    list.value = items
    total.value = nextTotal
    totalPages.value = nextPages
    hasMore.value = Boolean(data && data.hasMore)
    if (data && typeof data.unreadCount === 'number') unreadCount.value = data.unreadCount
    if (data && Number.isFinite(Number(data.page)) && Number(data.page) > 0) {
      page.value = Number(data.page)
    }

    markRead()
  } catch (err) {
    if (disposed || current !== requestSeq) return
    if (!session.token) {
      goLogin()
      return
    }
    error.value = errorText(err, '消息加载失败，请检查网络后重试')
  } finally {
    if (!disposed && current === requestSeq) loading.value = false
  }
}

function switchTab(type) {
  if (activeType.value === type) return
  activeType.value = type
  requestSeq += 1
  loading.value = false
  error.value = ''
  page.value = 1
  list.value = []
  load(true)
}

function goPage(target) {
  if (loading.value) return
  const next = Math.min(Math.max(1, target), totalPages.value)
  if (next === page.value) return
  page.value = next
  load(false)
}

function openMessage(message) {
  if (!message || message.postId == null) return
  router.push(`/posts/${message.postId}`)
}

onMounted(() => {
  if (!session.token) {
    goLogin()
    return
  }
  load(true)
})

onBeforeUnmount(() => {
  disposed = true
  requestSeq += 1
})
</script>

<style scoped>
.messages-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 4px 0 32px;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  color: #246bfd;
}

.page-head h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.3;
  color: #17243b;
}

.page-sub {
  margin: 8px 0 0;
  font-size: 13.5px;
  line-height: 1.7;
  color: #6b7a90;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 9px;
}

.unread-pill {
  padding: 4px 9px;
  font-size: 10.5px;
  font-weight: 600;
  color: #1859df;
  background: #edf4ff;
  border: 1px solid #d4e3ff;
  border-radius: 20px;
}

.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 34px;
  padding: 0 13px;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  color: #56708f;
  background: #ffffff;
  border: 1px solid #dce5f0;
  border-radius: 8px;
  cursor: pointer;
}

.refresh-btn:hover:not(:disabled) {
  color: #246bfd;
  border-color: #b9cef8;
}

.refresh-btn:disabled {
  cursor: wait;
  opacity: 0.65;
}

.tiny-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(86, 112, 143, 0.25);
  border-top-color: #56708f;
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.panel {
  background: #ffffff;
  border: 1px solid #e6ebf3;
  border-radius: 12px;
}

.messages-panel {
  overflow: hidden;
}

.messages-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 16px 20px;
  border-bottom: 1px solid #eef2f7;
}

.tabs {
  display: inline-flex;
  gap: 4px;
  padding: 3px;
  background: #f4f7fb;
  border-radius: 9px;
}

.tab {
  padding: 7px 14px;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  color: #6b7a90;
  background: transparent;
  border: 0;
  border-radius: 7px;
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease, box-shadow 0.16s ease;
}

.tab:hover {
  color: #3b4a60;
}

.tab.active {
  color: #1859df;
  background: #ffffff;
  box-shadow: 0 1px 4px rgba(23, 36, 59, 0.09);
}

.list-total {
  flex: 0 0 auto;
  margin: 0;
  font-size: 11.5px;
  color: #98a4b5;
}

.loading-note {
  margin-left: 7px;
  color: #246bfd;
}

.list-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 16px 20px 0;
  padding: 12px 14px;
  background: #fdf6f6;
  border: 1px solid #f0d2d2;
  border-radius: 9px;
}

.list-alert strong {
  font-size: 12.5px;
  color: #b33636;
}

.list-alert p {
  margin: 3px 0 0;
  font-size: 11.5px;
  line-height: 1.6;
  color: #8a4a4a;
}

.retry-btn {
  flex: 0 0 auto;
  height: 32px;
  padding: 0 13px;
  font: inherit;
  font-size: 11.5px;
  font-weight: 600;
  color: #b33636;
  background: #ffffff;
  border: 1px solid #e5c4c4;
  border-radius: 7px;
  cursor: pointer;
}

.retry-btn:disabled {
  cursor: wait;
  opacity: 0.6;
}

.message-list {
  transition: opacity 0.16s ease;
}

.message-list.refreshing {
  opacity: 0.58;
  pointer-events: none;
}

.message-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  width: 100%;
  padding: 17px 20px;
  font: inherit;
  text-align: left;
  color: inherit;
  background: transparent;
  border: 0;
  border-bottom: 1px solid #f0f3f8;
  cursor: default;
}

.message-item:last-child {
  border-bottom: 0;
}

.message-item.clickable {
  cursor: pointer;
}

.message-item.clickable:hover {
  background: #f9fbff;
}

.message-item.unread {
  background: #fbfdff;
}

.message-item.unread.clickable:hover {
  background: #f6faff;
}

.message-item:disabled {
  opacity: 1;
}

.message-avatar {
  position: relative;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  overflow: hidden;
  background: #eef4ff;
  border-radius: 50%;
}

.avatar-letter {
  font-size: 14px;
  font-weight: 700;
  color: #246bfd;
}

.message-avatar img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.unread-dot {
  position: absolute;
  top: 0;
  right: 0;
  width: 8px;
  height: 8px;
  background: #246bfd;
  border: 2px solid #ffffff;
  border-radius: 50%;
}

.message-body {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 5px;
}

.message-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12.5px;
  line-height: 1.6;
  color: #6b7a90;
}

.message-title strong {
  font-weight: 600;
  color: #2a3a50;
}

.message-kind {
  margin-left: auto;
  padding: 1px 7px;
  font-size: 10px;
  color: #7f8da1;
  background: #f3f6fa;
  border-radius: 20px;
}

.message-content {
  display: block;
  overflow: hidden;
  font-size: 12.5px;
  line-height: 1.7;
  color: #45566d;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-post {
  display: block;
  overflow: hidden;
  font-size: 11.5px;
  line-height: 1.6;
  color: #8b98aa;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-time {
  display: block;
  font-size: 10.5px;
  color: #a1adbc;
}

.message-arrow {
  flex: 0 0 auto;
  align-self: center;
  font-size: 20px;
  line-height: 1;
  color: #b7c3d1;
}

.empty-state {
  padding: 62px 24px 68px;
  text-align: center;
  background: transparent;
  border: 0;
}

.empty-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  margin: 0 auto 14px;
  font-size: 16px;
  font-weight: 700;
  color: #246bfd;
  background: #edf4ff;
  border-radius: 50%;
}

.empty-state h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #2a3a50;
}

.empty-state p {
  margin: 7px 0 0;
  font-size: 12px;
  line-height: 1.7;
  color: #8b98aa;
}

.skeleton-list {
  padding: 4px 20px;
}

.skeleton-row {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 17px 0;
  border-bottom: 1px solid #f2f5f9;
}

.skeleton-avatar {
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  background: #eef2f8;
  border-radius: 50%;
  animation: pulse 1.2s ease-in-out infinite;
}

.skeleton-copy {
  flex: 1;
  display: grid;
  gap: 8px;
  padding-top: 3px;
}

.skeleton-line {
  width: 54%;
  height: 9px;
  background: #eef2f8;
  border-radius: 5px;
  animation: pulse 1.2s ease-in-out infinite;
}

.skeleton-line.wide {
  width: 28%;
  height: 11px;
}

.skeleton-line.short {
  width: 20%;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}

.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 20px;
  background: #fbfcfe;
  border-top: 1px solid #eef2f7;
}

.pager-info {
  font-size: 11.5px;
  color: #8b98aa;
}

.pager-actions {
  display: flex;
  gap: 7px;
}

.pager-btn {
  height: 31px;
  padding: 0 13px;
  font: inherit;
  font-size: 11.5px;
  font-weight: 600;
  color: #3b4a60;
  background: #ffffff;
  border: 1px solid #dce5f0;
  border-radius: 7px;
  cursor: pointer;
}

.pager-btn:hover:not(:disabled) {
  color: #246bfd;
  border-color: #b9cef8;
}

.pager-btn:disabled {
  color: #b0bccb;
  background: #f7f9fc;
  cursor: not-allowed;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 600px) {
  .page-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .messages-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .tabs {
    width: 100%;
    overflow-x: auto;
  }

  .tab {
    flex: 1;
    padding: 7px 9px;
    white-space: nowrap;
  }

  .message-item {
    padding: 15px 16px;
  }

  .pager {
    align-items: flex-start;
    flex-direction: column;
    gap: 9px;
  }
}
</style>
