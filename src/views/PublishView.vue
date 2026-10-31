<template>
  <div class="publish-view">
    <div class="publish-content">
      <header class="page-head">
        <div>
          <p class="eyebrow">{{ editing ? '编辑帖子' : '创作中心' }}</p>
          <h1>{{ editing ? '编辑帖子' : '发布新帖' }}</h1>
          <p class="page-sub">
            {{
              editing
                ? '可以修改标题、正文、话题和贴吧；帖子原有图片会保持不变。'
                : '写下标题与正文，选择贴吧和分类，最多附带 9 张图片。'
            }}
          </p>
        </div>
        <router-link class="head-link" :to="editing ? `/posts/${editPostId}` : '/my-posts'">
          {{ editing ? '返回帖子' : '查看我的帖子' }}
        </router-link>
      </header>

      <div v-if="successPost && !editing" class="result-banner" role="status">
        <div>
          <strong>发布成功</strong>
          <p>帖子已经写入社区，可立即查看或继续发布下一篇。</p>
        </div>
        <div class="result-actions">
          <router-link v-if="successPost.id != null" class="banner-btn primary" :to="`/posts/${successPost.id}`">
            查看帖子
          </router-link>
          <button type="button" class="banner-btn" @click="successPost = null">继续发布</button>
        </div>
      </div>

      <div v-if="error" class="error-alert" role="alert">
        <div>
          <strong>{{ editing ? '保存未完成' : '发布未完成' }}</strong>
          <p>{{ error }}</p>
        </div>
        <div class="alert-actions">
          <router-link
            v-if="!session.token"
            class="alert-btn"
            :to="{ path: '/login', query: { redirect: route.fullPath } }"
          >
            重新登录
          </router-link>
          <button type="button" class="alert-btn" :disabled="submitting" @click="submit">
            {{ editing ? '重试保存' : '重试发布' }}
          </button>
        </div>
      </div>

      <div v-if="editing && editLoading" class="panel edit-state" aria-busy="true">
        <span class="spinner spinner-dark" aria-hidden="true"></span>
        <p>正在加载帖子内容…</p>
      </div>

      <div v-else-if="editing && editError" class="error-alert" role="alert">
        <div>
          <strong>无法编辑</strong>
          <p>{{ editError }}</p>
        </div>
        <div class="alert-actions">
          <router-link class="alert-btn" :to="editPostId ? `/posts/${editPostId}` : '/'">
            返回帖子
          </router-link>
        </div>
      </div>

      <div v-else class="compose-layout">
        <section class="panel editor-panel" aria-labelledby="editor-heading">
          <h2 id="editor-heading" class="sr-only">帖子内容</h2>

          <label class="title-field" for="post-title">
            <span class="field-label">
              标题
              <em>{{ title.length }}/100</em>
            </span>
            <input
              id="post-title"
              v-model="title"
              class="title-input"
              type="text"
              maxlength="100"
              placeholder="给帖子起一个清晰的标题"
              :disabled="submitting"
              @input="error = ''"
            />
          </label>

          <label class="content-field" for="post-content">
            <span class="field-label">
              正文
              <em>{{ content.length }}/2000</em>
            </span>
            <textarea
              id="post-content"
              v-model="content"
              class="content-input"
              rows="12"
              maxlength="2000"
              placeholder="分享你的经历、问题或见解…"
              :disabled="submitting"
              @input="error = ''"
            ></textarea>
          </label>

          <div class="media-block">
            <div class="media-head">
              <div>
                <span class="field-label">图片</span>
                <p class="media-note">
                  {{
                    editing
                      ? '本次只修改文字与贴吧，帖子原有图片会完整保留，不支持增删图片。'
                      : '支持 JPG、PNG、GIF、WebP、BMP，单张不超过 5MB。'
                  }}
                </p>
              </div>
              <span class="media-count">{{ editing ? existingImages.length : images.length }}/9</span>
            </div>

            <template v-if="editing">
              <div v-if="existingImages.length" class="image-grid">
                <figure v-for="image in existingImages" :key="image.id" class="image-item">
                  <button
                    type="button"
                    class="image-preview"
                    :aria-label="`预览${image.name}`"
                    @click="preview = image"
                  >
                    <img :src="image.url" :alt="image.name" />
                  </button>
                </figure>
              </div>
              <p v-else class="media-keep-empty">本帖没有图片，编辑不会新增图片。</p>
              <p class="media-notice keep-notice" role="status">图片保持原样，不会随本次编辑变动。</p>
            </template>

            <template v-else>
              <input
                ref="fileInput"
                class="file-input"
                type="file"
                accept=".jpg,.jpeg,.png,.gif,.webp,.bmp,image/*"
                multiple
                :disabled="submitting"
                @change="onFileChange"
              />

              <div
                class="image-grid"
                :class="{ dragging: dragActive }"
                @dragover.prevent="dragActive = true"
                @dragleave.prevent="dragActive = false"
                @drop.prevent="onDrop"
              >
                <figure v-for="image in images" :key="image.id" class="image-item">
                  <button
                    type="button"
                    class="image-preview"
                    :disabled="submitting"
                    :aria-label="`预览图片 ${image.name}`"
                    @click="preview = image"
                  >
                    <img :src="image.url" :alt="image.name" />
                  </button>
                  <button
                    type="button"
                    class="image-remove"
                    :disabled="submitting"
                    :aria-label="`移除图片 ${image.name}`"
                    @click="removeImage(image.id)"
                  >
                    ×
                  </button>
                </figure>

                <button
                  v-if="images.length < MAX_IMAGES"
                  type="button"
                  class="image-add"
                  :disabled="submitting"
                  @click="chooseFiles"
                >
                  <span class="add-plus" aria-hidden="true"></span>
                  <span>添加图片</span>
                  <small>也可拖拽到此处</small>
                </button>
              </div>

              <p v-if="notice" class="media-notice" role="status">{{ notice }}</p>
            </template>
          </div>
        </section>

        <aside class="side-column">
          <section class="panel settings-panel" aria-labelledby="settings-heading">
            <div class="settings-head">
              <h2 id="settings-heading">{{ editing ? '编辑设置' : '发布设置' }}</h2>
              <span class="settings-hint">{{ editing ? '保存后立即生效' : '发布后不可在这里修改' }}</span>
            </div>

            <div class="setting-block">
              <span class="setting-label">选择贴吧</span>
              <button type="button" class="bar-select" :disabled="submitting" @click="openPicker">
                <img
                  v-if="selectedBar && selectedBar.img"
                  class="bar-select-img"
                  :src="imageUrl(selectedBar.img)"
                  :alt="selectedBar.name"
                />
                <span v-else class="bar-select-placeholder" aria-hidden="true">吧</span>
                <span class="bar-select-name" :class="{ muted: !selectedBar }">
                  {{ selectedBar ? selectedBar.name : '选择要发布的贴吧' }}
                </span>
                <span class="select-arrow" aria-hidden="true">›</span>
              </button>

              <p v-if="barsLoading" class="inline-state">正在加载贴吧…</p>
              <p v-else-if="barsError" class="inline-error">
                {{ barsError }}
                <button type="button" class="text-btn" @click="loadBars">重试</button>
              </p>
              <p v-else-if="!bars.length" class="inline-error">
                暂无可发布的贴吧
                <button type="button" class="text-btn" @click="loadBars">刷新</button>
              </p>
            </div>

            <div class="setting-block">
              <label class="setting-label" for="post-tag">分类标签</label>
              <input
                id="post-tag"
                v-model="tag"
                class="tag-input"
                type="text"
                maxlength="32"
                placeholder="如：分享、求助、讨论"
                :disabled="submitting"
              />
              <div class="tag-chips" role="group" aria-label="常用分类">
                <button
                  v-for="item in tagOptions"
                  :key="item"
                  type="button"
                  class="tag-chip"
                  :class="{ active: tag === item }"
                  :disabled="submitting"
                  @click="tag = item"
                >
                  {{ item }}
                </button>
              </div>
            </div>

            <div class="publish-summary">
              <div>
                <span>目标贴吧</span>
                <strong>{{ selectedBar ? selectedBar.name : '未选择' }}</strong>
              </div>
              <div>
                <span>{{ editing ? '保留图片' : '已选图片' }}</span>
                <strong>{{ editing ? existingImages.length : images.length }} 张</strong>
              </div>
            </div>

            <button class="submit-btn" type="button" :disabled="submitting" @click="submit">
              <span v-if="submitting" class="spinner" aria-hidden="true"></span>
              <span>
                {{
                  submitting
                    ? (editing ? '正在保存…' : '正在发布…')
                    : (editing ? '保存修改' : '发布帖子')
                }}
              </span>
            </button>

            <p class="submit-note">
              {{ editing ? '保存后自动返回帖子详情，可立即看到最新内容。' : '发布成功后，可在「我的帖子」中查看。' }}
            </p>
          </section>

          <section class="panel guide-panel" aria-labelledby="guide-heading">
            <h2 id="guide-heading">{{ editing ? '编辑提示' : '发布提示' }}</h2>
            <ul v-if="editing">
              <li>只有原作者可以编辑，保存后修改立即生效。</li>
              <li>本次不会改动帖子图片、点赞和评论。</li>
              <li>正文为纯文本展示，不支持脚本或外链嵌入。</li>
            </ul>
            <ul v-else>
              <li>标题简明扼要，便于其他用户快速理解主题。</li>
              <li>正文为纯文本展示，不支持脚本或外链嵌入。</li>
              <li>图片会随表单一次性上传，请确认内容后再发布。</li>
            </ul>
          </section>
        </aside>
      </div>
    </div>

    <div v-if="pickerOpen" class="modal-mask" @click.self="closePicker">
      <section class="picker-panel" role="dialog" aria-modal="true" aria-labelledby="picker-title">
        <header class="picker-head">
          <div>
            <h2 id="picker-title">选择贴吧</h2>
            <p>从社区现有贴吧中选择发布位置。</p>
          </div>
          <button type="button" class="icon-btn" aria-label="关闭" @click="closePicker">×</button>
        </header>

        <label class="picker-search" for="bar-search">
          <span aria-hidden="true">搜索</span>
          <input
            id="bar-search"
            ref="barSearchInput"
            v-model="barKeyword"
            type="search"
            placeholder="输入吧名筛选"
            autocomplete="off"
          />
        </label>

        <div class="picker-body">
          <p v-if="barsLoading" class="picker-state">正在加载贴吧…</p>
          <div v-else-if="barsError" class="picker-state">
            <p>{{ barsError }}</p>
            <button type="button" class="text-btn" @click="loadBars">重新加载</button>
          </div>
          <p v-else-if="!bars.length" class="picker-state">社区暂时还没有可发布的贴吧。</p>
          <p v-else-if="!filteredBars.length" class="picker-state">没有找到匹配的贴吧。</p>
          <div v-else class="picker-list">
            <button
              v-for="bar in filteredBars"
              :key="bar.id"
              type="button"
              class="picker-item"
              :class="{ selected: selectedBar && selectedBar.id === bar.id }"
              @click="selectBar(bar)"
            >
              <img v-if="bar.img" class="picker-item-img" :src="imageUrl(bar.img)" :alt="bar.name" />
              <span v-else class="picker-item-placeholder" aria-hidden="true">吧</span>
              <span class="picker-item-text">
                <strong>{{ bar.name }}</strong>
                <small>{{ bar.desc || '社区贴吧' }}</small>
              </span>
              <span v-if="selectedBar && selectedBar.id === bar.id" class="picker-check">已选择</span>
            </button>
          </div>
        </div>
      </section>
    </div>

    <div v-if="preview" class="modal-mask preview-mask" @click.self="preview = null">
      <div class="preview-box" role="dialog" aria-modal="true" aria-label="图片预览">
        <img :src="preview.url" :alt="preview.name" />
        <button type="button" class="preview-close" aria-label="关闭预览" @click="preview = null">×</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, imageUrl } from '../api'
