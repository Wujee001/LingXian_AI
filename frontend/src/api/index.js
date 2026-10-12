/* -*- coding: utf-8 -*-
 *
 * 前端接口统一封装模块
 *
 * 基于 axios 封装单字识别、整谱上传、人工修正、
 * 知识库、句读等全部后端接口调用。
 * 统一响应拦截：成功剥离 data；失败 ElMessage 提示并写日志。
 *
 * 作者：
 *     @Wujee
 *
 * 创建日期：2026-10-1
 * 版本：1.0.2
 *
 * 许可证：内部使用，未经许可不得传播。
 *
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import { logError, logWarn } from '../logger.js'

const request = axios.create({
  baseURL: '',
  timeout: 20000
})

request.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const isConnRefused =
      err?.code === 'ERR_NETWORK' ||
      err?.code === 'ECONNREFUSED' ||
      err?.message?.includes('Network Error')

    // 后端未起：仅开发期提示，不弹窗
    if (isConnRefused && import.meta.env.DEV) {
      logWarn('后端未启动或不可达', err?.config?.url)
      return Promise.reject(Object.assign(err, { __silent: true }))
    }

    const msg =
      err?.response?.data?.message ||
      err?.response?.data?.detail ||
      err?.message ||
      '网络异常，请稍后重试'
    logError('接口调用失败', { url: err?.config?.url, msg })
    ElMessage.error(msg)
    return Promise.reject(err)
  }
)

// ---- 单减字 ----
export function predictSingle(file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/api/char/predict', fd)
}

// ---- 整谱打谱 ----
export function uploadSheet(file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/api/sheet/upload', fd)
}

export function correctSheet(payload) {
  return request.post('/api/sheet/correct', payload)
}

// ---- 知识库（对应后端 api/knowledge.py） ----
// GET /api/knowledge/library?char_type=
export function getKbList(charType) {
  const params = charType ? { char_type: charType } : {}
  return request.get('/api/knowledge/library', { params })
}

// GET /api/knowledge/detail/{char_key}
export function getKbItem(key) {
  return request.get(`/api/knowledge/detail/${encodeURIComponent(key)}`)
}

// GET /api/knowledge/search?q=
export function searchKb(q) {
  return request.get('/api/knowledge/search', { params: { q } })
}

// GET /api/knowledge/registry
export function getKbRegistry() {
  return request.get('/api/knowledge/registry')
}

// ---- 智能句读 ----
export function segmentJudou(sequence) {
  return request.post('/api/judou/segment', { sequence })
}

export default request