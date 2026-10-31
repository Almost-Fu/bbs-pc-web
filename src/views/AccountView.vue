<template>
  <div class="account-view">
    <div class="account-content">
      <header class="page-head">
        <div>
          <p class="eyebrow">个人中心</p>
          <h1>账号设置</h1>
          <p class="page-sub">维护昵称与头像，进入我的帖子、收藏和互动消息。</p>
        </div>
        <button type="button" class="refresh-btn" :disabled="loading || refreshing" @click="loadProfile">
          <span v-if="refreshing" class="tiny-spinner" aria-hidden="true"></span>
          <span>{{ refreshing ? '同步中…' : '刷新资料' }}</span>
        </button>
      </header>

      <div v-if="loading" class="panel overview-skeleton" aria-live="polite">
        <span class="sr-only">正在加载账号资料</span>
        <div class="skeleton-avatar"></div>
        <div class="skeleton-lines">
          <span class="skeleton-line wide"></span>
          <span class="skeleton-line"></span>
          <span class="skeleton-line short"></span>
        </div>
      </div>

      <div v-else-if="loadError && !user" class="panel load-error" role="alert">
        <div>
          <strong>账号资料加载失败</strong>
          <p>{{ loadError }}</p>
        </div>
        <div class="load-error-actions">
          <button type="button" class="secondary-btn" @click="loadProfile">重试</button>
          <button type="button" class="secondary-btn danger" @click="logoutOpen = true">退出登录</button>
        </div>
      </div>

      <div v-else-if="user" class="account-layout">
        <aside class="panel identity-panel">
          <div class="avatar-frame">
            <img
              v-if="avatarPreview && !avatarError"
              class="avatar-image"
              :src="avatarPreview"
              :alt="displayName"
              @error="avatarError = true"
            />
            <span v-else class="avatar-fallback" aria-hidden="true">{{ initials }}</span>
          </div>

          <h2 class="identity-name">{{ displayName }}</h2>
          <p class="identity-username">@{{ user.username }}</p>
          <span class="role-chip">{{ roleText }}</span>

          <dl class="identity-meta">
            <div>
              <dt>用户名</dt>
              <dd>{{ user.username }}</dd>
            </div>
            <div>
              <dt>账号权限</dt>
              <dd>{{ roleText }}</dd>
            </div>
            <div>
              <dt>登录状态</dt>
              <dd class="status-ok">已登录</dd>
            </div>
          </dl>

          <button type="button" class="logout-btn" @click="logoutOpen = true">退出登录</button>
          <p v-if="refreshing" class="sync-note">正在从服务器同步最新资料…</p>
        </aside>

        <div class="account-main">
          <div v-if="loadError" class="action-alert error" role="alert">
            <span>{{ loadError }}</span>
            <button type="button" class="inline-link as-button" @click="loadProfile">重试同步</button>
          </div>

          <section class="panel profile-panel" aria-labelledby="profile-heading">
            <div class="panel-head">
              <div>
                <h2 id="profile-heading">个人资料</h2>
                <p>头像上传后会立即写入账号，昵称保存后同步更新。</p>
              </div>
            </div>

            <div v-if="actionError" class="action-alert error" role="alert">
              <span>{{ actionError }}</span>
              <router-link
                v-if="!session.token"
                class="inline-link"
                :to="{ path: '/login', query: { redirect: route.fullPath } }"
              >
                重新登录
              </router-link>
            </div>
            <div v-else-if="actionSuccess" class="action-alert success" role="status">
              {{ actionSuccess }}
            </div>

            <div class="avatar-row">
              <div class="avatar-preview-small">
                <img
                  v-if="avatarPreview && !avatarError"
                  :src="avatarPreview"
                  :alt="displayName"
                  @error="avatarError = true"
                />
                <span v-else aria-hidden="true">{{ initials }}</span>
              </div>
              <div class="avatar-copy">
                <strong>头像</strong>
                <p>支持 JPG、PNG、GIF、WebP、BMP，单张不超过 5MB。</p>
                <input
                  ref="avatarInput"
                  class="hidden-input"
                  type="file"
                  accept=".jpg,.jpeg,.png,.gif,.webp,.bmp,image/*"
                  :disabled="avatarUploading || saving"
                  @change="onAvatarChange"
                />
                <button
                  type="button"
                  class="secondary-btn"
                  :disabled="avatarUploading || saving"
                  @click="chooseAvatar"
                >
                  <span v-if="avatarUploading" class="tiny-spinner dark" aria-hidden="true"></span>
                  <span>{{ avatarUploading ? '正在上传…' : '上传新头像' }}</span>
                </button>
              </div>
            </div>

            <form class="profile-form" novalidate @submit.prevent="saveProfile">
              <label class="ui-field" for="profile-nickname">
                <span class="field-label">
                  昵称
                  <em>{{ nickname.length }}/20</em>
                </span>
                <input
                  id="profile-nickname"
                  v-model="nickname"
                  class="text-input"
                  type="text"
                  maxlength="20"
                  placeholder="请输入昵称"
                  :disabled="saving || avatarUploading"
                  @input="clearMessages"
                />
              </label>

              <div class="form-footer">
                <p class="form-hint">昵称会显示在你发布的帖子与互动消息中。</p>
                <button class="primary-btn" type="submit" :disabled="saving || avatarUploading">
                  <span v-if="saving" class="tiny-spinner" aria-hidden="true"></span>
                  <span>{{ saving ? '正在保存…' : '保存资料' }}</span>
                </button>
              </div>
            </form>
          </section>

          <section class="panel shortcuts-panel" aria-labelledby="shortcuts-heading">
            <div class="panel-head">
              <div>
                <h2 id="shortcuts-heading">我的社区</h2>
                <p>快速前往与你账号关联的内容页面。</p>
              </div>
            </div>

            <div class="shortcut-list">
              <router-link class="shortcut-item" to="/my-posts">
                <span class="shortcut-mark" aria-hidden="true">帖</span>
                <span class="shortcut-copy">
                  <strong>我的帖子</strong>
                  <small>查看自己发布过的帖子</small>
                </span>
                <span class="shortcut-arrow" aria-hidden="true">›</span>
              </router-link>

              <router-link class="shortcut-item" to="/favorites">
                <span class="shortcut-mark" aria-hidden="true">藏</span>
                <span class="shortcut-copy">
                  <strong>我的收藏</strong>
                  <small>查看收藏过的帖子</small>
                </span>
                <span class="shortcut-arrow" aria-hidden="true">›</span>
              </router-link>

              <router-link class="shortcut-item" to="/messages">
                <span class="shortcut-mark" aria-hidden="true">信</span>
                <span class="shortcut-copy">
                  <strong>互动消息</strong>
                  <small>查看点赞、回复与 @ 消息</small>
                </span>
                <span class="shortcut-arrow" aria-hidden="true">›</span>
              </router-link>
            </div>
          </section>
        </div>
      </div>

      <div v-else class="panel load-error">
        <div>
          <strong>登录状态已失效</strong>
          <p>请重新登录后再访问账号设置。</p>
        </div>
        <router-link class="secondary-btn" :to="{ path: '/login', query: { redirect: route.fullPath } }">
          去登录
        </router-link>
      </div>
    </div>

    <div v-if="logoutOpen" class="modal-mask" @click.self="logoutOpen = false">
      <section class="confirm-panel" role="dialog" aria-modal="true" aria-labelledby="logout-title">
        <h2 id="logout-title">退出登录</h2>
        <p>退出后需要重新输入账号密码才能发布、收藏和查看消息。确定退出吗？</p>
        <div class="confirm-actions">
          <button type="button" class="secondary-btn" @click="logoutOpen = false">取消</button>
          <button type="button" class="danger-btn" @click="confirmLogout">确认退出</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, imageUrl } from '../api'