import { session } from '../session'

const MAX_IMAGES = 9
const MAX_IMAGE_BYTES = 5 * 1024 * 1024
const IMAGE_EXT = /\.(jpe?g|png|gif|webp|bmp)$/i

const route = useRoute()
const router = useRouter()

const editPostId = computed(() => {
  if (route.name !== 'post-edit') return null
  const value = Number(route.params.id)
  return Number.isInteger(value) && value > 0 ? value : null
})
const editing = computed(() => route.name === 'post-edit' && editPostId.value != null)
const editLoading = ref(false)
const editError = ref('')
const existingImages = ref([])

const bars = ref([])
const barsLoading = ref(Boolean(session.token))
const barsError = ref('')
const selectedBar = ref(null)
const pickerOpen = ref(false)
const barKeyword = ref('')
const barSearchInput = ref(null)

const title = ref('')
const content = ref('')
const tag = ref('')
const tagOptions = ['分享', '求助', '讨论', '攻略', '闲聊']

const images = ref([])
const preview = ref(null)
const dragActive = ref(false)
const notice = ref('')
const submitting = ref(false)
const error = ref('')
const successPost = ref(null)

const fileInput = ref(null)

let barsSeq = 0
let imageKey = 0
let disposed = false

const filteredBars = computed(() => {
  const keyword = barKeyword.value.trim().toLowerCase()
  if (!keyword) return bars.value
  return bars.value.filter((bar) => {
    const name = String(bar.name || '').toLowerCase()
    const desc = String(bar.desc || '').toLowerCase()
    return name.includes(keyword) || desc.includes(keyword)
  })
})

