<!-- -*- coding: utf-8 -*- -->
<!--
  减字库页面（泠弦智谱 V1）

  左侧：类别主表（/api/knowledge/registry）—— 按拼音 key 列出全部减字；
        顶部搜索框调用 /api/knowledge/search 做模糊匹配；
        可按类型筛选（/api/knowledge/library?char_type=）。
  右侧：选中减字的完整释义（优先用列表已有的完整对象；
        如列表精简则再请求 /api/knowledge/detail/{key}）。

  后端未启动时回退内置演示数据（6 条），页面顶部标签标明来源。

  作者：@zlx
  创建日期：2026-10-13
  版本：1.0.0
-->

<template>
  <div class="kb">
    <el-row :gutter="16">
      <!-- 左：检索 + 列表 -->
      <el-col :xs="24" :sm="10">
        <el-card shadow="never" class="leaf">
          <div class="blk"><span class="blk-orn">○</span> 检 索</div>

          <div class="search-row">
            <el-input v-model="q" placeholder="输入指法 / 弦 / 徽位 / 拼音 key"
                      clearable @keyup.enter="doSearch" />
            <el-button type="primary" plain @click="doSearch">搜 索</el-button>
          </div>

          <div class="filter-row">
            <span class="lbl">类 型</span>
            <el-radio-group v-model="charType" size="small" @change="loadList">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="散音">散音</el-radio-button>
              <el-radio-button label="按音">按音</el-radio-button>
              <el-radio-button label="泛音">泛音</el-radio-button>
              <el-radio-button label="装饰音">装饰音</el-radio-button>
              <el-radio-button label="复合音">复合音</el-radio-button>
            </el-radio-group>
          </div>

          <div class="blk2">
            <span v-if="loading">载入中…</span>
            <span v-else>共 {{ list.length }} 条</span>
            <el-tag size="small" :type="fromBackend ? 'success' : 'warning'" class="src-tag">
              {{ fromBackend ? '后端知识库' : '演示数据' }}
            </el-tag>
          </div>

          <ul class="kb-list">
            <li v-for="item in list" :key="item.char_key"
                :class="{ active: cur && cur.char_key === item.char_key }"
                @click="selectItem(item)">
              <span class="kb-key">{{ item.char_key }}</span>
              <span class="kb-cn">{{ item.display }}</span>
              <span class="kb-type">{{ item.type }}</span>
            </li>
            <li v-if="!list.length && !loading" class="kb-empty">
              未找到匹配的减字
            </li>
          </ul>
        </el-card>
      </el-col>

      <!-- 右：详情 -->
      <el-col :xs="24" :sm="14">
        <el-card shadow="never" class="leaf">
          <div v-if="!cur" class="empty">
            从左侧选择一个减字<br />查看其指法释义与乐理说明
          </div>

          <template v-else>
            <div class="p-title">
              <span class="p-display">{{ cur.display }}</span>
              <el-tag size="small" type="info">{{ cur.type }}</el-tag>
            </div>
            <div class="p-key">拼音 key：{{ cur.char_key }}</div>

            <div class="blk"><span class="blk-orn">○</span> 指法释义</div>
            <div class="parse">
              <div class="parse-row">
                <span class="k">右 手</span>{{ fmtRh(cur.right_hand) }}
              </div>
              <div class="parse-row">
                <span class="k">左 手</span>{{ fmtLh(cur.left_hand) }}
              </div>
              <div class="meaning">{{ cur.meaning || '暂未收录该减字释义' }}</div>
            </div>

            <div class="blk"><span class="blk-orn">○</span> 标 记</div>
            <div class="flags">
              <span class="flag" :class="{ on: cur.is_san }">散音</span>
              <span class="flag" :class="{ on: cur.is_fan }">泛音</span>
              <span class="flag" :class="{ on: !cur.is_san && !cur.is_fan }">按音</span>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { getKbList, getKbItem, searchKb } from '../api/index.js'
import { logInfo, logWarn } from '../logger.js'

const XIAN = ['', '一', '二', '三', '四', '五', '六', '七']
const HUI_MAP = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十', 11: '十一', 12: '十二', 13: '十三' }

