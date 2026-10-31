// ---------------------------------------------------------------------------
// 后端接口封装（PC Web 唯一数据入口）
//
//   后端：FastAPI，统一响应体 { code, message, data }，code === 0 表示成功；
//         失败时 HTTP 状态码与 code 相同（401 未登录 / 403 无权限 / 404 不存在 ...）。
//   地址：开发环境走同源 /api（Vite 代理到线上后端），生产环境走 VITE_API_ORIGIN。
//   登录：token 由 session.js 管理，这里自动加 Authorization: Bearer <token>。
//
//   约定：
//     · request(path, { method, body, query, signal }) 直接返回 data
//     · 90 秒超时；401 自动清 session；所有异常都是可直接展示的中文 Error
//     · body 为 FormData 时不设置 Content-Type（交给浏览器带 boundary）
//     · 不在这里 import router / 视图，避免循环依赖
// ---------------------------------------------------------------------------
import { clearSession, session, setSession, updateUser } from './session'

/** 生产后端（Render） */
export const PROD_API_ORIGIN = 'https://bbs-app-backend-zuzm.onrender.com'

/** 90 秒：Render 免费实例冷启动要 30~60 秒，给足时间 */
export const REQUEST_TIMEOUT = 90000

const configuredOrigin = String(
  import.meta.env.VITE_API_ORIGIN || PROD_API_ORIGIN
)
  .trim()
  .replace(/\/+$/, '')

/**
 * 接口与图片的后端源：
 *   开发 = ''（同源，/api、/uploads、/static 由 Vite proxy 转发）
 *   生产 = VITE_API_ORIGIN || Render 地址
 */
export const API_ORIGIN = import.meta.env.DEV ? '' : configuredOrigin

const API_BASE = `${API_ORIGIN}/api`

const STATUS_MESSAGES = {
  400: '请求参数有误，请检查后重试',
  401: '登录已过期，请重新登录',
  403: '没有权限执行该操作',
  404: '请求的内容不存在或已被删除',
  409: '操作冲突，请刷新后重试',
  413: '上传内容过大，请压缩后重试',
  422: '提交的内容格式不正确，请检查后重试',
  429: '操作过于频繁，请稍后再试',
  500: '服务器繁忙，请稍后重试',
  502: '服务器暂时不可用，请稍后重试',
  503: '服务器暂时不可用，请稍后重试',
  504: '服务器响应超时，请稍后重试'
}

/** 统一的、用户可读的接口异常 */
export class ApiError extends Error {
  constructor(message, { status = 0, code = '', data = null, canceled = false } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.data = data
    this.canceled = canceled
  }
}

function abortError() {
  const error = new ApiError('请求已取消', { code: 'ABORTED', canceled: true })
  // 页面通常通过 error.name === 'AbortError' 忽略「切路由导致的取消」
  error.name = 'AbortError'
  return error
}

function normalizeFetchError(error, { timedOut, abortedByCaller }) {
  if (timedOut) {
    return new ApiError('请求超时（90 秒），服务器可能正在唤醒，请稍后重试', {
      code: 'TIMEOUT'
    })
  }
  if (abortedByCaller || (error && error.name === 'AbortError')) {
    return abortError()
  }
  return new ApiError('无法连接服务器，请检查网络后重试', { code: 'NETWORK' })
}

let lastUnauthorizedEventAt = 0

/**
 * 401：只有「发出请求时用的 token」仍然等于当前 session.token 才处理。
 *
 * 场景：旧 token 的慢请求在用户退出 / 换号并登录成功之后才返回 401，
 * 此时 session 已经是新用户，绝不能清掉新 token，也不能触发跳转。
 * 返回是否真的处理了这次 401。
 */
function handleUnauthorized(message, requestToken) {
  if (session.token !== requestToken) return false

  if (requestToken) clearSession()

  if (typeof window === 'undefined' || typeof window.dispatchEvent !== 'function') return true
  const now = Date.now()
  if (now - lastUnauthorizedEventAt < 1000) return true
  lastUnauthorizedEventAt = now
  try {
    window.dispatchEvent(
      new CustomEvent('bbs:unauthorized', { detail: { message } })
    )
  } catch {
    // 老浏览器不支持 CustomEvent 构造时忽略，页面仍会看到 401 异常
  }
  return true
}