function errorText(err, fallback) {
  const text = err && typeof err.message === 'string' ? err.message.trim() : ''
  if (text && !/failed to fetch|networkerror|load failed|fetch failed/i.test(text)) return text
  const status = err && (err.status || err.code)
  if (status === 401) return '登录状态已失效，请重新登录后再操作'
  if (status === 403) return editing.value ? '只能编辑自己发布的帖子' : '当前账号没有发布权限'
  if (status === 404) return editing.value ? '帖子不存在或已被删除' : '目标贴吧不存在，请重新选择'
  if (status === 413) return '图片体积过大，请压缩后重试'
  if (status === 429) return '操作过于频繁，请稍后再试'
  if (status >= 500) return '服务器暂时不可用，请稍后重试'
  return fallback
}

async function loadBars() {
  const current = ++barsSeq
  barsLoading.value = true
  barsError.value = ''

  try {
    const data = await api.bars()
    if (disposed || current !== barsSeq) return
    bars.value = Array.isArray(data) ? data : []
    if (selectedBar.value && !bars.value.some((bar) => bar.id === selectedBar.value.id)) {
      selectedBar.value = null
    }
    if (!editing.value) applyQueryBar()
  } catch (err) {
    if (disposed || current !== barsSeq) return
    bars.value = []
    barsError.value = errorText(err, '贴吧列表加载失败，请重试')
  } finally {
    if (!disposed && current === barsSeq) barsLoading.value = false
  }
}

