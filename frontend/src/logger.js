/* -*- coding: utf-8 -*-
 *
 * 前端操作日志模块
 *
 * 记录界面关键操作（上传、画框、切换候选、确认、导出）。
 * V1 输出到浏览器控制台；后端日志统一由 utils/mlnlog.py
 * 持久化，后续可将本模块埋点经 /api/log 转发至 mlnlog。
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

function stamp() {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

export function logInfo(action, detail) {
  console.log(`[${stamp()}][INFO] ${action}`, detail ?? '')
}

export function logWarn(action, detail) {
  console.warn(`[${stamp()}][WARN] ${action}`, detail ?? '')
}

export function logError(action, detail) {
  console.error(`[${stamp()}][ERROR] ${action}`, detail ?? '')
}