function readMessage(payload, status) {
  if (payload && typeof payload.message === 'string' && payload.message.trim()) {
    return payload.message.trim()
  }
  return STATUS_MESSAGES[status] || `请求失败（HTTP ${status}）`
}

function appendQuery(url, query) {
  if (!query || typeof query !== 'object') return url
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item !== undefined && item !== null) params.append(key, String(item))
      }
    } else {
      params.append(key, String(value))
    }
  }
  const qs = params.toString()
  if (!qs) return url
  return `${url}${url.includes('?') ? '&' : '?'}${qs}`
}

function buildUrl(path, query) {
  const raw = String(path || '')
  let url
  if (/^https?:\/\//i.test(raw)) {
    url = raw
  } else {
    url = `${API_BASE}${raw.startsWith('/') ? raw : `/${raw}`}`
  }
  return appendQuery(url, query)
}

/**
 * 发起请求并返回后端 data
 * @param {string} path  以 / 开头的接口路径（不含 /api 前缀），如 '/posts'
 * @param {object} [options]
 * @param {'GET'|'POST'|'PATCH'|'PUT'|'DELETE'} [options.method='GET']
 * @param {object|FormData} [options.body]
 * @param {object} [options.query]
 * @param {AbortSignal} [options.signal]
 * @returns {Promise<any>}
 */
export async function request(path, { method = 'GET', body, query, signal } = {}) {
  const upperMethod = String(method || 'GET').toUpperCase()
  const url = buildUrl(path, query)
  const headers = { Accept: 'application/json' }

  // 记下本次请求实际使用的 token：迟到响应回来后用它判断登录态是否已经变化
  const requestToken = session.token

  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
  const hasBody =
    body !== undefined && body !== null && upperMethod !== 'GET' && upperMethod !== 'HEAD'

  // FormData 绝不能手动加 Content-Type，否则 boundary 会丢
  if (hasBody && !isFormData) headers['Content-Type'] = 'application/json'
  if (requestToken) headers.Authorization = `Bearer ${requestToken}`

  const controller = new AbortController()
  let timedOut = false
  let abortedByCaller = false

  const timeoutId = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, REQUEST_TIMEOUT)

  const onExternalAbort = () => {
    abortedByCaller = true
    controller.abort()
  }

  if (signal) {
    if (signal.aborted) {
      abortedByCaller = true
      controller.abort()
    } else {
      signal.addEventListener('abort', onExternalAbort, { once: true })
    }
  }

  try {
    let response
    try {
      response = await fetch(url, {
        method: upperMethod,
        headers,
        body: hasBody ? (isFormData ? body : JSON.stringify(body)) : undefined,
        signal: controller.signal
      })
    } catch (error) {
      throw normalizeFetchError(error, { timedOut, abortedByCaller })
    }

    let text = ''
    try {
      text = await response.text()
    } catch (error) {
      throw normalizeFetchError(error, { timedOut, abortedByCaller })
    }

    let payload = null
    if (text) {
      try {
        payload = JSON.parse(text)
      } catch {
        payload = null
      }
    }

    if (response.status === 204) return null

    const httpOk = response.status >= 200 && response.status < 300
    const hasEnvelope =
      payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'code')

    // 后端业务错误：HTTP 状态码与 code 一致；401 统一清 session
    if (!httpOk) {
      const message = readMessage(payload, response.status)
      if (response.status === 401) handleUnauthorized(message, requestToken)
      throw new ApiError(message, {
        status: response.status,
        code: hasEnvelope ? payload.code : response.status,
        data: hasEnvelope ? payload.data : null
      })
    }

    if (hasEnvelope) {
      if (payload.code === 0) return payload.data
      const message = readMessage(payload, response.status)
      if (payload.code === 401) handleUnauthorized(message, requestToken)
      throw new ApiError(message, {
        status: response.status,
        code: payload.code,
        data: payload.data
      })
    }

    // 理论上 /api 一定带统一响应体；这里保留兜底，避免把 HTML 当数据渲染
    if (!payload || typeof payload !== 'object') {
      throw new ApiError('服务器返回了无法识别的数据，请稍后重试', {
        status: response.status,
        code: 'BAD_RESPONSE'
      })
    }
    return payload
  } finally {
    clearTimeout(timeoutId)
    if (signal && typeof signal.removeEventListener === 'function') {
      signal.removeEventListener('abort', onExternalAbort)
    }
  }
}

