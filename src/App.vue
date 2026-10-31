<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import Icon from './components/Icon.vue'
import { api, imageUrl } from './api'
import { clearSession, session, updateUser } from './session'

const route = useRoute()
const router = useRouter()
const isAuthPage = computed(() => route.path === '/login' || route.path === '/register')

/* --------------------------------------------------------------------------
   搜索
   -------------------------------------------------------------------------- */

const searchInput = ref(null)
const keyword = ref('')

function submitSearch() {
  const term = keyword.value.trim()
  if (!term) {
    searchInput.value?.focus()
    return
  }
  if (route.path === '/search' && String(route.query.q || '').trim() === term) return
  router.push({ path: '/search', query: { q: term } })
}

function onSearchEscape() {
  if (keyword.value) {
    keyword.value = ''
  } else {
    searchInput.value?.blur()
  }
}

watch(
  () => route.query.q,
  (value) => {
    if (route.path !== '/search') return
    const q = Array.isArray(value) ? value[0] : value
    keyword.value = typeof q === 'string' ? q : ''
  },
  { immediate: true }
)

/* --------------------------------------------------------------------------
   导航与登录入口
   -------------------------------------------------------------------------- */

const navItems = [
  { key: 'home', label: '首页', to: '/', icon: 'home', isActive: (path) => path === '/' },
  {
    key: 'bars',
    label: '发现贴吧',
    to: '/bars',
    icon: 'compass',
    isActive: (path) => path === '/bars' || path.startsWith('/bars/')
  },
  {
    key: 'favorites',
    label: '我的收藏',
    to: '/favorites',
    icon: 'bookmark',
    isActive: (path) => path === '/favorites'
  },
  {
    key: 'messages',
    label: '消息',
    to: '/messages',
    icon: 'bell',
    isActive: (path) => path === '/messages'
  },
  {
    key: 'my-posts',
    label: '我的帖子',
    to: '/my-posts',
    icon: 'user',
    isActive: (path) => path === '/my-posts'
  }
]

const loginTo = computed(() => {
  if (route.path === '/login' || route.path === '/register') return { path: '/login' }
  return { path: '/login', query: { redirect: route.fullPath } }
})

const registerTo = computed(() => {
  if (route.path === '/login' || route.path === '/register') return { path: '/register' }
  return { path: '/register', query: { redirect: route.fullPath } }
})

const protectedPrefixes = ['/publish', '/messages', '/account', '/favorites', '/my-posts']

function isProtectedPath(path) {
  return protectedPrefixes.some((prefix) => path === prefix || path.startsWith(`${prefix}/`))
}

/* --------------------------------------------------------------------------
   窄屏侧栏抽屉
   -------------------------------------------------------------------------- */

function mediaMatches(query) {
  return typeof window !== 'undefined' && window.matchMedia(query).matches
}

const narrowLeft = ref(mediaMatches('(max-width: 920px)'))
const narrowRight = ref(mediaMatches('(max-width: 1180px)'))
const activeDrawer = ref(null)

const leftDrawerOpen = computed(() => activeDrawer.value === 'left')
const rightDrawerOpen = computed(() => activeDrawer.value === 'right')
const anyDrawerOpen = computed(() => activeDrawer.value !== null)

const leftTriggerRef = ref(null)
const rightTriggerRef = ref(null)
const leftAsideRef = ref(null)
const rightAsideRef = ref(null)
const leftCloseRef = ref(null)
const rightCloseRef = ref(null)

let leftMediaQuery = null
let rightMediaQuery = null

function drawerCloseButton(side) {
  return side === 'left' ? leftCloseRef.value : rightCloseRef.value
}

function drawerTrigger(side) {
  return side === 'left' ? leftTriggerRef.value : rightTriggerRef.value
}

function openDrawer(side) {
  if (side === 'left' && !narrowLeft.value) return
  if (side === 'right' && !narrowRight.value) return
  activeDrawer.value = side
  closeUserMenu()
  nextTick(() => drawerCloseButton(side)?.focus())
}

function closeDrawer(restoreFocus = true) {
  const side = activeDrawer.value
  if (!side) return
  activeDrawer.value = null
  if (restoreFocus) {
    nextTick(() => drawerTrigger(side)?.focus())
  }
}

function toggleDrawer(side) {
  if (activeDrawer.value === side) {
    closeDrawer(true)
  } else {
    openDrawer(side)
  }
}

function onDrawerLinkClick(event) {
  if (!anyDrawerOpen.value) return
  if (event.target instanceof Element && event.target.closest('a')) {
    closeDrawer(true)
  }
}

function drawerFocusables(root) {
  const selector =
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  return Array.from(root.querySelectorAll(selector)).filter(
    (element) => element.getClientRects().length > 0
  )
}

function onDocumentKeydown(event) {
  if (!anyDrawerOpen.value) return

  if (event.key === 'Escape') {
    event.preventDefault()
    closeDrawer(true)
    return
  }

  if (event.key !== 'Tab') return

  const root = activeDrawer.value === 'left' ? leftAsideRef.value : rightAsideRef.value
  if (!root) return
  const focusables = drawerFocusables(root)
  if (!focusables.length) {
    event.preventDefault()
    return
  }

  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  const current = document.activeElement
  const index = focusables.indexOf(current)
  // 焦点不在可 Tab 元素列表中（含抽屉自身 tabindex="-1"）时按边界处理
  const outside = !root.contains(current) || index === -1

  if (event.shiftKey) {
    if (outside || current === first) {
      event.preventDefault()
      last.focus()
    }
  } else if (outside || current === last) {
    event.preventDefault()
    first.focus()
  }
}

function onLeftMediaChange(event) {
  narrowLeft.value = event.matches
  if (!event.matches && activeDrawer.value === 'left') closeDrawer(false)
}

function onRightMediaChange(event) {
  narrowRight.value = event.matches
  if (!event.matches && activeDrawer.value === 'right') closeDrawer(false)
}

let savedBodyOverflow = ''
let bodyOverflowLocked = false

