/* -*- coding: utf-8 -*-
 *
 * 路由配置模块
 *
 * 采用 Hash 路由，注册单减字识别、整谱打谱两个功能页，
 * 根路径重定向到单减字识别。
 * （main.js 当前以 el-tabs 切换页面、未启用本路由；
 *   保留配置供后续多视图扩展。）
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

import { createRouter, createWebHashHistory } from 'vue-router'
import SingleChar from '../views/SingleChar.vue'
import WholeSheet from '../views/WholeSheet.vue'

const routes = [
  {
    path: '/',
    redirect: '/single'
  },
  {
    path: '/single',
    name: '单减字识别',
    component: SingleChar
  },
  {
    path: '/sheet',
    name: '整谱打谱',
    component: WholeSheet
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router