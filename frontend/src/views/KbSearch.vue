<!-- -*- coding: utf-8 -*- -->
<!--
  减字检索页（泠弦智谱 V2）

  册页布局：左页为减字列表与检索，右页为选中减字的
  指法释义。接入后端 /api/knowledge/library 与 /detail/{key}。
  URL 带 ?mock=1 时降级本地假数据。

  后端返回结构：
    library → { success, count, data: { key: item } }
    detail  → { success, data: item }
    item    → { display, type, right_hand, left_hand, meaning, ... }

  作者：
      @Wujee

  创建日期：2026-10-1
  版本：2.0.1

  许可证：内部使用，未经许可不得传播。
-->

<template>
  <section class="book">
    <!-- 左页：检索 + 列表 -->
    <div class="page page-left">
      <div class="page-head">
        <span class="page-head-num">索</span>
        <span class="page-head-title">减字名录</span>
        <span class="count-badge" v-if="list.length">共 {{ list.length }} 条</span>
      </div>

      <el-input
        v-model="keyword"
        placeholder="输入减字名、指法或键值，如「勾」「大指」"
        clearable
        class="search-input"
      />

      <div class="list-wrap">
        <div v-if="loadingList" class="list-empty">正在展卷…</div>
        <div v-else-if="!filtered.length" class="list-empty">
          无匹配减字
        </div>
        <ul v-else class="list">
          <li
            v-for="it in filtered"
            :key="it.key"
            class="list-item"
            :class="{ active: current === it.key }"
            @click="select(it)"
          >
            <span class="list-name">{{ it.name }}</span>
            <span class="list-type" v-if="it.type">{{ it.type }}</span>
            <span class="list-key">{{ it.key }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- 中缝 -->
    <div class="spine" aria-hidden="true"></div>

    <!-- 右页：详情 -->
    <div class="page page-right">
      <div class="page-head">
        <span class="page-head-num">释</span>
        <span class="page-head-title">指 法 释 义</span>
      </div>

      <div v-if="!detail" class="empty">
        <div class="empty-mark">谱</div>
        <div class="empty-main">自左页择一减字</div>
        <div class="empty-hint">右页将示其指法释义</div>
      </div>

      <template v-else>
        <div class="detail-title">
          <span class="dt-name">{{ detail.name }}</span>
          <span class="dt-type" v-if="detail.type">{{ detail.type }}</span>
          <span class="dt-key">{{ detail.key }}</span>
        </div>

        <div class="blk">指 法</div>
        <div class="parse">
          <div class="parse-row">
            <span class="parse-label">右手</span>
            <span>{{ detail.right_hand.finger || '—' }} ·
                  {{ detail.right_hand.string || '—' }}</span>
          </div>
          <div class="parse-row">
            <span class="parse-label">左手</span>
            <span>{{ detail.left_hand.finger || '—' }} ·
                  {{ detail.left_hand.hui || '—' }}</span>
          </div>
          <div class="deco-divider">
            <span class="deco-mark">· 释义 ·</span>
          </div>
          <div class="meaning">{{ detail.meaning || '暂无释义' }}</div>
        </div>

        <template v-if="detail.alias && detail.alias.length">
          <div class="blk">别 名</div>
          <div class="chips">
            <span v-for="a in detail.alias" :key="a" class="chip">{{ a }}</span>
          </div>
        </template>
      </template>
    </div>
  </section>
</template>

<script>
import { getKbList, getKbItem } from '../api/index.js'
import { logInfo, logError } from '../logger.js'

const USE_MOCK =
  typeof window !== 'undefined' &&
  new URLSearchParams(window.location.search).get('mock') === '1'

const MOCK_LIB = {
  da_9_gou_4: {
    display: '大九勾四',
    type: '按音',
    right_hand: { finger: '勾', string: '四弦' },
    left_hand: { finger: '大指', hui: '九徽' },
    meaning: '【演示数据】大指按九徽，右手中指向内弹四弦。'
  },
  san_tiao_7: {
    display: '散挑七',
    type: '散音',
    right_hand: { finger: '挑', string: '七弦' },
    left_hand: { finger: '—', hui: '—' },
    meaning: '【演示数据】右手食指向外挑七弦，散音。'
  },
  gou_5: {
    display: '勾五',
    type: '散音',
    right_hand: { finger: '勾', string: '五弦' },
    left_hand: { finger: '—', hui: '—' },
    meaning: '【演示数据】右手中指向内弹五弦，散音。'
  }
}

/* 后端 item → 前端统一结构 */
function normalizeItem(key, item) {
  return {
    key,
    name: item.display || item.name || key,
    type: item.type || '',
    right_hand: item.right_hand || { finger: '—', string: '—' },
    left_hand: item.left_hand || { finger: '—', hui: '—' },
    meaning: item.meaning || '',
    alias: item.alias || []
  }
}

export default {
  name: 'KbSearch',
  data() {
    return {
      keyword: '',
      list: [],
      loadingList: false,
      current: null,
      detail: null
    }
  },
  computed: {
    filtered() {
      const k = this.keyword.trim().toLowerCase()
      if (!k) return this.list
      return this.list.filter((x) => {
        const hay = [
          x.name, x.key, x.type,
          x.right_hand?.finger, x.left_hand?.finger,
          x.meaning
        ].join(' ').toLowerCase()
        return hay.includes(k)
      })
    }
  },
  mounted() {
    this.fetchList()
  },
  methods: {
    async fetchList() {
      this.loadingList = true
      try {
        if (USE_MOCK) {
          this.list = Object.entries(MOCK_LIB).map(
            ([k, v]) => normalizeItem(k, v)
          )
        } else {
          const res = await getKbList()
          // 后端返回 { success, count, data: { key: item } }
          const dict = res?.data && !Array.isArray(res.data) ? res.data : {}
          this.list = Object.entries(dict).map(
            ([k, v]) => normalizeItem(k, v)
          )
        }
        logInfo('减字名录载入', `共 ${this.list.length} 条`)
      } catch (e) {
        if (e?.__silent) {
          // 后端未起，静默降级到 mock
          this.list = Object.entries(MOCK_LIB).map(
            ([k, v]) => normalizeItem(k, v)
          )
          logInfo('后端未启动，使用演示数据')
        } else {
          logError('减字名录载入失败', e?.message)
        }
      } finally {
        this.loadingList = false
      }
    },

    async select(it) {
      this.current = it.key
      if (USE_MOCK) {
        this.detail = normalizeItem(it.key, MOCK_LIB[it.key] || {})
        logInfo('检索减字(演示)', it.key)
        return
      }
      try {
        const res = await getKbItem(it.key)
        // 后端返回 { success, data: item }
        const item = res?.data || {}
        this.detail = normalizeItem(it.key, item)
        logInfo('检索减字', it.key)
      } catch (e) {
        if (e?.__silent) {
          this.detail = normalizeItem(it.key, MOCK_LIB[it.key] || {})
        } else {
          logError('减字详情载入失败', e?.message)
        }
      }
    }
  }
}
</script>

<style scoped>
.book {
  display: flex;
  position: relative;
  background: var(--paper-light);
  border: 1px solid var(--line);
  border-radius: 2px;
  box-shadow:
    inset 0 0 40px rgba(139, 90, 43, 0.05),
    0 2px 10px rgba(80, 60, 30, 0.10),
    0 1px 2px rgba(80, 60, 30, 0.06);
  overflow: hidden;
}
.book::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 0% 0%,     rgba(120, 90, 50, 0.10), transparent 6%),
    radial-gradient(circle at 100% 0%,   rgba(120, 90, 50, 0.08), transparent 6%),
    radial-gradient(circle at 0% 100%,   rgba(120, 90, 50, 0.10), transparent 6%),
    radial-gradient(circle at 100% 100%, rgba(120, 90, 50, 0.08), transparent 6%);
  z-index: 3;
}

