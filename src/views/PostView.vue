<template>
  <div class="post-view">
    <div class="crumbs">
      <button type="button" class="back-button" @click="goBack">
        <Icon name="back" :size="16" />
        返回
      </button>
      <nav class="crumb-links" aria-label="面包屑">
        <RouterLink to="/">首页</RouterLink>
        <span aria-hidden="true">/</span>
        <template v-if="post">
          <RouterLink :to="`/bars/${post.barId}`">{{ post.barName || '贴吧' }}</RouterLink>
          <span aria-hidden="true">/</span>
          <span class="current">帖子详情</span>
        </template>
        <span v-else class="current">帖子详情</span>
      </nav>
    </div>

    <section v-if="loading" class="detail-loading" aria-busy="true" aria-label="正在加载帖子">
      <div class="detail-skeleton panel">
        <div class="skeleton-line skeleton-short"></div>
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line skeleton-title-short"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line skeleton-short"></div>
      </div>
      <p class="loading-note">正在加载帖子…</p>
    </section>

    <section v-else-if="error" class="error-state panel" role="alert">
      <span class="state-mark">!</span>
      <h2>帖子加载失败</h2>
      <p>{{ error }}</p>
      <div class="state-actions">
        <button type="button" class="btn btn-primary" @click="loadAll">重新加载</button>
        <RouterLink class="btn btn-ghost" to="/">返回首页</RouterLink>
      </div>
    </section>

    <template v-else-if="post">
      <article class="detail-card panel">
        <header class="detail-head">
          <div class="head-left">
            <RouterLink class="bar-link" :to="`/bars/${post.barId}`">
              <span class="bar-mark" aria-hidden="true">
                <span v-if="!barImage || barImageBroken" class="bar-initial">{{ barInitial }}</span>
                <img
                  v-else
                  :src="barImage"
                  alt=""
                  referrerpolicy="no-referrer"
                  @error="barImageBroken = true"
                />
              </span>
              <span class="bar-name">{{ post.barName || '未知贴吧' }}</span>
            </RouterLink>
            <span v-if="post.tag" class="tag">{{ post.tag }}</span>
            <span class="post-time">{{ post.time || '' }}</span>
          </div>
          <div class="head-actions">
            <RouterLink
              v-if="isAuthor"
              class="edit-link"
              :to="`/posts/${post.id}/edit`"
            >
              编辑帖子
            </RouterLink>
            <span v-if="post.isTop" class="top-label">置顶</span>
          </div>
        </header>

        <h1 class="post-title">{{ post.title || '无标题' }}</h1>

        <div class="byline">
          <span class="author-avatar" aria-hidden="true">
            <span class="avatar-initial">{{ authorInitial }}</span>
            <img
              v-if="authorAvatar && !authorAvatarBroken"
              :src="authorAvatar"
              alt=""
              referrerpolicy="no-referrer"
              @error="authorAvatarBroken = true"
            />
          </span>
          <span class="author-name">{{ post.author || '匿名用户' }}</span>
        </div>

        <div class="post-content">{{ post.content }}</div>

        <div
          v-if="visibleImages.length"
          class="gallery"
          :class="{ 'gallery-single': visibleImages.length === 1 }"
        >
          <button
            v-for="(image, index) in visibleImages"
            :key="`${image}-${index}`"
            type="button"
            class="gallery-item"
            :aria-label="`预览第 ${index + 1} 张图片`"
            @click="openPreview(index)"
          >
            <img
              :src="image"
              :alt="post.title || '帖子图片'"
              loading="lazy"
              referrerpolicy="no-referrer"
              @error="markImageFailed(image)"
            />
          </button>
        </div>

        <p v-if="actionError" class="action-error" role="alert">{{ actionError }}</p>

        <footer class="detail-actions">
          <button
            type="button"
            class="detail-action"
            :class="{ active: post.liked }"
            :aria-pressed="post.liked"
            :disabled="busyAction === 'like'"
            @click="toggleLike"
          >
            <Icon name="like" :size="18" />
            <span>{{ post.likes || 0 }}</span>
            <span class="action-label">点赞</span>
          </button>

          <button type="button" class="detail-action" @click="scrollToComments">
            <Icon name="chat" :size="18" />
            <span>{{ post.commentCount || 0 }}</span>
            <span class="action-label">评论</span>
          </button>

          <span class="detail-action detail-static">
            <Icon name="eye" :size="18" />
            <span>{{ post.views || 0 }}</span>
            <span class="action-label">浏览</span>
          </span>

          <button
            type="button"
            class="detail-action favorite-action"
            :class="{ active: post.favorited }"
            :aria-pressed="post.favorited"
            :disabled="busyAction === 'favorite'"
            @click="toggleFavorite"
          >
            <Icon name="bookmark" :size="18" />
            <span>{{ post.favorited ? '已收藏' : '收藏' }}</span>
          </button>
        </footer>
      </article>

      <section id="comments" ref="commentsSection" class="comments-panel panel">
        <header class="comments-head">
          <div>
            <span class="comments-kicker">DISCUSSION</span>
            <h2>评论 <span class="comments-count">{{ shownCommentsCount }}</span></h2>
          </div>
          <span class="comments-note">保持友善，认真交流</span>
        </header>

        <form v-if="session.token" class="comment-composer" @submit.prevent="submitComment">
          <span class="comment-avatar" aria-hidden="true">
            <span class="avatar-initial">{{ myInitial }}</span>
            <img
              v-if="myAvatar && !myAvatarBroken"
              :src="myAvatar"
              alt=""
              referrerpolicy="no-referrer"
              @error="myAvatarBroken = true"
            />
          </span>
          <div class="composer-main">
            <textarea
              v-model="commentText"
              rows="3"
              maxlength="1000"
              placeholder="写下你的看法，和大家一起讨论…"
              :disabled="submitting"
              aria-label="评论内容"
            ></textarea>
            <div class="composer-foot">
              <span class="char-count">{{ commentText.length }} / 1000</span>
              <button
                type="submit"
                class="btn btn-primary comment-submit"
                :disabled="submitting || (commentsLoading && !commentsLoaded)"
              >{{ submitting ? '发布中…' : '发布评论' }}</button>
            </div>
            <p v-if="commentFormError" class="form-error" role="alert">{{ commentFormError }}</p>
          </div>
        </form>

        <div v-else class="login-callout">
          <div>
            <strong>登录后参与讨论</strong>
            <span>和社区里的朋友分享你的看法。</span>
          </div>
          <button type="button" class="btn btn-primary" @click="goLogin">登录评论</button>
        </div>

        <div v-if="commentsLoading && !commentsLoaded" class="comments-loading" aria-busy="true">
          <div class="comment-skeleton">
            <span></span>
            <div>
              <i></i>
              <i></i>
            </div>
          </div>
          <div class="comment-skeleton">
            <span></span>
            <div>
              <i></i>
              <i></i>
            </div>
          </div>
          <p class="loading-note">正在加载评论…</p>
        </div>

        <div v-else-if="commentsError && !commentsLoaded" class="comments-error" role="alert">
          <span>{{ commentsError }}</span>
          <button type="button" class="text-action" @click="retryComments">重试</button>
        </div>

        <div v-else-if="!displayedComments.length" class="comments-empty">
          <span class="empty-mark">
            <Icon name="chat" :size="23" />
          </span>
          <h3>还没有评论</h3>
          <p>来写下第一条评论，开启这段讨论。</p>
        </div>

        <div v-else class="comment-list">
          <article v-for="comment in displayedComments" :key="comment.id" class="comment-item">
            <span class="comment-avatar" aria-hidden="true">
              <span class="avatar-initial">{{ initialOf(comment.author) }}</span>
              <img
                v-if="commentAvatar(comment) && !brokenCommentAvatars.includes(comment.id)"
                :src="commentAvatar(comment)"
                alt=""
                loading="lazy"
                referrerpolicy="no-referrer"
                @error="markCommentAvatarBroken(comment.id)"
              />
            </span>
            <div class="comment-main">
              <div class="comment-head">
                <strong>{{ comment.author || '匿名用户' }}</strong>
                <span>{{ comment.time || '' }}</span>
              </div>
              <p class="comment-text">{{ comment.text }}</p>
              <div class="comment-meta">
                <span class="comment-like">
                  <Icon name="like" :size="14" />
                  {{ comment.likes || 0 }}
                </span>
              </div>
            </div>
          </article>
        </div>

        <div v-if="commentsLoaded && displayedComments.length" class="comments-pagination">
          <span>已展示 {{ displayedComments.length }} / {{ commentsTotal }} 条</span>
          <span v-if="commentsMoreError" class="load-more-error" role="alert">
            {{ commentsMoreError }}
            <button type="button" class="text-action" @click="loadMoreComments">重试</button>
          </span>
          <button
            v-else-if="commentsHasMore"
            type="button"
            class="btn btn-ghost load-more"
            :disabled="commentsLoading"
            @click="loadMoreComments"
          >{{ commentsLoading ? '加载中…' : '加载更多评论' }}</button>
          <span v-else class="pagination-end">已加载全部评论</span>
        </div>
      </section>
    </template>

    <dialog
      ref="previewDialog"
      class="image-dialog"
      aria-label="图片预览"
      @click="onDialogBackdropClick"
      @close="previewIndex = 0"
    >
      <div v-if="previewImage" class="dialog-shell" @click.stop>
        <div class="dialog-bar">
          <span>{{ previewIndex + 1 }} / {{ visibleImages.length }}</span>
          <button type="button" class="dialog-button" aria-label="关闭图片预览" @click="closePreview">关闭</button>
        </div>
        <img :src="previewImage" :alt="post?.title || '帖子图片'" referrerpolicy="no-referrer" />
        <div v-if="visibleImages.length > 1" class="dialog-nav">
          <button type="button" class="dialog-button" aria-label="上一张" @click="stepPreview(-1)">上一张</button>
          <button type="button" class="dialog-button" aria-label="下一张" @click="stepPreview(1)">下一张</button>
        </div>
      </div>
    </dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api, imageUrl } from '../api'