function applyQueryBar() {
  const raw = route.query.barId
  const value = Array.isArray(raw) ? raw[0] : raw
  if (value == null || value === '') return
  const id = Number(value)
  if (!Number.isFinite(id)) return
  const found = bars.value.find((bar) => Number(bar.id) === id)
  if (found) selectedBar.value = found
}

async function loadEditPost() {
  const postId = editPostId.value
  editLoading.value = true
  editError.value = ''
  existingImages.value = []

  if (!postId) {
    editLoading.value = false
    editError.value = '帖子地址无效，请返回重试。'
    return
  }

  try {
    const data = await api.post(postId)
    if (!data || typeof data !== 'object') {
      throw new Error('帖子数据返回异常，请稍后重试')
    }

    let myId = session.user && session.user.id
    if (myId == null) {
      // 本地缓存里只有 token 没有用户信息时，先补一次当前用户，避免误判成非作者
      const me = await api.me()
      myId = me && me.id
    }
    if (myId == null || Number(myId) !== Number(data.authorId)) {
      editError.value = '只能编辑自己发布的帖子。'
      return
    }

    title.value = data.title || ''
    content.value = data.content || ''
    tag.value = data.tag && data.tag !== '未分类' ? data.tag : ''
    existingImages.value = (Array.isArray(data.images) ? data.images : []).map((raw, index) => ({
      id: `existing-${index}`,
      url: imageUrl(raw),
      name: `原有图片 ${index + 1}`
    }))

    const found = bars.value.find((bar) => Number(bar.id) === Number(data.barId))
    selectedBar.value =
      found ||
      (data.barId != null
        ? { id: data.barId, name: data.barName || '原贴吧', img: data.barImg || '', desc: '' }
        : null)
  } catch (err) {
    editError.value = errorText(err, '帖子加载失败，请稍后重试')
  } finally {
    editLoading.value = false
  }
}

function openPicker() {
  if (submitting.value) return
  barKeyword.value = ''
  pickerOpen.value = true
  nextTick(() => barSearchInput.value && barSearchInput.value.focus())
}

function closePicker() {
  pickerOpen.value = false
}

function selectBar(bar) {
  selectedBar.value = bar
  error.value = ''
  closePicker()
}

function chooseFiles() {
  if (submitting.value) return
  if (fileInput.value) fileInput.value.click()
}

function onFileChange(event) {
  const input = event.target
  const files = input && input.files ? input.files : []
  ingestFiles(files)
  if (input) input.value = ''
}

function onDrop(event) {
  dragActive.value = false
  if (submitting.value) return
  const files = event.dataTransfer && event.dataTransfer.files ? event.dataTransfer.files : []
  ingestFiles(files)
}