watch(anyDrawerOpen, (open) => {
  if (open) {
    if (!bodyOverflowLocked) {
      savedBodyOverflow = document.body.style.overflow
      bodyOverflowLocked = true
    }
    document.body.style.overflow = 'hidden'
  } else if (bodyOverflowLocked) {
    document.body.style.overflow = savedBodyOverflow
    bodyOverflowLocked = false
  }
})

/* --------------------------------------------------------------------------
   账户、会话校验与未读角标
   -------------------------------------------------------------------------- */

const sessionCheckDone = ref(!session.token)
const avatarBroken = ref(false)
const menuOpen = ref(false)
const userMenuRef = ref(null)
const userTriggerRef = ref(null)
const unread = ref(0)

const displayName = computed(
  () => session.user?.nickname?.trim() || session.user?.username?.trim() || '社区用户'
)
const username = computed(() => session.user?.username || '')
const userAvatar = computed(() => (session.user?.avatar ? imageUrl(session.user.avatar) : ''))
const userInitial = computed(() => initialOf(displayName.value, 'U'))
const unreadText = computed(() => (unread.value > 99 ? '99+' : String(unread.value)))

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const currentYear = new Date().getFullYear()

watch(
  () => [session.user?.id, session.user?.avatar],
  () => {
    avatarBroken.value = false
  }
)

function toggleUserMenu() {
  if (!session.user) return
  menuOpen.value = !menuOpen.value
}

function closeUserMenu(restoreFocus = false) {
  menuOpen.value = false
  if (restoreFocus) {
    nextTick(() => userTriggerRef.value?.focus())
  }
}

function onMenuKeydown(event) {
  if (event.key === 'Escape' && menuOpen.value) {
    event.stopPropagation()
    closeUserMenu(true)
  }
}

function onDocumentPointerDown(event) {
  if (!menuOpen.value) return
  const root = userMenuRef.value
  if (root && event.target instanceof Node && !root.contains(event.target)) {
    menuOpen.value = false
  }
}

function onAvatarError() {
  avatarBroken.value = true
}

function onLogout() {
  closeUserMenu()
  clearSession()
  if (isProtectedPath(route.path) || route.name === 'post-edit') router.replace('/')
}

let validatingToken = ''

async function validateSession() {
  const token = session.token
  if (!token || validatingToken === token) return
  validatingToken = token
  try {
    const currentUser = await api.me()
    if (currentUser && session.token === token) updateUser(currentUser)
  } catch {
    // 401 已由 api.js 清除 session；网络异常时保留本地缓存，不自动重试，避免请求循环。
  } finally {
    if (validatingToken === token) {
      validatingToken = ''
      sessionCheckDone.value = true
    }
  }
}

let unreadSeq = 0

async function loadUnread() {
  const token = session.token
  if (!token) {
    unread.value = 0
    return
  }
  const seq = ++unreadSeq
  try {
    const data = await api.unread()
    if (seq !== unreadSeq || session.token !== token) return
    const raw =
      typeof data === 'number' ? data : Number(data?.unreadCount ?? data?.count ?? 0)
    unread.value = Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : 0
  } catch {
    // 角标失败时静默隐藏，不阻塞任何页面，也不触发重试循环。
    if (seq === unreadSeq && session.token === token) unread.value = 0
  }
}

let unreadRefreshTimer = null

watch(
  () => route.fullPath,
  (to, from) => {
    menuOpen.value = false
    closeDrawer(false)
    if (!session.token) return
    const isMessages = (path) => path === '/messages' || path.startsWith('/messages?')
    if (isMessages(to) || (from && isMessages(from))) {
      clearTimeout(unreadRefreshTimer)
      unreadRefreshTimer = setTimeout(() => loadUnread(), 800)
    }
  }
)

/* --------------------------------------------------------------------------
   右栏与左栏真实数据
   -------------------------------------------------------------------------- */

const hotBars = ref([])
const hotBarsLoading = ref(true)
const hotBarsError = ref('')
const hotWords = ref([])
const hotWordsLoading = ref(true)
const hotWordsError = ref('')
const followedBars = ref([])
const followedLoading = ref(Boolean(session.token))
const followedError = ref('')
const failedBarImages = ref(new Set())

function toErrorMessage(error, fallback) {
  if (typeof error === 'string' && error.trim()) return error.trim()
  if (error && typeof error.message === 'string' && error.message.trim()) {
    return error.message.trim()
  }
  return fallback
}

function formatCount(value) {
  const count = Number(value)
  if (!Number.isFinite(count) || count < 0) return ''
  if (count >= 100000000) {
    return `${(count / 100000000).toFixed(1).replace(/\.0$/, '')}亿`
  }
  if (count >= 10000) {
    return `${(count / 10000).toFixed(1).replace(/\.0$/, '')}万`
  }
  return String(Math.floor(count))
}

function barFollowLabel(bar) {
  const memberText = bar?.members == null ? '' : String(bar.members).trim()
  if (memberText) return `${memberText} 关注`
  if (Number.isFinite(Number(bar?.followCount))) {
    return `${formatCount(bar.followCount)} 关注`
  }
  return ''
}

function initialOf(value, fallback = '·') {
  const chars = Array.from(String(value ?? '').trim())
  return chars[0] || fallback
}

function barInitial(bar) {
  return initialOf(bar?.name, '吧')
}

function barImage(bar) {
  if (!bar || bar.id == null || !bar.img) return ''
  if (failedBarImages.value.has(bar.id)) return ''
  return imageUrl(bar.img) || ''
}

function onBarImageError(id) {
  const next = new Set(failedBarImages.value)
  next.add(id)
  failedBarImages.value = next
}

function rankLabel(index) {
  return String(index + 1).padStart(2, '0')
}

async function loadHotBars() {
  hotBarsLoading.value = true
  hotBarsError.value = ''
  try {
    const data = await api.bars()
    const list = Array.isArray(data) ? data.filter((bar) => bar && bar.id != null) : []
    hotBars.value = list
      .slice()
      .sort((a, b) => (Number(b.followCount) || 0) - (Number(a.followCount) || 0))
      .slice(0, 6)
  } catch (error) {
    hotBars.value = []
    hotBarsError.value = toErrorMessage(error, '热门贴吧加载失败，请稍后重试')
  } finally {
    hotBarsLoading.value = false
  }
}