.page { flex: 1 1 50%; min-width: 0; padding: 28px 34px 34px; position: relative; }

.spine {
  width: 32px;
  flex: 0 0 32px;
  position: relative;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(139, 90, 43, 0.05) 30%,
    rgba(139, 90, 43, 0.13) 50%,
    rgba(139, 90, 43, 0.05) 70%,
    transparent 100%
  );
}
.spine::before {
  content: '';
  position: absolute;
  top: 24px; bottom: 24px;
  left: 50%;
  width: 1px;
  background: linear-gradient(180deg, transparent, var(--line), transparent);
  transform: translateX(-50%);
}

.page-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding-bottom: 12px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--line-soft);
  position: relative;
}
.page-head::after {
  content: '';
  position: absolute;
  left: 0; bottom: -1px;
  width: 40px; height: 2px;
  background: var(--zheshi);
  opacity: 0.55;
}
.page-head-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px; height: 22px;
  background: var(--zhusha);
  color: #f3e6cc;
  font-family: var(--font-brush);
  font-size: 13px;
  border-radius: 2px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
}
.page-head-title {
  font-family: var(--font-brush);
  font-size: 17px;
  letter-spacing: 5px;
  color: var(--ink);
}
.count-badge {
  margin-left: auto;
  font-family: var(--font-brush);
  font-size: 12px;
  color: var(--ink-mute);
  letter-spacing: 2px;
}