/**
 * 图片地址白名单：
 *   · 空 → ''
 *   · http/https → 原样
 *   · blob: → 原样（本页产生的预览地址）
 *   · data:image/<mime>[,;...] → 原样（只允许图片类型，data:text/html 等一律拒绝）
 *   · 根相对路径（/ 开头且不是 // 或 /\）→ 补后端源；开发环境 API_ORIGIN 为 '' 即同源代理
 *   · 其他（javascript:、vbscript:、file:、协议相对 //host、普通相对路径等）→ ''
 *
 * 返回空串时调用方应展示占位图 / 首字，绝不能把危险 scheme 拼成后端路径。
 * @param {string} path
 * @returns {string}
 */
export function imageUrl(path) {
  if (!path) return ''
  const value = String(path).trim()
  if (!value) return ''

  if (/^https?:\/\//i.test(value)) return value
  if (/^blob:/i.test(value)) return value
  if (/^data:image\/[a-z0-9.+-]+(?:;[a-z0-9=.+-]+)*,/i.test(value)) return value

  const isRootRelative =
    value.startsWith('/') && !value.startsWith('//') && !value.startsWith('/\\')
  if (!isRootRelative) return ''

  return `${API_ORIGIN}${value}`
}

// ---- 客服跳转：后端返回的是 uni-app 页面路径，PC 端统一换成站内路由 ----
const CS_ACTION_PATHS = {
  publish: '/publish',
  my_posts: '/my-posts',
  favorites: '/favorites',
  message: '/messages',
  profile: '/account',
  login: '/login',
  register: '/register',
  home: '/'
}

function normalizeCsAction(action) {
  if (!action || typeof action !== 'object') return null
  const key = typeof action.key === 'string' ? action.key : ''
  const path = CS_ACTION_PATHS[key] || ''
  return { ...action, path }
}

function pageQuery(defaults, query) {
  return { ...defaults, ...(query && typeof query === 'object' ? query : {}) }
}

/**
 * 迟到的用户资料响应只有在「发请求时的 token 仍是非空的当前 token」时才允许写回 session。
 * 否则用户可能已经退出或换号，旧响应会把上一个账号的资料写进新 session。
 */
function canWriteUser(token) {
  return Boolean(token) && session.token === token
}

/**
 * 业务接口集合（函数名与实施合同完全一致）
 * like/favorite/follow 的第二参数是「目标状态」：true = POST，false = DELETE。
 */
export const api = {
  // ---------------------------- 帖子 ----------------------------
  posts(query = {}) {
    return request('/posts', { query: pageQuery({ page: 1, pageSize: 10 }, query) })
  },

  // ---------------------------- 贴吧 ----------------------------
  bars(keyword = '') {
    const word = typeof keyword === 'string' ? keyword.trim() : keyword
    return request('/bars', { query: word ? { keyword: word } : {} })
  },

  bar(id) {
    return request(`/bars/${id}`)
  },

  barPosts(id, query = {}) {
    return request(`/bars/${id}/posts`, {
      query: pageQuery({ page: 1, pageSize: 10 }, query)
    })
  },

  // ---------------------------- 帖子详情 / 互动 ----------------------------
  post(id) {
    return request(`/posts/${id}`)
  },

  comments(id, query = {}) {
    return request(`/posts/${id}/comments`, {
      query: pageQuery({ page: 1, pageSize: 20 }, query)
    })
  },

  addComment(id, text) {
    return request(`/posts/${id}/comments`, {
      method: 'POST',
      body: { text: String(text ?? '') }
    })
  },

  likePost(id, liked) {
    return request(`/posts/${id}/like`, { method: liked ? 'POST' : 'DELETE' })
  },

  favoritePost(id, favorited) {
    return request(`/posts/${id}/favorite`, {
      method: favorited ? 'POST' : 'DELETE'
    })
  },

  followBar(id, followed) {
    return request(`/bars/${id}/follow`, { method: followed ? 'POST' : 'DELETE' }).then((data) => {
      if (typeof window !== 'undefined') window.dispatchEvent(new Event('bbs:bars-changed'))
      return data
    })
  },

  followedBars() {
    return request('/users/me/followed-bars')
  },

  // ---------------------------- 我的 ----------------------------
  myPosts(query = {}) {
    return request('/users/me/posts', {
      query: pageQuery({ page: 1, pageSize: 10 }, query)
    })
  },

  favorites(query = {}) {
    return request('/users/me/favorites', {
      query: pageQuery({ page: 1, pageSize: 10 }, query)
    })
  },

  // ---------------------------- 搜索 ----------------------------
  search(keyword, query = {}) {
    return request('/search', {
      query: { ...pageQuery({ page: 1, pageSize: 10 }, query), keyword }
    })
  },

  hotSearch() {
    return request('/search/hot')
  },

  // ---------------------------- 认证 ----------------------------
  async login(username, password) {
    const data = await request('/auth/login', {
      method: 'POST',
      body: { username, password }
    })
    if (data && data.token) {
      setSession({ token: data.token, user: data.user })
    }
    return data
  },

  async register(payload) {
    const data = await request('/auth/register', {
      method: 'POST',
      body: payload || {}
    })
    if (data && data.token) {
      setSession({ token: data.token, user: data.user })
    }
    return data
  },

  async me() {
    const token = session.token
    const user = await request('/auth/me')
    if (user && typeof user === 'object' && canWriteUser(token)) updateUser(user)
    return user
  },

  // ---------------------------- 发布 / 资料 ----------------------------
  createPost(formData) {
    if (typeof FormData === 'undefined' || !(formData instanceof FormData)) {
      return Promise.reject(
        new ApiError('发布数据必须使用 FormData（字段：barId、title、content、tag、files）', {
          code: 'INVALID_BODY'
        })
      )
    }
    return request('/posts', { method: 'POST', body: formData })
  },

  updatePost(id, payload) {
    const data = payload && typeof payload === 'object' ? payload : {}
    return request(`/posts/${id}`, {
      method: 'PATCH',
      body: {
        barId: data.barId,
        title: data.title,
        content: data.content,
        tag: data.tag
      }
    })
  },

  notifications(type = 'all', query = {}) {
    return request('/users/me/notifications', {
      query: {
        ...pageQuery({ page: 1, pageSize: 20 }, query),
        type: type || 'all'
      }
    })
  },

  readNotifications() {
    return request('/users/me/notifications/read', { method: 'POST' })
  },

  unread() {
    return request('/users/me/notifications/unread')
  },

  async updateMe(payload) {
    const token = session.token
    const user = await request('/users/me', { method: 'PATCH', body: payload || {} })
    if (user && typeof user === 'object' && canWriteUser(token)) updateUser(user)
    return user
  },

  async uploadAvatar(file) {
    if (typeof FormData === 'undefined' || !file) {
      throw new ApiError('请选择要上传的图片', { code: 'INVALID_FILE' })
    }
    const token = session.token
    const formData = new FormData()
    formData.append('file', file)
    const user = await request('/users/me/avatar', { method: 'POST', body: formData })
    if (user && typeof user === 'object' && canWriteUser(token)) updateUser(user)
    return user
  },

  // ---------------------------- 智能客服 ----------------------------
  cs(message, history = []) {
    const safeHistory = (Array.isArray(history) ? history : [])
      .filter(
        (item) =>
          item &&
          (item.role === 'user' || item.role === 'assistant') &&
          typeof item.content === 'string' &&
          item.content
      )
      .slice(-10)
      .map((item) => ({
        role: item.role,
        content: String(item.content).slice(0, 500)
      }))
    const safeMessage = String(message ?? '').slice(0, 500)
    return request('/cs/chat', {
      method: 'POST',
      body: { message: safeMessage, history: safeHistory }
    }).then((data) => {
      if (!data || typeof data !== 'object') return data
      return { ...data, action: normalizeCsAction(data.action) }
    })
  }
}

export default api
