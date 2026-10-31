<template>
  <div class="auth-view">
    <section class="auth-shell" aria-labelledby="auth-title">
      <aside class="auth-intro">
        <div>
          <p class="intro-mark">BBS COMMUNITY</p>
          <h1>在共同的兴趣里，<br />找到认真交流的人。</h1>
          <p class="intro-copy">
            登录后即可发布图文、收藏帖子并查看互动消息。希望你能在这里找到同好，认真交流，也自在分享。
          </p>
        </div>
        <ul class="intro-points">
          <li>
            <span class="point-dot" aria-hidden="true"></span>
            <span>发布帖子，最多可上传 9 张图片</span>
          </li>
          <li>
            <span class="point-dot" aria-hidden="true"></span>
            <span>关注感兴趣的贴吧，持续参与讨论</span>
          </li>
          <li>
            <span class="point-dot" aria-hidden="true"></span>
            <span>点赞、回复与 @ 消息分类查看</span>
          </li>
        </ul>
        <p class="intro-foot">愿每次交流都有回应，也愿你在这里找到同好。</p>
      </aside>

      <div class="auth-form-panel">
        <header class="form-head">
          <p class="eyebrow">{{ isRegister ? '创建账号' : '欢迎回来' }}</p>
          <h2 id="auth-title">{{ isRegister ? '注册社区账号' : '登录社区' }}</h2>
          <p class="form-sub">
            {{ isRegister ? '填写信息后即可直接进入社区。' : '使用已有账号继续浏览与互动。' }}
          </p>
        </header>

        <div v-if="error" class="form-alert" role="alert">
          <div>
            <strong>操作未完成</strong>
            <p>{{ error }}</p>
          </div>
          <button type="button" class="alert-retry" @click="submit">重试</button>
        </div>

        <form class="auth-form" novalidate @submit.prevent="submit">
          <label class="ui-field" for="auth-username">
            <span class="field-label">用户名</span>
            <input
              id="auth-username"
              v-model="username"
              class="text-input"
              type="text"
              autocomplete="username"
              maxlength="20"
              placeholder="2–20 个字符"
              :disabled="loading"
              @input="error = ''"
            />
          </label>

          <label v-if="isRegister" class="ui-field" for="auth-nickname">
            <span class="field-label">
              昵称
              <em>选填</em>
            </span>
            <input
              id="auth-nickname"
              v-model="nickname"
              class="text-input"
              type="text"
              autocomplete="nickname"
              maxlength="20"
              placeholder="留空则使用用户名"
              :disabled="loading"
              @input="error = ''"
            />
          </label>

          <label class="ui-field" for="auth-password">
            <span class="field-label">密码</span>
            <input
              id="auth-password"
              v-model="password"
              class="text-input"
              type="password"
              :autocomplete="isRegister ? 'new-password' : 'current-password'"
              maxlength="32"
              :placeholder="isRegister ? '至少 6 位字符' : '请输入当前密码'"
              :disabled="loading"
              @input="error = ''"
            />
          </label>

          <label v-if="isRegister" class="ui-field" for="auth-confirm">
            <span class="field-label">确认密码</span>
            <input
              id="auth-confirm"
              v-model="confirmPassword"
              class="text-input"
              type="password"
              autocomplete="new-password"
              maxlength="32"
              placeholder="请再次输入密码"
              :disabled="loading"
              @input="error = ''"
            />
          </label>

          <button class="submit-btn" type="submit" :disabled="loading">
            <span v-if="loading" class="spinner" aria-hidden="true"></span>
            <span>{{ loading ? (isRegister ? '正在创建账号…' : '正在登录…') : (isRegister ? '注册并进入' : '登录') }}</span>
          </button>
        </form>

        <p class="auth-switch">
          {{ isRegister ? '已经有账号了？' : '还没有账号？' }}
          <router-link :to="switchTarget" :aria-disabled="loading ? 'true' : 'false'" :class="{ disabled: loading }">
            {{ isRegister ? '直接登录' : '注册一个账号' }}
          </router-link>
        </p>

        <p v-if="redirectHint" class="redirect-hint">登录后将继续刚才的操作</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { safeRedirect as resolveSafeRedirect } from '../router'
import { setSession } from '../session'

const route = useRoute()
const router = useRouter()

