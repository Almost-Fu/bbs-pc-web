// ---------------------------------------------------------------------------
// 路由（hash 模式：生产静态部署不需要服务器做 history fallback 重写）
//
//   /                 FeedView        首页信息流
//   /search?q=        FeedView        搜索结果（FeedView watch route.fullPath 切换数据源）
//   /favorites        FeedView        我的收藏（需登录）
//   /my-posts         FeedView        我的帖子（需登录）
//   /bars             BarsView        全部贴吧
//   /bars/:id         BarView          吧详情
//   /posts/:id        PostView         帖子详情
//   /posts/:id/edit   PublishView      编辑自己的帖子（需登录，仅作者本人）
//   /publish          PublishView      发帖（需登录，query.barId 可选）
//   /messages         MessagesView     互动消息（需登录）
//   /account          AccountView      我的账号（需登录）
//   /login /register  AuthView         登录 / 注册
//   /support          SupportView      帮助与客服
//
//   守卫：受保护页面未登录 → /login?redirect=原 fullPath。
//   安全：redirect 只接受以 / 开头且不以 //（或 /\）开头的站内路径；
//         进入登录页时若 query.redirect 不合法会被就地剥掉，AuthView 无需再判断。
// ---------------------------------------------------------------------------
import { createRouter, createWebHashHistory } from 'vue-router'
import { session } from './session'

const FeedView = () => import('./views/FeedView.vue')
const BarsView = () => import('./views/BarsView.vue')
const BarView = () => import('./views/BarView.vue')
const PostView = () => import('./views/PostView.vue')
const AuthView = () => import('./views/AuthView.vue')
const PublishView = () => import('./views/PublishView.vue')
const AccountView = () => import('./views/AccountView.vue')
const MessagesView = () => import('./views/MessagesView.vue')
const SupportView = () => import('./views/SupportView.vue')

const routes = [
  { path: '/', name: 'home', component: FeedView, meta: { title: '首页' } },
  { path: '/search', name: 'search', component: FeedView, meta: { title: '搜索' } },
  {
    path: '/favorites',
    name: 'favorites',
    component: FeedView,
    meta: { title: '我的收藏', requiresAuth: true }
  },
  {
    path: '/my-posts',
    name: 'my-posts',
    component: FeedView,
    meta: { title: '我的帖子', requiresAuth: true }
  },
  { path: '/bars', name: 'bars', component: BarsView, meta: { title: '贴吧' } },
  { path: '/bars/:id', name: 'bar', component: BarView, meta: { title: '吧详情' } },
  { path: '/posts/:id', name: 'post', component: PostView, meta: { title: '帖子详情' } },
  {
    path: '/posts/:id/edit',
    name: 'post-edit',
    component: PublishView,
    meta: { title: '编辑帖子', requiresAuth: true }
  },
  {
    path: '/publish',
    name: 'publish',
    component: PublishView,
    meta: { title: '发布帖子', requiresAuth: true }
  },
  {
    path: '/messages',
    name: 'messages',
    component: MessagesView,
    meta: { title: '互动消息', requiresAuth: true }
  },
  {
    path: '/account',
    name: 'account',
    component: AccountView,
    meta: { title: '我的账号', requiresAuth: true }
  },
  { path: '/login', name: 'login', component: AuthView, meta: { title: '登录' } },
  { path: '/register', name: 'register', component: AuthView, meta: { title: '注册' } },
  { path: '/support', name: 'support', component: SupportView, meta: { title: '帮助与客服' } },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

/**
 * 是否是允许的站内跳转地址。
 * 合同要求：以 / 开头，且不能以 // 开头（//evil.com 是协议相对的外站地址）。
 * 额外拒绝 /\evil.com，避免浏览器把反斜杠归一化成 // 后再跳走。
 */
export function isSafeRedirect(value) {
  if (typeof value !== 'string' || !value) return false
  if (!value.startsWith('/')) return false
  if (value.startsWith('//')) return false
  if (value.startsWith('/\\')) return false
  return true
}

/** 不合法时回落到 fallback（默认首页），供 AuthView 登录成功后使用 */
export function safeRedirect(value, fallback = '/') {
  return isSafeRedirect(value) ? value : fallback
}

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

router.beforeEach((to) => {
  // 1) 受保护页面：未登录送回登录页，并带上原地址
  if (to.meta.requiresAuth && !session.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // 2) 登录 / 注册页：把不合法的 redirect 从地址栏剥掉。
  //    这样即使调用方直接 router.push(route.query.redirect)，也只会落到站内。
  if (to.name === 'login' || to.name === 'register') {
    const redirect = to.query.redirect
    if (redirect !== undefined && !isSafeRedirect(redirect)) {
      const query = { ...to.query }
      delete query.redirect
      return { path: to.path, query }
    }
  }

  return true
})

router.afterEach((to) => {
  if (typeof document === 'undefined') return
  const title = to.meta && to.meta.title ? `${to.meta.title} · 贴吧社区` : '贴吧社区'
  document.title = title
})

export default router