function ingestFiles(fileList) {
  const incoming = Array.from(fileList || [])
  if (!incoming.length) return

  error.value = ''
  notice.value = ''

  const signatures = new Set(images.value.map((item) => `${item.file.name}:${item.file.size}:${item.file.lastModified}`))
  const additions = []
  let formatSkipped = 0
  let sizeSkipped = 0
  let overflow = 0

  for (const file of incoming) {
    if (images.value.length + additions.length >= MAX_IMAGES) {
      overflow += 1
      continue
    }
    if (!IMAGE_EXT.test(file.name || '')) {
      formatSkipped += 1
      continue
    }
    if (file.size > MAX_IMAGE_BYTES) {
      sizeSkipped += 1
      continue
    }
    const signature = `${file.name}:${file.size}:${file.lastModified}`
    if (signatures.has(signature)) continue
    signatures.add(signature)

    let url = ''
    try {
      url = URL.createObjectURL(file)
    } catch (err) {
      formatSkipped += 1
      continue
    }

    additions.push({
      id: ++imageKey,
      file,
      name: file.name || `image-${imageKey}`,
      url
    })
  }

  images.value.push(...additions)

  const messages = []
  if (overflow) messages.push(`最多 9 张图片，超出部分未添加`)
  if (formatSkipped) messages.push(`${formatSkipped} 个文件格式不支持`)
  if (sizeSkipped) messages.push(`${sizeSkipped} 张图片超过 5MB`)
  notice.value = messages.join('；')
}

function removeImage(id) {
  const index = images.value.findIndex((image) => image.id === id)
  if (index === -1) return
  const [removed] = images.value.splice(index, 1)
  if (removed) URL.revokeObjectURL(removed.url)
  if (preview.value && preview.value.id === id) preview.value = null
}

function cleanupImages() {
  images.value.forEach((image) => {
    try {
      URL.revokeObjectURL(image.url)
    } catch (err) {
      /* 已释放或不支持时忽略 */
    }
  })
  images.value = []
  preview.value = null
}

function resetDraft() {
  title.value = ''
  content.value = ''
  tag.value = ''
  notice.value = ''
}

async function submit() {
  if (submitting.value) return

  error.value = ''
  successPost.value = null

  if (!session.token) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }

  const cleanTitle = title.value.trim()
  const cleanContent = content.value.trim()

  if (!cleanTitle) {
    error.value = '请填写帖子标题'
    return
  }
  if (cleanTitle.length > 100) {
    error.value = '标题不能超过 100 个字符'
    return
  }
  if (!cleanContent) {
    error.value = '请填写帖子正文'
    return
  }
  if (!selectedBar.value) {
    error.value = editing.value ? '请选择帖子所属的贴吧' : '请选择要发布的贴吧'
    openPicker()
    return
  }

  if (editing.value) {
    submitting.value = true
    try {
      // 只提交文字字段；图片由后端原样保留，不随这次请求变化
      const updated = await api.updatePost(editPostId.value, {
        barId: Number(selectedBar.value.id),
        title: cleanTitle,
        content: cleanContent,
        tag: tag.value.trim() || '未分类'
      })
      if (!updated || updated.id == null) {
        throw new Error('修改已提交，但返回数据异常，请到帖子详情确认')
      }
      router.replace(`/posts/${updated.id}`)
    } catch (err) {
      error.value = errorText(err, '保存失败，请检查内容后重试')
    } finally {
      submitting.value = false
    }
    return
  }

  const formData = new FormData()
  formData.append('barId', String(selectedBar.value.id))
  formData.append('title', cleanTitle)
  formData.append('content', cleanContent)
  formData.append('tag', tag.value.trim() || '未分类')
  images.value.forEach((image) => {
    formData.append('files', image.file, image.name)
  })

  submitting.value = true
  try {
    const post = await api.createPost(formData)
    if (!post || post.id == null) {
      throw new Error('服务器未返回新帖信息，请到「我的帖子」确认后再试')
    }

    cleanupImages()
    resetDraft()
    successPost.value = post
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (err) {
    error.value = errorText(err, '发布失败，请检查内容后重试')
  } finally {
    submitting.value = false
  }
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    if (preview.value) {
      preview.value = null
    } else if (pickerOpen.value) {
      closePicker()
    }
  }
}

watch(
  () => route.query.barId,
  () => {
    if (!editing.value) applyQueryBar()
  }
)

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  if (!session.token) {
    router.replace({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  await loadBars()
  if (editing.value) await loadEditPost()
  else applyQueryBar()
})

onBeforeUnmount(() => {
  disposed = true
  barsSeq += 1
  window.removeEventListener('keydown', onKeydown)
  cleanupImages()
})
</script>

<style scoped>
.publish-view {
  max-width: 1000px;
  margin: 0 auto;
  padding: 4px 0 32px;
}

.publish-content {
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

.result-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
  padding: 16px 18px;
  background: #f2f7ff;
  border: 1px solid #cadcff;
  border-radius: 12px;
}

.result-banner strong {
  font-size: 13.5px;
  color: #1859df;
}

.result-banner p {
  margin: 4px 0 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: #56708f;
}

.result-actions,
.alert-actions {
  display: flex;
  align-items: center;
  gap: 9px;
  flex: 0 0 auto;
}

.banner-btn,
.alert-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 33px;
  padding: 0 14px;
  font: inherit;
  font-size: 12.5px;
  font-weight: 600;
  color: #3b4a60;
  background: #ffffff;
  border: 1px solid #d5dfec;
  border-radius: 8px;
  text-decoration: none;
  cursor: pointer;
}