const isRegister = computed(() => route.path === '/register')

const username = ref('')
const nickname = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')

let submitSeq = 0

/** 只接受站内绝对路径；//evil.com 这类协议相对地址一律回首页 */
function validRedirect(raw) {
  const value = Array.isArray(raw) ? raw[0] : raw
  if (typeof value !== 'string') return ''
  return resolveSafeRedirect(value.trim(), '')
}

const redirectTarget = computed(() => {
  const target = validRedirect(route.query.redirect)
  return target && target !== '/' ? target : ''
})
const redirectPath = computed(() => redirectTarget.value || '/')
const redirectHint = computed(() => Boolean(redirectTarget.value))

const switchTarget = computed(() => ({
  path: isRegister.value ? '/login' : '/register',
  query: redirectTarget.value ? { redirect: redirectTarget.value } : {}
}))

watch(
  () => route.path,
  () => {
    submitSeq += 1
    loading.value = false
    error.value = ''
    password.value = ''
    confirmPassword.value = ''
    if (route.path === '/login') nickname.value = ''
  }
)

function messageOf(err, fallback) {
  const text = err && typeof err.message === 'string' ? err.message.trim() : ''
  if (text && !/failed to fetch|networkerror|load failed|fetch failed/i.test(text)) return text
  const status = err && (err.status || err.code)
  if (status === 401) return isRegister.value ? '注册信息校验失败，请检查后重试' : '用户名或密码错误'
  if (status === 403) return '账号已被禁用，请联系管理员'
  if (status === 429) return '尝试次数过多，请稍后再试'
  if (status === 400) return '提交的信息不符合要求，请检查后重试'
  return fallback
}

function validate() {
  const name = username.value.trim()
  if (!name) return '请输入用户名'
  if (name.length < 2 || name.length > 20) return '用户名需为 2–20 个字符'

  if (!isRegister.value) {
    if (!password.value) return '请输入密码'
    return ''
  }

  if (nickname.value.trim().length > 20) return '昵称不能超过 20 个字符'
  if (!password.value) return '请输入密码'
  if (password.value.length < 6) return '密码至少需要 6 位'
  if (password.value.length > 32) return '密码不能超过 32 位'
  if (password.value !== confirmPassword.value) return '两次输入的密码不一致'
  return ''
}

async function submit() {
  if (loading.value) return

  const invalid = validate()
  if (invalid) {
    error.value = invalid
    return
  }

  const current = ++submitSeq
  loading.value = true
  error.value = ''

  try {
    const data = isRegister.value
      ? await api.register({
          username: username.value.trim(),
          password: password.value,
          nickname: nickname.value.trim() || username.value.trim()
        })
      : await api.login(username.value.trim(), password.value)

    if (current !== submitSeq) return

    if (!data || typeof data.token !== 'string' || !data.token) {
      throw new Error('服务器返回的登录信息不完整，请重试')
    }

    setSession({ token: data.token, user: data.user || null })
    await router.replace(redirectPath.value)
  } catch (err) {
    if (current !== submitSeq) return
    error.value = messageOf(err, isRegister.value ? '注册失败，请稍后重试' : '登录失败，请稍后重试')
  } finally {
    if (current === submitSeq) loading.value = false
  }
}
</script>

<style scoped>
.auth-view {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 12px 0 32px;
  container-type: inline-size;
}

.auth-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(380px, 430px);
  min-height: 590px;
  background: #ffffff;
  border: 1px solid #e6ebf3;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 22px 60px rgba(23, 36, 59, 0.08);
}

.auth-intro {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 36px;
  padding: 52px 54px 44px;
  color: #ffffff;
  background: #246bfd;
}

.intro-mark {
  margin: 0 0 22px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: rgba(255, 255, 255, 0.68);
}

.auth-intro h1 {
  margin: 0;
  font-size: 34px;
  font-weight: 700;
  line-height: 1.42;
  letter-spacing: -0.02em;
}

.intro-copy {
  max-width: 360px;
  margin: 22px 0 0;
  font-size: 14px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.78);
}

.intro-points {
  display: grid;
  gap: 16px;
  margin: 0;
  padding: 26px 0;
  list-style: none;
  border-top: 1px solid rgba(255, 255, 255, 0.18);
  border-bottom: 1px solid rgba(255, 255, 255, 0.18);
}

