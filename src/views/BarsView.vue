<template>
  <div class="bars-view">
    <section class="bars-hero panel">
      <div class="hero-copy">
        <span class="hero-eyebrow">EXPLORE COMMUNITIES</span>
        <h1>发现贴吧</h1>
        <p>找到同好，加入正在发生的讨论。每个贴吧都来自真实社区。</p>
      </div>
      <form class="bar-search" @submit.prevent="searchBars">
        <Icon name="search" :size="17" />
        <input
          v-model="searchText"
          type="search"
          maxlength="40"
          placeholder="按吧名或简介搜索"
          aria-label="搜索贴吧"
        />
        <button v-if="appliedKeyword" type="button" class="clear-search" @click="clearSearch">清除</button>
        <button type="submit" class="search-button">搜索</button>
      </form>
      <span class="hero-decoration" aria-hidden="true"></span>
    </section>

    <div class="list-heading">
      <div class="heading-copy">
        <span class="heading-kicker">ALL BARS</span>
        <h2>{{ listTitle }}</h2>
      </div>
      <span v-if="!loading && !error" class="bar-count">{{ bars.length }} 个吧</span>
    </div>

    <p v-if="actionError" class="inline-error" role="alert">
      {{ actionError }}
      <button type="button" class="inline-close" aria-label="关闭提示" @click="actionError = ''">关闭</button>
    </p>

    <section v-if="loading" class="bar-grid" aria-busy="true" aria-label="正在加载贴吧">
      <div v-for="item in 4" :key="item" class="bar-skeleton panel">
        <div class="skeleton-logo"></div>
        <div class="skeleton-copy">
          <div class="skeleton-line skeleton-name"></div>
          <div class="skeleton-line"></div>
          <div class="skeleton-line skeleton-desc"></div>
        </div>
      </div>
      <p class="loading-note">正在加载贴吧…</p>
    </section>

    <section v-else-if="error" class="error-state panel" role="alert">
      <span class="state-mark">!</span>
      <h2>贴吧加载失败</h2>
      <p>{{ error }}</p>
      <button type="button" class="btn btn-primary" @click="loadBars">重新加载</button>
    </section>

    <section v-else-if="!bars.length" class="empty-state panel">
      <span class="empty-mark">
        <Icon name="compass" :size="26" />
      </span>
      <h2>{{ appliedKeyword ? '没有找到相关贴吧' : '社区里还没有贴吧' }}</h2>
      <p>{{ appliedKeyword ? '换一个关键词试试，或清除搜索查看全部贴吧。' : '贴吧创建后会出现在这里，暂时还没有可浏览的贴吧。' }}</p>
      <button
        v-if="appliedKeyword"
        type="button"
        class="btn btn-primary"
        @click="clearSearch"
      >查看全部贴吧</button>
    </section>

    <div v-else class="bar-grid">
      <article
        v-for="bar in bars"
        :key="bar.id"
        class="bar-card panel"
      >
        <RouterLink class="bar-main" :to="`/bars/${bar.id}`">
          <span class="bar-avatar" aria-hidden="true">
            <span v-if="!barImage(bar) || brokenImages.includes(bar.id)" class="bar-initial">{{ initialOf(bar) }}</span>
            <img
              v-else
              :src="barImage(bar)"
              alt=""
              loading="lazy"
              referrerpolicy="no-referrer"
              @error="markBroken(bar.id)"
            />
          </span>

          <span class="bar-copy">
            <span class="bar-name-row">
              <strong class="bar-name">{{ bar.name }}</strong>
              <span v-if="bar.owner" class="bar-owner">吧主 {{ bar.owner }}</span>
            </span>
            <span class="bar-desc">{{ bar.desc || '这个吧还没有填写简介。' }}</span>
            <span class="bar-stats">
              <span>帖子 <strong>{{ statOf(bar.posts, bar.postCount) }}</strong></span>
              <span class="stat-dot"></span>
              <span>关注 <strong>{{ statOf(bar.members, bar.followCount) }}</strong></span>
            </span>
          </span>

          <span class="bar-arrow" aria-hidden="true">
            <Icon name="arrow" :size="16" />
          </span>
        </RouterLink>

        <div class="card-foot">
          <span class="foot-note">进入贴吧参与讨论</span>
          <button
            type="button"
            class="follow-button"
            :class="{ followed: bar.followed }"
            :disabled="Boolean(pendingFollows[bar.id])"
            @click="toggleFollow(bar)"
          >
            {{ pendingFollows[bar.id] ? '处理中…' : (bar.followed ? '已关注' : '+ 关注') }}
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api, imageUrl } from '../api'
import { session } from '../session'
import Icon from '../components/Icon.vue'

