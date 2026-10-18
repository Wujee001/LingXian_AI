/* -*- coding: utf-8 -*-
 *
 * 前端接口统一封装模块
 *
 * 基于 axios 封装单字识别、整谱上传、人工修正、知识库、句读
 * 等全部后端接口调用。
 *
 * 统一异常策略：
 *   - 网络错误（后端未启动）：静默 reject，由页面决定降级；
 *   - 501 / 503 / detail 含「未实现/开发中/TODO」：
 *     统一弹「功能正在开发中」，交给调用方降级；
 *   - 其他 5xx：弹「服务异常」；
 *   - 4xx：原样 reject，由调用方处理。
 *
 * 作者：@Wujee
 * 维护：@zlxaaa
 * 更新日期：2026-10-13
 * 版本：1.2.0（统一异常拦截）
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import { auth, clearAuth } from '../store/auth.js'

const request = axios.create({
  baseURL: '',
  timeout: 20000
})

/* ---------------- 请求拦截：自动带 Bearer ---------------- */
request.interceptors.request.use(
  config => {
    if (auth.token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${auth.token}`
    }
    return config
  },
  err => Promise.reject(err)
)

/* ---------------- 401 统一处理（登录接口自身除外） ---------------- */
const AUTH_PUBLIC_URLS = ['/api/auth/login']

/* ---------------- 统一异常拦截 ---------------- */
request.interceptors.response.use(
  res => res,
  err => {
    const resp = err.response
    const isNetwork = !resp                       // 无 response → 网络错误
    const status = resp && resp.status
    const detail = (resp && resp.data && (resp.data.detail || resp.data.msg)) || ''

    // 网络错误（后端未启动）：不弹窗，页面自行降级
    if (isNetwork) return Promise.reject(err)

      // 401：清 token + 跳登录（登录接口本身除外）
if (
  status === 401 &&
  !AUTH_PUBLIC_URLS.some(u => String(err.config?.url || '').includes(u))
) {
  clearAuth()
  if (!window.location.hash.startsWith('#/login')) {
    window.location.hash = '#/login'
  }
  return Promise.reject(err)
}

    // 明确的"未实现"信号 → 统一提示
    const notImpl =
      status === 501 ||
      status === 503 ||
      /未实现|开发中|not\s*implemented|todo/i.test(String(detail))
    if (notImpl) {
      ElMessage.warning('功能正在开发中')
      return Promise.reject(err)
    }

    // 其他 5xx：服务异常
    if (status >= 500) {
      ElMessage.error(`服务异常：${detail || status}`)
      return Promise.reject(err)
    }

    // 4xx：交给调用方
    return Promise.reject(err)
  }
)

/* ---------------- 单减字 ---------------- */
export function predictSingle(file, engine = 'auto') {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('engine', engine)            // auto 自动 / yolo 本地模型 / qwen 多模态
  // 多模态兜底单图可能耗时，放宽到 60s
  return request.post('/api/char/predict', fd, { timeout: 60000 })
}

/* ---------------- 整谱打谱 ---------------- */
export function uploadSheet(file, engine = 'auto') {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('engine', engine)            // auto 自动 / yolo 本地模型 / qwen 多模态
  // qwen 模式整谱逐框走多模态，放宽到 300s
  return request.post('/api/sheet/upload', fd, { timeout: 300000 })
}

export function parseAttributes(attributes) {
  return request.post('/api/char/parse-attributes', { attributes })
}

export function getModelStatus() {
  return request.get('/api/sheet/model-status')
}

export function correctSheet(payload) {
  return request.post('/api/sheet/correct', payload)
}

/* ---------------- 知识库 ---------------- */
export function getKbList(charType) {
  const params = charType ? { char_type: charType } : {}
  return request.get('/api/knowledge/library', { params })
}

export function getKbItem(key) {
  return request.get(`/api/knowledge/detail/${key}`)
}

export function searchKb(q) {
  return request.get('/api/knowledge/search', { params: { q } })
}

export function getKbRegistry() {
  return request.get('/api/knowledge/registry')
}

/* ---------------- 智能句读 ---------------- */
export function segmentJudou(chars) {
  return request.post('/api/judou/segment', { chars })
}

/* ---------------- 认证 ---------------- */
export function login(username, password) {
  return request.post('/api/auth/login', { username, password })
}

export function logout() {
  return request.post('/api/auth/logout')
}

export function fetchMe() {
  return request.get('/api/auth/me')
}

/* ---------------- 管理员：用户管理 ---------------- */
export function adminListUsers() {
  return request.get('/api/admin/users')
}

export function adminCreateUser(username, password, role = 'user') {
  return request.post('/api/admin/users', { username, password, role })
}

export function adminPatchUser(userId, disabled) {
  return request.patch(`/api/admin/users/${userId}`, { disabled })
}

export function adminResetPassword(userId, password) {
  return request.post(`/api/admin/users/${userId}/reset-password`, { password })
}

export function adminAudit(page = 1, pageSize = 20) {
  return request.get('/api/admin/audit', { params: { page, page_size: pageSize } })
}

/* ---------------- 历史记录（需登录） ---------------- */
export function listHistory(page = 1, pageSize = 20, q = '') {
  const params = { page, page_size: pageSize }
  if (q) params.q = q
  return request.get('/api/history', { params })
}

export function getHistory(id) {
  return request.get(`/api/history/${id}`)
}

export function deleteHistory(id) {
  return request.delete(`/api/history/${id}`)
}

export function setHistoryVisibility(id, visibility) {
  return request.patch(`/api/history/${id}/visibility`, { visibility })
}

/* ---------------- 个人笔记 ---------------- */
export function listNotes(page = 1, pageSize = 20, q = '') {
  const params = { page, page_size: pageSize }
  if (q) params.q = q
  return request.get('/api/notes', { params })
}
export function createNote(payload) {
  return request.post('/api/notes', payload)
}
export function getNote(id) {
  return request.get(`/api/notes/${id}`)
}
export function updateNote(id, payload) {
  return request.put(`/api/notes/${id}`, payload)
}
export function deleteNote(id) {
  return request.delete(`/api/notes/${id}`)
}
export function setNoteVisibility(id, visibility) {
  return request.patch(`/api/notes/${id}/visibility`, { visibility })
}

/* ---------------- 广场 ---------------- */
export function squareNotes(page = 1, pageSize = 20, q = '') {
  const params = { page, page_size: pageSize }
  if (q) params.q = q
  return request.get('/api/square/notes', { params })
}
export function squareNoteDetail(id) {
  return request.get(`/api/square/notes/${id}`)
}
export function squareHistory(page = 1, pageSize = 20, q = '') {
  const params = { page, page_size: pageSize }
  if (q) params.q = q
  return request.get('/api/square/history', { params })
}
export function squareHistoryDetail(id) {
  return request.get(`/api/square/history/${id}`)
}
export function adminHideNote(id) {
  return request.patch(`/api/square/notes/${id}/hide`)
}
export function adminHideHistory(id) {
  return request.patch(`/api/square/history/${id}/hide`)
}

/* ---------------- 管理员：被隐藏内容 ---------------- */
export function adminListHiddenNotes(page = 1, pageSize = 20) {
  return request.get('/api/admin/hidden/notes', { params: { page, page_size: pageSize } })
}
export function adminListHiddenHistory(page = 1, pageSize = 20) {
  return request.get('/api/admin/hidden/history', { params: { page, page_size: pageSize } })
}
export function adminUnhideNote(id) {
  return request.patch(`/api/admin/hidden/notes/${id}/unhide`)
}
export function adminUnhideHistory(id) {
  return request.patch(`/api/admin/hidden/history/${id}/unhide`)
}

export default request