.banner-btn.primary {
  color: #ffffff;
  background: #246bfd;
  border-color: #246bfd;
}

.banner-btn:hover,
.alert-btn:hover:not(:disabled) {
  border-color: #b4c4d8;
}

.banner-btn.primary:hover {
  background: #1859df;
  border-color: #1859df;
}

.alert-btn:disabled {
  cursor: wait;
  opacity: 0.6;
}

.error-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px 18px;
  background: #fdf6f6;
  border: 1px solid #f0d2d2;
  border-radius: 12px;
}

.error-alert strong {
  font-size: 13.5px;
  color: #b33636;
}

.error-alert p {
  margin: 4px 0 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: #8a4a4a;
}

.edit-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 220px;
  padding: 40px 24px;
  color: #6b7a90;
  font-size: 13px;
}

.spinner-dark {
  border-color: rgba(36, 107, 253, 0.22);
  border-top-color: #246bfd;
}

.compose-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 20px;
  align-items: start;
}

.panel {
  background: #ffffff;
  border: 1px solid #e6ebf3;
  border-radius: 12px;
}

.editor-panel {
  padding: 26px 28px 24px;
}

.title-field,
.content-field {
  display: block;
}

.field-label {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: #3b4a60;
}

.field-label em {
  font-style: normal;
  font-weight: 400;
  color: #9aa6b6;
}

.title-input {
  width: 100%;
  height: 48px;
  padding: 0 2px;
  font: inherit;
  font-size: 20px;
  font-weight: 600;
  color: #17243b;
  background: transparent;
  border: 0;
  border-bottom: 1px solid #dbe3ee;
  border-radius: 0;
  outline: none;
  transition: border-color 0.16s ease;
}

.title-input::placeholder {
  font-weight: 500;
  color: #a6b1c0;
}

.title-input:focus {
  border-color: #246bfd;
}

.content-field {
  margin-top: 22px;
}

.content-input {
  display: block;
  width: 100%;
  min-height: 260px;
  padding: 15px 16px;
  font: inherit;
  font-size: 14px;
  line-height: 1.9;
  color: #2a3a50;
  background: #f9fbff;
  border: 1px solid #e2e9f2;
  border-radius: 9px;
  outline: none;
  resize: vertical;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
}

.content-input::placeholder {
  color: #9ca8b8;
}

.content-input:focus {
  background: #ffffff;
  border-color: #246bfd;
  box-shadow: 0 0 0 3px rgba(36, 107, 253, 0.1);
}

.title-input:disabled,
.content-input:disabled,
.tag-input:disabled {
  color: #8492a6;
  background: #f3f5f9;
  cursor: not-allowed;
}

.media-block {
  margin-top: 24px;
  padding-top: 22px;
  border-top: 1px solid #eef2f7;
}

.media-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 13px;
}

.media-head .field-label {
  display: block;
  margin-bottom: 3px;
}

.media-note {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.6;
  color: #97a3b3;
}

.media-count {
  flex: 0 0 auto;
  padding: 3px 9px;
  font-size: 11.5px;
  font-weight: 600;
  color: #56708f;
  background: #f2f5fa;
  border-radius: 20px;
}

.file-input {
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

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
  gap: 10px;
  padding: 2px;
  border-radius: 10px;
  transition: background 0.16s ease, box-shadow 0.16s ease;
}

.image-grid.dragging {
  background: #f2f7ff;
  box-shadow: inset 0 0 0 2px #a9c7ff;
}

.image-item {
  position: relative;
  margin: 0;
  aspect-ratio: 1;
}

.image-preview {
  display: block;
  width: 100%;
  height: 100%;
  padding: 0;
  overflow: hidden;
  background: #f2f5fa;
  border: 1px solid #e3e9f2;
  border-radius: 9px;
  cursor: zoom-in;
}

.image-preview img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-preview:hover img {
  opacity: 0.9;
}

.image-remove {
  position: absolute;
  top: 5px;
  right: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 23px;
  height: 23px;
  padding: 0;
  font-size: 17px;
  line-height: 1;
  color: #ffffff;
  background: rgba(23, 36, 59, 0.62);
  border: 0;
  border-radius: 50%;
  cursor: pointer;
}

