/* -*- coding: utf-8 -*-
 *
 * 路由配置模块（泠弦智谱 V1）
 *
 * 采用 Hash 路由，注册四个功能页：
 *   单字释读 /single  → POST /api/char/predict
 *   整谱打谱 /sheet   → POST /api/sheet/upload + /api/sheet/correct
 *   减字库   /knowledge → GET /api/knowledge/*
 *   智能句读 /judou    → POST /api/judou/segment
 * 根路径重定向到单字释读。
 *
 * 作者：@Wujee
 * 更新日期：2026-10-13
 * 版本：1.1.0（启用路由，4 页全覆盖 5 项接口）
 */

import { createRouter, createWebHashHistory } from 'vue-router'
import SingleChar from '../views/SingleChar.vue'
import WholeSheet from '../views/WholeSheet.vue'
import Knowledge from '../views/Knowledge.vue'
import Judou from '../views/Judou.vue'

const routes = [
  { path: '/', redirect: '/single' },
  {
    path: '/single',
    name: 'single',
    component: SingleChar,
    meta: { title: '单字释读' }
  },
  {
    path: '/sheet',
    name: 'sheet',
    component: WholeSheet,
    meta: { title: '整谱打谱' }
  },
  {
    path: '/knowledge',
    name: 'knowledge',
    component: Knowledge,
    meta: { title: '减字库' }
  },
  {
    path: '/judou',
    name: 'judou',
    component: Judou,
    meta: { title: '智能句读' }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router