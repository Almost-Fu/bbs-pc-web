<template>
  <div class="feed-view">
    <section v-if="mode === 'home'" class="welcome panel">
      <div class="welcome-copy">
        <h1>{{ greeting }}</h1>
        <p>发现真实的讨论，分享有趣的想法。</p>
      </div>
      <RouterLink class="btn btn-primary welcome-publish" to="/publish">
        <Icon name="edit" :size="15" />
        发布帖子
      </RouterLink>
    </section>

    <section v-else class="context-panel panel">
      <div class="context-head">
        <span class="context-icon">
          <Icon :name="modeMeta.icon" :size="22" />
        </span>
        <div class="context-copy">
          <span class="context-eyebrow">{{ modeMeta.eyebrow }}</span>
          <h1>{{ modeMeta.title }}</h1>
          <p>{{ modeMeta.description }}</p>
        </div>
      </div>

      <form v-if="mode === 'search'" class="inline-search" @submit.prevent="submitSearch">
        <Icon name="search" :size="17" />
        <input
          v-model="searchInput"
          type="search"
          maxlength="60"
          placeholder="搜索帖子、话题或吧名"
          aria-label="搜索关键词"
        />
        <button type="submit" class="search-submit">搜索</button>
      </form>

      <div v-if="mode === 'search'" class="hot-keywords" aria-live="polite">
        <span class="hot-label">热门搜索</span>
        <template v-if="hotLoading">
          <span class="hot-hint">正在读取热门话题…</span>
        </template>
        <template v-else-if="hotKeywords.length">
          <button
            v-for="word in hotKeywords"
            :key="word"
            type="button"
            class="hot-chip"
            @click="pickKeyword(word)"
          >{{ word }}</button>
        </template>
        <span v-else-if="hotError" class="hot-hint">
          {{ hotError }}
          <button type="button" class="text-action" @click="loadHotSearch">重试</button>
        </span>
        <span v-else class="hot-hint">暂无热门搜索词</span>
      </div>
    </section>

    <section
      v-if="showStream"
      class="stream-toolbar"
      :aria-label="mode === 'home' ? '帖子排序' : '内容列表'"
    >
      <div v-if="mode === 'home'" class="tabs" role="tablist" aria-label="排序方式">
        <button
          v-for="tab in SORT_TABS"
          :key="tab.key"
          type="button"
          role="tab"
          class="tab"
          :class="{ active: activeSort === tab.key }"
          :aria-selected="activeSort === tab.key"
          @click="selectSort(tab.key)"
        >
          <Icon v-if="tab.key === 'hot'" name="fire" :size="14" />
          {{ tab.label }}
        </button>
      </div>
      <div v-else class="stream-label">
        <span class="stream-kicker">POSTS</span>
        <h2>{{ streamHeading }}</h2>
      </div>

      <div class="toolbar-right">
        <span v-if="!loading && !error" class="result-count">
          共 <strong>{{ total }}</strong> 篇
        </span>
        <button
          type="button"
          class="refresh-button"
          :disabled="loading || loadingMore"
          @click="loadFirst"
        >
          <Icon name="refresh" :size="15" />
          刷新
        </button>
      </div>
    </section>

    <section v-if="loading" class="skeleton-list" aria-busy="true" aria-label="正在加载帖子">
      <div v-for="item in 3" :key="item" class="skeleton-card panel">
        <div class="skeleton-line skeleton-short"></div>
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line skeleton-medium"></div>
      </div>
      <p class="loading-note">正在加载社区内容…</p>
    </section>

    <section v-else-if="error" class="error-state panel" role="alert">
      <span class="state-mark">!</span>
      <h2>内容加载失败</h2>
      <p>{{ error }}</p>
      <div class="state-actions">
        <button type="button" class="btn btn-primary" @click="loadFirst">重新加载</button>
        <button v-if="needsLogin" type="button" class="btn btn-ghost" @click="goLogin">去登录</button>
      </div>
    </section>

    <template v-else-if="showStream">
      <div v-if="posts.length" class="post-list">
        <PostCard
          v-for="post in posts"
          :key="post.id"
          :post="post"
          @changed="handlePostChanged"
        />
      </div>

      <section v-else class="empty-state panel">
        <span class="empty-mark">
          <Icon :name="modeMeta.icon" :size="26" />
        </span>
        <h2>{{ emptyTitle }}</h2>
        <p>{{ emptyDescription }}</p>
        <div class="state-actions">
          <RouterLink v-if="mode === 'home'" class="btn btn-primary" to="/bars">去逛逛贴吧</RouterLink>
          <button
            v-else-if="mode === 'search'"
            type="button"
            class="btn btn-primary"
            @click="clearSearch"
          >清除关键词</button>
          <RouterLink v-else-if="mode === 'favorites'" class="btn btn-primary" to="/">返回首页</RouterLink>
          <RouterLink v-else-if="mode === 'my-posts'" class="btn btn-primary" to="/publish">写第一篇帖子</RouterLink>
        </div>
      </section>

      <div v-if="posts.length" class="feed-pagination">
        <span class="pagination-note">
          已展示 {{ posts.length }} / {{ total }} 篇
        </span>
        <span v-if="loadMoreError" class="load-more-error" role="alert">
          {{ loadMoreError }}
          <button type="button" class="text-action" @click="loadMore">重试</button>
        </span>
        <button
          v-else-if="hasMore"
          type="button"
          class="btn btn-ghost load-more"
          :disabled="loadingMore"
          @click="loadMore"
        >{{ loadingMore ? '加载中…' : '加载更多' }}</button>
        <span v-else class="pagination-end">已经到底了</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { session } from '../session'