.image-remove:hover {
  background: #17243b;
}

.image-add {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  aspect-ratio: 1;
  padding: 10px;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  color: #56708f;
  background: #f9fbfe;
  border: 1px dashed #c8d4e3;
  border-radius: 9px;
  cursor: pointer;
  transition: border-color 0.16s ease, background 0.16s ease, color 0.16s ease;
}

.image-add:hover:not(:disabled) {
  color: #246bfd;
  background: #f3f8ff;
  border-color: #8db3ff;
}

.image-add small {
  font-size: 10.5px;
  font-weight: 400;
  color: #a1adbc;
}

.add-plus {
  position: relative;
  width: 16px;
  height: 16px;
}

.add-plus::before,
.add-plus::after {
  position: absolute;
  top: 50%;
  left: 50%;
  content: '';
  background: #8ba0ba;
  border-radius: 1px;
  transform: translate(-50%, -50%);
}

.add-plus::before {
  width: 14px;
  height: 1.5px;
}

.add-plus::after {
  width: 1.5px;
  height: 14px;
}

.media-notice {
  margin: 12px 0 0;
  padding: 9px 11px;
  font-size: 12px;
  line-height: 1.6;
  color: #8a6324;
  background: #fff9ed;
  border: 1px solid #f3e2bd;
  border-radius: 8px;
}

.keep-notice {
  color: #3f6797;
  background: #f2f8ff;
  border-color: #d4e5fb;
}

.media-keep-empty {
  margin: 0;
  padding: 22px 16px;
  font-size: 12px;
  line-height: 1.7;
  color: #8a97a8;
  text-align: center;
  background: #f9fbfe;
  border: 1px dashed #d3dfec;
  border-radius: 9px;
}

.side-column {
  display: grid;
  gap: 16px;
  position: sticky;
  top: 20px;
}

.settings-panel {
  padding: 22px 20px 20px;
}

.settings-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 15px;
  border-bottom: 1px solid #eef2f7;
}

.settings-head h2,
.guide-panel h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #17243b;
}

.settings-hint {
  font-size: 10.5px;
  color: #9aa6b6;
}

.setting-block {
  margin-top: 18px;
}

.setting-label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #3b4a60;
}

.bar-select {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 10px;
  min-height: 44px;
  padding: 7px 10px;
  font: inherit;
  text-align: left;
  background: #f9fbfe;
  border: 1px solid #e0e7f0;
  border-radius: 9px;
  cursor: pointer;
  transition: border-color 0.16s ease, background 0.16s ease;
}

.bar-select:hover:not(:disabled) {
  background: #ffffff;
  border-color: #b8cae0;
}

.bar-select-img,
.bar-select-placeholder {
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  object-fit: cover;
  background: #eef3fa;
}

.bar-select-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: #8ba0ba;
}

.bar-select-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-size: 12.5px;
  font-weight: 600;
  color: #2a3a50;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-select-name.muted {
  font-weight: 400;
  color: #97a3b3;
}

.select-arrow {
  flex: 0 0 auto;
  font-size: 19px;
  line-height: 1;
  color: #a3afbe;
}

.inline-state,
.inline-error {
  margin: 8px 0 0;
  font-size: 11.5px;
  line-height: 1.6;
  color: #97a3b3;
}

.inline-error {
  color: #a85050;
}

.text-btn {
  padding: 0;
  margin-left: 5px;
  font: inherit;
  font-size: 11.5px;
  font-weight: 600;
  color: #246bfd;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.text-btn:hover {
  text-decoration: underline;
}

.tag-input {
  width: 100%;
  height: 38px;
  padding: 0 10px;
  font: inherit;
  font-size: 12.5px;
  color: #2a3a50;
  background: #f9fbfe;
  border: 1px solid #e0e7f0;
  border-radius: 8px;
  outline: none;
}

.tag-input:focus {
  background: #ffffff;
  border-color: #246bfd;
  box-shadow: 0 0 0 3px rgba(36, 107, 253, 0.1);
}

.tag-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
}

.tag-chip {
  padding: 4px 9px;
  font: inherit;
  font-size: 11px;
  color: #56708f;
  background: #f4f7fb;
  border: 1px solid #e3e9f2;
  border-radius: 20px;
  cursor: pointer;
}

.tag-chip:hover:not(:disabled) {
  color: #246bfd;
  border-color: #b9cef8;
}

.tag-chip.active {
  color: #1859df;
  background: #eef4ff;
  border-color: #b9cef8;
}

.publish-summary {
  display: grid;
  gap: 8px;
  margin: 20px 0 16px;
  padding: 12px 13px;
  background: #f7f9fc;
  border-radius: 9px;
}