import { clearSession, session, updateUser } from '../session'

const MAX_AVATAR_BYTES = 5 * 1024 * 1024
const IMAGE_EXT = /\.(jpe?g|png|gif|webp|bmp)$/i

const route = useRoute()
const router = useRouter()

const loading = ref(!session.user)
const refreshing = ref(false)
const loadError = ref('')

const nickname = ref('')
const avatarPath = ref('')
const avatarError = ref(false)
const avatarUploading = ref(false)
const saving = ref(false)
const actionError = ref('')
const actionSuccess = ref('')
const logoutOpen = ref(false)
const avatarInput = ref(null)

let disposed = false
let successTimer = 0

const user = computed(() => session.user)

const displayName = computed(() => {
  const current = user.value
  return (current && (current.nickname || current.username)) || '社区用户'
})

const roleText = computed(() => {
  const role = user.value && user.value.role
  if (role === 'admin') return '管理员'
  if (role === 'user') return '社区成员'
  return role || '未提供'
})

const initials = computed(() => {
  const source = String(displayName.value || '友').trim()
  return Array.from(source)[0] || '友'
})

const avatarPreview = computed(() => (avatarPath.value ? imageUrl(avatarPath.value) : ''))

watch(avatarPath, () => {
  avatarError.value = false
})

function errorText(err, fallback) {
  const text = err && typeof err.message === 'string' ? err.message.trim() : ''
  if (text && !/failed to fetch|networkerror|load failed|fetch failed/i.test(text)) return text
  const status = err && (err.status || err.code)
  if (status === 401) return '登录状态已失效，请重新登录'
  if (status === 403) return '当前账号无权执行此操作'
  if (status === 413) return '图片体积过大，请压缩后重试'
  if (status === 422) return '提交的资料格式不正确'
  if (status >= 500) return '服务器暂时不可用，请稍后重试'
  return fallback
}

