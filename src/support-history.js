// ---------------------------------------------------------------------------
// 客服对话本地历史（按账号持久化 + 进行中请求托管）
//
//   · 账号身份：session.token + session.user.id；游客单独一份。
//     存储 key 只用「用户 id / guest」，绝不使用 token。
//   · 请求状态放在模块里：离开页面后回答仍会写回「发起请求的账号」。
//   · generation：清空后递增，旧请求的迟到结果不会再写回来。
//   · 所有 localStorage 访问都容错：存储不可用时只保留内存态。
//   · 缓存内容全部经过白名单校验；版本不符或损坏时安全回空。
// ---------------------------------------------------------------------------
import { reactive } from 'vue'
import { api } from './api'
import { session } from './session'

export const SCHEMA_VERSION = 1
export const MAX_HISTORY = 10
export const MAX_MESSAGES = 40
export const MAX_MESSAGE_CHARS = 500

const MAX_DRAFT_CHARS = 500
const MAX_STORED_CONTENT_CHARS = 2000
const MAX_FAILED_CONTENT_CHARS = 200
const MAX_ACTION_LABEL_CHARS = 20
const STORAGE_PREFIX = 'bbs:support:v1:'

export const ACTION_TARGETS = {
  publish: '/publish',
  my_posts: '/my-posts',
  favorites: '/favorites',
  message: '/messages',
  profile: '/account',
  login: '/login',
  register: '/register',
  home: '/'
}

const ACTION_LABELS = {
  publish: '去发帖',
  my_posts: '我的帖子',
  favorites: '我的收藏',
  message: '查看消息',
  profile: '编辑资料',
  login: '去登录',
  register: '去注册',
  home: '返回首页'
}

/** 当前页面展示的客服状态（由本模块独占维护） */
export const supportState = reactive({
  key: '',
  unresolved: false,
  messages: [],
  draft: '',
  sending: false
})

const accounts = new Map()
let requestSeq = 0

/* --------------------------------------------------------------------------
   账号身份与存储 key
   -------------------------------------------------------------------------- */

/**
 * authbootstrap 阶段可能「有 token、还没 user」：此时身份未知，返回 null，
 * 既不读取也不写入任何账号缓存，避免把旧账号记录误当成 guest。
 */
export function resolveIdentity() {
  const token = typeof session.token === 'string' ? session.token : ''
  const rawId = session.user && session.user.id != null ? session.user.id : ''
  const userId = rawId === '' || rawId == null ? '' : String(rawId)

  if (!token && !userId) return { key: 'guest', guest: true, userId: '' }
  if (!userId) return null
  if (!token) return { key: 'guest', guest: true, userId: '' }
  return { key: `user:${encodeURIComponent(userId)}`, guest: false, userId }
}

function storageKey(accountKey) {
  return `${STORAGE_PREFIX}${accountKey}`
}

function safeRead(key) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return null
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function safeWrite(key, value) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return
    window.localStorage.setItem(key, value)
  } catch {
    // 隐私模式 / 配额满 / 存储被禁用：保留内存态即可
  }
}

function safeRemove(key) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return
    window.localStorage.removeItem(key)
  } catch {
    // 同上
  }
}

/* --------------------------------------------------------------------------
   缓存内容校验
   -------------------------------------------------------------------------- */

function sanitizeAction(action) {
  if (!action || typeof action !== 'object') return null
  const key = typeof action.key === 'string' ? action.key : ''
  if (!Object.prototype.hasOwnProperty.call(ACTION_TARGETS, key)) return null
  const rawLabel = typeof action.label === 'string' ? action.label.trim() : ''
  const label = rawLabel
    ? Array.from(rawLabel).slice(0, MAX_ACTION_LABEL_CHARS).join('')
    : ACTION_LABELS[key]
  return { key, label }
}

function sanitizeRetryText(value) {
  if (typeof value !== 'string') return ''
  const text = value.trim()
  if (!text) return ''
  return text.slice(0, MAX_MESSAGE_CHARS)
}

function sanitizeDraft(value) {
  return typeof value === 'string' ? value.slice(0, MAX_DRAFT_CHARS) : ''
}

function sanitizeMessage(raw) {
  if (!raw || typeof raw !== 'object') return null
  const role = raw.role
  if (role !== 'user' && role !== 'assistant') return null

  const limit = role === 'user' ? MAX_MESSAGE_CHARS : MAX_STORED_CONTENT_CHARS
  const content =
    typeof raw.content === 'string' ? raw.content.trim().slice(0, limit) : ''
  if (!content) return null

  if (raw.failed === true) {
    if (role !== 'assistant') return null
    const retryText = sanitizeRetryText(raw.retryText)
    if (!retryText) return null
    return {
      role: 'assistant',
      failed: true,
      content: content.slice(0, MAX_FAILED_CONTENT_CHARS),
      retryText
    }
  }

  const message = { role, content }
  if (role === 'assistant') {
    const action = sanitizeAction(raw.action)
    if (action) message.action = action
    if (raw.fallback === true) message.fallback = true
  }
  return message
}