async function loadHotSearch() {
  hotWordsLoading.value = true
  hotWordsError.value = ''
  try {
    const data = await api.hotSearch()
    const raw = Array.isArray(data?.keywords) ? data.keywords : Array.isArray(data) ? data : []
    hotWords.value = raw
      .map((word) => (typeof word === 'string' ? word.trim() : ''))
      .filter(Boolean)
      .slice(0, 8)
  } catch (error) {
    hotWords.value = []
    hotWordsError.value = toErrorMessage(error, '热门搜索加载失败，请稍后重试')
  } finally {
    hotWordsLoading.value = false
  }
}

let followedSeq = 0

async function loadFollowedBars() {
  const token = session.token
  const seq = ++followedSeq
  if (!token) {
    followedBars.value = []
    followedError.value = ''
    followedLoading.value = false
    return
  }
  followedLoading.value = true
  followedError.value = ''
  try {
    const data = await api.followedBars()
    if (seq !== followedSeq || session.token !== token) return
    followedBars.value = Array.isArray(data)
      ? data.filter((bar) => bar && bar.id != null).slice(0, 6)
      : []
  } catch (error) {
    if (seq !== followedSeq || session.token !== token) return
    followedBars.value = []
    followedError.value = toErrorMessage(error, '关注的吧加载失败')
  } finally {
    if (seq === followedSeq) followedLoading.value = false
  }
}

watch(
  () => session.token,
  (token) => {
    if (token) {
      sessionCheckDone.value = false
      validateSession()
      loadUnread()
      loadFollowedBars()
    } else {
      sessionCheckDone.value = true
      followedBars.value = []
      followedError.value = ''
      followedLoading.value = false
      unread.value = 0
      menuOpen.value = false
    }
  }
)

/* --------------------------------------------------------------------------
   生命周期与跨组件刷新
   -------------------------------------------------------------------------- */

function onNotificationsRead() {
  loadUnread()
}

function onBarsChanged() {
  loadFollowedBars()
  loadHotBars()
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
  document.addEventListener('keydown', onDocumentKeydown)
  window.addEventListener('bbs:notifications-read', onNotificationsRead)
  window.addEventListener('bbs:bars-changed', onBarsChanged)

  leftMediaQuery = window.matchMedia('(max-width: 920px)')
  rightMediaQuery = window.matchMedia('(max-width: 1180px)')
  narrowLeft.value = leftMediaQuery.matches
  narrowRight.value = rightMediaQuery.matches
  leftMediaQuery.addEventListener('change', onLeftMediaChange)
  rightMediaQuery.addEventListener('change', onRightMediaChange)

  loadHotBars()
  loadHotSearch()
  if (session.token) {
    validateSession()
    loadUnread()
    loadFollowedBars()
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  document.removeEventListener('keydown', onDocumentKeydown)
  window.removeEventListener('bbs:notifications-read', onNotificationsRead)
  window.removeEventListener('bbs:bars-changed', onBarsChanged)
  leftMediaQuery?.removeEventListener('change', onLeftMediaChange)
  rightMediaQuery?.removeEventListener('change', onRightMediaChange)
  clearTimeout(unreadRefreshTimer)
  if (bodyOverflowLocked) {
    document.body.style.overflow = savedBodyOverflow
    bodyOverflowLocked = false
  }
})
</script>

