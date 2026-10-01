/* -*- coding: utf-8 -*-
 *
 * 前端应用入口模块（泠弦智谱 V1）
 *
 * 创建 Vue 应用实例，挂载 Element-Plus 与全局国风样式。
 * V1 为单页面应用，不使用路由。
 *
 * 作者：
 *     @Wujee
 *
 * 创建日期：2026-10-1
 * 版本：1.0.0
 *
 * 许可证：内部使用，未经许可不得传播。
 *
 */

import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './style.css'
import App from './App.vue'

const app = createApp(App)
app.use(ElementPlus)
app.mount('#app')
