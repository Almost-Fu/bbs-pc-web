<template>
  <div class="bar-view">
    <div class="crumbs">
      <button type="button" class="back-button" @click="goBack">
        <Icon name="back" :size="16" />
        返回
      </button>
      <nav class="crumb-links" aria-label="面包屑">
        <RouterLink to="/">首页</RouterLink>
        <span aria-hidden="true">/</span>
        <RouterLink to="/bars">贴吧</RouterLink>
        <template v-if="barDetail">
          <span aria-hidden="true">/</span>
          <span class="current">{{ barDetail.name }}</span>
        </template>
      </nav>
    </div>

    <section v-if="loading" class="bar-loading" aria-busy="true" aria-label="正在加载贴吧">
      <div class="hero-skeleton panel">
        <div class="skeleton-avatar"></div>
        <div class="skeleton-copy">
          <div class="skeleton-line skeleton-title"></div>
          <div class="skeleton-line"></div>
          <div class="skeleton-line skeleton-short"></div>
        </div>
      </div>
      <div v-for="item in 2" :key="item" class="post-skeleton panel">
        <div class="skeleton-line skeleton-short"></div>
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line"></div>
      </div>
      <p class="loading-note">正在加载贴吧内容…</p>
    </section>

    <section v-else-if="error" class="error-state panel" role="alert">
      <span class="state-mark">!</span>
      <h2>贴吧加载失败</h2>
      <p>{{ error }}</p>
      <div class="state-actions">
        <button type="button" class="btn btn-primary" @click="loadFirst">重新加载</button>
        <RouterLink class="btn btn-ghost" to="/bars">返回贴吧列表</RouterLink>
      </div>
    </section>

    <template v-else-if="barDetail">
      <section class="bar-hero panel">
        <div class="hero-main">
          <span class="bar-avatar" aria-hidden="true">
            <span v-if="!barImage || barImageBroken" class="bar-initial">{{ barInitial }}</span>
            <img
              v-else
              :src="barImage"
              alt=""
              referrerpolicy="no-referrer"
              @error="barImageBroken = true"
            />
          </span>

          <div class="hero-copy">
            <div class="hero-kicker-row">
              <span class="hero-kicker">BAR PROFILE</span>
              <span v-if="barDetail.owner" class="owner">吧主 {{ barDetail.owner }}</span>
            </div>
            <h1>{{ barDetail.name }}</h1>
            <p class="bar-description">{{ barDetail.desc || '这个吧还没有填写简介。' }}</p>
            <div class="bar-stats">
              <span class="bar-stat">
                <span class="stat-value">{{ displayPosts }}</span>
                <span class="stat-label">帖子</span>
              </span>
              <span class="stat-separator" aria-hidden="true"></span>
              <span class="bar-stat">
                <span class="stat-value">{{ displayMembers }}</span>
                <span class="stat-label">关注</span>
              </span>
            </div>
          </div>
        </div>

        <div class="hero-actions">
          <button
            type="button"
            class="follow-button"
            :class="{ followed: barDetail.followed }"
            :disabled="followBusy"
            @click="toggleFollow"
          >
            {{ followBusy ? '处理中…' : (barDetail.followed ? '已关注' : '+ 关注') }}
          </button>
          <button type="button" class="btn btn-primary publish-button" @click="goPublish">
            <Icon name="edit" :size="15" />
            发布帖子
          </button>
        </div>
      </section>

      <p v-if="actionError" class="inline-error" role="alert">
        {{ actionError }}
        <button type="button" class="inline-close" aria-label="关闭提示" @click="actionError = ''">关闭</button>
      </p>

      <section class="stream-header">
        <div>
          <span class="stream-kicker">DISCUSSIONS</span>
          <h2>吧内帖子</h2>
        </div>
        <div class="stream-meta">
          <span v-if="!postsLoading">共 {{ total }} 篇</span>
          <button
            type="button"
            class="refresh-button"
            :disabled="loadingMore || postsLoading"
            @click="loadFirst"
          >
            <Icon name="refresh" :size="15" />
            刷新
          </button>
        </div>
      </section>

      <section v-if="postsLoading" class="post-skeleton panel" aria-busy="true">
        <div class="skeleton-line skeleton-short"></div>
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line"></div>
        <p class="loading-note">正在加载帖子…</p>
      </section>

      <div v-else-if="posts.length" class="post-list">
        <PostCard
          v-for="post in posts"
          :key="post.id"
          :post="post"
          @changed="handlePostChanged"
        />
      </div>

      <section v-else class="empty-state panel">
        <span class="empty-mark">
          <Icon name="edit" :size="26" />
        </span>
        <h2>这个吧还没有帖子</h2>
        <p>成为第一个在这里分享想法的人。</p>
        <button type="button" class="btn btn-primary" @click="goPublish">发布第一篇帖子</button>
      </section>

      <div v-if="posts.length" class="bar-pagination">
        <span class="pagination-note">已展示 {{ posts.length }} / {{ total }} 篇</span>
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
import { api, imageUrl } from '../api'
import { session } from '../session'
import Icon from '../components/Icon.vue'
import PostCard from '../components/PostCard.vue'