import Icon from '../components/Icon.vue'
import PostCard from '../components/PostCard.vue'

const PAGE_SIZE = 10
const SORT_TABS = [
  { key: 'latest', label: '最新' },
  { key: 'hot', label: '最热' }
]

const route = useRoute()
const router = useRouter()

const mode = ref('home')
const keyword = ref('')
const searchInput = ref('')
const activeSort = ref('latest')
const posts = ref([])
const page = ref(1)
const total = ref(0)
const totalPages = ref(0)
const hasMore = ref(false)
const loading = ref(true)
const loadingMore = ref(false)
const error = ref('')
const needsLogin = ref(false)
const loadMoreError = ref('')
const hotKeywords = ref([])
const hotLoading = ref(false)
const hotError = ref('')

let requestSeq = 0
let hotSeq = 0

const showStream = computed(() => mode.value !== 'search' || Boolean(keyword.value))

const greeting = computed(() => {
  const nickname = String(session.user?.nickname || '').trim()
  return nickname ? `欢迎回来，${nickname}` : '欢迎来到社区'
})

const modeMeta = computed(() => {
  if (mode.value === 'search') {
    return {
      icon: 'search',
      eyebrow: 'SEARCH',
      title: keyword.value ? `搜索“${keyword.value}”` : '搜索社区',
      description: keyword.value ? '在海量真实讨论中查找你感兴趣的内容。' : '输入关键词，查找帖子、话题与贴吧。'
    }
  }
  if (mode.value === 'favorites') {
    return {
      icon: 'bookmark',
      eyebrow: 'MY FAVORITES',
      title: '我的收藏',
      description: '把值得重读的讨论留在这里。'
    }
  }
  if (mode.value === 'my-posts') {
    return {
      icon: 'edit',
      eyebrow: 'MY POSTS',
      title: '我的帖子',
      description: '查看你在社区发布过的全部内容。'
    }
  }
  return {
    icon: 'compass',
    eyebrow: 'FEED',
    title: '社区信息流',
    description: '社区里的新鲜事。'
  }
})

const streamHeading = computed(() => {
  if (mode.value === 'search') return keyword.value ? `“${keyword.value}” 的搜索结果` : '搜索结果'
  if (mode.value === 'favorites') return '收藏的帖子'
  if (mode.value === 'my-posts') return '我发布的帖子'
  return '社区帖子'
})

const emptyTitle = computed(() => {
  if (mode.value === 'search') return '没有找到相关帖子'
  if (mode.value === 'favorites') return '收藏夹还是空的'
  if (mode.value === 'my-posts') return '还没有发布过帖子'
  return '这里暂时还没有帖子'
})

