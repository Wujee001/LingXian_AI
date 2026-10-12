<!-- -*- coding: utf-8 -*- -->
<!--
  整谱打谱页（泠弦智谱 V2）

  册页布局：左页为整谱图与检测框（占据较大宽度），
  右页为选中减字的候选、指法、句读与操作。
  底部为按演奏顺序排列的减字序列。
  接入 api/index.js；URL 带 ?mock=1 时降级本地假数据。

  作者：
      @Wujee

  创建日期：2026-10-1
  版本：2.0.0

  许可证：内部使用，未经许可不得传播。
-->

<template>
  <div class="whole-sheet">
    <!-- 工具条 -->
    <div class="toolbar">
      <el-upload
        :auto-upload="false"
        show-file-list="false"
        accept=".png,.jpg,.jpeg"
        :on-change="onPick"
      >
        <el-button type="primary">上 传 减 字 谱</el-button>
      </el-upload>
      <el-button
        type="success"
        plain
        :disabled="!imageUrl"
        :loading="loading"
        @click="genBoxes"
      >
        {{ loading ? '识别中…' : '一 键 画 框' }}
      </el-button>
      <el-button plain :disabled="!items.length" @click="clearAll">清 除</el-button>
      <el-button plain :disabled="!items.length" @click="exportResult">
        导 出 结 果
      </el-button>
      <span v-if="fileName" class="fname">〔{{ fileName }}〕</span>
    </div>

    <!-- 册页主体 -->
    <section v-if="items.length" class="book">
      <div class="page page-canvas">
        <div class="page-head">
          <span class="page-head-num">谱</span>
          <span class="page-head-title">减字谱原图</span>
        </div>
        <SheetCanvas
          :image-url="imageUrl"
          v-model:boxes="items"
          @select="onSelect"
        />
      </div>

      <div class="spine" aria-hidden="true"></div>

      <div class="page page-panel">
        <div class="page-head">
          <span class="page-head-num">释</span>
          <span class="page-head-title">识别与释义</span>
        </div>

        <div v-if="cur === null" class="empty">
          <div class="empty-mark">点</div>
          <div class="empty-main">点击左侧任一方框</div>
          <div class="empty-hint">查看候选 · 指法 · 句读</div>
        </div>

        <template v-else>
          <div class="item-title">
            <span class="item-title-text">
              第 <em>{{ selectedIdx + 1 }}</em> 个减字
            </span>
            <el-tag
              size="small"
              :type="cur.status === 'U' ? 'danger' : 'success'"
              effect="plain"
            >
              {{ cur.status === 'U' ? '待复核' : '已确认' }}
            </el-tag>
          </div>

          <div class="blk">候 选 · Top 3</div>
          <el-radio-group v-model="cur.pick" class="cands" @change="reparse">
            <el-radio
              v-for="c in cur.candidates"
              :key="c[0]"
              :value="c[0]"
              border
            >
              <span class="cand-key">{{ c[0] }}</span>
              <span class="conf">{{ (c[1] * 100).toFixed(0) }}%</span>
            </el-radio>
          </el-radio-group>

          <div class="blk">指 法 释 义</div>
          <div class="parse">
            <div class="parse-row">
              <span class="parse-label">右手</span>
              <span>
                {{ cur.parse_result.right_hand.finger }} ·
                {{ cur.parse_result.right_hand.string }}
              </span>
            </div>
            <div class="parse-row">
              <span class="parse-label">左手</span>
              <span>
                {{ cur.parse_result.left_hand.finger }} ·
                {{ cur.parse_result.left_hand.hui }}
              </span>
            </div>
            <div class="deco-divider">
              <span class="deco-mark">· 释义 ·</span>
            </div>
            <div class="meaning">{{ cur.parse_result.meaning }}</div>
          </div>

          <div class="blk">节 奏 · 句 读</div>
          <el-select v-model="cur.rhythm" size="default" style="width: 100%">
            <el-option label="连续（C）" value="C" />
            <el-option label="短停（S）" value="S" />
            <el-option label="长停（L）" value="L" />
            <el-option label="句末（E）" value="E" />
          </el-select>

          <div class="actions">
            <el-button type="success" @click="confirmItem">确 认</el-button>
            <el-button type="warning" @click="markReview">标 记 复 核</el-button>
          </div>
        </template>
      </div>
    </section>

    <!-- 空状态 -->
    <section v-else class="blank">
      <div class="blank-mark">谱</div>
      <div class="blank-title">卷 未 开</div>
      <div class="blank-hint">请先上传一张减字谱，再点「一键画框」</div>
    </section>

    <!-- 减字序列 -->
    <section v-if="items.length" class="seq-block">
      <div class="blk seq-blk">整 谱 减 字 序 列（按演奏顺序）</div>
      <div class="seq">
        <template v-for="(it, i) in items" :key="i">
          <el-tag
            :type="it.status === 'U' ? 'danger' : 'info'"
            size="default"
            effect="plain"
            class="seq-tag"
          >
            {{ it.pick }}
          </el-tag>
          <span v-if="it.rhythm && it.rhythm !== 'C'" class="rh">{{ it.rhythm }}</span>
        </template>
      </div>
    </section>
  </div>
