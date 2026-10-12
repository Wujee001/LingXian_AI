/* -*- coding: utf-8 -*-
 *
 * 前端操作日志模块
 *
 * 记录界面关键操作（上传、画框、切换候选、确认、导出）。
 * 支持 VITE_LOG_LEVEL 控制输出级别（debug/info/warn/error）。
 * 后续可增加 /api/log 转发至后端 mlnlog。
 *
 * 作者：
 *     @Wujee
 *
 * 创建日期：2026-10-1
 * 版本：1.0.1
 *
 * 许可证：内部使用，未经许可不得传播。
 *
 */

const LEVELS = { debug: 10, info: 20, warn: 30, error: 40, silent: 99 }

const CURRENT_LEVEL = (() => {
  try {
    const lv = import.meta?.env?.VITE_LOG_LEVEL
    return LEVELS[lv] ?? LEVELS.info
  } catch {
    return LEVELS.info
  }
})()

function stamp() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function emit(level, action, detail) {
  if (LEVELS[level] < CURRENT_LEVEL) return
  const tag = `[${stamp()}][${level.toUpperCase()}]`
  const fn =
    level === 'error' ? console.error :
    level === 'warn' ? console.warn :
    console.log
  fn(tag, action, detail ?? '')
}

export const logDebug = (a, d) => emit('debug', a, d)
export const logInfo = (a, d) => emit('info', a, d)
export const logWarn = (a, d) => emit('warn', a, d)
export const logError = (a, d) => emit('error', a, d)