const emptyDescription = computed(() => {
  if (mode.value === 'search') return '换一个关键词试试，或从热门搜索中挑一个话题。'
  if (mode.value === 'favorites') return '遇到想反复阅读的帖子时，点一下收藏就能在这里找到。'
  if (mode.value === 'my-posts') return '把你的想法写下来，和社区里的朋友一起讨论。'
  return '社区正在等待第一篇内容，去贴吧看看或发布一个帖子吧。'
})

function getRouteContext() {
  const path = route.path.replace(/\/+$/, '') || '/'
  const rawQuery = Array.isArray(route.query.q) ? route.query.q[0] : route.query.q
  const nextKeyword = String(rawQuery || '').trim()

  if (path === '/search') return { mode: 'search', keyword: nextKeyword }
  if (path === '/favorites') return { mode: 'favorites', keyword: '' }
  if (path === '/my-posts') return { mode: 'my-posts', keyword: '' }
  return { mode: 'home', keyword: '' }
}

function fetchPage(context, targetPage) {
  const query = { page: targetPage, pageSize: PAGE_SIZE }
  if (context.mode === 'search') {
    return api.search(context.keyword, query)
  }
  if (context.mode === 'favorites') {
    return api.favorites(query)
  }
  if (context.mode === 'my-posts') {
    return api.myPosts(query)
  }
  const order = activeSort.value === 'hot' ? 'hot' : 'latest'
  return api.posts({ ...query, order })
}

function applyPage(data, append) {
  if (!data || !Array.isArray(data.list)) {
    throw new Error('返回数据格式异常，请稍后重试')
  }

  const nextPosts = data.list
  posts.value = append ? [...posts.value, ...nextPosts] : nextPosts
  page.value = Math.max(1, Number(data.page) || (append ? page.value : 1))
  total.value = Math.max(0, Number(data.total) || 0)
  totalPages.value = Math.max(0, Number(data.totalPages) || 0)
  hasMore.value = typeof data.hasMore === 'boolean'
    ? data.hasMore
    : (totalPages.value > 0 ? page.value < totalPages.value : false)
}

async function loadFirst() {
  const context = getRouteContext()
  mode.value = context.mode
  keyword.value = context.keyword
  searchInput.value = context.keyword

  const seq = ++requestSeq
  loading.value = true
  loadingMore.value = false
  error.value = ''
  needsLogin.value = false
  loadMoreError.value = ''
  posts.value = []
  page.value = 1
  total.value = 0
  totalPages.value = 0
  hasMore.value = false

  if (context.mode === 'search') loadHotSearch()

  if (context.mode === 'search' && !context.keyword) {
    loading.value = false
    return
  }

  if ((context.mode === 'favorites' || context.mode === 'my-posts') && !session.token) {
    loading.value = false
    needsLogin.value = true
    error.value = '请先登录后再查看这里的内容。'
    return
  }

  try {
    const data = await fetchPage(context, 1)
    if (seq !== requestSeq) return
    applyPage(data, false)
  } catch (requestError) {
    if (seq !== requestSeq) return
    error.value = requestError?.message || '网络异常，请稍后重试'
  } finally {
    if (seq === requestSeq) loading.value = false
  }
}

async function loadMore() {
  if (loading.value || loadingMore.value || !hasMore.value) return

  const context = getRouteContext()
  const seq = requestSeq
  const nextPage = page.value + 1
  loadingMore.value = true
  loadMoreError.value = ''

  try {
    const data = await fetchPage(context, nextPage)
    if (seq !== requestSeq) return
    applyPage(data, true)
  } catch (requestError) {
    if (seq !== requestSeq) return
    loadMoreError.value = requestError?.message || '加载更多失败，请稍后重试'
  } finally {
    if (seq === requestSeq) loadingMore.value = false
  }
}

function selectSort(key) {
  if (activeSort.value === key) return
  activeSort.value = key
  loadFirst()
}

async function loadHotSearch() {
  const seq = ++hotSeq
  hotLoading.value = true
  hotError.value = ''
  try {
    const data = await api.hotSearch()
    if (seq !== hotSeq) return
    const words = Array.isArray(data?.keywords) ? data.keywords : []
    hotKeywords.value = words.map((word) => String(word || '').trim()).filter(Boolean)
  } catch (requestError) {
    if (seq !== hotSeq) return
    hotKeywords.value = []
    hotError.value = requestError?.message || '热门搜索加载失败'
  } finally {
    if (seq === hotSeq) hotLoading.value = false
  }
}

