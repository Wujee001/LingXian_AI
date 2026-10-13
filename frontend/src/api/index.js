/* -*- coding: utf-8 -*-
 *
 * 前端接口统一封装模块
 *
 * 基于 axios 封装单字识别、整谱上传、人工修正、
 * 知识库、句读等全部后端接口调用。
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

import axios from 'axios'

const request = axios.create({
  baseURL: '',
  timeout: 20000
})

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

// ---- 知识库 ----
export function getKbList() {
  return request.get('/api/knowledge/library')
}

export function getKbItem(key) {
  return request.get(`/api/knowledge/detail/${key}`)
}

// ---- 智能句读 ----
export function segmentJudou(chars) {
  return request.post('/api/judou/segment', { chars })
}

export default request
