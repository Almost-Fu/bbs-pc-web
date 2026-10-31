<template>
  <article
    class="post-card panel"
    :class="{
      'post-card-single': visibleImages.length === 1,
      'post-card-no-media': visibleImages.length === 0
    }"
  >
    <header class="post-head">
      <div class="bar-identity">
        <span class="bar-mark" aria-hidden="true">
          <span v-if="!barImage || barImageBroken" class="bar-letter">{{ barInitial }}</span>
          <img
            v-else
            :src="barImage"
            alt=""
            loading="lazy"
            referrerpolicy="no-referrer"
            @error="barImageBroken = true"
          />
        </span>
        <div class="bar-meta">
          <RouterLink class="bar-name" :to="barPath" @click.stop>{{ post.barName || '未知贴吧' }}</RouterLink>
          <span class="post-time">{{ post.time || '' }}</span>
        </div>
      </div>
      <span v-if="post.tag" class="tag">{{ post.tag }}</span>
    </header>

    <div class="post-body">
      <RouterLink class="title-link" :to="postPath" @click.stop>
        <h2 class="post-title">{{ post.title || '无标题' }}</h2>
      </RouterLink>

      <p v-if="post.content" class="post-excerpt">{{ post.content }}</p>
    </div>

    <div
      v-if="visibleImages.length"
      class="media"
      :class="{ 'media-single': visibleImages.length === 1 }"
    >
      <button
        v-for="(image, index) in visibleImages.slice(0, 4)"
        :key="`${image}-${index}`"
        type="button"
        class="media-item"
        :aria-label="`预览第 ${index + 1} 张图片`"
        @click.stop="openPreview(index)"
      >
        <img
          :src="image"
          alt=""
          loading="lazy"
          referrerpolicy="no-referrer"
          @error="markImageFailed(image)"
        />
        <span
          v-if="index === 3 && visibleImages.length > 4"
          class="media-more"
        >+{{ visibleImages.length - 4 }}</span>
      </button>
    </div>

    <p v-if="actionError" class="action-error" role="alert">{{ actionError }}</p>

    <footer class="post-foot">
      <div class="author">
        <span class="avatar-wrap" aria-hidden="true">
          <span class="avatar-letter">{{ authorInitial }}</span>
          <img
            v-if="authorAvatar && !authorAvatarBroken"
            :src="authorAvatar"
            alt=""
            loading="lazy"
            referrerpolicy="no-referrer"
            @error="authorAvatarBroken = true"
          />
        </span>
        <span class="author-name">{{ post.author || '匿名用户' }}</span>
      </div>

      <div class="actions">
        <button
          type="button"
          class="action"
          :class="{ active: likeState.liked }"
          :aria-pressed="likeState.liked"
          :disabled="busyLike"
          aria-label="点赞帖子"
          @click.stop="toggleLike"
        >
          <Icon name="like" :size="17" />
          <span>{{ likeState.likes }}</span>
        </button>

        <RouterLink class="action" :to="postPath" aria-label="查看评论" @click.stop>
          <Icon name="chat" :size="17" />
          <span>{{ post.commentCount || 0 }}</span>
        </RouterLink>

        <span class="action action-static" aria-label="浏览量">
          <Icon name="eye" :size="17" />
          <span>{{ post.views || 0 }}</span>
        </span>

        <button
          type="button"
          class="action"
          :class="{ active: likeState.favorited }"
          :aria-pressed="likeState.favorited"
          :disabled="busyFavorite"
          aria-label="收藏帖子"
          @click.stop="toggleFavorite"
        >
          <Icon name="bookmark" :size="17" />
          <span>{{ likeState.favorited ? '已收藏' : '收藏' }}</span>
        </button>
      </div>
    </footer>

    <dialog
      ref="previewDialog"
      class="image-dialog"
      aria-label="图片预览"
      @click="onDialogBackdropClick"
      @close="closePreview"
    >
      <div v-if="previewImage" class="dialog-shell" @click.stop>
        <div class="dialog-bar">
          <span>{{ previewIndex + 1 }} / {{ visibleImages.length }}</span>
          <button type="button" class="dialog-close" aria-label="关闭图片预览" @click="closePreview">关闭</button>
        </div>
        <img :src="previewImage" :alt="post.title || '帖子图片'" referrerpolicy="no-referrer" />
        <div v-if="visibleImages.length > 1" class="dialog-nav">
          <button type="button" aria-label="上一张" @click="stepPreview(-1)">上一张</button>
          <button type="button" aria-label="下一张" @click="stepPreview(1)">下一张</button>
        </div>
      </div>
    </dialog>
  </article>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api, imageUrl } from '../api'
import { session } from '../session'
import Icon from './Icon.vue'