const PAGE_SIZE = 10

const route = useRoute()
const router = useRouter()

const barDetail = ref(null)
const posts = ref([])
const page = ref(1)
const total = ref(0)
const totalPages = ref(0)
const hasMore = ref(false)
const loading = ref(true)
const postsLoading = ref(false)
const loadingMore = ref(false)
const error = ref('')
const loadMoreError = ref('')
const actionError = ref('')
const followBusy = ref(false)
const barImageBroken = ref(false)

let requestSeq = 0

const barImage = computed(() => {
  const value = barDetail.value?.img
  if (!value) return ''
  const resolved = imageUrl(value)
  if (/^https?:\/\//i.test(resolved)) return resolved
  if (resolved.startsWith('/') && !resolved.startsWith('//') && !resolved.startsWith('/\\')) {
    return resolved
  }
  return ''
})

const barInitial = computed(() => {
  const name = String(barDetail.value?.name || '').trim()
  return name ? name.slice(0, 1) : '吧'
})

const displayPosts = computed(() => statOf(barDetail.value?.posts, barDetail.value?.postCount))
const displayMembers = computed(() => statOf(barDetail.value?.members, barDetail.value?.followCount))

function statOf(formatted, exact) {
  if (formatted !== undefined && formatted !== null && formatted !== '') return formatted
  if (exact !== undefined && exact !== null && exact !== '') return exact
  return 0
}

function parseBarId() {
  const value = Number(route.params.id)
  return Number.isInteger(value) && value > 0 ? value : null
}

function applyPage(data, append) {
  if (!data || !Array.isArray(data.list)) {
    throw new Error('返回数据格式异常，请稍后重试')
  }

  posts.value = append ? [...posts.value, ...data.list] : data.list
  page.value = Math.max(1, Number(data.page) || (append ? page.value : 1))
  total.value = Math.max(0, Number(data.total) || 0)
  totalPages.value = Math.max(0, Number(data.totalPages) || 0)
  hasMore.value = typeof data.hasMore === 'boolean'
    ? data.hasMore
    : (totalPages.value > 0 ? page.value < totalPages.value : false)
}

async function loadFirst() {
  const barId = parseBarId()
  const seq = ++requestSeq

  barDetail.value = null
  posts.value = []
  page.value = 1
  total.value = 0
  totalPages.value = 0
  hasMore.value = false
  loading.value = true
  postsLoading.value = false
  loadingMore.value = false
  error.value = ''
  loadMoreError.value = ''
  actionError.value = ''
  followBusy.value = false
  barImageBroken.value = false

  if (!barId) {
    loading.value = false
    error.value = '贴吧地址无效，请返回列表重新选择。'
    return
  }

  try {
    const [detail, data] = await Promise.all([
      api.bar(barId),
      api.barPosts(barId, { page: 1, pageSize: PAGE_SIZE })
    ])
    if (seq !== requestSeq) return
    if (!detail || typeof detail !== 'object') {
      throw new Error('贴吧信息返回异常，请稍后重试')
    }
    barDetail.value = detail
    applyPage(data, false)
  } catch (requestError) {
    if (seq !== requestSeq) return
    barDetail.value = null
    error.value = requestError?.message || '网络异常，请稍后重试'
  } finally {
    if (seq === requestSeq) loading.value = false
  }
}

async function loadMore() {
  if (loading.value || loadingMore.value || !hasMore.value) return
  const barId = parseBarId()
  if (!barId) return

  const seq = requestSeq
  loadingMore.value = true
  loadMoreError.value = ''
  try {
    const data = await api.barPosts(barId, { page: page.value + 1, pageSize: PAGE_SIZE })
    if (seq !== requestSeq) return
    applyPage(data, true)
  } catch (requestError) {
    if (seq !== requestSeq) return
    loadMoreError.value = requestError?.message || '加载更多失败，请稍后重试'
  } finally {
    if (seq === requestSeq) loadingMore.value = false
  }
}

function requireLogin() {
  if (session.token) return true
  router.push({ path: '/login', query: { redirect: route.fullPath } })
  return false
}

async function toggleFollow() {
  actionError.value = ''
  if (!barDetail.value || followBusy.value || !requireLogin()) return

  const barId = barDetail.value.id
  const target = !barDetail.value.followed
  const seq = requestSeq
  const token = session.token
  const isCurrentRequest = () => (
    seq === requestSeq &&
    session.token === token &&
    parseBarId() === barId &&
    barDetail.value?.id === barId
  )

  followBusy.value = true
  try {
    const result = await api.followBar(barId, target)
    if (!isCurrentRequest()) return

    const followed = typeof result?.followed === 'boolean' ? result.followed : target
    const next = {
      ...barDetail.value,
      followed,
      followCount: Number.isFinite(Number(result?.followCount))
        ? Math.max(0, Number(result.followCount))
        : barDetail.value.followCount
    }
    if (result?.members !== undefined) next.members = result.members
    barDetail.value = next
  } catch (requestError) {
    if (!isCurrentRequest()) return
    actionError.value = requestError?.message || '关注操作失败，请稍后重试'
  } finally {
    if (isCurrentRequest()) followBusy.value = false
  }
}

function goPublish() {
  if (!barDetail.value || !requireLogin()) return
  router.push({ path: '/publish', query: { barId: String(barDetail.value.id) } })
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/bars')
}

function handlePostChanged(updated) {
  if (!updated || updated.id == null) return
  const index = posts.value.findIndex((item) => item.id === updated.id)
  if (index >= 0) posts.value[index] = updated
}

watch(
  () => session.token,
  () => {
    followBusy.value = false
    actionError.value = ''
  }
)

watch(
  () => route.params.id,
  () => loadFirst(),
  { immediate: true }
)
</script>

<style scoped>
.bar-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.crumbs {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 28px;
  padding: 0 2px;
}

.back-button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 8px 0 5px;
  border: 1px solid #e3eaf4;
  border-radius: 7px;
  background: #ffffff;
  color: #66768d;
  font: inherit;
  font-size: 11px;
  cursor: pointer;
}

