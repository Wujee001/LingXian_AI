<!-- -*- coding: utf-8 -*- -->
<!--
  整谱打谱页面（泠弦智谱 V1 · 纯前端演示）

  面向古琴学习者：上传原版减字谱（无需节拍标注）→
  一键生成示意检测框 → 点框查看 Top-3 候选、指法解析、
  节奏句读标记 → 可切换候选、拖框、删框、手动画框、
  确认或标复核 → 底部按演奏顺序输出减字序列并可导出。
  不依赖后端；接入后端时仅替换数据来源。

  作者：
      @Wujee

  创建日期：2026-10-1
  版本：1.0.0

  许可证：内部使用，未经许可不得传播。
-->

<template>
  <div class="whole-sheet">
    <!-- 工具栏 -->
    <el-card shadow="never">
      <div class="toolbar">
        <el-upload :auto-upload="false" show-file-list="false"
                   accept=".png,.jpg,.jpeg" :on-change="onPick">
          <el-button type="primary">上传减字谱</el-button>
        </el-upload>
        <el-button type="success" plain :disabled="!imageUrl" @click="genBoxes">
          一键画框
        </el-button>
        <el-button plain :disabled="!items.length" @click="clearAll">清除</el-button>
        <el-button plain :disabled="!items.length" @click="exportResult">
          导出打谱结果
        </el-button>
        <span class="fname" v-if="fileName">{{ fileName }}</span>
      </div>
    </el-card>

    <!-- 主体 -->
    <div v-if="items.length" class="work">
      <el-card shadow="never" class="canvas-card">
        <SheetCanvas :image-url="imageUrl" v-model:boxes="items" @select="onSelect" />
      </el-card>

      <el-card shadow="never" class="panel-card">
        <div v-if="cur === null" class="empty">点击左侧任意框<br />查看识别与解析</div>

        <template v-else>
          <div class="p-title">
            第 {{ selectedIdx + 1 }} 个减字
            <el-tag size="small" :type="cur.status === 'U' ? 'danger' : 'success'">
              {{ cur.status === 'U' ? '待复核' : '已确认' }}
            </el-tag>
          </div>

          <div class="blk">识别候选（Top-3）</div>
          <el-radio-group v-model="cur.pick" @change="reparse">
            <el-radio v-for="c in cur.candidates" :key="c[0]"
                      :label="c[0]" border size="small" class="cand">
              {{ c[0] }} <span class="conf">{{ (c[1] * 100).toFixed(0) }}%</span>
            </el-radio>
          </el-radio-group>

          <div class="blk">指法解析</div>
          <div class="parse">
            <div>右手：{{ cur.parse_result.right_hand.finger }} · {{ cur.parse_result.right_hand.string }}</div>
            <div>左手：{{ cur.parse_result.left_hand.finger }} · {{ cur.parse_result.left_hand.hui }}</div>
            <div class="meaning">{{ cur.parse_result.meaning }}</div>
          </div>

          <div class="blk">节奏 / 句读</div>
          <el-select v-model="cur.rhythm" size="small" style="width:100%">
            <el-option label="连续（C）" value="C" />
            <el-option label="短停（S）" value="S" />
            <el-option label="长停（L）" value="L" />
            <el-option label="句末（E）" value="E" />
          </el-select>

          <div class="actions">
            <el-button type="success" size="small" @click="confirmItem">确认</el-button>
            <el-button type="warning" size="small" @click="markReview">标记复核</el-button>
          </div>
        </template>
      </el-card>
    </div>

    <!-- 空状态 -->
    <el-card v-else shadow="never" class="blank">
      <el-empty description="请先上传一张减字谱，再点击「一键画框」" />
    </el-card>

    <!-- 减字序列 -->
    <el-card v-if="items.length" shadow="never" class="seq-card">
      <div class="blk">整谱减字序列（按演奏顺序）</div>
      <div class="seq">
        <template v-for="(it, i) in items" :key="i">
          <el-tag :type="it.status === 'U' ? 'danger' : 'info'" size="small" class="seq-tag">
            {{ it.pick }}
          </el-tag>
          <span v-if="it.rhythm && it.rhythm !== 'C'" class="rh">{{ it.rhythm }}</span>
        </template>
      </div>
    </el-card>
  </div>