const props = defineProps({
  post: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['changed'])
const route = useRoute()
const router = useRouter()

const busyLike = ref(false)
const busyFavorite = ref(false)
const actionError = ref('')
const barImageBroken = ref(false)
const authorAvatarBroken = ref(false)
const failedImages = ref([])
const previewDialog = ref(null)
const previewIndex = ref(0)

const likeState = reactive({
  liked: false,
  likes: 0,
  favorited: false
})

const postPath = computed(() => `/posts/${props.post.id}`)
const barPath = computed(() => `/bars/${props.post.barId}`)

function safeImage(value) {
  if (!value) return ''
  const resolved = imageUrl(value)
  if (/^https?:\/\//i.test(resolved)) return resolved
  if (resolved.startsWith('/') && !resolved.startsWith('//') && !resolved.startsWith('/\\')) {
    return resolved
  }
  return ''
}

const barImage = computed(() => safeImage(props.post.barImg))
const authorAvatar = computed(() => safeImage(props.post.authorAvatar))
const visibleImages = computed(() => {
  const images = Array.isArray(props.post.images) ? props.post.images : []
  return images
    .map(safeImage)
    .filter((url) => url && !failedImages.value.includes(url))
})

const previewImage = computed(() => visibleImages.value[previewIndex.value] || '')

const barInitial = computed(() => {
  const name = String(props.post.barName || '').trim()
  return name ? name.slice(0, 1) : '吧'
})

const authorInitial = computed(() => {
  const name = String(props.post.author || '').trim()
  return name ? name.slice(0, 1) : '访'
})

function syncLikeState() {
  likeState.liked = Boolean(props.post.liked)
  likeState.likes = Number(props.post.likes) || 0
  likeState.favorited = Boolean(props.post.favorited)
}

watch(
  () => [
    props.post.id,
    props.post.liked,
    props.post.likes,
    props.post.favorited
  ],
  syncLikeState,
  { immediate: true }
)

watch(
  () => props.post.id,
  () => {
    barImageBroken.value = false
    authorAvatarBroken.value = false
    failedImages.value = []
    actionError.value = ''
    closePreview()
  }
)

function requireLogin() {
  if (session.token) return true
  router.push({ path: '/login', query: { redirect: route.fullPath } })
  return false
}

function markImageFailed(url) {
  if (!failedImages.value.includes(url)) {
    failedImages.value = [...failedImages.value, url]
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

function patchPost(patch) {
  emit('changed', { ...props.post, ...patch })
}

async function toggleLike() {
  actionError.value = ''
  if (!requireLogin() || busyLike.value) return
  busyLike.value = true
  const target = !likeState.liked
  try {
    const result = await api.likePost(props.post.id, target)
    const liked = typeof result?.liked === 'boolean' ? result.liked : target
    const likes = Number.isFinite(Number(result?.likes))
      ? Math.max(0, Number(result.likes))
      : Math.max(0, likeState.likes + (target ? 1 : -1))
    likeState.liked = liked
    likeState.likes = likes
    patchPost({ liked, likes })
  } catch (error) {
    actionError.value = error?.message || '点赞失败，请稍后重试'
  } finally {
    busyLike.value = false
  }
}

async function toggleFavorite() {
  actionError.value = ''
  if (!requireLogin() || busyFavorite.value) return
  busyFavorite.value = true
  const target = !likeState.favorited
  try {
    const result = await api.favoritePost(props.post.id, target)
    const favorited = typeof result?.favorited === 'boolean' ? result.favorited : target
    likeState.favorited = favorited
    patchPost({ favorited })
  } catch (error) {
    actionError.value = error?.message || '收藏失败，请稍后重试'
  } finally {
    busyFavorite.value = false
  }
}
</script>

<style scoped>
.post-card {
  padding: 16px 18px 12px;
  border-radius: 12px;
  border: 1px solid #e7ecf5;
  background: #ffffff;
  transition: box-shadow 0.18s ease, border-color 0.18s ease;
}

.post-card:hover {
  border-color: #dbe5f5;
  box-shadow: 0 4px 14px rgba(31, 69, 128, 0.055);
}

.post-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.bar-identity {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 8px;
}

.bar-mark {
  position: relative;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  overflow: hidden;
  border-radius: 8px;
  background: #eef4ff;
  color: #246bfd;
  font-size: 12px;
  font-weight: 700;
}

.bar-mark img {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.bar-letter {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
}

.bar-meta {
  display: flex;
  align-items: baseline;
  min-width: 0;
  gap: 8px;
}

.bar-name {
  overflow: hidden;
  color: #17243b;
  font-size: 13px;
  font-weight: 650;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-decoration: none;
}

.bar-name:hover {
  color: #246bfd;
}

.post-time {
  flex: 0 0 auto;
  color: #98a5ba;
  font-size: 12px;
}

.tag {
  flex: 0 0 auto;
  max-width: 130px;
  overflow: hidden;
  padding: 3px 9px;
  border-radius: 6px;
  background: #f1f5fb;
  color: #5b6b83;
  font-size: 11px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.post-body {
  display: grid;
  gap: 10px;
  min-width: 0;
  margin-top: 8px;
}

.title-link {
  display: block;
  color: inherit;
  text-align: left;
  text-decoration: none;
}

.post-title {
  margin: 0;
  color: #17243b;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.45;
  letter-spacing: -0.01em;
}

.title-link:hover .post-title {
  color: #246bfd;
}

.post-excerpt {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: #5f6e84;
  font-size: 13px;
  line-height: 1.5;
  white-space: normal;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.media {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  width: min(100%, 744px);
  margin-top: 12px;
}

.media.media-single {
  grid-template-columns: minmax(0, 1fr);
}

.media-item {
  position: relative;
  display: block;
  overflow: hidden;
  width: 100%;
  max-width: 180px;
  min-width: 0;
  padding: 0;
  border: 0;
  border-radius: 10px;
  background: #f1f5fb;
  aspect-ratio: 3 / 2;
  cursor: zoom-in;
}

.media.media-single .media-item {
  max-width: 320px;
  height: 180px;
  aspect-ratio: auto;
}

.media-item img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.25s ease;
}

.media-item:hover img {
  transform: scale(1.025);
}

.media-more {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(16, 29, 51, 0.6);
  color: #ffffff;
  font-size: 18px;
  font-weight: 650;
}

.action-error {
  margin: 10px 0 0;
  color: #c23434;
  font-size: 12px;
  line-height: 1.5;
}

.post-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f3f8;
}

.author {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 8px;
}

.avatar-wrap {
  position: relative;
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  flex: 0 0 26px;
  overflow: hidden;
  border-radius: 50%;
  background: #eef4ff;
  color: #246bfd;
  font-size: 11px;
  font-weight: 700;
}

.avatar-wrap img {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-letter {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
}

.author-name {
  overflow: hidden;
  color: #68788f;
  font-size: 12px;
  font-weight: 550;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actions {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 2px;
}

.action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-width: 44px;
  min-height: 28px;
  padding: 3px 8px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #7b899f;
  font: inherit;
  font-size: 12px;
  line-height: 1;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.16s ease, background 0.16s ease;
}

.action:hover:not(:disabled) {
  background: #f4f7fc;
  color: #246bfd;
}

.action.active {
  color: #246bfd;
  background: #edf3ff;
}

.action:disabled {
  cursor: wait;
  opacity: 0.6;
}

.action-static {
  cursor: default;
}

.action-static:hover {
  background: transparent;
  color: #7b899f;
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

.dialog-close,
.dialog-nav button {
  padding: 8px 14px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

.dialog-close:hover,
.dialog-nav button:hover {
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

@media (min-width: 761px) {
  .post-card:not(.post-card-no-media) {
    display: grid;
    grid-template-columns: minmax(240px, 280px) minmax(0, 1fr);
    grid-template-areas:
      "head head"
      "media title"
      "media excerpt"
      "error error"
      "foot foot";
    align-items: start;
    column-gap: 20px;
    row-gap: 8px;
  }

  .post-card:not(.post-card-no-media) > .post-head {
    grid-area: head;
  }

  .post-card:not(.post-card-no-media) > .post-body {
    grid-area: title / title / excerpt / excerpt;
    align-content: start;
    align-self: start;
    min-width: 0;
    margin-top: 0;
  }

  .post-card:not(.post-card-no-media) > .media {
    grid-area: media;
    width: 100%;
    max-width: 280px;
    margin-top: 0;
  }

  .post-card:not(.post-card-no-media) > .media:not(.media-single) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .post-card:not(.post-card-no-media) > .action-error {
    grid-area: error;
    margin-top: 0;
  }

  .post-card:not(.post-card-no-media) > .post-foot {
    grid-area: foot;
    width: 100%;
    margin-top: 0;
  }

  .post-card-single .media.media-single .media-item {
    width: 100%;
    max-width: 280px;
    height: auto;
    aspect-ratio: 280 / 158;
  }

  .post-card:not(.post-card-no-media) .post-title {
    overflow-wrap: anywhere;
  }
}

@media (max-width: 760px) {
  .post-card {
    padding: 15px 14px 10px;
  }

  .post-title {
    font-size: 17px;
  }

  .post-foot {
    align-items: flex-start;
    flex-direction: column;
  }

  .actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
