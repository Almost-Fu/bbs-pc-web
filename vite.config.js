import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// ===========================================================================
// 贴吧社区 PC 网页版（bbs-pc-web）
//   1. 开发端口固定为 5182（被占用时 Vite 会自动顺延，不会挤掉别的项目）
//   2. /api（接口）、/uploads（帖子图片）、/static（吧图 / 默认头像）
//      全部代理到后端，浏览器同源访问，不依赖后端 CORS，也没有跨域预检
//   3. 生产为纯静态产物，配合 hash 路由部署，服务器不需要 history 重写
//   4. @ 指向 src，方便跨层级引用
// ===========================================================================
const PROD_BACKEND_ORIGIN = 'https://bbs-app-backend-zuzm.onrender.com'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = String(env.VITE_DEV_PROXY_TARGET || PROD_BACKEND_ORIGIN)
    .trim()
    .replace(/\/+$/, '')
  const base = env.VITE_BASE_PATH || '/'

  const proxy = {}
  for (const prefix of ['/api', '/uploads', '/static']) {
    proxy[prefix] = {
      target: proxyTarget,
      changeOrigin: true,
      secure: true,
      // Render 免费实例冷启动需要 30~60 秒，代理超时与 api.js 的 90 秒保持一致
      timeout: 90000,
      proxyTimeout: 90000
    }
  }

  return {
    base,
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      host: '127.0.0.1',
      port: 5182,
      strictPort: false,
      open: false,
      proxy
    },
    preview: {
      host: '127.0.0.1',
      port: 5182
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: false,
      chunkSizeWarningLimit: 1200
    }
  }
})