</template>

<script>
/*
 * 页面逻辑：纯前端假数据演示；操作埋点 logger.js，
 * 后端接入后日志统一 mlnlog。
 */
import SheetCanvas from '../components/SheetCanvas.vue'
import { logInfo, logWarn } from '../logger.js'

const KEY_POOL = ['san_gou3', 'da9_gou4', 'san_tiao2', 'ming10_gou3', 'da9_tiao4']

export default {
  name: 'WholeSheet',
  components: { SheetCanvas },
  data() {
    return {
      imageUrl: '',
      fileName: '',
      items: [],
      selectedIdx: null
    }
  },
  computed: {
    cur() {
      return this.selectedIdx === null ? null : this.items[this.selectedIdx]
    }
  },
  methods: {
    onPick(file) {
      this.imageUrl = URL.createObjectURL(file.raw)
      this.fileName = file.name
      this.items = []
      this.selectedIdx = null
      logInfo('上传减字谱', file.name)
    },
    // 模拟检测：3 列（竖排从右往左）× 4 行示意框
    genBoxes() {
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
      this.items = boxes.map((b, i) => this.fakeItem(b, i))
      logInfo('一键画框完成', `共 ${this.items.length} 框`)
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
        parse_result: this.fakeParse(k0)
      }
    },
    fakeParse(key) {
      return {
        right_hand: { finger: '勾', string: '三弦' },
        left_hand: { finger: '—', hui: '—' },
        meaning: '【演示数据】右手中指向内弹三弦，散音。'
      }
    },
    onSelect(i) {
      this.selectedIdx = i
      if (i !== null) logInfo('选中减字', this.items[i].pick)
    },
    reparse(key) {
      this.cur.parse_result = {
        right_hand: { finger: '—', string: '—' },
        left_hand: { finger: '—', hui: '—' },
        meaning: '【演示数据】切换候选后，接入后端返回真实释义。'
      }
      this.cur.status = 'U'
      logWarn('切换识别候选', key)
    },
    confirmItem() {
      this.cur.status = 'A'
      logInfo('确认减字', this.cur.pick)
    },
    markReview() {
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
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = 'lingxian_result.txt'
      a.click()
      logInfo('导出打谱结果')
    }
  }
}
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.fname { font-size: 12px; color: var(--ink-soft); }

.work { display: flex; gap: 14px; margin-top: 14px; flex-wrap: wrap; }
.canvas-card { flex: 2 1 440px; min-width: 0; }
.panel-card { flex: 1 1 280px; min-width: 0; }
.blank { margin-top: 14px; }

.empty { color: var(--ink-soft); font-size: 13px; padding: 34px 0; text-align: center; line-height: 2; }
.p-title { font-size: 15px; font-weight: 700; display: flex; justify-content: space-between; align-items: center; font-family: 'KaiTi','STKaiti',serif; }
.blk { font-size: 12.5px; font-weight: 700; color: var(--ink-soft); margin: 16px 0 8px; }
.cand { display: flex; margin: 0 8px 8px 0; }
.conf { color: var(--ink-soft); font-size: 11px; }

.parse { font-size: 12.5px; line-height: 1.9; background: rgba(184,134,11,0.07); border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; }
.parse .meaning { color: var(--zhusha); margin-top: 4px; }

.actions { margin-top: 16px; display: flex; gap: 8px; }

.seq-card { margin-top: 14px; }
.seq { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.seq-tag { font-family: monospace; letter-spacing: 0; }
.rh { color: var(--zhusha); font-size: 12px; font-weight: 700; }
</style>
