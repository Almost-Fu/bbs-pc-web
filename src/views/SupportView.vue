<template>
  <div class="support-view">
    <header class="page-head">
      <div>
        <p class="eyebrow">帮助中心</p>
        <h1>客服对话</h1>
        <p class="page-sub">咨询发帖、头像、关注贴吧与账号使用问题。</p>
      </div>
      <router-link class="head-link" to="/">返回首页</router-link>
    </header>

    <section class="panel chat-panel" aria-labelledby="chat-heading">
      <header class="chat-head">
        <div class="agent">
          <span class="agent-avatar" aria-hidden="true">客</span>
          <div class="agent-copy">
            <h2 id="chat-heading">社区客服小吧</h2>
            <p>智能客服 · 社区使用帮助</p>
          </div>
        </div>
        <div class="chat-head-actions">
          <span class="agent-status">自动应答</span>
          <button
            type="button"
            class="clear-btn"
            :disabled="!messages.length && !draft.length"
            @click="clearChat"
          >
            清空对话
          </button>
        </div>
      </header>

      <div ref="messagesEl" class="chat-body" aria-live="polite">
        <div class="message-row assistant welcome-row">
          <span class="bubble-avatar" aria-hidden="true">客</span>
          <div class="bubble assistant-bubble">
            <p>你好，我是社区客服小吧。发帖、上传头像、关注贴吧、账号登录等问题都可以问我。</p>
            <p class="bubble-note">回答由社区客服接口实时生成；未配置模型时会返回本地知识库内容。</p>
          </div>
        </div>

        <div v-if="showQuick" class="quick-block">
          <p class="quick-title">你可以这样问</p>
          <div class="quick-list">
            <button
              v-for="question in quickQuestions"
              :key="question"
              type="button"
              class="quick-chip"
              :disabled="sending"
              @click="askQuick(question)"
            >
              {{ question }}
            </button>
          </div>
        </div>

        <div
          v-for="message in messages"
          :key="message.id"
          class="message-row"
          :class="message.role"
        >
          <span v-if="message.role === 'assistant'" class="bubble-avatar" aria-hidden="true">客</span>

          <div class="bubble" :class="message.role === 'user' ? 'user-bubble' : 'assistant-bubble'">
            <template v-if="message.failed">
              <p class="failed-text">{{ message.content }}</p>
              <button type="button" class="retry-link" :disabled="sending" @click="retry(message)">
                重新发送
              </button>
            </template>
            <template v-else>
              <p>{{ message.content }}</p>
              <button
                v-if="message.action"
                type="button"
                class="action-btn"
                @click="openAction(message.action)"
              >
                {{ message.action.label }}
                <span aria-hidden="true">→</span>
              </button>
              <span v-if="message.fallback" class="fallback-tag">知识库回答</span>
            </template>
          </div>

          <span v-if="message.role === 'user'" class="bubble-avatar user-avatar" aria-hidden="true">
            {{ userInitial }}
          </span>
        </div>

        <div v-if="sending" class="message-row assistant">
          <span class="bubble-avatar" aria-hidden="true">客</span>
          <div class="bubble assistant-bubble typing-bubble" aria-label="客服正在输入">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
      </div>

      <footer class="composer">
        <div class="composer-input">
          <textarea
            v-model="draft"
            class="chat-input"
            rows="3"
            maxlength="500"
            placeholder="请输入问题（1–500 字）"
            aria-label="客服问题输入"
            @keydown.enter="onEnter"
            @input="draftError = ''"
          ></textarea>
          <div class="composer-meta">
            <span :class="{ over: draft.length > 500 }">{{ draft.length }}/500</span>
            <span>Enter 发送 · Shift + Enter 换行</span>
          </div>
        </div>
        <button type="button" class="send-btn" :disabled="!canSend" @click="send">
          <span v-if="sending" class="send-spinner" aria-hidden="true"></span>
          <span>{{ sending ? '发送中' : '发送' }}</span>
        </button>
      </footer>

      <p v-if="draftError" class="composer-error" role="alert">{{ draftError }}</p>
      <p class="chat-foot">对话保存在当前设备，可随时清空。</p>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { session } from '../session'
import {
  ACTION_TARGETS,
  MAX_MESSAGE_CHARS,
  clearSupportHistory,
  retrySupportMessage,
  sendSupportMessage,
  setSupportDraft,
  supportState,
  syncSupportIdentity
} from '../support-history'

const quickQuestions = ['怎么发帖？', '怎么上传头像？', '怎么关注贴吧？', '忘记密码怎么办？']

const router = useRouter()

const draftError = ref('')
const messagesEl = ref(null)

const messages = computed(() => supportState.messages)
const sending = computed(() => supportState.sending)
const draft = computed({
  get: () => supportState.draft,
  set: (value) => setSupportDraft(value)
})

