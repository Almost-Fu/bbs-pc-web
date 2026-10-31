// ---------------------------------------------------------------------------
// 登录态（本文件是唯一数据源，不能 import api.js，避免 api <-> session 循环依赖）
//
//   页面读：session.token / session.user
//   页面写：setSession({ token, user }) / clearSession() / updateUser(user)
//   持久化：localStorage['bbs_token'] / localStorage['bbs_current_user']
//
//   说明：session.user 只是「上次登录成功后的缓存」，用于首屏直接渲染头像和昵称；
//         需要最新资料时由页面调用 api.me() 或 api.updateMe() 刷新（api.js 会同步本文件）。
// ---------------------------------------------------------------------------
import { reactive } from 'vue'

export const TOKEN_KEY = 'bbs_token'
export const USER_KEY = 'bbs_current_user'

function safeGetItem(key) {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function safeSetItem(key, value) {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // 隐私模式 / 存储被禁用时只保留内存态，不影响页面使用
  }
}

function safeRemoveItem(key) {
  try {
    window.localStorage.removeItem(key)
  } catch {
    // 同上
  }
}

function parseUser(raw) {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

function readToken() {
  const token = safeGetItem(TOKEN_KEY)
  return typeof token === 'string' ? token : ''
}

function readUser() {
  return parseUser(safeGetItem(USER_KEY))
}

/** 全局响应式登录态：token 为空即游客 */
export const session = reactive({
  token: readToken(),
  user: readUser()
})

/** 登录 / 注册成功后写入（token 可空，但正常不会） */
export function setSession({ token, user } = {}) {
  session.token = token ? String(token) : ''
  session.user = user && typeof user === 'object' ? user : null

  if (session.token) safeSetItem(TOKEN_KEY, session.token)
  else safeRemoveItem(TOKEN_KEY)

  if (session.user) safeSetItem(USER_KEY, JSON.stringify(session.user))
  else safeRemoveItem(USER_KEY)
}

/** 退出登录 / token 失效（api.js 收到 401 时会自动调用） */
export function clearSession() {
  session.token = ''
  session.user = null
  safeRemoveItem(TOKEN_KEY)
  safeRemoveItem(USER_KEY)
}

/** 局部刷新当前用户缓存（修改资料 / 上传头像 / 拉取 /auth/me 后调用） */
export function updateUser(user) {
  if (!user || typeof user !== 'object') {
    session.user = null
    safeRemoveItem(USER_KEY)
    return null
  }
  session.user = { ...(session.user || {}), ...user }
  safeSetItem(USER_KEY, JSON.stringify(session.user))
  return session.user
}

// 多标签页同步：在另一个标签页登录 / 退出时，本页的 session 立即跟着变
if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
  window.addEventListener('storage', (event) => {
    if (event.key === TOKEN_KEY) {
      session.token = event.newValue || ''
    } else if (event.key === USER_KEY) {
      session.user = parseUser(event.newValue)
    }
  })
}