.back-button:hover {
  border-color: #cfdcf0;
  color: #246bfd;
}

.crumb-links {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 7px;
  color: #a0acbd;
  font-size: 11px;
}

.crumb-links a {
  color: #7e8da2;
  text-decoration: none;
}

.crumb-links a:hover {
  color: #246bfd;
}

.crumb-links .current {
  overflow: hidden;
  max-width: 260px;
  color: #4d5d74;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-hero {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  overflow: hidden;
  padding: 25px 26px;
  border: 1px solid #e6ecf6;
  border-radius: 18px;
  background: #ffffff;
}

.bar-hero::after {
  position: absolute;
  right: 110px;
  bottom: -80px;
  width: 170px;
  height: 170px;
  border: 1px solid #edf2fb;
  border-radius: 50%;
  content: "";
}

.hero-main {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  min-width: 0;
  gap: 17px;
}

.bar-avatar {
  position: relative;
  display: grid;
  place-items: center;
  width: 76px;
  height: 76px;
  flex: 0 0 76px;
  overflow: hidden;
  border: 1px solid #dfe9fa;
  border-radius: 18px;
  background: #eef4ff;
  color: #246bfd;
  font-size: 27px;
  font-weight: 750;
}

.bar-avatar img {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.bar-initial {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
}

.hero-copy {
  min-width: 0;
}

.hero-kicker-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-kicker,
.stream-kicker {
  display: block;
  color: #246bfd;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.14em;
  line-height: 1.5;
}

.owner {
  color: #99a6b8;
  font-size: 10px;
}

.hero-copy h1 {
  margin: 5px 0 0;
  color: #17243b;
  font-size: 26px;
  font-weight: 750;
  line-height: 1.35;
  letter-spacing: -0.02em;
  overflow-wrap: anywhere;
}

.bar-description {
  display: -webkit-box;
  overflow: hidden;
  max-width: 620px;
  margin: 6px 0 0;
  color: #738299;
  font-size: 12px;
  line-height: 1.7;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.bar-stats {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-top: 12px;
}

.bar-stat {
  display: flex;
  align-items: baseline;
  gap: 5px;
}

.stat-value {
  color: #2e3e56;
  font-size: 15px;
  font-weight: 750;
}

.stat-label {
  color: #97a4b6;
  font-size: 10px;
}

.stat-separator {
  width: 1px;
  height: 12px;
  background: #e8edf5;
}

.hero-actions {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 8px;
  padding-top: 4px;
}

.follow-button {
  height: 34px;
  min-width: 76px;
  padding: 0 13px;
  border: 1px solid #cfdeff;
  border-radius: 8px;
  background: #f4f8ff;
  color: #246bfd;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease;
}

.follow-button:hover:not(:disabled) {
  border-color: #a9c4ff;
  background: #eaf2ff;
}

.follow-button.followed {
  border-color: #e2e9f3;
  background: #f6f8fb;
  color: #77869b;
}

.follow-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.publish-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 13px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 650;
}

.inline-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0;
  padding: 10px 13px;
  border: 1px solid #f0dada;
  border-radius: 9px;
  background: #fff9f9;
  color: #b63c3c;
  font-size: 12px;
  line-height: 1.6;
}