function applyUser(next) {
  if (!next) return
  nickname.value = next.nickname || ''
  avatarPath.value = next.avatar || ''
}

function clearMessages() {
  actionError.value = ''
  actionSuccess.value = ''
  if (successTimer) {
    window.clearTimeout(successTimer)
    successTimer = 0
  }
}

function flashSuccess(message) {
  actionSuccess.value = message
  actionError.value = ''
  if (successTimer) window.clearTimeout(successTimer)
  successTimer = window.setTimeout(() => {
    actionSuccess.value = ''
    successTimer = 0
  }, 3500)
}

async function loadProfile() {
  const token = session.token
  if (!token) {
    router.replace({ path: '/login', query: { redirect: route.fullPath } })
    return
  }

  if (session.user) {
    refreshing.value = true
  } else {
    loading.value = true
  }
  loadError.value = ''

  try {
    const fresh = await api.me()
    if (disposed || !token || session.token !== token) return
    if (!fresh) throw new Error('服务器未返回账号资料')
    updateUser(fresh)
    applyUser(fresh)
  } catch (err) {
    if (disposed || !token || session.token !== token) return
    loadError.value = errorText(err, '账号资料加载失败，请检查网络后重试')
  } finally {
    if (!disposed) {
      loading.value = false
      refreshing.value = false
    }
  }
}

function chooseAvatar() {
  if (avatarUploading.value || saving.value) return
  if (avatarInput.value) avatarInput.value.click()
}

async function onAvatarChange(event) {
  const input = event.target
  const file = input && input.files ? input.files[0] : null
  if (input) input.value = ''
  if (!file) return

  clearMessages()

  if (!IMAGE_EXT.test(file.name || '')) {
    actionError.value = '头像仅支持 JPG、PNG、GIF、WebP 或 BMP 格式'
    return
  }
  if (file.size > MAX_AVATAR_BYTES) {
    actionError.value = '头像图片不能超过 5MB，请压缩后重试'
    return
  }
  if (avatarUploading.value) return

  const token = session.token
  if (!token) {
    actionError.value = '登录状态已失效，请重新登录后再上传头像'
    return
  }

  avatarUploading.value = true
  try {
    const updated = await api.uploadAvatar(file)
    if (disposed || !token || session.token !== token) return
    if (!updated) throw new Error('服务器未返回更新后的账号资料')
    updateUser(updated)
    // 只替换头像，保留用户尚未保存的昵称草稿
    if (updated.avatar) avatarPath.value = updated.avatar
    avatarError.value = false
    flashSuccess('头像已更新')
  } catch (err) {
    if (disposed || !token || session.token !== token) return
    actionError.value = errorText(err, '头像上传失败，请稍后重试')
  } finally {
    if (!disposed) avatarUploading.value = false
  }
}