function submitSearch() {
  const word = searchInput.value.trim()
  if (!word) {
    router.push('/search')
    return
  }
  router.push({ path: '/search', query: { q: word } })
}

function pickKeyword(word) {
  searchInput.value = word
  router.push({ path: '/search', query: { q: word } })
}

function clearSearch() {
  searchInput.value = ''
  router.push('/search')
}

function goLogin() {
  router.push({ path: '/login', query: { redirect: route.fullPath } })
}

function handlePostChanged(updated) {
  if (!updated || updated.id == null) return
  const index = posts.value.findIndex((item) => item.id === updated.id)
  if (index < 0) return

  if (mode.value === 'favorites' && updated.favorited === false) {
    posts.value.splice(index, 1)
    total.value = Math.max(0, total.value - 1)
    return
  }

  posts.value[index] = updated
}

watch(
  () => route.fullPath,
  () => loadFirst(),
  { immediate: true }
)
</script>

<style scoped>
.feed-view {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.welcome {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  min-height: 96px;
  padding: 16px 20px;
  border: 1px solid #e8edf5;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(23, 36, 59, 0.035);
}

.welcome-copy {
  min-width: 0;
}

.welcome h1 {
  margin: 0;
  color: #17243b;
  font-size: 21px;
  font-weight: 700;
  line-height: 1.35;
  letter-spacing: -0.015em;
  overflow-wrap: anywhere;
}

.welcome-copy p {
  margin: 4px 0 0;
  color: #6e7d93;
  font-size: 13px;
  line-height: 1.5;
}

.welcome-publish {
  flex: 0 0 auto;
  height: 34px;
  padding: 0 14px;
  border-radius: 8px;
  font-size: 12px;
}

.context-eyebrow,
.stream-kicker {
  display: block;
  color: #246bfd;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.14em;
  line-height: 1.5;
}

.context-panel {
  padding: 22px 24px;
  border: 1px solid #e7ecf5;
  border-radius: 16px;
  background: #ffffff;
}

.context-head {
  display: flex;
  align-items: flex-start;
  gap: 13px;
}

.context-icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  border-radius: 11px;
  background: #eef4ff;
  color: #246bfd;
}

.context-copy {
  min-width: 0;
}

.context-copy h1 {
  margin: 4px 0 0;
  color: #17243b;
  font-size: 23px;
  font-weight: 750;
  line-height: 1.4;
  letter-spacing: -0.015em;
  overflow-wrap: anywhere;
}

.context-copy p {
  margin: 5px 0 0;
  color: #77869c;
  font-size: 12px;
  line-height: 1.7;
}

.inline-search {
  display: flex;
  align-items: center;
  gap: 9px;
  height: 40px;
  margin-top: 17px;
  padding: 0 5px 0 13px;
  border: 1px solid #dfe7f3;
  border-radius: 9px;
  background: #f9fbfe;
  color: #8a98ad;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.inline-search:focus-within {
  border-color: #9dbcfb;
  box-shadow: 0 0 0 3px rgba(36, 107, 253, 0.08);
}

.inline-search input {
  min-width: 0;
  flex: 1;
  height: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: #17243b;
  font: inherit;
  font-size: 13px;
}

.inline-search input::placeholder {
  color: #a3afc0;
}

.search-submit {
  height: 30px;
  padding: 0 14px;
  border: 0;
  border-radius: 7px;
  background: #246bfd;
  color: #ffffff;
  font: inherit;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}

.hot-keywords {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 13px;
}

.hot-label {
  margin-right: 3px;
  color: #96a3b7;
  font-size: 11px;
  font-weight: 600;
}

.hot-chip {
  padding: 5px 10px;
  border: 1px solid #e5ebf5;
  border-radius: 999px;
  background: #ffffff;
  color: #53647c;
  font: inherit;
  font-size: 11px;
  cursor: pointer;
  transition: color 0.16s ease, border-color 0.16s ease, background 0.16s ease;
}

.hot-chip:hover {
  border-color: #bdd2ff;
  background: #f3f7ff;
  color: #246bfd;
}