const userInitial = computed(() => {
  const current = session.user
  const source = String((current && (current.nickname || current.username)) || '我').trim()
  return Array.from(source)[0] || '我'
})

const showQuick = computed(() => !messages.value.some((message) => message.role === 'user'))
const canSend = computed(
  () =>
    !sending.value &&
    !supportState.unresolved &&
    draft.value.trim().length > 0 &&
    draft.value.trim().length <= MAX_MESSAGE_CHARS
)

function scrollToBottom() {
  nextTick(() => {
    const element = messagesEl.value
    if (element) element.scrollTop = element.scrollHeight
  })
}

function send() {
  if (!canSend.value) {
    if (!draft.value.trim()) {
      draftError.value = '请输入要咨询的问题'
    } else if (draft.value.trim().length > MAX_MESSAGE_CHARS) {
      draftError.value = '问题不能超过 500 个字符'
    }
    return
  }
  draftError.value = ''
  if (!sendSupportMessage(draft.value)) {
    draftError.value = '暂时无法发送，请稍后再试'
  }
}

function askQuick(question) {
  if (sending.value) return
  draftError.value = ''
  if (!sendSupportMessage(question)) {
    draftError.value = '暂时无法发送，请稍后再试'
  }
}

function retry(message) {
  if (sending.value) return
  retrySupportMessage(message)
}

function openAction(action) {
  if (!action || !ACTION_TARGETS[action.key]) return
  router.push(ACTION_TARGETS[action.key])
}

function clearChat() {
  clearSupportHistory()
  draftError.value = ''
  scrollToBottom()
}

function onEnter(event) {
  if (event.isComposing || event.keyCode === 229) return
  if (event.shiftKey) return
  event.preventDefault()
  send()
}

// 进入页面先同步当前账号；身份未就绪（authbootstrap）时保持内存态，不写 guest
syncSupportIdentity()

watch(
  () => [session.token, session.user && session.user.id],
  () => {
    syncSupportIdentity()
    scrollToBottom()
  }
)

watch(
  () => [supportState.key, supportState.messages.length, supportState.sending],
  () => scrollToBottom(),
  { flush: 'post' }
)

onMounted(() => {
  syncSupportIdentity()
  scrollToBottom()
})
</script>

<style scoped>
.support-view {
  max-width: 920px;
  margin: 0 auto;
  padding: 4px 0 32px;
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

.head-link {
  flex: 0 0 auto;
  padding-bottom: 2px;
  font-size: 12.5px;
  font-weight: 600;
  color: #246bfd;
  text-decoration: none;
}

.head-link:hover {
  text-decoration: underline;
}

.panel {
  background: #ffffff;
  border: 1px solid #e6ebf3;
  border-radius: 12px;
}

.chat-panel {
  display: flex;
  flex-direction: column;
  height: clamp(520px, 66vh, 700px);
  overflow: hidden;
}

.chat-head {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 15px 20px;
  border-bottom: 1px solid #eef2f7;
}

.agent {
  display: flex;
  align-items: center;
  gap: 11px;
}

.agent-avatar,
.bubble-avatar {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  font-size: 12px;
  font-weight: 700;
  color: #ffffff;
  background: #246bfd;
  border-radius: 50%;
}

.agent-copy h2 {
  margin: 0;
  font-size: 13.5px;
  font-weight: 700;
  color: #17243b;
}

.agent-copy p {
  margin: 2px 0 0;
  font-size: 10.5px;
  color: #8b98aa;
}

.chat-head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.agent-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10.5px;
  font-weight: 600;
  color: #2d7a57;
}

.agent-status::before {
  width: 5px;
  height: 5px;
  content: '';
  background: #48a578;
  border-radius: 50%;
}

.clear-btn {
  height: 29px;
  padding: 0 10px;
  font: inherit;
  font-size: 11px;
  color: #6b7a90;
  background: #ffffff;
  border: 1px solid #e0e7f0;
  border-radius: 7px;
  cursor: pointer;
}

.clear-btn:hover:not(:disabled) {
  color: #246bfd;
  border-color: #b9cef8;
}

.clear-btn:disabled {
  color: #b0bccb;
  border-color: #edf1f6;
  cursor: not-allowed;
}

.chat-body {
  flex: 1;
  min-height: 0;
  padding: 22px 20px 26px;
  overflow-y: auto;
  background: #f8fafd;
  scrollbar-width: thin;
  scrollbar-color: #d6dfea transparent;
}

.message-row {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin-bottom: 17px;
}

.message-row.user {
  justify-content: flex-end;
}

.bubble-avatar {
  width: 30px;
  height: 30px;
  margin-top: 1px;
  font-size: 11px;
  background: #6b8fc9;
}