function serializeMessage(message) {
  if (message.failed) {
    return {
      role: 'assistant',
      failed: true,
      content: String(message.content || '').slice(0, MAX_FAILED_CONTENT_CHARS),
      retryText: sanitizeRetryText(message.retryText)
    }
  }
  const output = { role: message.role, content: String(message.content || '') }
  if (message.action) output.action = { key: message.action.key, label: message.action.label }
  if (message.fallback) output.fallback = true
  return output
}

/* --------------------------------------------------------------------------
   账号状态与持久化
   -------------------------------------------------------------------------- */

function createAccount(key) {
  return reactive({
    key,
    loaded: false,
    generation: 0,
    seq: 0,
    messages: [],
    draft: '',
    request: null
  })
}

function trimAccount(account) {
  if (account.messages.length > MAX_MESSAGES) {
    account.messages.splice(0, account.messages.length - MAX_MESSAGES)
  }
}

function persistAccount(account) {
  if (!account || !account.key) return
  try {
    const data = {
      v: SCHEMA_VERSION,
      messages: account.messages.slice(-MAX_MESSAGES).map(serializeMessage),
      draft: sanitizeDraft(account.draft),
      pending: account.request
        ? { text: String(account.request.text || '').slice(0, MAX_MESSAGE_CHARS) }
        : null
    }
    safeWrite(storageKey(account.key), JSON.stringify(data))
  } catch {
    // 序列化异常也不影响内存态
  }
}

function loadAccount(account) {
  if (account.loaded) return
  account.loaded = true

  const raw = safeRead(storageKey(account.key))
  if (!raw) return

  let data
  try {
    data = JSON.parse(raw)
  } catch {
    return
  }
  if (!data || typeof data !== 'object' || data.v !== SCHEMA_VERSION) return

  const list = Array.isArray(data.messages) ? data.messages : []
  const restored = []
  for (const item of list) {
    const message = sanitizeMessage(item)
    if (message) restored.push(message)
  }
  const kept = restored.slice(-MAX_MESSAGES)

  // 恢复时重新编号，保证 id 唯一且 seq 不会回退
  let seq = 0
  for (const message of kept) {
    message.id = `m${++seq}`
  }
  account.messages.splice(0, account.messages.length, ...kept)
  account.seq = seq
  account.draft = sanitizeDraft(data.draft)

  // 上次页面在等待回答时被刷新：转成可重试的失败气泡，不自动重发
  const pendingText = sanitizeRetryText(data.pending && data.pending.text)
  if (pendingText) {
    const last = account.messages[account.messages.length - 1]
    if (!(last && last.failed && last.retryText === pendingText)) {
      account.messages.push({
        id: `m${++account.seq}`,
        role: 'assistant',
        failed: true,
        content: '上次回答未完成，请点击重新发送。',
        retryText: pendingText
      })
      trimAccount(account)
    }
    persistAccount(account)
  }
}

function getAccount(key) {
  let account = accounts.get(key)
  if (!account) {
    account = createAccount(key)
    accounts.set(key, account)
  }
  loadAccount(account)
  return account
}

function activeAccount() {
  if (!supportState.key) return null
  return accounts.get(supportState.key) || null
}

function isActive(account) {
  return Boolean(account) && supportState.key === account.key
}

function activate(key) {
  const account = getAccount(key)
  supportState.key = key
  supportState.unresolved = false
  supportState.messages = account.messages
  supportState.draft = account.draft
  supportState.sending = Boolean(account.request)
}

/** 页面调用：按当前登录态切换到对应账号记录；身份未知时只清空展示态 */
export function syncSupportIdentity() {
  const identity = resolveIdentity()
  if (!identity) {
    // authbootstrap 中「有 token、暂无 user」：身份未知，立即清空页面展示，
    // 避免继续显示上一账号的对话。accounts 内的记录、进行中的请求和持久化缓存
    // 一律不动；身份恢复后 activate 会重新挂回原账号。
    supportState.key = ''
    supportState.messages = []
    supportState.draft = ''
    supportState.sending = false
    supportState.unresolved = true
    return false
  }
  if (supportState.key === identity.key) {
    supportState.unresolved = false
    return true
  }
  activate(identity.key)
  return true
}

/** 输入草稿：随账号保存；身份未知时只留在内存，绝不写 guest */
export function setSupportDraft(value) {
  const text = sanitizeDraft(typeof value === 'string' ? value : '')
  const account = activeAccount()
  if (!account) {
    supportState.draft = text
    return
  }
  account.draft = text
  if (isActive(account)) supportState.draft = text
  persistAccount(account)
}

/* --------------------------------------------------------------------------
   请求与消息
   -------------------------------------------------------------------------- */

