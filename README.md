# 贴吧社区 PC 网页版（bbs-pc-web）

独立的桌面端社区前端，使用 Vue 3 + Vite + Vue Router 与原生 HTML/CSS，不依赖 Element Plus，不内置演示数据。所有内容（帖子、贴吧、评论、收藏、关注、消息、资料）均通过真实 FastAPI 后端读写，统一响应体为 `{ code, message, data }`，`code === 0` 为成功。

- 项目目录：`D:/项目/BBS/bbs-pc-web`
- 线上地址：`https://bbs-pc-web.vercel.app`
- 生产后端：`https://bbs-app-backend-zuzm.onrender.com`
- 开发端口：`5182`
- Vercel 部署：框架预设 Vite，构建命令 `npm run build`，输出目录 `dist`
- 路由模式：hash（`createWebHashHistory`），静态托管无需 history 重写
- 桌面三栏布局：左侧导航、中间内容、右侧热门吧，1440 / 1024 宽度均已验证

---

## 功能

- 首页信息流，支持最新 / 最热排序；关键词搜索与热门搜索词。
- 全部贴吧、吧详情、吧内帖子分页；贴吧关注 / 取消关注。
- 帖子详情、图片预览、评论分页与发表评论；点赞、收藏。
- 登录 / 注册；我的帖子、我的收藏、互动消息（点赞 / 回复 / @我）与未读角标。
- 发帖（选择吧、标题、正文、标签、最多 9 张图片）；作者可编辑自己的标题、正文、话题与贴吧，原图及互动保留。
- 账号资料修改、头像上传、退出登录。
- 智能客服对话（后端未配置模型时自动返回 FAQ 兜底）；当前设备按账号保存最近 40 条消息与草稿，支持退出重进、刷新恢复和清空对话。
- 游客可浏览公开内容；发布、收藏、消息、账号等受保护页面会跳转登录，登录后回到原页面。

---

## 开发与构建

要求 Node.js >= 18。仓库带 `package-lock.json`，可直接使用 `npm ci` 安装锁定版本依赖。

```bash
npm ci

npm run dev       # 开发：http://127.0.0.1:5182/
npm run build     # 生产构建：输出 dist/
npm run preview   # 本地预览构建产物：http://127.0.0.1:5182/
```

开发服务器默认把 `/api`、`/uploads`、`/static` 代理到线上 Render 后端。Render 免费实例长时间无请求会休眠，首次访问可能需要 30~60 秒；请求超时为 90 秒，超时会给出可读提示。

---

## 环境变量

复制 `.env.example` 为 `.env.local`（开发）或 `.env.production`（生产构建）后修改。仅 `VITE_` 前缀变量会暴露给前端。

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| `VITE_DEV_PROXY_TARGET` | 开发服务器 `/api`、`/uploads`、`/static` 的代理目标 | `https://bbs-app-backend-zuzm.onrender.com` |
| `VITE_API_ORIGIN` | 生产构建使用的后端源；必须是纯 origin，不带 `/api`、不带结尾 `/` | Render 地址 |
| `VITE_BASE_PATH` | 部署在子路径时使用，例如 `/bbs/`；根目录保持 `/` | `/` |

开发环境走同源代理，不涉及跨域；生产环境接口拼为 `${VITE_API_ORIGIN}/api/...`，图片拼为 `${VITE_API_ORIGIN}/uploads/...` 或 `/static/...`。

---

## 路由

hash 模式下地址形如 `http://127.0.0.1:5182/#/posts/1`。

| 路径 | 页面 | 登录 |
| --- | --- | --- |
| `/` | 首页信息流 | 否 |
| `/search?q=关键词` | 搜索结果 | 否 |
| `/bars`、`/bars/:id` | 全部贴吧、吧详情 | 否 |
| `/posts/:id` | 帖子详情 | 否 |
| `/posts/:id/edit` | 编辑自己的帖子 | 是 |
| `/support` | 帮助与智能客服 | 否 |
| `/favorites` | 我的收藏 | 是 |
| `/my-posts` | 我的帖子 | 是 |
| `/publish?barId=` | 发帖（`barId` 可选） | 是 |
| `/messages` | 互动消息 | 是 |
| `/account` | 我的账号 | 是 |
| `/login`、`/register` | 登录、注册 | 否 |