async function saveProfile() {
  if (saving.value || avatarUploading.value) return

  const cleanNickname = nickname.value.trim()
  if (!cleanNickname) {
    actionError.value = '昵称不能为空'
    actionSuccess.value = ''
    return
  }
  if (cleanNickname.length > 20) {
    actionError.value = '昵称不能超过 20 个字符'
    actionSuccess.value = ''
    return
  }

  const token = session.token
  if (!token) {
    actionError.value = '登录状态已失效，请重新登录后再保存资料'
    actionSuccess.value = ''
    return
  }

  clearMessages()
  saving.value = true
  try {
    const updated = await api.updateMe({ nickname: cleanNickname })
    if (disposed || !token || session.token !== token) return
    if (!updated) throw new Error('服务器未返回更新后的账号资料')
    updateUser(updated)
    applyUser(updated)
    flashSuccess('资料已保存')
  } catch (err) {
    if (disposed || !token || session.token !== token) return
    actionError.value = errorText(err, '资料保存失败，请稍后重试')
  } finally {
    if (!disposed) saving.value = false
  }
}

function confirmLogout() {
  logoutOpen.value = false
  clearSession()
  router.replace('/')
}

onMounted(() => {
  if (!session.token) {
    router.replace({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  applyUser(session.user)
  loadProfile()
})

onBeforeUnmount(() => {
  disposed = true
  if (successTimer) window.clearTimeout(successTimer)
})
</script>

<style scoped>
.account-view {
  max-width: 1000px;
  margin: 0 auto;
  padding: 4px 0 32px;
}

.account-content {
  container-type: inline-size;
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

.panel {
  background: #ffffff;
  border: 1px solid #e6ebf3;
  border-radius: 12px;
}

.account-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.identity-panel {
  position: sticky;
  top: 20px;
  padding: 30px 24px 24px;
  text-align: center;
  background: #fbfcff;
}

.avatar-frame {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 96px;
  margin: 0 auto 16px;
  padding: 4px;
  background: #ffffff;
  border: 1px solid #dce6f4;
  border-radius: 50%;
  box-shadow: 0 8px 24px rgba(36, 107, 253, 0.1);
}

.avatar-image,
.avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 86px;
  height: 86px;
  border-radius: 50%;
  object-fit: cover;
  background: #eef4ff;
}

.avatar-fallback {
  font-size: 30px;
  font-weight: 700;
  color: #246bfd;
}

.identity-name {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  line-height: 1.4;
  color: #17243b;
  word-break: break-word;
}

.identity-username {
  margin: 5px 0 12px;
  font-size: 12px;
  color: #8b98aa;
}

.role-chip {
  display: inline-block;
  padding: 4px 10px;
  font-size: 10.5px;
  font-weight: 600;
  color: #1859df;
  background: #edf4ff;
  border: 1px solid #d4e3ff;
  border-radius: 20px;
}

.identity-meta {
  display: grid;
  gap: 0;
  margin: 24px 0 20px;
  padding: 4px 0;
  text-align: left;
  border-top: 1px solid #e9eef5;
  border-bottom: 1px solid #e9eef5;
}

.identity-meta > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
}

.identity-meta dt {
  font-size: 11.5px;
  color: #8b98aa;
}

.identity-meta dd {
  max-width: 150px;
  margin: 0;
  overflow: hidden;
  font-size: 11.5px;
  font-weight: 600;
  color: #3b4a60;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.identity-meta dd.status-ok {
  color: #2d7a57;
}

.logout-btn {
  width: 100%;
  height: 38px;
  font: inherit;
  font-size: 12.5px;
  font-weight: 600;
  color: #b33636;
  background: #ffffff;
  border: 1px solid #ead2d2;
  border-radius: 8px;
  cursor: pointer;
}

.logout-btn:hover {
  background: #fdf6f6;
  border-color: #dcb6b6;
}

.sync-note {
  margin: 12px 0 0;
  font-size: 10.5px;
  color: #9aa6b6;
}

.account-main {
  display: grid;
  gap: 18px;
}

.profile-panel,
.shortcuts-panel {
  padding: 24px 26px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 17px;
  border-bottom: 1px solid #eef2f7;
}

.panel-head h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #17243b;
}

.panel-head p {
  margin: 5px 0 0;
  font-size: 11.5px;
  line-height: 1.6;
  color: #8b98aa;
}

.action-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 18px;
  padding: 11px 13px;
  font-size: 12px;
  line-height: 1.6;
  border-radius: 8px;
}

