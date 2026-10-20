/* -*- coding: utf-8 -*-
 * 前端接口统一封装（纯本地模型，无云API）
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '',
  timeout: 30000
})

request.interceptors.response.use(
  res => res,
  err => {
    const resp = err.response
    const isNetwork = !resp
    const status = resp && resp.status
    const detail = (resp && resp.data && (resp.data.detail || resp.data.msg)) || ''

    if (isNetwork) {
      ElMessage.error('无法连接后端服务，请联系开发人员检查')
      return Promise.reject(err)
    }

    if (status >= 500) {
      ElMessage.error(detail || '服务异常，请联系开发人员检查')
      return Promise.reject(err)
    }

    if (status >= 400) {
      ElMessage.error(detail || '请求异常')
      return Promise.reject(err)
    }

    return Promise.reject(err)
  }
)

/* 单减字识别 */
export function predictSingle(file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/api/char/predict', fd)
}

/* 整谱上传 */
export function uploadSheet(file) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/api/sheet/upload', fd, { timeout: 60000 })
}

/* 人工修正反馈 */
export function submitCorrection(payload) {
  return request.post('/api/sheet/correct', payload)
}
export const correctSheet = submitCorrection

/* 知识库 */
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

/* 智能句读 */
export function segmentJudou(chars) {
  return request.post('/api/judou/segment', { chars })
}

export default request
