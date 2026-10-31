# BBS 本地部署启动器

有界实现：只初始化本机独立库 `bbs_local_codex`，然后启动后端、移动 H5、PC 网页和管理后台四个本地服务。
不会修改原 `.env`、后端/前端源码或 H5 发行包，也不会碰 MySQL 上已有的其他库。

## 一键启动

双击或在命令行运行：

```bat
start.cmd
```

- 自动 `chcp 65001`，兼容中文/空格路径；
- 使用后端虚拟环境 Python 的绝对路径
  `D:\项目\BBS\bbs-app-backend\.venv\Scripts\python.exe`；
- 启动器异常退出时保留窗口并提示查看 `logs\`；
- 只结束本启动器创建的进程，不杀外部进程；
- 可传参只做检查：`start.cmd --check`。

等价的命令行方式：

```bat
D:\项目\BBS\bbs-app-backend\.venv\Scripts\python.exe "..\bbs-pc-web\demo\local\run.py"
```

只做前置检查（端口 / 数据库连接 / 文件 / 初始化前置），不建库、不启动：

```bat
D:\项目\BBS\bbs-app-backend\.venv\Scripts\python.exe "..\bbs-pc-web\demo\local\run.py" --check
```

停止：`Ctrl+C`。只会结束本启动器创建的进程。

## 本地地址

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| 后端 API | http://127.0.0.1:8001 | 接口文档 `/docs` |
| 移动 H5 | http://127.0.0.1:5183 | 只读发行包 + 同源代理 |
| PC 网页 | http://127.0.0.1:5184 | Vite dev，代理到 8001 |
| 管理后台 | http://127.0.0.1:5185 | Vite dev，代理到 8001 |

端口启动前会检查；被占用时直接报错，不会终止占用者。

## 管理后台（5185）

- 目录：`D:\项目\BBS\bbs-admin-web`；
- 已存在 `node_modules` 时由 `run.py` 启动 Vite dev，端口固定 5185；
- **不改 admin-web 的源码或 `.env`**：只在子进程环境里设置
  `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8001`，把 `/api`、`/uploads`、`/static`
  固定代理到本机后端；
- 如果 `node_modules` 不存在，**不会自动安装**，会打印提示并跳过 5185，其余服务照常启动；
- 需要补依赖时请人工在该目录执行 `npm install`（本项目交付不执行安装）。

## 数据库

- 固定使用独立库 `bbs_local_codex`，连接账号来自后端 `.env` 的
  `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD`，且 `DB_HOST` 必须是 `localhost` 或 `127.0.0.1`。
- 库不存在：`CREATE DATABASE` 后导入 `sql/bbs_schema.sql`；导入前替换库名并移除全部
  `DROP TABLE`，用 `CLIENT.MULTI_STATEMENTS` 一次执行。
- 库已存在且 10 张核心表齐全：直接复用，不导入、不清库。
- 库已存在但表不完整：报错退出，绝不清库。

> 建表脚本自带的示例用户 / 贴吧 / 帖子仅用于本地演示，**不代表线上数据**。

## 演示数据（seed_demo.py）

在启动器已经把独立库准备好之后，可再补一批专用演示数据：

```bat
D:\项目\BBS\bbs-app-backend\.venv\Scripts\python.exe "..\bbs-pc-web\demo\local\seed_demo.py" --check
D:\项目\BBS\bbs-app-backend\.venv\Scripts\python.exe "..\bbs-pc-web\demo\local\seed_demo.py"
```

（在任意工作目录执行均可，脚本内部使用绝对路径。）

约束：

- 运行时读取后端 `.env`，但**不打印账号、密码或 `.env` 内容**；
- 只连 `localhost / 127.0.0.1` 的固定库 `bbs_local_codex`，**没有库名参数**，不能改库绕过；
- **不 DROP、不 TRUNCATE、不清库、不 DELETE、不 UPDATE 既有用户资料**；
- 只新增 `demo_*` 专用普通用户 / 演示管理员、约 20 篇中文帖子，以及关联的评论、点赞、
  收藏、关注和足迹；固定用户名 + 固定标题/评论内容作为自然键，重复执行不会重复插入；
- 图片只复用 `D:\项目\BBS\bbs-app-backend\static\images\bars` 的本地吧图，复制到
  `demo/local/uploads/posts/demo_seed/`，不访问外网；
- 全部写入在一个事务里，失败整体回滚；
- `--check` 只读：不复制图片、不写数据库。

演示账号和密码只记录在 `outputs/bbs-demo-guide.md`，脚本和日志都不打印。

## 运行状态

`state.json`（本地 JWT secret）、`logs/`、`uploads/` 均为运行状态，已被 `.gitignore` 忽略。
日志：`logs/backend.log`、`logs/pc.log`、`logs/admin.log`、`logs/mobile.log`，不输出数据库密码。

## 依赖与本机路径

- Python：`D:\项目\BBS\bbs-app-backend\.venv\Scripts\python.exe`
  （已含 fastapi/uvicorn/pymysql/dotenv）
- PC：`D:\项目\BBS\bbs-pc-web`（node + 已装 vite，端口 5184）
- 管理后台：`D:\项目\BBS\bbs-admin-web`（node + 已装 vite，端口 5185；缺依赖则跳过）
- 移动 H5 发行包：`D:\项目\BBS\bbs-app-frontend\unpackage\dist\build\web`
  （只读，端口 5183）
- 项目根路径写死在 `run.py` 顶部常量中；目录变动时改常量即可。

移动端服务在运行时把 JS 中的线上 API 域名替换为空串以走同源 `/api`，不会改写发行包文件。