未登录访问受保护页面会跳转 `/login?redirect=<原路径>`。`redirect` 只接受以 `/` 开头且不以 `//`（或 `/\`）开头的站内路径，非法值会被剥除；登录成功后返回该页面。

---

## 目录结构

```
bbs-pc-web/
├─ index.html
├─ package.json
├─ package-lock.json
├─ vite.config.js
├─ .env.example
├─ .gitignore
└─ src/
   ├─ main.js          # 应用入口，安装路由并处理 401 跳转
   ├─ router.js        # 路由表、登录守卫、redirect 白名单
   ├─ api.js           # 请求封装、图片地址处理、全部业务接口
   ├─ session.js       # 响应式登录态与 localStorage 持久化
   ├─ App.vue          # 桌面三栏外壳
   ├─ style.css        # 全局样式
   ├─ components/      # PostCard、Icon 等组件
   └─ views/           # 各页面组件
```

---

## API 与登录态约定

- `request(path, { method, body, query, signal })` 返回后端 `data`；自动携带 `Authorization: Bearer <token>`，超时 90 秒；401 仅在请求 token 仍为当前 token 时清除登录态，避免旧响应影响新登录；`FormData` 不设置 JSON 头。
- 业务方法按领域提供：内容 `api.posts / search / bars / bar / barPosts / post / comments`；互动 `api.likePost / favoritePost / followBar / followedBars`；用户 `api.myPosts / favorites / login / register / me / updateMe / uploadAvatar`；发布与消息 `api.createPost / notifications / readNotifications / unread / cs`。
- 分页对象统一为 `{ list, page, pageSize, total, totalPages, hasMore }`。
- `imageUrl(path)` 仅允许 `http/https`、根相对路径、`blob:` 与 `data:image/*`；其他协议返回空串，由页面展示占位内容。
- `session` 为响应式对象：`session.token`、`session.user`；通过 `setSession`、`clearSession`、`updateUser` 维护，持久化为 localStorage 的 `bbs_token`、`bbs_current_user`。

---

## 生产部署（Vercel）

线上地址：`https://bbs-pc-web.vercel.app`。Vercel 项目使用 **Vite** 预设，构建命令 `npm run build`，输出目录 `dist`（本仓库没有 `vercel.json`，这些是 Vercel 项目侧配置）。

1. 在 Vercel 项目的 Production 环境变量中设置 `VITE_API_ORIGIN=https://bbs-app-backend-zuzm.onrender.com`；该值必须是**纯 origin**，不带 `/api`、不带结尾 `/`。修改环境变量后必须重新部署，旧的构建产物不会自动读取新值。
2. 执行 `npm run build` 生成 `dist/`；部署在子路径时设置 `VITE_BASE_PATH`。
3. 使用 hash 路由，服务器不需要为前端路由配置 history fallback。
4. 前后端跨域部署时，后端 `CORS_ORIGINS` 需要包含 PC 域名。当前线上完整值为：

   ```text
   https://bbs-app-wheat.vercel.app,https://bbs-admin-web.vercel.app,https://bbs-pc-web.vercel.app
   ```

   逗号分隔、只写纯 origin（不带路径、末尾 `/` 或通配符）；保留已有旧域名，不要只写新增域名。后端保存后需要重新部署才生效。
5. 推送 Git 只有在 Vercel 已启用对应项目的自动部署时才会触发；未启用时需要在 Vercel 手动 Redeploy。

开发环境经 Vite 代理为同源，无需额外跨域配置；若生产使用同域反向代理，则按同域部署处理。

---

## 验收状态

- 生产构建已通过（历史记录）。
- 浏览器验证通过：1440 / 1024 宽度布局正常；游客点击发布跳转登录；登录页空值校验生效；注册流程保留 redirect 并在成功后返回原页面。
- **2026-10-31 部署记录（非实时）**：PC 站点 `https://bbs-pc-web.vercel.app` 已部署；后端 `/api/health` 返回 `code: 0`、`env: production`、`db: true`；`/api/bars` 返回 16 个吧；PC 页面已恢复读取线上数据。
- `db: true` 只代表后端能连上数据库，不代表全部业务写操作都已在线复验；本轮未重新执行线上注册、发帖、评论等写操作。Render 免费实例冷启动约 30~60 秒，PC 请求超时为 90 秒，冷启动时请耐心等待或先访问 `/api/health` 唤醒。

## 本地完整演示

将本仓库与 `bbs-app-backend`、`bbs-app-frontend`、`bbs-admin-web` 放在同一父目录。配置后端 `.env` 并安装各项目依赖后，双击 `demo/local/start.cmd`，启动 PC5184、移动H55183、后台5185、API8001。运行状态和本地密钥不会入库。

账号和 5–8 分钟展示路线见 [演示指南](demo/GUIDE.md)；演示数据脚本固定使用本机独立库 `bbs_local_codex`，不修改其他库。默认开发代理指向线上后端，完整本地演示请使用此启动器。