// 演示兜底数据（后端未启动时用）
const FALLBACK = [
  { char_key: 'san_tiao_7', display: '散挑七', type: '散音', left_hand: null,
    right_hand: { finger: '挑', finger_name: '食指', string: 7 }, is_san: true, is_fan: false,
    meaning: '右手食指向外挑七弦空弦，散音，左手不按弦。' },
  { char_key: 'gou_5', display: '勾五', type: '散音', left_hand: null,
    right_hand: { finger: '勾', finger_name: '中指', string: 5 }, is_san: true, is_fan: false,
    meaning: '右手中指向内勾五弦空弦，散音，左手不按弦。' },
  { char_key: 'da_9_gou_4', display: '大九勾四', type: '按音',
    left_hand: { finger: '大指', string: 4, hui: 9 },
    right_hand: { finger: '勾', finger_name: '中指', string: 4 }, is_san: false, is_fan: false,
    meaning: '左手大指按四弦九徽，右手中指向内勾四弦，得按音。' },
  { char_key: 'ming_10_gou_5', display: '名十勾五', type: '按音',
    left_hand: { finger: '名指', string: 5, hui: 10 },
    right_hand: { finger: '勾', finger_name: '中指', string: 5 }, is_san: false, is_fan: false,
    meaning: '左手无名指按五弦十徽，右手中指向内勾五弦，得按音。' },
  { char_key: 'zhuang', display: '撞', type: '装饰音',
    left_hand: { finger: '随前音', string: null, hui: null },
    right_hand: null, is_san: false, is_fan: false,
    meaning: '左手按弦得音后，快速向上移动少许再回原位，产生装饰性顿挫。' },
  { char_key: 'cuo_ming_10_gou_4_san_tiao_6', display: '名十勾四＋散挑六（撮）', type: '复合音',
    left_hand: { finger: '名指', string: 4, hui: 10 },
    right_hand: { finger: '撮', finger_name: '中指+食指', string: '4+6' }, is_san: false, is_fan: false,
    meaning: '撮音：右手中指勾四弦（左手名指按十徽）与食指挑六弦散音同时发声。' }
]

export default {
  name: 'Knowledge',
  data() {
    return {
      q: '',
      charType: '',
      loading: false,
      list: [],
      cur: null,
      fromBackend: false
    }
  },
  mounted() {
    this.loadList()
  },
  methods: {
    async loadList() {
      this.loading = true
      try {
        const res = await getKbList(this.charType || undefined)
        const body = res && res.data
        const dict = (body && body.success && body.data) || {}
        const arr = Object.values(dict)
        if (!arr.length && !this.charType) throw new Error('空知识库')
        this.list = arr
        this.cur = arr[0] || null
        this.fromBackend = true
        logInfo('知识库加载完成', `共 ${arr.length} 条`)
      } catch (e) {
        logWarn('知识库接口不可用，回退演示数据', e && e.message)
        let arr = FALLBACK.slice()
        if (this.charType) arr = arr.filter(x => x.type === this.charType)
        this.list = arr
        this.cur = arr[0] || null
        this.fromBackend = false
      } finally {
        this.loading = false
      }
    },

    async doSearch() {
      const q = (this.q || '').trim()
      if (!q) return this.loadList()
      this.loading = true
      try {
        const res = await searchKb(q)
        const body = res && res.data
        const dict = (body && body.success && body.data) || {}
        const arr = Object.values(dict)
        this.list = arr
        this.cur = arr[0] || null
        this.fromBackend = true
        logInfo('知识库搜索', `q=${q} → ${arr.length} 条`)
      } catch (e) {
        logWarn('搜索接口不可用，本地过滤', e && e.message)
        const k = q.toLowerCase()
        const arr = FALLBACK.filter(x =>
          (x.char_key + ' ' + x.display + ' ' + (x.meaning || '')).toLowerCase().includes(k)
        )
        this.list = arr
        this.cur = arr[0] || null
        this.fromBackend = false
      } finally {
        this.loading = false
      }
    },

    async selectItem(item) {
      if (item.meaning || item.right_hand !== undefined) {
        this.cur = item
        return
      }
      try {
        const res = await getKbItem(item.char_key)
        const body = res && res.data
        this.cur = (body && body.success && body.data) ? body.data : item
      } catch (e) {
        logWarn('detail 接口不可用，展示列表项', e && e.message)
        this.cur = item
      }
    },

    fmtRh(rh) {
      if (!rh) return '—'
      const f = rh.finger || rh.finger_name || '—'
      const s = rh.string != null
        ? (typeof rh.string === 'number' ? (XIAN[rh.string] || rh.string) + '弦' : rh.string)
        : '—'
      return `${f} · ${s}`
    },
    fmtLh(lh) {
      if (!lh) return '散音（不按弦）'
      const f = lh.finger || '—'
      const h = lh.hui != null ? (HUI_MAP[lh.hui] || lh.hui) + '徽' : '—'
      return `${f} · ${h}`
    }
  }
}
</script>