import { session } from '../session'
import Icon from '../components/Icon.vue'

const COMMENT_PAGE_SIZE = 20

const route = useRoute()
const router = useRouter()

const post = ref(null)
const loading = ref(true)
const error = ref('')
const busyAction = ref('')
const actionError = ref('')

const comments = ref([])
const pendingComments = ref([])
const commentsLoaded = ref(false)
const commentsLoading = ref(false)
const commentsError = ref('')
const commentsMoreError = ref('')
const commentsTotal = ref(0)
const commentsPage = ref(0)
const commentsTotalPages = ref(0)
const commentsHasMore = ref(false)

const commentText = ref('')
const commentFormError = ref('')
const submitting = ref(false)

const barImageBroken = ref(false)
const authorAvatarBroken = ref(false)
const myAvatarBroken = ref(false)
const failedImages = ref([])
const brokenCommentAvatars = ref([])
const previewDialog = ref(null)
const previewIndex = ref(0)
const commentsSection = ref(null)

let requestSeq = 0

function safeImage(value) {
  if (!value) return ''
  const resolved = imageUrl(value)
  if (/^https?:\/\//i.test(resolved)) return resolved
  if (resolved.startsWith('/') && !resolved.startsWith('//') && !resolved.startsWith('/\\')) {
    return resolved
  }
  return ''
}

const authorAvatar = computed(() => safeImage(post.value?.authorAvatar))
const myAvatar = computed(() => safeImage(session.user?.avatar))
const barImage = computed(() => safeImage(post.value?.barImg))
const isAuthor = computed(() => {
  const myId = session.user && session.user.id
  return myId != null && post.value?.authorId != null && Number(myId) === Number(post.value.authorId)
})

const visibleImages = computed(() => {
  const images = Array.isArray(post.value?.images) ? post.value.images : []
  return images
    .map(safeImage)
    .filter((url) => url && !failedImages.value.includes(url))
})

const previewImage = computed(() => visibleImages.value[previewIndex.value] || '')

function mergeCommentsById(primary, extra) {
  const seen = new Set()
  const merged = []
  for (const comment of [...primary, ...extra]) {
    if (!comment) continue
    if (comment.id != null) {
      if (seen.has(comment.id)) continue
      seen.add(comment.id)
    }
    merged.push(comment)
  }
  return merged
}

// 新发布的评论单独放在列表末尾，避免在尚未加载完分页时插到旧评论之间。
// 合并时按 id 去重：后端后续分页若包含刚发布的评论，只保留服务端返回的那一条。
const displayedComments = computed(() => mergeCommentsById(comments.value, pendingComments.value))

const barInitial = computed(() => initialOf(post.value?.barName, '吧'))
const authorInitial = computed(() => initialOf(post.value?.author, '访'))
const myInitial = computed(() => initialOf(session.user?.nickname || session.user?.username, '我'))

const shownCommentsCount = computed(() => {
  if (commentsLoaded.value) return commentsTotal.value
  return Math.max(0, Number(post.value?.commentCount) || 0)
})

function initialOf(value, fallback = '访') {
  const name = String(value || '').trim()
  return name ? name.slice(0, 1) : fallback
}

function commentAvatar(comment) {
  return safeImage(comment?.authorAvatar)
}

function markCommentAvatarBroken(id) {
  if (!brokenCommentAvatars.value.includes(id)) {
    brokenCommentAvatars.value = [...brokenCommentAvatars.value, id]
  }
}

function markImageFailed(url) {
  if (!failedImages.value.includes(url)) {
    failedImages.value = [...failedImages.value, url]
  }
}

function parsePostId() {
  const value = Number(route.params.id)
  return Number.isInteger(value) && value > 0 ? value : null
}

function resetComments() {
  comments.value = []
  pendingComments.value = []
  commentsLoaded.value = false
  commentsLoading.value = false
  commentsError.value = ''
  commentsMoreError.value = ''
  commentsTotal.value = 0
  commentsPage.value = 0
  commentsTotalPages.value = 0
  commentsHasMore.value = false
}

async function loadAll() {
  const postId = parsePostId()
  const seq = ++requestSeq

  post.value = null
  loading.value = true
  error.value = ''
  busyAction.value = ''
  actionError.value = ''
  commentText.value = ''
  commentFormError.value = ''
  submitting.value = false
  barImageBroken.value = false
  authorAvatarBroken.value = false
  myAvatarBroken.value = false
  failedImages.value = []
  brokenCommentAvatars.value = []
  resetComments()
  closePreview()

  if (!postId) {
    loading.value = false
    error.value = '帖子地址无效，请返回列表重新选择。'
    return
  }

  try {
    const data = await api.post(postId)
    if (seq !== requestSeq) return
    if (!data || typeof data !== 'object') {
      throw new Error('帖子数据返回异常，请稍后重试')
    }
    post.value = data
  } catch (requestError) {
    if (seq !== requestSeq) return
    error.value = requestError?.message || '网络异常，请稍后重试'
  } finally {
    if (seq === requestSeq) loading.value = false
  }

  if (post.value && seq === requestSeq) {
    loadComments(true, seq)
  }
}

async function loadComments(reset, seq = requestSeq) {
  if (commentsLoading.value) return
  const postId = parsePostId()
  if (!postId) return

  commentsLoading.value = true
  if (reset) {
    commentsError.value = ''
    commentsMoreError.value = ''
  } else {
    commentsMoreError.value = ''
  }

  const targetPage = reset ? 1 : commentsPage.value + 1

  try {
    const data = await api.comments(postId, { page: targetPage, pageSize: COMMENT_PAGE_SIZE })
    if (seq !== requestSeq) return
    if (!data || !Array.isArray(data.list)) {
      throw new Error('评论数据返回异常，请稍后重试')
    }

    const list = data.list
    comments.value = mergeCommentsById(reset ? [] : comments.value, list)
    const loadedIds = new Set(
      comments.value
        .map((comment) => comment.id)
        .filter((id) => id != null)
    )
    pendingComments.value = pendingComments.value.filter(
      (comment) => comment.id == null || !loadedIds.has(comment.id)
    )
    commentsPage.value = Math.max(1, Number(data.page) || targetPage)
    commentsTotal.value = Math.max(0, Number(data.total) || 0)
    commentsTotalPages.value = Math.max(0, Number(data.totalPages) || 0)
    commentsHasMore.value = typeof data.hasMore === 'boolean'
      ? data.hasMore
      : (commentsTotalPages.value > 0 ? commentsPage.value < commentsTotalPages.value : false)
    commentsLoaded.value = true
    commentsError.value = ''
  } catch (requestError) {
    if (seq !== requestSeq) return
    if (reset) {
      commentsLoaded.value = false
      commentsError.value = requestError?.message || '评论加载失败，请稍后重试'
    } else {
      commentsMoreError.value = requestError?.message || '加载更多评论失败，请稍后重试'
    }
  } finally {
    if (seq === requestSeq) commentsLoading.value = false
  }
}

function retryComments() {
  loadComments(true)
}

function loadMoreComments() {
  if (commentsLoading.value || !commentsHasMore.value) return
  loadComments(false)
}

function requireLogin() {
  if (session.token) return true
  router.push({ path: '/login', query: { redirect: route.fullPath } })
  return false
}

function goLogin() {
  router.push({ path: '/login', query: { redirect: route.fullPath } })
}

async function toggleLike() {
  actionError.value = ''
  if (!post.value || busyAction.value || !requireLogin()) return

  const postId = post.value.id
  const target = !post.value.liked
  const previousLikes = Math.max(0, Number(post.value.likes) || 0)
  const seq = requestSeq
  const token = session.token
  const isCurrentRequest = () => (
    seq === requestSeq &&
    session.token === token &&
    parsePostId() === postId &&
    post.value?.id === postId
  )

  busyAction.value = 'like'
  try {
    const result = await api.likePost(postId, target)
    if (!isCurrentRequest()) return

    const liked = typeof result?.liked === 'boolean' ? result.liked : target
    const likes = Number.isFinite(Number(result?.likes))
      ? Math.max(0, Number(result.likes))
      : Math.max(0, previousLikes + (target ? 1 : -1))
    post.value = { ...post.value, liked, likes }
  } catch (requestError) {
    if (!isCurrentRequest()) return
    actionError.value = requestError?.message || '点赞失败，请稍后重试'
  } finally {
    if (isCurrentRequest()) busyAction.value = ''
  }
}

async function toggleFavorite() {
  actionError.value = ''
  if (!post.value || busyAction.value || !requireLogin()) return

  const postId = post.value.id
  const target = !post.value.favorited
  const seq = requestSeq
  const token = session.token
  const isCurrentRequest = () => (
    seq === requestSeq &&
    session.token === token &&
    parsePostId() === postId &&
    post.value?.id === postId
  )

  busyAction.value = 'favorite'
  try {
    const result = await api.favoritePost(postId, target)
    if (!isCurrentRequest()) return

    const favorited = typeof result?.favorited === 'boolean' ? result.favorited : target
    post.value = { ...post.value, favorited }
  } catch (requestError) {
    if (!isCurrentRequest()) return
    actionError.value = requestError?.message || '收藏失败，请稍后重试'
  } finally {
    if (isCurrentRequest()) busyAction.value = ''
  }
}

async function submitComment() {
  commentFormError.value = ''
  if (!post.value || submitting.value) return
  if (!requireLogin()) return

  const text = commentText.value.trim()
  if (!text) {
    commentFormError.value = '评论内容不能为空'
    return
  }
  if (text.length > 1000) {
    commentFormError.value = '评论内容不能超过 1000 个字符'
    return
  }

  submitting.value = true
  const seq = requestSeq
  try {
    const created = await api.addComment(post.value.id, text)
    if (seq !== requestSeq) return
    if (!created || created.id == null) {
      throw new Error('评论已发送，但返回数据异常，请刷新后查看')
    }

    const previousCount = Math.max(0, Number(post.value.commentCount) || 0)
    const alreadyLoaded = comments.value.some((comment) => comment.id === created.id)
    const nextCount = alreadyLoaded
      ? Math.max(previousCount + 1, commentsTotal.value)
      : (commentsLoaded.value ? commentsTotal.value : previousCount) + 1
    if (!alreadyLoaded) {
      pendingComments.value = mergeCommentsById(pendingComments.value, [created])
    }
    commentsLoaded.value = true
    commentsError.value = ''
    commentsTotal.value = nextCount
    post.value = { ...post.value, commentCount: previousCount + 1 }
    commentText.value = ''

    await nextTick()
    const items = commentsSection.value?.querySelectorAll('.comment-item')
    const lastItem = items?.[items.length - 1]
    if (lastItem && typeof lastItem.scrollIntoView === 'function') {
      lastItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  } catch (requestError) {
    if (seq !== requestSeq) return
    commentFormError.value = requestError?.message || '评论发布失败，请稍后重试'
  } finally {
    if (seq === requestSeq) submitting.value = false
  }
}

function scrollToComments() {
  if (typeof commentsSection.value?.scrollIntoView === 'function') {
    commentsSection.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

function openPreview(index) {
  if (!visibleImages.value.length) return
  previewIndex.value = Math.min(index, visibleImages.value.length - 1)
  const dialog = previewDialog.value
  if (!dialog) return
  if (typeof dialog.showModal === 'function' && !dialog.open) {
    dialog.showModal()
  } else if (!dialog.open) {
    dialog.setAttribute('open', '')
  }
}

function closePreview() {
  const dialog = previewDialog.value
  if (!dialog || !dialog.open) return
  if (typeof dialog.close === 'function') dialog.close()
  else dialog.removeAttribute('open')
}

function stepPreview(direction) {
  const total = visibleImages.value.length
  if (total < 2) return
  previewIndex.value = (previewIndex.value + direction + total) % total
}

function onDialogBackdropClick(event) {
  if (event.target === previewDialog.value) closePreview()
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/')
}

watch(
  () => session.token,
  () => {
    busyAction.value = ''
    actionError.value = ''
  }
)

watch(
  () => route.params.id,
  () => loadAll(),
  { immediate: true }
)
</script>

<style scoped>
.post-view {
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
  overflow: hidden;
  max-width: 190px;
  color: #7e8da2;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.crumb-links a:hover {
  color: #246bfd;
}

.crumb-links .current {
  color: #4d5d74;
}

.detail-card {
  padding: 28px 30px 22px;
  border: 1px solid #e6ecf6;
  border-radius: 17px;
  background: #ffffff;
}

.detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.head-left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  min-width: 0;
  gap: 9px;
}

.bar-link {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  gap: 8px;
  color: #17243b;
  text-decoration: none;
}

.bar-mark {
  position: relative;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  overflow: hidden;
  border-radius: 9px;
  background: #eef4ff;
  color: #246bfd;
  font-size: 13px;
  font-weight: 750;
}

.bar-mark img {
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

.bar-name {
  overflow: hidden;
  max-width: 260px;
  font-size: 12px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-link:hover .bar-name {
  color: #246bfd;
}

.tag {
  padding: 3px 8px;
  border-radius: 5px;
  background: #f1f5fb;
  color: #5b6b83;
  font-size: 10px;
  line-height: 1.5;
}

.post-time {
  color: #99a6b8;
  font-size: 11px;
}

.head-actions {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 8px;
}

.edit-link {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 11px;
  border: 1px solid #d7e4fb;
  border-radius: 7px;
  background: #f5f9ff;
  color: #246bfd;
  font-size: 11px;
  font-weight: 650;
  text-decoration: none;
  transition: background-color 0.16s ease, border-color 0.16s ease;
}

.edit-link:hover {
  border-color: #b8cff8;
  background: #edf4ff;
}

.top-label {
  flex: 0 0 auto;
  padding: 3px 8px;
  border-radius: 5px;
  background: #edf3ff;
  color: #246bfd;
  font-size: 10px;
  font-weight: 650;
}

.post-title {
  margin: 18px 0 0;
  color: #17243b;
  font-size: 29px;
  font-weight: 750;
  line-height: 1.42;
  letter-spacing: -0.025em;
  overflow-wrap: anywhere;
}

.byline {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 15px;
}

.author-avatar,
.comment-avatar {
  position: relative;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 50%;
  background: #eef4ff;
  color: #246bfd;
  font-size: 11px;
  font-weight: 700;
}

.author-avatar {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
}

.author-avatar img,
.comment-avatar img {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-initial {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
}

.author-name {
  color: #5f7089;
  font-size: 12px;
  font-weight: 600;
}

.post-content {
  margin-top: 22px;
  color: #34445c;
  font-size: 15px;
  line-height: 1.9;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.gallery {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 20px;
}

.gallery.gallery-single {
  grid-template-columns: minmax(0, 1fr);
}

.gallery-item {
  display: block;
  overflow: hidden;
  min-width: 0;
  padding: 0;
  border: 0;
  border-radius: 10px;
  background: #f1f5fb;
  aspect-ratio: 4 / 3;
  cursor: zoom-in;
}

.gallery.gallery-single .gallery-item {
  max-height: 460px;
  aspect-ratio: 16 / 8;
}

.gallery-item img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.25s ease;
}

.gallery-item:hover img {
  transform: scale(1.02);
}

.action-error {
  margin: 13px 0 0;
  color: #c23434;
  font-size: 12px;
  line-height: 1.6;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 22px;
  padding-top: 16px;
  border-top: 1px solid #f0f3f8;
}

.detail-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 11px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #708097;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease;
}

.detail-action:hover:not(:disabled) {
  background: #f4f7fc;
  color: #246bfd;
}

.detail-action.active {
  background: #edf3ff;
  color: #246bfd;
}

.detail-action:disabled {
  cursor: wait;
  opacity: 0.65;
}

.detail-static {
  cursor: default;
}

.detail-static:hover {
  background: transparent;
  color: #708097;
}

.action-label {
  color: #9aa7b9;
  font-size: 10px;
}

.detail-action.active .action-label {
  color: #5689f5;
}

.favorite-action {
  margin-left: auto;
}

.comments-panel {
  padding: 24px 26px;
  border: 1px solid #e6ecf6;
  border-radius: 17px;
  background: #ffffff;
  scroll-margin-top: 16px;
}

.comments-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
  padding-bottom: 15px;
  border-bottom: 1px solid #f0f3f8;
}

.comments-kicker {
  display: block;
  color: #246bfd;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.14em;
  line-height: 1.5;
}

.comments-head h2 {
  margin: 4px 0 0;
  color: #223149;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.45;
}

.comments-count {
  color: #246bfd;
  font-size: 15px;
}

.comments-note {
  color: #a1adbd;
  font-size: 10px;
}

.comment-composer {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  margin-top: 17px;
}

.comment-avatar {
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  margin-top: 2px;
}

.composer-main {
  min-width: 0;
  flex: 1;
}

.composer-main textarea {
  display: block;
  width: 100%;
  min-height: 82px;
  box-sizing: border-box;
  padding: 11px 12px;
  resize: vertical;
  border: 1px solid #dfe7f3;
  border-radius: 9px;
  outline: 0;
  background: #f9fbfe;
  color: #26354c;
  font: inherit;
  font-size: 13px;
  line-height: 1.65;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
}

.composer-main textarea:focus {
  border-color: #9dbcfb;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(36, 107, 253, 0.08);
}

.composer-main textarea::placeholder {
  color: #a3afc0;
}

.composer-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
}

.char-count {
  color: #a0acbd;
  font-size: 10px;
}

.comment-submit {
  min-height: 30px;
  padding: 0 13px;
  border-radius: 7px;
  font-size: 11px;
  font-weight: 650;
}

.comment-submit:disabled {
  cursor: wait;
  opacity: 0.65;
}

.form-error {
  margin: 7px 0 0;
  color: #c23434;
  font-size: 11px;
  line-height: 1.6;
}

.login-callout {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 17px;
  padding: 13px 14px;
  border: 1px solid #e5edfa;
  border-radius: 10px;
  background: #f8faff;
}

.login-callout strong {
  display: block;
  color: #34445c;
  font-size: 12px;
  font-weight: 650;
}

.login-callout span {
  display: block;
  margin-top: 3px;
  color: #8a98ad;
  font-size: 11px;
}

.login-callout .btn {
  min-height: 30px;
  padding: 0 13px;
  border-radius: 7px;
  font-size: 11px;
}

.comments-loading,
.comments-error,
.comments-empty {
  margin-top: 20px;
}

.comment-skeleton {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 13px 0;
  border-bottom: 1px solid #f4f6fa;
}

.comment-skeleton > span {
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  border-radius: 50%;
  background: #eef2f8;
  animation: soft-pulse 1.5s ease-in-out infinite;
}

.comment-skeleton > div {
  min-width: 0;
  flex: 1;
}

.comment-skeleton i {
  display: block;
  width: 72%;
  height: 9px;
  margin-top: 8px;
  border-radius: 5px;
  background: #eef2f8;
  animation: soft-pulse 1.5s ease-in-out infinite;
}

.comment-skeleton i:first-child {
  width: 24%;
  margin-top: 2px;
}

.comments-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 13px;
  border: 1px solid #f0dada;
  border-radius: 9px;
  background: #fff9f9;
  color: #b63c3c;
  font-size: 12px;
}

.comments-empty {
  display: flex;
  align-items: center;
  flex-direction: column;
  padding: 34px 20px 27px;
  text-align: center;
}

.empty-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #eef4ff;
  color: #246bfd;
}

.comments-empty h3 {
  margin: 11px 0 0;
  color: #34445c;
  font-size: 14px;
  font-weight: 650;
}

.comments-empty p {
  margin: 5px 0 0;
  color: #96a3b6;
  font-size: 11px;
}

.comment-list {
  display: flex;
  flex-direction: column;
  margin-top: 11px;
}

.comment-item {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 16px 0;
  border-bottom: 1px solid #f2f5f9;
}

.comment-item:last-child {
  border-bottom: 0;
}

.comment-main {
  min-width: 0;
  flex: 1;
}

.comment-head {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
}

.comment-head strong {
  color: #34445c;
  font-size: 12px;
  font-weight: 650;
}

.comment-head span {
  color: #a0acbd;
  font-size: 10px;
}

.comment-text {
  margin: 7px 0 0;
  color: #53647c;
  font-size: 13px;
  line-height: 1.75;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.comment-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 7px;
}

.comment-like {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #94a1b4;
  font-size: 10px;
}

.comments-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 12px;
  padding-top: 13px;
  border-top: 1px solid #f0f3f8;
  color: #93a0b3;
  font-size: 11px;
}

