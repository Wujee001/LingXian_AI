/* -*- coding: utf-8 -*-
 *
 * 认证状态（token + user）
 *
 * localStorage 持久化；reactive 供组件响应。
 *
 * 作者：@zlxaaa
 * 创建日期：2026-10-18
 * 版本：1.0.0
 */

import { reactive } from 'vue'

const TOKEN_KEY = 'lingxian_token'
const USER_KEY = 'lingxian_user'

function readUser() {
  try {
    const s = localStorage.getItem(USER_KEY)
    return s ? JSON.parse(s) : null
  } catch {
    return null
  }
}

export const auth = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  user: readUser(),
})

export function setAuth(token, user) {
  auth.token = token
  auth.user = user
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth() {
  auth.token = ''
  auth.user = null
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isLoggedIn() {
  return !!auth.token
}

export function isAdmin() {
  return auth.user && auth.user.role === 'admin'
}