</template>

<script>
import SheetCanvas from '../components/SheetCanvas.vue'
import { uploadSheet } from '../api/index.js'
import { logInfo, logWarn, logError } from '../logger.js'

const USE_MOCK =
  typeof window !== 'undefined' &&
  new URLSearchParams(window.location.search).get('mock') === '1'

const KEY_POOL = ['da_9_gou_4', 'san_tiao_7', 'gou_5', 'ming_10_gou_5', 'tiao_6']

export default {
  name: 'WholeSheet',
  components: { SheetCanvas },
  data() {
    return {
      imageUrl: '',
      fileRaw: null,
      fileName: '',
      items: [],
      selectedIdx: null,
      loading: false
    }
  },
  computed: {
    cur() {
      return this.selectedIdx === null ? null : this.items[this.selectedIdx]
    }
  },
  beforeUnmount() {
    this.revokeUrl()
  },
  methods: {
    revokeUrl() {
      if (this.imageUrl && this.imageUrl.startsWith('blob:')) {
        URL.revokeObjectURL(this.imageUrl)
      }
    },
    onPick(file) {
      this.revokeUrl()
      this.imageUrl = URL.createObjectURL(file.raw)
      this.fileRaw = file.raw
      this.fileName = file.name
      this.items = []
      this.selectedIdx = null
      logInfo('上传减字谱', file.name)
    },
    async genBoxes() {
      if (!this.imageUrl) return
      this.loading = true
      try {
        if (USE_MOCK) {
          this.items = this.mockBoxes()
        } else {
          const data = await uploadSheet(this.fileRaw)
          const list = data?.boxes || data?.items || (Array.isArray(data) ? data : [])
          this.items = list.map((b, i) => this.normalizeItem(b, i))
        }
        this.selectedIdx = null
        logInfo('一键画框完成', `共 ${this.items.length} 框`)
      } catch (e) {
        logError('整谱识别失败', e?.message)
      } finally {
        this.loading = false
      }
    },
    normalizeItem(b, i) {
      const cands = b.candidates || []
      const first = cands[0]?.[0] || ''
      return {
        x: b.x, y: b.y, w: b.w, h: b.h,
        status: b.status || 'A',
        candidates: cands,
        pick: b.pick || first,
        rhythm: b.rhythm || 'C',
        parse_result: b.parse_result || this.fakeParse()
      }
    },
    mockBoxes() {
      const boxes = []
      const cols = 3, rows = 4
      const cw = 0.22, ch = 0.16, gx = 0.07, gy = 0.06, x0 = 0.1, y0 = 0.08
      for (let c = 0; c < cols; c++) {
        const x = 1 - x0 - (c + 1) * cw - c * gx
        for (let r = 0; r < rows; r++) {
          boxes.push({
            x: Number(x.toFixed(4)),
            y: Number((y0 + r * (ch + gy)).toFixed(4)),
            w: cw, h: ch
          })
        }
      }
      return boxes.map((b, i) => this.fakeItem(b, i))
    },
    fakeItem(box, i) {
      const k0 = KEY_POOL[i % KEY_POOL.length]
      return {
        ...box,
        status: i % 5 === 4 ? 'U' : 'A',
        candidates: [
          [k0, 0.82],
          [KEY_POOL[(i + 1) % KEY_POOL.length], 0.11],
          [KEY_POOL[(i + 2) % KEY_POOL.length], 0.04]
        ],
        pick: k0,
        rhythm: 'C',
        parse_result: this.fakeParse()
      }
    },
    fakeParse() {
      return {
        right_hand: { finger: '勾', string: '三弦' },
        left_hand: { finger: '—', hui: '—' },
        meaning: '【演示数据】右手中指向内弹三弦，散音。'
      }
    },
    onSelect(i) {
      this.selectedIdx = i
      if (i !== null && this.items[i]) logInfo('选中减字', this.items[i].pick)
    },
    reparse(key) {
      if (!this.cur) return
      this.cur.parse_result = {
        right_hand: { finger: '—', string: '—' },
        left_hand: { finger: '—', hui: '—' },
        meaning: '【演示数据】切换候选后，接入后端返回真实释义。'
      }
      this.cur.status = 'U'
      logInfo('切换识别候选', key)
    },
    confirmItem() {
      if (!this.cur) return
      this.cur.status = 'A'
      logInfo('确认减字', this.cur.pick)
    },
    markReview() {
      if (!this.cur) return
      this.cur.status = 'U'
      logWarn('标记人工复核', this.cur.pick)
    },
    clearAll() {
      this.items = []
      this.selectedIdx = null
      logInfo('清除画布')
    },
    exportResult() {
      const lines = this.items.map((it, i) => {
        const rh = it.rhythm && it.rhythm !== 'C' ? `  [${it.rhythm}]` : ''
        return `${String(i + 1).padStart(2, '0')}. ${it.pick}${rh}`
      })
      const text = `泠弦智谱 · 打谱结果\n源文件：${this.fileName}\n\n${lines.join('\n')}\n`
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'lingxian_result.txt'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(url), 0)
      logInfo('导出打谱结果')
    }
  }
}
</script>