.intro-points li {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  font-size: 13.5px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.9);
}

.point-dot {
  flex: 0 0 auto;
  width: 5px;
  height: 5px;
  margin-top: 8px;
  border-radius: 50%;
  background: #ffffff;
}

.intro-foot {
  margin: 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.58);
}

.auth-form-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 52px 46px;
}

.form-head {
  margin-bottom: 26px;
}

.eyebrow {
  margin: 0 0 10px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  color: #246bfd;
}

.form-head h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.35;
  color: #17243b;
}

.form-sub {
  margin: 10px 0 0;
  font-size: 13.5px;
  line-height: 1.7;
  color: #6b7a90;
}

.form-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  padding: 13px 15px;
  border: 1px solid #f3d2d2;
  border-radius: 10px;
  background: #fdf6f6;
}

.form-alert strong {
  display: block;
  font-size: 13px;
  color: #b33636;
}

.form-alert p {
  margin: 4px 0 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: #8a4a4a;
}

.alert-retry {
  flex: 0 0 auto;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #b33636;
  background: #ffffff;
  border: 1px solid #e9bcbc;
  border-radius: 7px;
  cursor: pointer;
}

.alert-retry:hover {
  background: #fff9f9;
}

.auth-form {
  display: grid;
  gap: 18px;
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
  color: #98a4b5;
}

.text-input {
  width: 100%;
  height: 46px;
  padding: 0 14px;
  font: inherit;
  font-size: 14px;
  color: #17243b;
  background: #f8fafe;
  border: 1px solid #dfe6f0;
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
  box-shadow: 0 0 0 3px rgba(36, 107, 253, 0.12);
}

.text-input:disabled {
  color: #8d99a9;
  background: #f3f5f9;
  cursor: not-allowed;
}

.submit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  width: 100%;
  height: 48px;
  margin-top: 6px;
  font: inherit;
  font-size: 14.5px;
  font-weight: 600;
  color: #ffffff;
  background: #246bfd;
  border: 0;
  border-radius: 9px;
  cursor: pointer;
  transition: background 0.16s ease, transform 0.16s ease;
}

.submit-btn:hover:not(:disabled) {
  background: #1859df;
}

.submit-btn:active:not(:disabled) {
  transform: translateY(1px);
}

.submit-btn:disabled {
  background: #9db8f8;
  cursor: wait;
}

.spinner {
  width: 15px;
  height: 15px;
  border: 2px solid rgba(255, 255, 255, 0.42);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.auth-switch {
  margin: 22px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: #6b7a90;
  text-align: center;
}

.auth-switch a {
  margin-left: 4px;
  font-weight: 600;
  color: #246bfd;
  text-decoration: none;
}

.auth-switch a:hover {
  text-decoration: underline;
}

.auth-switch a.disabled {
  pointer-events: none;
  opacity: 0.5;
}

.redirect-hint {
  margin: 14px 0 0;
  font-size: 11.5px;
  line-height: 1.6;
  color: #98a4b5;
  text-align: center;
  word-break: break-all;
}

@container (max-width: 900px) {
  .auth-intro {
    padding: 42px 34px 36px;
  }

  .auth-intro h1 {
    font-size: 28px;
  }

  .intro-copy {
    margin-top: 17px;
    font-size: 13px;
  }

  .auth-form-panel {
    padding: 42px 32px;
  }
}

@container (max-width: 720px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }

  .auth-intro {
    padding: 36px 32px 30px;
  }

  .intro-points {
    display: none;
  }

  .auth-form-panel {
    padding: 38px 32px 42px;
  }
}

@container (max-width: 560px) {
  .auth-intro {
    padding: 28px 24px;
  }

  .auth-form-panel {
    padding: 30px 22px 34px;
  }
}

@media (max-width: 900px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }

  .auth-intro {
    padding: 34px 32px 30px;
  }

  .auth-intro h1 {
    font-size: 27px;
  }

  .intro-points {
    display: none;
  }

  .auth-form-panel {
    padding: 36px 30px 40px;
  }
}

@media (max-width: 560px) {
  .auth-view {
    padding-top: 0;
  }

  .auth-intro {
    padding: 28px 24px;
  }

  .auth-form-panel {
    padding: 30px 22px 34px;
  }
}
</style>