<template>
  <div class="page-app">
    <a class="skip-link" href="#main-content" :inert="anyDrawerOpen">跳到主要内容</a>

    <header class="site-header" :inert="anyDrawerOpen">
      <div class="header-inner">
        <RouterLink class="brand" to="/" aria-label="BBS 社区首页">
          <span class="brand-mark" aria-hidden="true"><Icon name="chat" :size="20" /></span>
          <span class="brand-word">BBS<span class="brand-dot">.</span></span>
          <span class="brand-sub">同好社区</span>
        </RouterLink>

        <form class="site-search" role="search" aria-label="全站搜索" @submit.prevent="submitSearch">
          <Icon name="search" :size="18" class="search-leading" />
          <input
            ref="searchInput"
            v-model="keyword"
            type="search"
            maxlength="60"
            autocomplete="off"
            enterkeyhint="search"
            aria-label="搜索关键词"
            placeholder="搜索帖子、贴吧或话题"
            @keydown.esc.prevent="onSearchEscape"
          />
          <button class="search-submit" type="submit" aria-label="搜索" title="搜索">
            <Icon name="arrow" :size="17" />
          </button>
        </form>

        <div class="header-actions">
          <button
            v-if="!isAuthPage && narrowLeft"
            ref="leftTriggerRef"
            class="header-tool"
            type="button"
            aria-controls="left-sidebar"
            :aria-expanded="leftDrawerOpen"
            :aria-label="leftDrawerOpen ? '关闭社区导航菜单' : '打开社区导航菜单'"
            @click="toggleDrawer('left')"
          >
            <Icon name="menu" :size="18" />
            <span>菜单</span>
          </button>

          <button
            v-if="!isAuthPage && narrowRight"
            ref="rightTriggerRef"
            class="header-tool"
            type="button"
            aria-controls="right-sidebar"
            :aria-expanded="rightDrawerOpen"
            :aria-label="rightDrawerOpen ? '关闭发现侧栏' : '打开发现侧栏'"
            @click="toggleDrawer('right')"
          >
            <Icon name="compass" :size="18" />
            <span>发现</span>
          </button>

          <RouterLink
            class="btn btn-primary publish-btn"
            to="/publish"
            aria-label="发布帖子"
            title="发布帖子"
          >
            <Icon name="edit" :size="17" />
            <span>发布</span>
          </RouterLink>

          <div v-if="session.user" ref="userMenuRef" class="user-menu" @keydown="onMenuKeydown">
            <button
              ref="userTriggerRef"
              class="user-trigger"
              type="button"
              aria-haspopup="true"
              aria-controls="user-dropdown"
              :aria-expanded="menuOpen"
              :aria-label="`账户菜单，${displayName}`"
              @click="toggleUserMenu"
            >
              <span class="avatar user-avatar" aria-hidden="true">
                <img
                  v-if="userAvatar && !avatarBroken"
                  :src="userAvatar"
                  alt=""
                  @error="onAvatarError"
                />
                <span v-else>{{ userInitial }}</span>
              </span>
              <span class="user-name">{{ displayName }}</span>
              <Icon
                name="chevron"
                :size="15"
                class="user-chevron"
                :class="{ 'is-open': menuOpen }"
              />
            </button>

            <Transition name="menu">
              <div v-if="menuOpen" id="user-dropdown" class="user-dropdown">
                <div class="dropdown-head">
                  <p class="dropdown-name">{{ displayName }}</p>
                  <p v-if="username" class="dropdown-handle">@{{ username }}</p>
                </div>
                <RouterLink class="dropdown-item" to="/account" @click="closeUserMenu()">
                  <Icon name="user" :size="16" />
                  <span>个人中心</span>
                </RouterLink>
                <RouterLink class="dropdown-item" to="/my-posts" @click="closeUserMenu()">
                  <Icon name="grid" :size="16" />
                  <span>我的帖子</span>
                </RouterLink>
                <RouterLink class="dropdown-item" to="/favorites" @click="closeUserMenu()">
                  <Icon name="bookmark" :size="16" />
                  <span>我的收藏</span>
                </RouterLink>
                <div class="dropdown-divider" role="separator"></div>
                <button class="dropdown-item dropdown-danger" type="button" @click="onLogout">
                  <Icon name="logout" :size="16" />
                  <span>退出登录</span>
                </button>
              </div>
            </Transition>
          </div>

          <RouterLink
            v-else-if="!session.token || sessionCheckDone"
            class="btn btn-ghost header-login"
            :to="loginTo"
            aria-label="登录"
          >
            <Icon name="user" :size="17" />
            <span>登录</span>
          </RouterLink>

          <div v-else class="header-avatar-pending" role="status" aria-label="正在恢复登录状态">
            <span class="skeleton header-avatar-skeleton" aria-hidden="true"></span>
          </div>
        </div>
      </div>
    </header>

    <div v-if="anyDrawerOpen" class="drawer-backdrop" aria-hidden="true" @click="closeDrawer(true)"></div>

    <div class="shell">
      <div class="layout" :class="{ 'layout-auth': isAuthPage }">
        <aside
          v-if="!isAuthPage"
          id="left-sidebar"
          ref="leftAsideRef"
          class="sidebar sidebar-left"
          :class="{ 'drawer-open': leftDrawerOpen }"
          aria-label="社区导航"
          :role="leftDrawerOpen ? 'dialog' : undefined"
          :aria-modal="leftDrawerOpen ? 'true' : undefined"
          :aria-labelledby="leftDrawerOpen ? 'left-drawer-title' : undefined"
          :inert="anyDrawerOpen && !leftDrawerOpen"
          :tabindex="leftDrawerOpen ? '-1' : undefined"
          @click="onDrawerLinkClick"
        >
          <div class="drawer-head">
            <h2 id="left-drawer-title" class="drawer-title">社区导航</h2>
            <button
              ref="leftCloseRef"
              class="drawer-close"
              type="button"
              aria-label="关闭菜单"
              @click="closeDrawer(true)"
            >
              <Icon name="close" :size="18" />
            </button>
          </div>

          <nav class="panel nav-panel" aria-label="主导航">
            <p class="eyebrow nav-eyebrow">浏览</p>
            <RouterLink
              v-for="item in navItems"
              :key="item.key"
              :to="item.to"
              class="nav-link"
              :class="{ active: item.isActive(route.path) }"
              :aria-current="item.isActive(route.path) ? 'page' : undefined"
            >
              <span class="nav-icon"><Icon :name="item.icon" :size="18" /></span>
              <span class="nav-label">{{ item.label }}</span>
              <template v-if="item.key === 'messages' && unread > 0">
                <span class="nav-badge" aria-hidden="true">{{ unreadText }}</span>
                <span class="sr-only">，{{ unread }} 条未读</span>
              </template>
            </RouterLink>
          </nav>

          <section class="panel followed-panel" aria-labelledby="followed-title" :aria-busy="followedLoading">
            <div class="side-head">
              <h2 id="followed-title" class="side-title">我关注的吧</h2>
              <RouterLink v-if="session.user" class="side-more" to="/bars">全部</RouterLink>
            </div>

            <template v-if="!session.token && !session.user">
              <p class="side-empty">登录后，这里会显示你关注的吧。</p>
              <RouterLink class="side-login" :to="loginTo">
                <Icon name="user" :size="14" />
                <span>登录查看</span>
              </RouterLink>
            </template>

            <div
              v-else-if="followedLoading"
              class="side-loading"
              role="status"
              aria-live="polite"
            >
              <span class="sr-only">正在加载关注的贴吧</span>
              <div v-for="n in 3" :key="n" class="skeleton-row" aria-hidden="true">
                <span class="skeleton sk-avatar"></span>
                <span class="sk-lines">
                  <span class="skeleton sk-line"></span>
                  <span class="skeleton sk-line short"></span>
                </span>
              </div>
            </div>

            <div v-else-if="followedError" class="side-error" role="alert">
              <p class="side-error-text" :title="followedError">{{ followedError }}</p>
              <button class="side-retry" type="button" @click="loadFollowedBars">
                <Icon name="refresh" :size="13" />
                <span>重试</span>
              </button>
            </div>

            <div v-else-if="!followedBars.length" class="side-empty-block">
              <p class="side-empty">还没有关注的贴吧。</p>
              <RouterLink class="side-text-link" to="/bars">去发现感兴趣的吧</RouterLink>
            </div>

            <ul v-else class="followed-list">
              <li v-for="bar in followedBars" :key="bar.id">
                <RouterLink class="followed-item" :to="`/bars/${bar.id}`">
                  <span class="bar-thumb" aria-hidden="true">
                    <img
                      v-if="barImage(bar)"
                      :src="barImage(bar)"
                      alt=""
                      loading="lazy"
                      @error="onBarImageError(bar.id)"
                    />
                    <span v-else>{{ barInitial(bar) }}</span>
                  </span>
                  <span class="followed-name">{{ bar.name }}</span>
                  <span v-if="barFollowLabel(bar)" class="followed-count">{{ barFollowLabel(bar) }}</span>
                </RouterLink>
              </li>
            </ul>
          </section>

          <RouterLink class="support-card" to="/support">
            <span class="support-icon" aria-hidden="true"><Icon name="help" :size="18" /></span>
            <span class="support-text">
              <strong>帮助与客服</strong>
              <small>使用问题与社区反馈</small>
            </span>
            <Icon name="chevron" :size="15" class="support-arrow" />
          </RouterLink>
        </aside>

        <main
          id="main-content"
          class="main-column"
          tabindex="-1"
          aria-label="主要内容"
          :inert="anyDrawerOpen"
        >
          <RouterView />
        </main>

        <aside
          v-if="!isAuthPage"
          id="right-sidebar"
          ref="rightAsideRef"
          class="sidebar sidebar-right"
          :class="{ 'drawer-open': rightDrawerOpen }"
          aria-label="社区推荐"
          :role="rightDrawerOpen ? 'dialog' : undefined"
          :aria-modal="rightDrawerOpen ? 'true' : undefined"
          :aria-labelledby="rightDrawerOpen ? 'right-drawer-title' : undefined"
          :inert="anyDrawerOpen && !rightDrawerOpen"
          :tabindex="rightDrawerOpen ? '-1' : undefined"
          @click="onDrawerLinkClick"
        >
          <div class="drawer-head">
            <h2 id="right-drawer-title" class="drawer-title">发现</h2>
            <button
              ref="rightCloseRef"
              class="drawer-close"
              type="button"
              aria-label="关闭发现侧栏"
              @click="closeDrawer(true)"
            >
              <Icon name="close" :size="18" />
            </button>
          </div>

          <section v-if="session.user" class="welcome-card" aria-labelledby="welcome-name">
            <div class="welcome-user">
              <span class="avatar welcome-avatar" aria-hidden="true">
                <img
                  v-if="userAvatar && !avatarBroken"
                  :src="userAvatar"
                  alt=""
                  @error="onAvatarError"
                />
                <span v-else>{{ userInitial }}</span>
              </span>
              <div class="welcome-identity">
                <h2 id="welcome-name" class="welcome-name">{{ displayName }}</h2>
                <p v-if="username" class="welcome-handle">@{{ username }}</p>
              </div>
            </div>
            <p class="welcome-copy">{{ greeting }}，来看看同好们的新鲜讨论。</p>
            <div class="welcome-actions">
              <RouterLink class="btn btn-primary" to="/publish">
                <Icon name="edit" :size="15" />
                <span>发帖</span>
              </RouterLink>
              <RouterLink class="btn btn-ghost" to="/account">
                <span>个人中心</span>
              </RouterLink>
            </div>
          </section>

          <section
            v-else-if="session.token && !sessionCheckDone"
            class="welcome-card welcome-pending"
            aria-busy="true"
          >
            <span class="sr-only">正在恢复登录状态</span>
            <div class="welcome-user">
              <span class="skeleton welcome-avatar-skeleton" aria-hidden="true"></span>
              <span class="sk-lines">
                <span class="skeleton sk-line"></span>
                <span class="skeleton sk-line short"></span>
              </span>
            </div>
            <p class="welcome-copy">正在恢复登录状态…</p>
          </section>

          <section v-else class="welcome-card" aria-labelledby="welcome-title">
            <p class="eyebrow">欢迎来到 BBS</p>
            <h2 id="welcome-title" class="welcome-title">和同好，聊点真的</h2>
            <p class="welcome-copy">登录后关注感兴趣的贴吧，收藏好帖，收到每一条真实的回复。</p>
            <div class="welcome-actions">
              <RouterLink class="btn btn-primary" :to="loginTo">
                <span>登录</span>
              </RouterLink>
              <RouterLink class="btn btn-ghost" :to="registerTo">
                <span>注册</span>
              </RouterLink>
            </div>
          </section>

          <section class="panel aside-card" aria-labelledby="hot-bars-title" :aria-busy="hotBarsLoading">
            <div class="aside-head">
              <h2 id="hot-bars-title" class="aside-title">热门贴吧</h2>
              <RouterLink class="aside-link" to="/bars">全部</RouterLink>
            </div>

            <div v-if="hotBarsLoading" class="aside-loading" role="status" aria-live="polite">
              <span class="sr-only">正在加载热门贴吧</span>
              <div v-for="n in 4" :key="n" class="skeleton-row" aria-hidden="true">
                <span class="skeleton sk-rank"></span>
                <span class="skeleton sk-avatar"></span>
                <span class="sk-lines">
                  <span class="skeleton sk-line"></span>
                  <span class="skeleton sk-line short"></span>
                </span>
              </div>
            </div>

            <div v-else-if="hotBarsError" class="aside-error" role="alert">
              <p class="aside-error-text" :title="hotBarsError">{{ hotBarsError }}</p>
              <button class="side-retry" type="button" @click="loadHotBars">
                <Icon name="refresh" :size="13" />
                <span>重试</span>
              </button>
            </div>

            <p v-else-if="!hotBars.length" class="aside-note">暂时还没有可展示的贴吧。</p>

            <ol v-else class="hotbar-list">
              <li v-for="(bar, index) in hotBars" :key="bar.id">
                <RouterLink class="hotbar-item" :to="`/bars/${bar.id}`">
                  <span class="hotbar-rank" :class="{ 'is-top': index < 3 }">{{ rankLabel(index) }}</span>
                  <span class="bar-thumb hotbar-thumb" aria-hidden="true">
                    <img
                      v-if="barImage(bar)"
                      :src="barImage(bar)"
                      alt=""
                      loading="lazy"
                      @error="onBarImageError(bar.id)"
                    />
                    <span v-else>{{ barInitial(bar) }}</span>
                  </span>
                  <span class="hotbar-main">
                    <span class="hotbar-name">{{ bar.name }}</span>
                    <span v-if="barFollowLabel(bar)" class="hotbar-stat">{{ barFollowLabel(bar) }}</span>
                  </span>
                </RouterLink>
              </li>
            </ol>
          </section>

          <section class="panel aside-card" aria-labelledby="hot-search-title" :aria-busy="hotWordsLoading">
            <div class="aside-head">
              <h2 id="hot-search-title" class="aside-title">
                <Icon name="fire" :size="14" />
                热门搜索
              </h2>
            </div>

            <div v-if="hotWordsLoading" class="hot-words" role="status" aria-live="polite">
              <span class="sr-only">正在加载热门搜索</span>
              <span
                v-for="n in 5"
                :key="n"
                class="skeleton hot-word-skeleton"
                aria-hidden="true"
              ></span>
            </div>

            <div v-else-if="hotWordsError" class="aside-error" role="alert">
              <p class="aside-error-text" :title="hotWordsError">{{ hotWordsError }}</p>
              <button class="side-retry" type="button" @click="loadHotSearch">
                <Icon name="refresh" :size="13" />
                <span>重试</span>
              </button>
            </div>

            <p v-else-if="!hotWords.length" class="aside-note">暂无热门搜索词。</p>

            <div v-else class="hot-words">
              <RouterLink
                v-for="word in hotWords"
                :key="word"
                class="hot-word"
                :to="{ path: '/search', query: { q: word } }"
              >
                {{ word }}
              </RouterLink>
            </div>
          </section>

          <footer class="aside-footer">
            <nav aria-label="页脚导航">
              <RouterLink to="/bars">发现贴吧</RouterLink>
              <RouterLink to="/support">帮助与客服</RouterLink>
            </nav>
            <p>© {{ currentYear }} BBS 社区</p>
            <p>认真交流，友善表达</p>
          </footer>
        </aside>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ==========================================================================
   外壳
   ========================================================================== */