<style scoped>
.whole-sheet {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ===== 工具条 ===== */
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 14px 20px;
  background: var(--paper-warm);
  border: 1px solid var(--line);
  border-radius: 2px;
  box-shadow: var(--shadow-card);
}
.fname {
  margin-left: auto;
  font-family: var(--font-brush);
  font-size: 13px;
  color: var(--ink-mute);
  letter-spacing: 2px;
}

/* ===== 册页 ===== */
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
    radial-gradient(circle at 0% 0%,     rgba(120, 90, 50, 0.10), transparent 5%),
    radial-gradient(circle at 100% 0%,   rgba(120, 90, 50, 0.08), transparent 5%),
    radial-gradient(circle at 0% 100%,   rgba(120, 90, 50, 0.10), transparent 5%),
    radial-gradient(circle at 100% 100%, rgba(120, 90, 50, 0.08), transparent 5%);
  z-index: 3;
}

.page { padding: 26px 30px 30px; position: relative; }
.page-canvas { flex: 1 1 62%; min-width: 0; }
.page-panel  { flex: 1 1 38%; min-width: 0; }

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
  margin-bottom: 18px;
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

/* ===== 通用块标题 ===== */
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
.blk:first-child { margin-top: 0; }

/* ===== 空态 ===== */
.empty {
  color: var(--ink-mute);
  text-align: center;
  padding: 70px 0 50px;
  line-height: 1.9;
}
.empty-mark {
  width: 66px; height: 66px;
  margin: 0 auto 14px;
  border: 1px solid var(--line-strong);
  border-radius: 2px;
  color: var(--zheshi);
  font-family: var(--font-brush);
  font-size: 34px;
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
  opacity: 0.55;
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
  margin-top: 4px;
  letter-spacing: 2px;
}

/* ===== 选中标题 ===== */
.item-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--line);
  margin-bottom: 4px;
}
.item-title-text {
  font-family: var(--font-brush);
  font-size: 15px;
  letter-spacing: 2px;
  color: var(--ink);
}
.item-title-text em {
  font-style: normal;
  color: var(--zhusha);
  padding: 0 4px;
  font-size: 17px;
}

/* ===== 候选 ===== */
.cands { display: flex; flex-wrap: wrap; }
.cand-key {
  font-family: 'Courier New', monospace;
  letter-spacing: 0;
  color: var(--ink);
}
.conf {
  color: var(--ink-mute);
  font-size: 11.5px;
  margin-left: 8px;
  font-family: var(--font-song);
}

/* ===== 释义框 ===== */
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

/* ===== 操作 ===== */
.actions {
  margin-top: 22px;
  display: flex;
  gap: 10px;
}
.actions .el-button { flex: 1; }

/* ===== 空白卷（未上传） ===== */
.blank {
  text-align: center;
  padding: 100px 20px;
  background: var(--paper-warm);
  border: 1px solid var(--line);
  border-radius: 2px;
  box-shadow: var(--shadow-card);
}
.blank-mark {
  width: 90px; height: 90px;
  margin: 0 auto 20px;
  border: 2px solid var(--line-strong);
  border-radius: 2px;
  color: var(--zheshi);
  font-family: var(--font-brush);
  font-size: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.blank-mark::before {
  content: '';
  position: absolute;
  inset: 6px;
  border: 1px solid var(--line);
  border-radius: 1px;
}
.blank-title {
  font-family: var(--font-brush);
  font-size: 20px;
  letter-spacing: 10px;
  color: var(--ink);
  margin-bottom: 10px;
  text-indent: 10px;
}
.blank-hint {
  font-size: 13px;
  color: var(--ink-mute);
  letter-spacing: 2px;
}

/* ===== 减字序列 ===== */
.seq-block {
  padding: 20px 22px;
  background: var(--paper-warm);
  border: 1px solid var(--line);
  border-radius: 2px;
  box-shadow: var(--shadow-card);
}
.seq-blk { margin-top: 0; }
.seq {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.seq-tag {
  font-family: 'Courier New', monospace;
  letter-spacing: 0;
  font-size: 12.5px;
  padding: 5px 10px;
}
.rh {
  color: var(--zhusha);
  font-family: var(--font-brush);
  font-size: 13px;
  font-weight: 400;
  padding: 0 2px;
}

@media (max-width: 960px) {
  .book { flex-direction: column; }
  .spine { display: none; }
  .page { padding: 22px 18px 26px; }
  .page-panel { border-top: 1px solid var(--line-soft); }
}
</style>