.action-alert.error {
  color: #8a4a4a;
  background: #fdf6f6;
  border: 1px solid #f0d2d2;
}

.action-alert.success {
  color: #2d6b4e;
  background: #f3faf6;
  border: 1px solid #cfe8d9;
}

.inline-link {
  flex: 0 0 auto;
  font-size: 11.5px;
  font-weight: 600;
  color: #b33636;
  text-decoration: underline;
}

.inline-link.as-button {
  padding: 0;
  font: inherit;
  font-size: 11.5px;
  font-weight: 600;
  color: #b33636;
  background: transparent;
  border: 0;
  text-decoration: underline;
  cursor: pointer;
}

.avatar-row {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-top: 22px;
  padding-bottom: 22px;
  border-bottom: 1px solid #eef2f7;
}

.avatar-preview-small {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 68px;
  height: 68px;
  overflow: hidden;
  background: #eef4ff;
  border-radius: 50%;
}

.avatar-preview-small img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-preview-small span {
  font-size: 22px;
  font-weight: 700;
  color: #246bfd;
}

.avatar-copy {
  flex: 1;
  min-width: 0;
}

.avatar-copy strong {
  display: block;
  font-size: 12.5px;
  color: #3b4a60;
}

.avatar-copy p {
  margin: 4px 0 10px;
  font-size: 11.5px;
  line-height: 1.6;
  color: #8b98aa;
}

.hidden-input {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.profile-form {
  margin-top: 22px;
}

.ui-field {
  display: grid;
  gap: 8px;
}

.field-label {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-size: 12.5px;
  font-weight: 600;
  color: #3b4a60;
}

.field-label em {
  font-style: normal;
  font-weight: 400;
  color: #9aa6b6;
}

.text-input {
  width: 100%;
  height: 44px;
  padding: 0 13px;
  font: inherit;
  font-size: 13.5px;
  color: #17243b;
  background: #f9fbfe;
  border: 1px solid #e0e7f0;
  border-radius: 9px;
  outline: none;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
}

.text-input::placeholder {
  color: #9ca8b8;
}

.text-input:focus {
  background: #ffffff;
  border-color: #246bfd;
  box-shadow: 0 0 0 3px rgba(36, 107, 253, 0.1);
}

.text-input:disabled {
  color: #8492a6;
  background: #f3f5f9;
  cursor: not-allowed;
}

.form-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-top: 18px;
}

.form-hint {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.6;
  color: #8b98aa;
}

.primary-btn,
.secondary-btn,
.danger-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  height: 38px;
  padding: 0 16px;
  font: inherit;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 8px;
  text-decoration: none;
  cursor: pointer;
  white-space: nowrap;
}

.primary-btn {
  color: #ffffff;
  background: #246bfd;
  border: 1px solid #246bfd;
}

.primary-btn:hover:not(:disabled) {
  background: #1859df;
  border-color: #1859df;
}

.secondary-btn {
  color: #3b4a60;
  background: #ffffff;
  border: 1px solid #d5dfec;
}