/* ===== 左页 ===== */
.search-input { margin-bottom: 16px; }

.list-wrap { min-height: 300px; }
.list-empty {
  text-align: center;
  padding: 80px 0;
  color: var(--ink-mute);
  font-family: var(--font-brush);
  letter-spacing: 3px;
  font-size: 13.5px;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: 1px solid var(--line-soft);
}
.list-item {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 12px 12px 12px 18px;
  border-bottom: 1px solid var(--line-soft);
  cursor: pointer;
  position: relative;
  transition: background-color .2s, color .2s;
}
.list-item::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px; height: 0;
  background: var(--zhusha);
  transition: height .2s ease;
}
.list-item:hover { background: var(--paper-warm); }
.list-item.active {
  background: var(--paper-warm);
  color: var(--zhusha-deep);
}
.list-item.active::before { height: 22px; }

.list-name {
  font-family: var(--font-brush);
  font-size: 16px;
  letter-spacing: 3px;
  color: var(--ink);
}
.list-item.active .list-name { color: var(--zhusha-deep); }
.list-type {
  font-family: var(--font-brush);
  font-size: 11px;
  color: var(--ink-faint);
  letter-spacing: 2px;
  padding: 1px 6px;
  border: 1px solid var(--line);
  border-radius: 2px;
}
.list-key {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: var(--ink-faint);
  letter-spacing: 0;
  margin-left: auto;
}

/* ===== 右页 ===== */
.empty {
  color: var(--ink-mute);
  text-align: center;
  padding: 80px 0 60px;
  line-height: 1.9;
}
.empty-mark {
  width: 74px; height: 74px;
  margin: 0 auto 16px;
  border: 1px solid var(--line-strong);
  border-radius: 2px;
  color: var(--zheshi);
  font-family: var(--font-brush);
  font-size: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--paper-warm);
  position: relative;
}
.empty-mark::before {
  content: '';
  position: absolute;
  inset: 5px;
  border: 1px solid var(--line);
  opacity: 0.6;
  border-radius: 1px;
}
.empty-main {
  font-family: var(--font-brush);
  font-size: 14px;
  letter-spacing: 3px;
  color: var(--ink-soft);
}
.empty-hint {
  font-size: 12px;
  color: var(--ink-faint);
  margin-top: 6px;
  letter-spacing: 2px;
}

.detail-title {
  display: flex;
  align-items: baseline;
  gap: 14px;
  padding-bottom: 14px;
  border-bottom: 1px dashed var(--line);
}
.dt-name {
  font-family: var(--font-brush);
  font-size: 26px;
  letter-spacing: 6px;
  color: var(--ink);
}
.dt-type {
  font-family: var(--font-brush);
  font-size: 12px;
  color: var(--zheshi);
  letter-spacing: 2px;
  padding: 2px 8px;
  border: 1px solid var(--line-strong);
  border-radius: 2px;
}
.dt-key {
  font-family: 'Courier New', monospace;
  font-size: 12.5px;
  color: var(--ink-faint);
  margin-left: auto;
}

.blk {
  font-family: var(--font-brush);
  font-size: 13px;
  color: var(--ink-mute);
  letter-spacing: 4px;
  margin: 18px 0 10px;
  padding-left: 10px;
  position: relative;
}
.blk::before {
  content: '';
  position: absolute;
  left: 0; top: 50%;
  transform: translateY(-50%);
  width: 3px; height: 12px;
  background: var(--zheshi);
  opacity: 0.6;
}

.parse {
  background: var(--paper-warm);
  border: 1px solid var(--line);
  border-radius: 2px;
  padding: 14px 16px;
  position: relative;
}
.parse::before {
  content: '';
  position: absolute;
  inset: 3px;
  border: 1px solid rgba(196, 179, 148, 0.5);
  border-radius: 1px;
  pointer-events: none;
}
.parse-row {
  display: flex;
  gap: 14px;
  align-items: baseline;
  font-size: 13.5px;
}
.parse-label {
  display: inline-block;
  min-width: 46px;
  color: var(--zheshi);
  font-family: var(--font-brush);
  letter-spacing: 3px;
  font-size: 13px;
}
.meaning {
  color: var(--ink-soft);
  font-size: 13.5px;
  line-height: 1.9;
}

.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  font-family: var(--font-brush);
  font-size: 13px;
  letter-spacing: 3px;
  padding: 5px 12px;
  background: var(--paper-warm);
  border: 1px solid var(--line);
  border-radius: 2px;
  color: var(--ink-soft);
}

@media (max-width: 860px) {
  .book { flex-direction: column; }
  .spine { display: none; }
  .page { padding: 22px 18px 26px; }
  .page-right { border-top: 1px solid var(--line-soft); }
}
</style>