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
 * 更新日期：2026-10-13
 * 版本：1.2.0（统一异常拦截）
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '',
  timeout: 20000
})

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

export default request