.secondary-btn:hover:not(:disabled) {
  border-color: #b4c4d8;
  background: #fbfcfe;
}

.secondary-btn.danger {
  color: #b33636;
  border-color: #ead2d2;
}

.danger-btn {
  color: #ffffff;
  background: #c34848;
  border: 1px solid #c34848;
}

.danger-btn:hover {
  background: #ac3a3a;
  border-color: #ac3a3a;
}

.primary-btn:disabled,
.secondary-btn:disabled {
  cursor: wait;
  opacity: 0.65;
}

.tiny-spinner {
  width: 13px;
  height: 13px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}

.tiny-spinner.dark {
  border-color: rgba(86, 112, 143, 0.25);
  border-top-color: #56708f;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.shortcut-list {
  display: grid;
  margin-top: 6px;
}

.shortcut-item {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 14px 2px;
  color: inherit;
  text-decoration: none;
  border-bottom: 1px solid #eef2f7;
}

.shortcut-item:last-child {
  border-bottom: 0;
  padding-bottom: 2px;
}

.shortcut-item:hover .shortcut-copy strong {
  color: #246bfd;
}

.shortcut-item:hover .shortcut-arrow {
  transform: translateX(2px);
}

.shortcut-mark {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  font-size: 12px;
  font-weight: 600;
  color: #56708f;
  background: #f2f6fc;
  border: 1px solid #e6edf6;
  border-radius: 9px;
}

.shortcut-copy {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 2px;
}

.shortcut-copy strong {
  font-size: 13px;
  font-weight: 600;
  color: #2a3a50;
  transition: color 0.16s ease;
}

.shortcut-copy small {
  font-size: 11px;
  color: #8b98aa;
}

.shortcut-arrow {
  flex: 0 0 auto;
  font-size: 20px;
  line-height: 1;
  color: #a8b5c4;
  transition: transform 0.16s ease;
}

.overview-skeleton {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 40px;
}

.skeleton-avatar {
  width: 84px;
  height: 84px;
  background: #eef2f8;
  border-radius: 50%;
  animation: pulse 1.2s ease-in-out infinite;
}

.skeleton-lines {
  flex: 1;
  display: grid;
  gap: 10px;
}

.skeleton-line {
  width: 45%;
  height: 11px;
  background: #eef2f8;
  border-radius: 6px;
  animation: pulse 1.2s ease-in-out infinite;
}

.skeleton-line.wide {
  width: 30%;
  height: 18px;
}

.skeleton-line.short {
  width: 22%;
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

.load-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 22px 24px;
}

.load-error strong {
  font-size: 13.5px;
  color: #b33636;
}

.load-error p {
  margin: 5px 0 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: #8a4a4a;
}

.load-error-actions {
  display: flex;
  gap: 8px;
  flex: 0 0 auto;
}

.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(23, 36, 59, 0.42);
}

.confirm-panel {
  width: min(400px, 100%);
  padding: 26px;
  background: #ffffff;
  border-radius: 14px;
  box-shadow: 0 28px 70px rgba(23, 36, 59, 0.24);
}

.confirm-panel h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #17243b;
}

.confirm-panel p {
  margin: 10px 0 22px;
  font-size: 12.5px;
  line-height: 1.8;
  color: #6b7a90;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 9px;
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

@container (max-width: 700px) {
  .account-layout {
    grid-template-columns: 1fr;
  }

  .identity-panel {
    position: static;
  }

  .identity-meta {
    max-width: 420px;
    margin-right: auto;
    margin-left: auto;
  }
}

@media (max-width: 900px) {
  .account-layout {
    grid-template-columns: 1fr;
  }

  .identity-panel {
    position: static;
  }
}

@media (max-width: 600px) {
  .page-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .profile-panel,
  .shortcuts-panel {
    padding: 20px 18px;
  }

  .avatar-row {
    align-items: flex-start;
  }

  .form-footer {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .form-footer .primary-btn {
    width: 100%;
  }

  .load-error {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