.user-avatar {
  color: #ffffff;
  background: #17243b;
}

.bubble {
  max-width: min(560px, 78%);
  padding: 11px 14px;
  font-size: 12.5px;
  line-height: 1.8;
  border-radius: 11px;
}

.bubble p {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.assistant-bubble {
  color: #2a3a50;
  background: #ffffff;
  border: 1px solid #e8eef6;
  border-top-left-radius: 4px;
}

.user-bubble {
  color: #ffffff;
  background: #246bfd;
  border-top-right-radius: 4px;
}

.welcome-row .assistant-bubble {
  background: #ffffff;
}

.bubble-note {
  margin-top: 7px !important;
  font-size: 10.5px;
  line-height: 1.6;
  color: #97a3b3;
}

.failed-text {
  color: #a83f3f;
}

.retry-link {
  margin-top: 6px;
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

.retry-link:disabled {
  opacity: 0.55;
  cursor: wait;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 9px;
  padding: 5px 10px;
  font: inherit;
  font-size: 11.5px;
  font-weight: 600;
  color: #246bfd;
  background: #f2f7ff;
  border: 1px solid #d4e3ff;
  border-radius: 7px;
  cursor: pointer;
}

.action-btn:hover {
  background: #eaf2ff;
}

.fallback-tag {
  display: inline-block;
  margin-top: 8px;
  padding: 1px 7px;
  font-size: 9.5px;
  color: #8b7a52;
  background: #fbf7ed;
  border: 1px solid #eee2c8;
  border-radius: 20px;
}

.quick-block {
  margin: 2px 0 20px 39px;
}

.quick-title {
  margin: 0 0 8px;
  font-size: 10.5px;
  color: #97a3b3;
}

.quick-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.quick-chip {
  padding: 5px 11px;
  font: inherit;
  font-size: 11.5px;
  color: #246bfd;
  background: #ffffff;
  border: 1px solid #dbe7fa;
  border-radius: 20px;
  cursor: pointer;
}

.quick-chip:hover:not(:disabled) {
  background: #f2f7ff;
  border-color: #b9cef8;
}

.quick-chip:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.typing-bubble {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 13px 15px;
}

.typing-dot {
  width: 5px;
  height: 5px;
  background: #a4b2c3;
  border-radius: 50%;
  animation: typing 1.1s ease-in-out infinite;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.15s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes typing {
  0%,
  60%,
  100% {
    opacity: 0.35;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

.composer {
  flex: 0 0 auto;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 13px 18px 8px;
  background: #ffffff;
  border-top: 1px solid #eef2f7;
}

.composer-input {
  flex: 1;
  min-width: 0;
}

.chat-input {
  display: block;
  width: 100%;
  min-height: 58px;
  max-height: 132px;
  padding: 10px 12px;
  font: inherit;
  font-size: 12.5px;
  line-height: 1.7;
  color: #2a3a50;
  background: #f8fafd;
  border: 1px solid #e2e9f2;
  border-radius: 9px;
  outline: none;
  resize: vertical;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
}

.chat-input::placeholder {
  color: #9ca8b8;
}

.chat-input:focus {
  background: #ffffff;
  border-color: #246bfd;
  box-shadow: 0 0 0 3px rgba(36, 107, 253, 0.1);
}

.composer-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 4px 2px 0;
  font-size: 9.5px;
  color: #a1adbc;
}

.composer-meta .over {
  color: #b33636;
}

.send-btn {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 74px;
  height: 38px;
  font: inherit;
  font-size: 12.5px;
  font-weight: 600;
  color: #ffffff;
  background: #246bfd;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.16s ease;
}

.send-btn:hover:not(:disabled) {
  background: #1859df;
}

.send-btn:disabled {
  background: #b7caf0;
  cursor: not-allowed;
}

.send-spinner {
  width: 12px;
  height: 12px;
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

.composer-error {
  flex: 0 0 auto;
  margin: 0;
  padding: 0 18px 6px;
  font-size: 10.5px;
  color: #b33636;
  background: #ffffff;
}

.chat-foot {
  flex: 0 0 auto;
  margin: 0;
  padding: 0 18px 11px;
  font-size: 9.5px;
  line-height: 1.6;
  color: #a1adbc;
  background: #ffffff;
}

@media (max-width: 600px) {
  .page-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .chat-panel {
    height: calc(100vh - 230px);
    min-height: 480px;
  }

  .chat-head {
    padding: 13px 15px;
  }

  .agent-status {
    display: none;
  }

  .chat-body {
    padding: 18px 14px 22px;
  }

  .bubble {
    max-width: 84%;
  }

  .quick-block {
    margin-left: 39px;
  }

  .composer {
    padding: 11px 14px 7px;
  }

  .send-btn {
    width: 62px;
  }
}
</style>
