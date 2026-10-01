/* -*- coding: utf-8 -*-
 *
 * 路由配置模块
 *
 * 采用 Hash 路由，注册整谱打谱、数据集标注、项目设置
 * 三个页面，根路径重定向到整谱打谱。
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
import WholeSheet from '../views/WholeSheet.vue'
import DatasetLabel from '../views/DatasetLabel.vue'
import Setting from '../views/Setting.vue'

const routes = [
  {
    path: '/',
    redirect: '/wholesheet'
  },
  {
    path: '/wholesheet',
    name: '整谱打谱',
    component: WholeSheet
  },
  {
    path: '/dataset',
    name: '数据集标注',
    component: DatasetLabel
  },
  {
    path: '/setting',
    name: '项目设置',
    component: Setting
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
