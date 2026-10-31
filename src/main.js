// ---------------------------------------------------------------------------
// 应用入口：挂载 App、安装路由、引入全局样式。
//
//   额外职责：api.js 收到 401 时会派发 bbs:unauthorized 事件（它不 import router，
//   避免循环依赖）。这里监听事件，把「当前页面需要登录」的情况送回登录页，
//   并保留 redirect，登录成功后可回到原页面。
// ---------------------------------------------------------------------------
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)
app.use(router)

if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
  let lastHandledAt = 0

  window.addEventListener('bbs:unauthorized', () => {
    const now = Date.now()
    // 多个并请求同时 401 时只处理一次
    if (now - lastHandledAt < 1000) return
    lastHandledAt = now

    const current = router.currentRoute.value
    if (!current.meta || !current.meta.requiresAuth) return
    if (current.name === 'login') return

    const redirect = current.fullPath
    router.replace({ path: '/login', query: redirect ? { redirect } : {} }).catch(() => {
      // 路由重复跳转等无害异常，忽略
    })
  })
}

app.mount('#app')