<style scoped>
.kb { padding: 4px 0; }
.leaf :deep(.el-card__body) { padding: 18px 20px; }

.blk {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.18em;
  margin: 4px 0 12px;
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--line-soft);
}
.blk-orn {
  color: var(--zheshi);
  font-size: 9px;
  margin-right: 6px;
  vertical-align: 2px;
}
.blk2 {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 12.5px;
  color: var(--ink-soft);
  letter-spacing: 0.1em;
  margin: 14px 0 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.src-tag { letter-spacing: 0.05em; }

.search-row { display: flex; gap: 8px; margin-bottom: 12px; }
.search-row .el-input { flex: 1; }

.filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
}
.filter-row .lbl {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 13px;
  color: var(--ink-soft);
  letter-spacing: 0.18em;
}

.kb-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 460px;
  overflow-y: auto;
  border-top: 1px solid var(--line-soft);
}
.kb-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 8px;
  border-bottom: 1px dashed var(--line-soft);
  cursor: pointer;
  transition: background-color 0.2s ease;
  font-size: 13px;
}
.kb-list li:hover { background-color: rgba(246, 238, 215, 0.6); }
.kb-list li.active {
  background-color: rgba(139, 90, 60, 0.1);
  border-left: 3px solid var(--zheshi);
  padding-left: 6px;
}
.kb-key {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: var(--zheshi-deep);
  min-width: 130px;
}
.kb-cn {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 14px;
  letter-spacing: 0.1em;
  flex: 1;
}
.kb-type {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 11.5px;
  color: var(--ink-faint);
}
.kb-empty {
  justify-content: center;
  color: var(--ink-faint);
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  letter-spacing: 0.15em;
  padding: 24px 0;
}

.empty {
  color: var(--ink-faint);
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 13px;
  text-align: center;
  line-height: 2.2;
  padding: 80px 0;
  letter-spacing: 0.12em;
}
.p-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--line-soft);
}
.p-display {
  font-family: 'STXingkai', '华文行楷', 'STKaiti', 'KaiTi', serif;
  font-size: 30px;
  color: var(--ink);
  letter-spacing: 0.18em;
}
.p-key {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: var(--ink-faint);
  margin-top: 6px;
}

.parse {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 13px;
  line-height: 2;
  background-color: rgba(246, 238, 215, 0.55);
  border: 1px solid var(--line);
  border-left: 3px solid var(--zheshi);
  border-radius: 2px;
  padding: 12px 14px;
}
.parse-row .k {
  display: inline-block;
  width: 56px;
  color: var(--ink-faint);
  font-family: 'STKaiti', 'KaiTi', serif;
  letter-spacing: 0.3em;
}
.parse .meaning {
  color: var(--zhusha-deep);
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--line-soft);
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  letter-spacing: 0.06em;
}

.flags { display: flex; gap: 10px; }
.flag {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 13px;
  letter-spacing: 0.14em;
  padding: 3px 12px;
  border: 1px solid var(--line-deep);
  border-radius: 2px;
  color: var(--ink-faint);
  background: transparent;
}
.flag.on {
  color: var(--zhusha-deep);
  border-color: var(--zhusha);
  background-color: rgba(138, 53, 42, 0.08);
}
</style>