.inline-close {
  flex: 0 0 auto;
  padding: 0;
  border: 0;
  background: transparent;
  color: #b63c3c;
  font: inherit;
  font-size: 11px;
  text-decoration: underline;
  cursor: pointer;
}

.stream-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 3px 3px 0;
}

.stream-header h2 {
  margin: 4px 0 0;
  color: #26354c;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.45;
}

.stream-meta {
  display: flex;
  align-items: center;
  gap: 11px;
  color: #96a3b6;
  font-size: 11px;
}

.refresh-button {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 29px;
  padding: 0 8px;
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
  background: #ffffff;
  color: #246bfd;
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.55;
}

.post-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bar-pagination {
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

.text-action {
  padding: 0;
  border: 0;
  background: transparent;
  color: #246bfd;
  font: inherit;
  cursor: pointer;
}

.hero-skeleton,
.post-skeleton {
  padding: 21px 22px;
  border: 1px solid #e7ecf5;
  border-radius: 14px;
  background: #ffffff;
}

.hero-skeleton {
  display: flex;
  align-items: flex-start;
  gap: 17px;
  min-height: 126px;
}

.skeleton-avatar {
  width: 76px;
  height: 76px;
  flex: 0 0 76px;
  border-radius: 18px;
  background: #eef2f8;
  animation: soft-pulse 1.5s ease-in-out infinite;
}

.skeleton-copy {
  min-width: 0;
  flex: 1;
}

.skeleton-line {
  height: 10px;
  margin-top: 10px;
  border-radius: 5px;
  background: #eef2f8;
  animation: soft-pulse 1.5s ease-in-out infinite;
}

.skeleton-line:first-child {
  margin-top: 2px;
}

.skeleton-title {
  width: 42%;
  height: 19px;
  margin-top: 17px;
}

.skeleton-short {
  width: 24%;
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
  padding: 44px 24px;
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
  margin: 7px 0 14px;
  color: #8391a5;
  font-size: 12px;
  line-height: 1.75;
}

.state-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 9px;
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

@media (max-width: 820px) {
  .bar-hero {
    flex-direction: column;
    padding: 21px 19px;
  }

  .hero-actions {
    width: 100%;
    padding-top: 3px;
  }

  .hero-copy h1 {
    font-size: 22px;
  }

  .crumb-links .current {
    max-width: 160px;
  }
}
</style>
