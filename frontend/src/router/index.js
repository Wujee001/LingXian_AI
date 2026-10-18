/* -*- coding: utf-8 -*-
 *
 * 路由配置（阶段 1：加 /admin/users + 管理员守卫）
 *
 * 作者：@Wujee
 * 维护：@zlxaaa
 * 更新日期：2026-10-18
 * 版本：1.3.0
 */

import { createRouter, createWebHashHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import SingleChar from '../views/SingleChar.vue'
import WholeSheet from '../views/WholeSheet.vue'
import Knowledge from '../views/Knowledge.vue'
import Judou from '../views/Judou.vue'
import Login from '../views/Login.vue'
import AdminUsers from '../views/AdminUsers.vue'
import { auth } from '../store/auth.js'
import History from '../views/History.vue'
import Notes from '../views/Notes.vue'
import Square from '../views/Square.vue'


const routes = [
  { path: '/', redirect: '/single' },
  { path: '/login', name: 'login', component: Login, meta: { public: true, title: '登录' } },
  { path: '/single', name: 'single', component: SingleChar, meta: { title: '单字释读' } },
  { path: '/sheet', name: 'sheet', component: WholeSheet, meta: { title: '整谱打谱' } },
  { path: '/knowledge', name: 'knowledge', component: Knowledge, meta: { title: '减字库' } },
  { path: '/judou', name: 'judou', component: Judou, meta: { title: '智能句读' } },
  {
  path: '/history',
  name: 'history',
  component: History,
  meta: { title: '我的历史', requiresAuth: true },
},
{ path: '/notes',  name: 'notes',  component: Notes,  meta: { title: '我的笔记', requiresAuth: true } },
{ path: '/square', name: 'square', component: Square, meta: { title: '广场', requiresAuth: true } },  


{
    path: '/admin/users',
    name: 'adminUsers',
    component: AdminUsers,
    meta: { title: '用户管理', requiresAuth: true, requiresAdmin: true },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  if (to.meta.public) return next()
  if (to.meta.requiresAuth && !auth.token) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }
  if (to.meta.requiresAdmin && (!auth.user || auth.user.role !== 'admin')) {
    ElMessage.warning('需要管理员权限')
    return next('/single')
  }
  next()
})

export default router