.page-app {
  min-height: 100vh;
}

.skip-link {
  position: fixed;
  top: -64px;
  left: 16px;
  z-index: 100;
  padding: 10px 14px;
  border-radius: 8px;
  background: var(--ink);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  transition: top 0.16s ease;
}

.skip-link:focus {
  top: 12px;
}

.shell {
  width: 100%;
  max-width: none;
  margin: 0 auto;
  padding: 0 clamp(20px, 2vw, 48px);
}

.drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  background: rgba(15, 23, 42, 0.42);
  backdrop-filter: blur(2px);
}

.layout {
  display: grid;
  grid-template-columns:
    clamp(184px, 12vw, 240px)
    minmax(0, 1fr)
    clamp(268px, 18vw, 340px);
  align-items: start;
  gap: clamp(16px, 1.2vw, 28px);
  padding: 22px 0 56px;
}

.layout.layout-auth {
  grid-template-columns: minmax(0, 1fr);
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
}

.main-column {
  min-width: 0;
  min-height: 70vh;
  outline: none;
}

.layout.layout-auth .main-column {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
}

.sidebar {
  position: sticky;
  top: 86px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-self: start;
  max-height: calc(100vh - 104px);
  padding: 4px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #d6deea transparent;
}

.drawer-head {
  display: none;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 2px 4px 10px;
}