.hot-hint {
  color: #9aa7b9;
  font-size: 11px;
}

.text-action {
  padding: 0;
  border: 0;
  background: transparent;
  color: #246bfd;
  font: inherit;
  cursor: pointer;
}

.stream-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 44px;
  padding: 3px 8px 3px 10px;
  border: 1px solid #e9eef6;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(23, 36, 59, 0.035);
}

.tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border-radius: 8px;
  background: #f2f5fa;
}

.tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 64px;
  height: 30px;
  padding: 0 13px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #69788e;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.16s ease, background 0.16s ease, box-shadow 0.16s ease;
}

.tab:hover {
  color: #246bfd;
}

.tab.active {
  background: #ffffff;
  color: #246bfd;
  box-shadow: 0 1px 2px rgba(36, 65, 110, 0.08);
}

.stream-label {
  display: flex;
  align-items: baseline;
  min-width: 0;
  gap: 9px;
}

.stream-label h2 {
  overflow: hidden;
  margin: 0;
  color: #26354c;
  font-size: 14px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolbar-right {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 12px;
}

.result-count {
  color: #96a3b6;
  font-size: 11px;
}

.result-count strong {
  color: #53647c;
  font-weight: 650;
}

.refresh-button {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 9px;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  color: #7c8ba0;
  font: inherit;
  font-size: 11px;
  cursor: pointer;
}

.refresh-button:hover:not(:disabled) {
  border-color: #e3eaf4;
  background: #f8fafd;
  color: #246bfd;
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.55;
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-card {
  padding: 16px 18px 12px;
  border: 1px solid #e7ecf5;
  border-radius: 12px;
  background: #ffffff;
}

.skeleton-line {
  height: 10px;
  margin-top: 10px;
  border-radius: 5px;
  background: #eef2f8;
  animation: soft-pulse 1.5s ease-in-out infinite;
}

.skeleton-line:first-child {
  margin-top: 0;
}

.skeleton-short {
  width: 18%;
  height: 9px;
}

.skeleton-title {
  width: 62%;
  height: 18px;
  margin-top: 17px;
}

.skeleton-medium {
  width: 42%;
}

.loading-note {
  margin: 2px 0 0;
  color: #9ba8ba;
  font-size: 11px;
  text-align: center;
}

@keyframes soft-pulse {
  0%,
  100% {
    opacity: 0.55;
  }
  50% {
    opacity: 1;
  }
}

.error-state,
.empty-state {
  display: flex;
  align-items: center;
  flex-direction: column;
  padding: 42px 24px;
  border: 1px solid #e7ecf5;
  border-radius: 14px;
  background: #ffffff;
  text-align: center;
}

.state-mark,
.empty-mark {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: #f2f5fa;
  color: #7f8ea4;
  font-size: 17px;
  font-weight: 700;
}

.empty-mark {
  background: #eef4ff;
  color: #246bfd;
}

.error-state h2,
.empty-state h2 {
  margin: 13px 0 0;
  color: #25344b;
  font-size: 16px;
  font-weight: 700;
}

.error-state p,
.empty-state p {
  max-width: 420px;
  margin: 7px 0 0;
  color: #8391a5;
  font-size: 12px;
  line-height: 1.75;
}

.state-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 9px;
  margin-top: 17px;
}

.state-actions .btn {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 14px;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
}

.post-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.feed-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 43px;
  padding: 5px 8px;
  color: #93a0b3;
  font-size: 11px;
}

.load-more {
  height: 32px;
  padding: 0 15px;
  border-radius: 7px;
  font-size: 12px;
}

.load-more-error {
  color: #bd3e3e;
  font-size: 11px;
}

.pagination-end {
  color: #aab5c5;
}

@media (max-width: 760px) {
  .welcome {
    min-height: 0;
    padding: 15px 16px;
  }

  .welcome h1 {
    font-size: 19px;
  }

  .welcome-publish {
    height: 32px;
    padding: 0 12px;
  }

  .stream-toolbar {
    align-items: flex-start;
    flex-direction: column;
    gap: 7px;
    padding: 6px 8px;
  }

  .toolbar-right {
    width: 100%;
    justify-content: flex-end;
  }

  .context-panel {
    padding: 18px 17px;
  }
}
</style>