.load-more {
  height: 31px;
  padding: 0 14px;
  border-radius: 7px;
  font-size: 11px;
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

.detail-skeleton {
  padding: 25px 26px;
  border: 1px solid #e7ecf5;
  border-radius: 16px;
  background: #ffffff;
}

.skeleton-line {
  height: 10px;
  margin-top: 11px;
  border-radius: 5px;
  background: #eef2f8;
  animation: soft-pulse 1.5s ease-in-out infinite;
}

.skeleton-line:first-child {
  margin-top: 0;
}

.skeleton-title {
  width: 74%;
  height: 26px;
  margin-top: 22px;
}

.skeleton-title-short {
  width: 45%;
  height: 20px;
  margin-top: 8px;
}

.skeleton-short {
  width: 23%;
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

.error-state {
  display: flex;
  align-items: center;
  flex-direction: column;
  padding: 44px 24px;
  border: 1px solid #e7ecf5;
  border-radius: 14px;
  background: #ffffff;
  text-align: center;
}

.state-mark {
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

.error-state h2 {
  margin: 13px 0 0;
  color: #25344b;
  font-size: 16px;
  font-weight: 700;
}

.error-state p {
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

.image-dialog {
  width: 100vw;
  max-width: none;
  height: 100vh;
  max-height: none;
  margin: 0;
  padding: 24px;
  border: 0;
  background: transparent;
  color: #ffffff;
}

.image-dialog::backdrop {
  background: rgba(10, 19, 34, 0.78);
  backdrop-filter: blur(3px);
}

.dialog-shell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  gap: 12px;
}

.dialog-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: min(1040px, 100%);
  color: #dce7fb;
  font-size: 12px;
}

.dialog-button {
  padding: 8px 14px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

.dialog-button:hover {
  background: rgba(255, 255, 255, 0.17);
}

.dialog-shell > img {
  display: block;
  width: auto;
  max-width: min(1040px, 100%);
  max-height: calc(100vh - 140px);
  border-radius: 10px;
  object-fit: contain;
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.28);
}

.dialog-nav {
  display: flex;
  gap: 10px;
}

@media (max-width: 760px) {
  .detail-card,
  .comments-panel {
    padding: 19px 17px;
  }

  .post-title {
    font-size: 23px;
  }

  .gallery {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .comments-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 3px;
  }

  .detail-actions {
    flex-wrap: wrap;
  }

  .favorite-action {
    margin-left: 0;
  }

  .comments-pagination {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