.drawer-title {
  color: var(--ink);
  font-size: 16px;
  font-weight: 750;
  line-height: 1.4;
  letter-spacing: -0.01em;
}

.drawer-close {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  flex: none;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #f7f9fd;
  color: var(--ink-2);
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.drawer-close:hover {
  border-color: #c4d5fb;
  background: var(--brand-soft);
  color: var(--brand-strong);
}

/* ==========================================================================
   顶栏
   ========================================================================== */

.site-header {
  position: sticky;
  top: 0;
  z-index: 50;
  border-bottom: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(12px);
}

.header-inner {
  display: flex;
  align-items: center;
  gap: 20px;
  width: 100%;
  max-width: none;
  height: 64px;
  margin: 0 auto;
  padding: 0 clamp(20px, 2vw, 48px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 132px;
  color: var(--ink);
  text-decoration: none;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  flex: none;
  border-radius: 10px;
  background: var(--brand);
  color: #fff;
  box-shadow: 0 4px 10px rgba(36, 107, 253, 0.24);
}

.brand-word {
  color: var(--brand);
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.045em;
}

.brand-dot {
  color: var(--ink);
}

.brand-sub {
  padding-left: 9px;
  border-left: 1px solid var(--line);
  color: var(--muted);
  font-size: 11px;
  line-height: 1.4;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.site-search {
  display: flex;
  align-items: center;
  flex: 1;
  max-width: 820px;
  min-width: 220px;
  height: 42px;
  padding: 0 5px 0 13px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: #f2f5fa;
  transition: background-color 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}

.site-search:focus-within {
  border-color: var(--brand);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(36, 107, 253, 0.14);
}

.search-leading {
  flex: none;
  color: var(--muted);
}

.site-search input {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 0 8px;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--ink);
  font-size: 14px;
}

.site-search input::-webkit-search-cancel-button {
  -webkit-appearance: none;
}

.search-submit {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: 8px;
  background: var(--brand);
  color: #fff;
  transition: background-color 0.16s ease;
}

.search-submit:hover {
  background: var(--brand-strong);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
  margin-left: auto;
}

.publish-btn {
  height: 40px;
  padding: 0 15px;
  border-radius: 10px;
}

.header-login {
  height: 40px;
  padding: 0 13px;
}

.header-tool {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 40px;
  padding: 0 10px;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  background: var(--surface);
  color: var(--ink-2);
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  transition: background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease;
}

.header-tool:hover,
.header-tool[aria-expanded='true'] {
  border-color: #c4d5fb;
  background: #f7faff;
  color: var(--brand-strong);
}

/* ==========================================================================
   用户菜单
   ========================================================================== */

.user-menu {
  position: relative;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 44px;
  padding: 3px 9px 3px 4px;
  border: 1px solid transparent;
  border-radius: 999px;
  color: var(--ink-2);
  transition: background-color 0.16s ease, border-color 0.16s ease;
}

.user-trigger:hover,
.user-trigger[aria-expanded='true'] {
  border-color: var(--line);
  background: #f5f8fc;
}

.user-avatar {
  width: 32px;
  height: 32px;
  font-size: 12px;
}

.user-name {
  max-width: 96px;
  overflow: hidden;
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-chevron {
  color: var(--muted);
  transform: rotate(90deg);
  transition: transform 0.16s ease;
}

.user-chevron.is-open {
  transform: rotate(-90deg);
}

.user-dropdown {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  z-index: 70;
  width: 230px;
  padding: 6px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--surface);
  box-shadow: 0 16px 40px rgba(23, 36, 59, 0.14);
}

.dropdown-head {
  padding: 10px 10px 9px;
  margin-bottom: 5px;
  border-bottom: 1px solid var(--line);
}

.dropdown-name {
  overflow: hidden;
  color: var(--ink);
  font-size: 13px;
  font-weight: 650;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-handle {
  margin-top: 1px;
  overflow: hidden;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 9px 10px;
  border-radius: 9px;
  color: var(--ink-2);
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.dropdown-item:hover {
  background: #f4f7fc;
  color: var(--ink);
}

.dropdown-divider {
  height: 1px;
  margin: 5px 4px;
  background: var(--line);
}

.dropdown-danger {
  color: #b0453b;
}

.dropdown-danger:hover {
  background: #fff5f4;
  color: #92352d;
}

.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.header-avatar-pending {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
}

.header-avatar-skeleton {
  width: 32px;
  height: 32px;
  border-radius: 50%;
}

/* ==========================================================================
   左栏：导航、关注吧、客服
   ========================================================================== */

.nav-panel {
  padding: 10px;
}

.nav-eyebrow {
  padding: 4px 10px 8px;
  color: var(--muted);
  font-size: 10px;
  letter-spacing: 0.14em;
}

.nav-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 40px;
  padding: 0 10px;
  border-radius: 9px;
  color: var(--ink-2);
  font-size: 14px;
  font-weight: 500;
  transition: background-color 0.16s ease, color 0.16s ease;
}

.nav-link:hover {
  background: #f3f6fb;
  color: var(--ink);
}

.nav-link.active {
  background: var(--brand-soft);
  color: var(--brand-strong);
  font-weight: 650;
}

.nav-link.active::before {
  position: absolute;
  top: 12px;
  left: 0;
  width: 3px;
  height: 18px;
  border-radius: 999px;
  background: var(--brand);
  content: '';
}

.nav-icon {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  flex: none;
}

.nav-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 19px;
  height: 19px;
  padding: 0 5px;
  margin-left: auto;
  border-radius: 999px;
  background: #d13438;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

.followed-panel {
  padding: 16px 12px 12px;
}

.side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 4px 10px;
}

.side-title {
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: 0.01em;
}

.side-more {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.4;
  transition: color 0.15s ease;
}

.side-more:hover {
  color: var(--brand-strong);
}

.followed-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.followed-item {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  padding: 7px 6px;
  border-radius: 8px;
  color: var(--ink-2);
  font-size: 13px;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.followed-item:hover {
  background: #f4f7fc;
  color: var(--ink);
}

.followed-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.followed-count {
  flex: none;
  color: var(--muted);
  font-size: 10px;
  white-space: nowrap;
}

.bar-thumb {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  flex: none;
  overflow: hidden;
  border: 1px solid #e4ebf5;
  border-radius: 7px;
  background: #eef3ff;
  color: var(--brand);
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
}

.bar-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.side-empty {
  padding: 2px 6px 8px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.65;
}

.side-empty-block {
  padding-bottom: 2px;
}

.side-text-link {
  display: inline-block;
  margin: 0 6px;
  color: var(--brand-strong);
  font-size: 12px;
  font-weight: 600;
}

.side-text-link:hover {
  text-decoration: underline;
}

.side-login {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 32px;
  margin: 0 4px 2px;
  border: 1px solid #d9e5ff;
  border-radius: 8px;
  background: #f6faff;
  color: var(--brand-strong);
  font-size: 12px;
  font-weight: 600;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.side-login:hover {
  border-color: #bcd2ff;
  background: var(--brand-soft);
}

.side-loading,
.aside-loading {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 2px 4px;
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 6px 0;
}

.sk-avatar {
  width: 26px;
  height: 26px;
  flex: none;
  border-radius: 7px;
}

.sk-rank {
  width: 16px;
  height: 10px;
  flex: none;
  border-radius: 4px;
}

.sk-lines {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.sk-line {
  width: 78%;
  height: 8px;
  border-radius: 4px;
}

.sk-line.short {
  width: 44%;
}

.skeleton {
  background: #edf1f7;
  animation: app-pulse 1.4s ease-in-out infinite;
}

@keyframes app-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}

.side-error {
  padding: 2px 4px 4px;
}

.side-error-text,
.aside-error-text {
  display: -webkit-box;
  overflow: hidden;
  color: #a84a40;
  font-size: 11.5px;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.side-retry {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  padding: 3px 0;
  color: var(--brand-strong);
  font-size: 12px;
  font-weight: 600;
  line-height: 1.4;
}

.side-retry:hover {
  text-decoration: underline;
}

.support-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 12px;
  border: 1px solid #e2ebff;
  border-radius: 12px;
  background: #f8fbff;
  transition: background-color 0.16s ease, border-color 0.16s ease;
}

.support-card:hover {
  border-color: #c3d5ff;
  background: #f3f8ff;
}

.support-icon {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: 9px;
  background: #e7efff;
  color: var(--brand);
}

.support-text {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.support-text strong {
  color: var(--ink);
  font-size: 12.5px;
  font-weight: 650;
  line-height: 1.4;
}

.support-text small {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.4;
}

.support-arrow {
  flex: none;
  color: var(--muted);
}

/* ==========================================================================
   右栏：欢迎卡、热门贴吧、热门搜索、页脚
   ========================================================================== */

.welcome-card {
  padding: 20px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--surface);
  box-shadow: var(--shadow);
}

.welcome-title {
  margin: 6px 0 8px;
  color: var(--ink);
  font-size: 19px;
  font-weight: 750;
  line-height: 1.35;
  letter-spacing: -0.02em;
}

.welcome-user {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.welcome-avatar {
  width: 40px;
  height: 40px;
}

.welcome-avatar-skeleton {
  width: 40px;
  height: 40px;
  flex: none;
  border-radius: 50%;
}

.welcome-identity {
  min-width: 0;
}

.welcome-name {
  overflow: hidden;
  color: var(--ink);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.welcome-handle {
  overflow: hidden;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.welcome-copy {
  margin-top: 12px;
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.7;
}

.welcome-actions {
  display: flex;
  gap: 8px;
  margin-top: 15px;
}

.welcome-actions .btn {
  flex: 1;
  height: 36px;
  padding: 0 10px;
  font-size: 13px;
}

.welcome-pending .welcome-copy {
  margin-top: 14px;
}

.aside-card {
  padding: 16px;
}

.aside-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.aside-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--ink);
  font-size: 13.5px;
  font-weight: 700;
  line-height: 1.4;
}

.aside-title svg {
  color: var(--brand);
}

.aside-link {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.4;
  transition: color 0.15s ease;
}

.aside-link:hover {
  color: var(--brand-strong);
}

.hotbar-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.hotbar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 7px 5px;
  border-radius: 8px;
  transition: background-color 0.15s ease;
}

.hotbar-item:hover {
  background: #f5f8fd;
}

.hotbar-rank {
  width: 18px;
  flex: none;
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  text-align: center;
}

.hotbar-rank.is-top {
  color: var(--brand-strong);
}

.hotbar-thumb {
  width: 30px;
  height: 30px;
  border-radius: 8px;
}

.hotbar-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.hotbar-name {
  overflow: hidden;
  color: var(--ink);
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hotbar-stat {
  color: var(--muted);
  font-size: 10.5px;
  line-height: 1.4;
}

.aside-loading .skeleton-row {
  padding: 5px 0;
}

.aside-loading .sk-avatar {
  width: 30px;
  height: 30px;
  border-radius: 8px;
}

.aside-error {
  padding: 4px 4px 2px;
}

.aside-note {
  padding: 8px 4px 4px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.65;
}

.hot-words {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.hot-word {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  padding: 6px 10px;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 8px;
  background: #f4f7fb;
  color: #4e5e76;
  font-size: 12px;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.hot-word:hover {
  border-color: #d8e4ff;
  background: var(--brand-soft);
  color: var(--brand-strong);
}

.hot-word-skeleton {
  height: 27px;
  border-radius: 8px;
}

.hot-word-skeleton:nth-child(2) {
  width: 54px;
}

.hot-word-skeleton:nth-child(3) {
  width: 72px;
}

.hot-word-skeleton:nth-child(4) {
  width: 48px;
}

.hot-word-skeleton:nth-child(5) {
  width: 64px;
}

.hot-word-skeleton:nth-child(6) {
  width: 40px;
}

.aside-footer {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 4px 2px 0;
  color: var(--muted);
  font-size: 10.5px;
  line-height: 1.6;
}

.aside-footer nav {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 1px;
}

.aside-footer a {
  transition: color 0.15s ease;
}

.aside-footer a:hover {
  color: var(--brand-strong);
}

/* ==========================================================================
   宽度降级：先降右栏，再降左栏；中栏在窄屏保持阅读宽度，不做手机拉伸
   ========================================================================== */

@media (max-width: 1180px) {
  .layout {
    grid-template-columns: 184px minmax(0, 1fr);
  }

  .sidebar-right {
    display: none;
  }

  .sidebar-right.drawer-open {
    position: fixed;
    top: 0;
    right: 0;
    z-index: 90;
    display: flex;
    width: min(360px, 92vw);
    max-width: 92vw;
    height: 100vh;
    height: 100dvh;
    max-height: 100vh;
    max-height: 100dvh;
    padding: 14px 16px calc(20px + env(safe-area-inset-bottom));
    overflow-y: auto;
    overscroll-behavior: contain;
    border-left: 1px solid var(--line);
    border-radius: 16px 0 0 16px;
    background: var(--surface);
    box-shadow: -24px 0 60px rgba(23, 36, 59, 0.18);
  }

  .sidebar-right.drawer-open .drawer-head {
    display: flex;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--line);
  }
}

@media (max-width: 1020px) {
  .brand {
    min-width: 0;
  }

  .brand-sub {
    display: none;
  }

  .user-name {
    display: none;
  }

  .site-search {
    max-width: none;
  }
}

@media (max-width: 920px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
    padding-top: 18px;
  }

  .sidebar-left {
    display: none;
  }

  .sidebar-left.drawer-open {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 90;
    display: flex;
    width: min(360px, 92vw);
    max-width: 92vw;
    height: 100vh;
    height: 100dvh;
    max-height: 100vh;
    max-height: 100dvh;
    padding: 14px 16px calc(20px + env(safe-area-inset-bottom));
    overflow-y: auto;
    overscroll-behavior: contain;
    border-right: 1px solid var(--line);
    border-radius: 0 16px 16px 0;
    background: var(--surface);
    box-shadow: 24px 0 60px rgba(23, 36, 59, 0.18);
  }

  .sidebar-left.drawer-open .drawer-head {
    display: flex;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--line);
  }

  .main-column {
    width: 100%;
    max-width: 760px;
    margin: 0 auto;
  }
}

@media (max-width: 760px) {
  .header-inner {
    flex-wrap: wrap;
    gap: 10px;
    height: auto;
    min-height: 64px;
    padding: 10px 16px;
  }

  .brand {
    min-width: 0;
  }

  .header-actions {
    margin-left: auto;
  }

  .site-search {
    order: 3;
    flex-basis: 100%;
  }

  .publish-btn {
    width: 40px;
    padding: 0;
  }

  .publish-btn span {
    display: none;
  }

  .shell {
    padding: 0 16px;
  }

  .layout {
    padding-top: 16px;
  }
}

@media (max-width: 480px) {
  .header-inner {
    gap: 6px;
  }

  .brand-word {
    display: none;
  }

  .header-actions {
    gap: 6px;
  }

  .header-tool {
    padding: 0 8px;
    font-size: 12px;
  }

  .header-login {
    width: 40px;
    padding: 0;
  }

  .header-login span {
    display: none;
  }

  .user-trigger {
    padding: 3px;
    gap: 0;
  }

  .user-chevron {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skip-link,
  .header-tool,
  .drawer-close,
  .user-chevron,
  .menu-enter-active,
  .menu-leave-active {
    transition-duration: 0.01ms;
  }

  .skeleton {
    animation: none;
  }
}
</style>