function buildHistory(messages) {
  // 失败的问答对不计入上下文：失败气泡本身跳过，同时摘掉与它对应的那条用户提问。
  const cleaned = []
  for (const message of messages) {
    if (message.failed) {
      if (!message.retryText) continue
      for (let index = cleaned.length - 1; index >= 0; index -= 1) {
        if (cleaned[index].role === 'user' && cleaned[index].content === message.retryText) {
          cleaned.splice(index, 1)
          break
        }
      }
      continue
    }
    if (
      (message.role === 'user' || message.role === 'assistant') &&
      typeof message.content === 'string' &&
      message.content
    ) {
      cleaned.push({ role: message.role, content: message.content })
    }
  }

  return cleaned
    .slice(-MAX_HISTORY)
    .map((message) => ({
      role: message.role,
      content: String(message.content).slice(0, MAX_MESSAGE_CHARS)
    }))
}

function errorTextOf(err) {
  const status = Number(err && (err.status || err.code))
  if (status === 429) return '问得太快啦，请稍等几秒再试。'
  if (status === 422) return '这个问题不太符合格式，换个说法再试。'
  if (status === 503) return '客服暂时繁忙，请稍后再试。'
  if (status >= 500) return '客服服务暂时不可用，请稍后重试。'

  const text = err && typeof err.message === 'string' ? err.message.trim() : ''
  if (text && !/failed to fetch|networkerror|load failed|fetch failed/i.test(text)) return text
  return '网络开小差了，回答没有发出去。'
}

function appendFailed(account, content, retryText) {
  account.messages.push({
    id: `m${++account.seq}`,
    role: 'assistant',
    failed: true,
    content: String(content || '').slice(0, MAX_FAILED_CONTENT_CHARS),
    retryText
  })
  trimAccount(account)
}

function completeRequest(account, requestId) {
  if (account.request && account.request.id === requestId) {
    account.request = null
    if (isActive(account)) supportState.sending = false
  }
}

function startAsk(account, text, pushUser) {
  if (!account || account.request) return false

  const content = String(text || '').trim()
  if (!content || content.length > MAX_MESSAGE_CHARS) return false

  // 历史必须在追加本轮提问之前读取，失败气泡不计入上下文
  const history = buildHistory(account.messages)
  const generation = account.generation

  if (pushUser) {
    account.messages.push({
      id: `m${++account.seq}`,
      role: 'user',
      content
    })
    trimAccount(account)
  }

  const requestId = ++requestSeq
  account.request = { id: requestId, text: content, generation }
  if (isActive(account)) supportState.sending = true
  persistAccount(account)

  api
    .cs(content, history)
    .then((data) => {
      // generation 变化（清空）或请求已被替换：旧结果一律丢弃
      if (account.generation !== generation) return
      if (!account.request || account.request.id !== requestId) return

      const reply = data && data.reply ? String(data.reply).trim() : ''
      if (reply) {
        account.messages.push({
          id: `m${++account.seq}`,
          role: 'assistant',
          content: reply,
          action: sanitizeAction(data && data.action),
          fallback: Boolean(data && data.fallback)
        })
        trimAccount(account)
      } else {
        appendFailed(account, '客服没有返回回答，请重新发送。', content)
      }
      completeRequest(account, requestId)
      persistAccount(account)
    })
    .catch((err) => {
      if (account.generation !== generation) return
      if (!account.request || account.request.id !== requestId) return
      appendFailed(account, errorTextOf(err), content)
      completeRequest(account, requestId)
      persistAccount(account)
    })
    .finally(() => {
      // 兜底：异常路径也要解除 sending，避免重进页面后永远在发送中
      if (account.request && account.request.id === requestId) {
        completeRequest(account, requestId)
        persistAccount(account)
      }
    })

  return true
}

/** 发送一条新消息（会自动清空并持久化草稿） */
export function sendSupportMessage(text) {
  const account = activeAccount()
  if (!account || supportState.unresolved) return false
  if (account.request) return false

  const content = String(text || '').trim()
  if (!content || content.length > MAX_MESSAGE_CHARS) return false

  account.draft = ''
  if (isActive(account)) supportState.draft = ''
  return startAsk(account, content, true)
}

/** 重试失败气泡：移除旧失败气泡与对应提问后重新发送 */
export function retrySupportMessage(message) {
  const account = activeAccount()
  if (!account || account.request || !message || !message.failed) return false

  const retryText = sanitizeRetryText(message.retryText)
  if (!retryText) return false

  const rest = account.messages.filter((item) => item.id !== message.id)
  for (let index = rest.length - 1; index >= 0; index -= 1) {
    if (rest[index].role === 'user' && !rest[index].failed && rest[index].content === retryText) {
      rest.splice(index, 1)
      break
    }
  }
  account.messages.splice(0, account.messages.length, ...rest)
  persistAccount(account)

  return startAsk(account, retryText, true)
}

/** 清空当前账号的对话与草稿，并让正在进行的旧请求失效 */
export function clearSupportHistory() {
  const account = activeAccount()
  if (!account) return false

  account.generation += 1
  account.request = null
  account.seq = 0
  account.messages.splice(0, account.messages.length)
  account.draft = ''
  if (isActive(account)) {
    supportState.draft = ''
    supportState.sending = false
  }
  safeRemove(storageKey(account.key))
  return true
}