.publish-summary > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.publish-summary span {
  font-size: 11.5px;
  color: #8492a6;
}

.publish-summary strong {
  font-size: 12px;
  font-weight: 600;
  color: #3b4a60;
}

.submit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  width: 100%;
  height: 44px;
  font: inherit;
  font-size: 13.5px;
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
  width: 14px;
  height: 14px;
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

.submit-note {
  margin: 10px 0 0;
  font-size: 10.5px;
  line-height: 1.6;
  color: #9aa6b6;
  text-align: center;
}

.guide-panel {
  padding: 20px;
}

.guide-panel h2 {
  margin-bottom: 11px;
}

.guide-panel ul {
  display: grid;
  gap: 9px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.guide-panel li {
  position: relative;
  padding-left: 13px;
  font-size: 11.5px;
  line-height: 1.75;
  color: #6b7a90;
}

.guide-panel li::before {
  position: absolute;
  top: 8px;
  left: 0;
  width: 4px;
  height: 4px;
  content: '';
  background: #b9c8da;
  border-radius: 50%;
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

.picker-panel {
  width: min(520px, 100%);
  max-height: min(680px, calc(100vh - 48px));
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 14px;
  box-shadow: 0 28px 70px rgba(23, 36, 59, 0.24);
  overflow: hidden;
}

.picker-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 22px 16px;
}

.picker-head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #17243b;
}

.picker-head p {
  margin: 5px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: #8492a6;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  padding: 0;
  font-size: 22px;
  line-height: 1;
  color: #8492a6;
  background: #f4f7fa;
  border: 0;
  border-radius: 50%;
  cursor: pointer;
}

.icon-btn:hover {
  color: #17243b;
  background: #eaf0f7;
}

.picker-search {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 22px 14px;
  padding: 0 12px;
  background: #f7f9fc;
  border: 1px solid #e4eaf2;
  border-radius: 9px;
}

.picker-search span {
  font-size: 11px;
  font-weight: 600;
  color: #98a4b5;
}

.picker-search input {
  flex: 1;
  height: 40px;
  font: inherit;
  font-size: 12.5px;
  color: #2a3a50;
  background: transparent;
  border: 0;
  outline: none;
}

.picker-body {
  flex: 1;
  min-height: 160px;
  overflow-y: auto;
  padding: 0 14px 18px;
}

.picker-state {
  margin: 0;
  padding: 42px 20px;
  font-size: 12.5px;
  line-height: 1.7;
  color: #8a97a8;
  text-align: center;
}

.picker-state p {
  margin: 0 0 8px;
}

.picker-list {
  display: grid;
  gap: 4px;
}

.picker-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px;
  font: inherit;
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 10px;
  cursor: pointer;
}

.picker-item:hover {
  background: #f8fafe;
}

.picker-item.selected {
  background: #f2f7ff;
  border-color: #d4e2ff;
}

.picker-item-img,
.picker-item-placeholder {
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  border-radius: 9px;
  object-fit: cover;
  background: #eef3fa;
}

.picker-item-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #8ba0ba;
}

.picker-item-text {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 2px;
}

.picker-item-text strong {
  overflow: hidden;
  font-size: 13px;
  font-weight: 600;
  color: #2a3a50;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.picker-item-text small {
  overflow: hidden;
  font-size: 11px;
  color: #8a97a8;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.picker-check {
  flex: 0 0 auto;
  font-size: 10.5px;
  font-weight: 600;
  color: #246bfd;
}

.preview-mask {
  background: rgba(13, 22, 38, 0.8);
}

.preview-box {
  position: relative;
  max-width: min(880px, 100%);
  max-height: calc(100vh - 64px);
}

.preview-box img {
  display: block;
  max-width: 100%;
  max-height: calc(100vh - 64px);
  object-fit: contain;
  border-radius: 8px;
}

.preview-close {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 32px;
  height: 32px;
  padding: 0;
  font-size: 22px;
  line-height: 1;
  color: #ffffff;
  background: rgba(23, 36, 59, 0.66);
  border: 0;
  border-radius: 50%;
  cursor: pointer;
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
  .compose-layout {
    grid-template-columns: 1fr;
  }

  .side-column {
    position: static;
    grid-template-columns: 1fr 1fr;
  }
}

@container (max-width: 560px) {
  .side-column {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 980px) {
  .compose-layout {
    grid-template-columns: 1fr;
  }

  .side-column {
    position: static;
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
  .page-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }

  .editor-panel {
    padding: 20px 18px;
  }

  .side-column {
    grid-template-columns: 1fr;
  }

  .result-banner,
  .error-alert {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