const route = useRoute()
const router = useRouter()

const bars = ref([])
const searchText = ref('')
const appliedKeyword = ref('')
const loading = ref(true)
const error = ref('')
const actionError = ref('')
const brokenImages = ref([])
const pendingFollows = reactive({})

let requestSeq = 0

const listTitle = computed(() => (
  appliedKeyword.value ? `“${appliedKeyword.value}” 相关贴吧` : '全部贴吧'
))

function safeImage(value) {
  if (!value) return ''
  const resolved = imageUrl(value)
  if (/^https?:\/\//i.test(resolved)) return resolved
  if (resolved.startsWith('/') && !resolved.startsWith('//') && !resolved.startsWith('/\\')) {
    return resolved
  }
  return ''
}

function barImage(bar) {
  return safeImage(bar?.img)
}

function initialOf(bar) {
  const name = String(bar?.name || '').trim()
  return name ? name.slice(0, 1) : '吧'
}

function statOf(formatted, exact) {
  if (formatted !== undefined && formatted !== null && formatted !== '') return formatted
  if (exact !== undefined && exact !== null && exact !== '') return exact
  return 0
}

function markBroken(id) {
  if (!brokenImages.value.includes(id)) {
    brokenImages.value = [...brokenImages.value, id]
  }
}

async function loadBars() {
  const seq = ++requestSeq
  loading.value = true
  error.value = ''
  actionError.value = ''
  bars.value = []

  try {
    const data = await api.bars(appliedKeyword.value || undefined)
    if (seq !== requestSeq) return
    if (!Array.isArray(data)) throw new Error('返回数据格式异常，请稍后重试')
    bars.value = data
  } catch (requestError) {
    if (seq !== requestSeq) return
    error.value = requestError?.message || '网络异常，请稍后重试'
  } finally {
    if (seq === requestSeq) loading.value = false
  }
}

function searchBars() {
  appliedKeyword.value = searchText.value.trim()
  loadBars()
}

function clearSearch() {
  searchText.value = ''
  appliedKeyword.value = ''
  loadBars()
}

function requireLogin() {
  if (session.token) return true
  router.push({ path: '/login', query: { redirect: route.fullPath } })
  return false
}

async function toggleFollow(bar) {
  actionError.value = ''
  if (!requireLogin() || pendingFollows[bar.id]) return

  pendingFollows[bar.id] = true
  const target = !bar.followed
  try {
    const result = await api.followBar(bar.id, target)
    bar.followed = typeof result?.followed === 'boolean' ? result.followed : target
    if (Number.isFinite(Number(result?.followCount))) {
      bar.followCount = Math.max(0, Number(result.followCount))
    }
    if (result?.members !== undefined) bar.members = result.members
  } catch (requestError) {
    actionError.value = requestError?.message || '关注操作失败，请稍后重试'
  } finally {
    delete pendingFollows[bar.id]
  }
}

onMounted(loadBars)
</script>

<style scoped>
.bars-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.bars-hero {
  position: relative;
  overflow: hidden;
  padding: 28px 28px 24px;
  border: 1px solid #e6ecf6;
  border-radius: 18px;
  background: #ffffff;
}

.hero-copy {
  position: relative;
  z-index: 1;
  max-width: 520px;
}

.hero-eyebrow,
.heading-kicker {
  display: block;
  color: #246bfd;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.14em;
  line-height: 1.5;
}

.hero-copy h1 {
  margin: 8px 0 0;
  color: #17243b;
  font-size: 27px;
  font-weight: 750;
  letter-spacing: -0.02em;
  line-height: 1.35;
}

.hero-copy p {
  margin: 8px 0 0;
  color: #6e7d93;
  font-size: 13px;
  line-height: 1.75;
}

.hero-decoration {
  position: absolute;
  top: -58px;
  right: -25px;
  width: 180px;
  height: 180px;
  border: 1px solid #e5edfb;
  border-radius: 50%;
}

.hero-decoration::before,
.hero-decoration::after {
  position: absolute;
  border: 1px solid #edf2fb;
  border-radius: 50%;
  content: "";
}

.hero-decoration::before {
  inset: 24px;
}

.hero-decoration::after {
  inset: 49px;
}

.bar-search {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  width: min(100%, 560px);
  height: 42px;
  margin-top: 20px;
  padding: 0 5px 0 13px;
  border: 1px solid #dfe7f3;
  border-radius: 9px;
  background: #f9fbfe;
  color: #8a98ad;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.bar-search:focus-within {
  border-color: #9dbcfb;
  box-shadow: 0 0 0 3px rgba(36, 107, 253, 0.08);
}

.bar-search input {
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

.bar-search input::placeholder {
  color: #a3afc0;
}

.clear-search {
  padding: 0 6px;
  border: 0;
  background: transparent;
  color: #8b99ad;
  font: inherit;
  font-size: 11px;
  cursor: pointer;
}

.search-button {
  height: 32px;
  padding: 0 15px;
  border: 0;
  border-radius: 7px;
  background: #246bfd;
  color: #ffffff;
  font: inherit;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}

.list-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding: 3px 3px 0;
}

.heading-copy h2 {
  margin: 4px 0 0;
  color: #26354c;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.45;
}

.bar-count {
  color: #96a3b6;
  font-size: 11px;
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

.bar-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.bar-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e7ecf5;
  border-radius: 14px;
  background: #ffffff;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.bar-card:hover {
  border-color: #dbe5f5;
  box-shadow: 0 8px 24px rgba(31, 69, 128, 0.07);
}

.bar-main {
  display: flex;
  align-items: flex-start;
  min-width: 0;
  gap: 12px;
  flex: 1;
  padding: 17px 17px 14px;
  color: inherit;
  text-decoration: none;
}

.bar-avatar {
  position: relative;
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  flex: 0 0 48px;
  overflow: hidden;
  border: 1px solid #e5edfb;
  border-radius: 13px;
  background: #eef4ff;
  color: #246bfd;
  font-size: 17px;
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

.bar-copy {
  display: block;
  min-width: 0;
  flex: 1;
}

.bar-name-row {
  display: flex;
  align-items: baseline;
  min-width: 0;
  gap: 8px;
}

.bar-name {
  overflow: hidden;
  color: #17243b;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-main:hover .bar-name {
  color: #246bfd;
}

.bar-owner {
  overflow: hidden;
  flex: 0 0 auto;
  max-width: 88px;
  color: #9aa7b9;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-desc {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 4px;
  color: #7b899e;
  font-size: 11px;
  line-height: 1.65;
  white-space: normal;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.bar-stats {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  color: #93a0b3;
  font-size: 10px;
}

.bar-stats strong {
  color: #5d6d83;
  font-weight: 650;
}

.stat-dot {
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: #c4ccd8;
}

.bar-arrow {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  flex: 0 0 24px;
  margin-top: 2px;
  border-radius: 50%;
  color: #a6b2c2;
  transition: color 0.16s ease, background 0.16s ease;
}

.bar-main:hover .bar-arrow {
  background: #eef4ff;
  color: #246bfd;
}

.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 0 17px;
  padding: 9px 0 11px;
  border-top: 1px solid #f0f3f8;
}

.foot-note {
  color: #a0acbc;
  font-size: 10px;
}

.follow-button {
  height: 28px;
  min-width: 64px;
  padding: 0 10px;
  border: 1px solid #cfdeff;
  border-radius: 7px;
  background: #f4f8ff;
  color: #246bfd;
  font: inherit;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease, border-color 0.16s ease;
}

.follow-button:hover:not(:disabled) {
  border-color: #a9c4ff;
  background: #eaf2ff;
}

.follow-button.followed {
  border-color: #e5ebf5;
  background: #f6f8fb;
  color: #7c8ba0;
}

.follow-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.bar-skeleton {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 17px;
  border: 1px solid #e7ecf5;
  border-radius: 14px;
  background: #ffffff;
}

.skeleton-logo {
  width: 48px;
  height: 48px;
  flex: 0 0 48px;
  border-radius: 13px;
  background: #eef2f8;
  animation: soft-pulse 1.5s ease-in-out infinite;
}

.skeleton-copy {
  min-width: 0;
  flex: 1;
}

.skeleton-line {
  height: 9px;
  margin-top: 8px;
  border-radius: 5px;
  background: #eef2f8;
  animation: soft-pulse 1.5s ease-in-out infinite;
}

.skeleton-line:first-child {
  margin-top: 2px;
}

.skeleton-name {
  width: 34%;
  height: 13px;
}

.skeleton-desc {
  width: 72%;
}

.loading-note {
  grid-column: 1 / -1;
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

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  padding: 0 14px;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
}

@media (max-width: 820px) {
  .bar-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .bars-hero {
    padding: 22px 20px;
  }

  .hero-copy h1 {
    font-size: 23px;
  }
}
</style>
