/* -*- coding: utf-8 -*-
 *
 * 前端应用入口模块（泠弦智谱 V1）
 *
 * 创建 Vue 应用实例，挂载 Element-Plus、路由与全局国风样式。
 *
 * 作者：@Wujee
 * 更新日期：2026-10-13
 * 版本：1.1.0（启用 router）
 */

import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './style.css'
import App from './App.vue'
import router from './router/index.js'

const app = createApp(App)
app.use(ElementPlus)
app.use(router)
app.mount('#app')