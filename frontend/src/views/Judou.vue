<!-- -*- coding: utf-8 -*- -->
<!--
  智能句读页面（泠弦智谱 V1）

  输入一串减字拼音 key（空格/逗号/换行分隔），
  调 POST /api/judou/segment 得到逐字 C/S/L/E/U 与置信度，
  横向标签展示，可按色识别边界类型。

  后端未启动时回退本地假规则（每8字E / 每4字S / 其余C），
  保证页面可独立演示。

  作者：@Wujee
  创建日期：2026-10-13
  版本：1.0.0
-->

<template>
  <div class="judou">
    <el-card shadow="never" class="leaf">
      <div class="blk"><span class="blk-orn">○</span> 减字序列输入</div>

      <div class="tip">
        输入拼音 key，用空格、逗号或换行分隔。例如：<br />
        <span class="tip-key">gou_3, da_9_gou_4, tiao_7, san_tiao_7</span>
      </div>

      <el-input
        v-model="rawInput"
        type="textarea"
        :rows="4"
        resize="none"
        placeholder="gou_3 da_9_gou_4 tiao_7 san_tiao_7 ..."
      />

      <div class="quick-row">
        <span class="lbl">示例</span>
        <el-button size="small" plain @click="fillExample(1)">四字散按</el-button>
        <el-button size="small" plain @click="fillExample(2)">八字段落</el-button>
        <el-button size="small" plain @click="fillExample(3)">含装饰音</el-button>
        <el-button size="small" plain @click="fillExample(4)">撮音段落</el-button>
      </div>

      <div class="action-row">
        <el-button type="primary" :loading="loading" @click="doSegment">
          开始句读
        </el-button>
        <el-button plain :disabled="!parsed.length" @click="clearAll">清 除</el-button>
        <el-tag v-if="parsed.length" size="small"
                :type="fromBackend ? 'success' : 'warning'">
          {{ fromBackend ? '后端识别' : '演示数据' }}
        </el-tag>
        <span v-if="parsed.length" class="cnt">共 {{ parsed.length }} 字</span>
      </div>
    </el-card>

    <!-- 结果 -->
    <el-card v-if="segments.length" shadow="never" class="leaf result-card">
      <div class="blk"><span class="blk-orn">○</span> 句读结果</div>

      <!-- 图例 -->
      <div class="legend">
        <span class="lg lg-c">C 连续</span>
        <span class="lg lg-s">S 短停</span>
        <span class="lg lg-l">L 长停</span>
        <span class="lg lg-e">E 句末</span>
        <span class="lg lg-u">U 复核</span>
      </div>

      <!-- 标签序列 -->
      <div class="seg-list">
        <div v-for="s in segments" :key="s.index"
             class="seg-item" :class="'seg-' + (s.label || 'C').toLowerCase()">
          <div class="seg-idx">{{ s.index + 1 }}</div>
          <div class="seg-key">{{ s.class_key }}</div>
          <div class="seg-label">{{ s.label }}</div>
          <div class="seg-conf">{{ (s.confidence * 100).toFixed(0) }}%</div>
        </div>
      </div>

      <!-- 文本概览 -->
      <div class="blk2"><span class="blk-orn">○</span> 演奏流</div>
      <div class="flow">
        <template v-for="(s, i) in segments" :key="i">
          <span class="flow-key">{{ s.class_key }}</span>
          <span v-if="s.label !== 'C'"
                class="flow-mark" :class="'mk-' + s.label.toLowerCase()">
            {{ markOf(s.label) }}
          </span>
        </template>
      </div>

      <div class="actions">
        <el-button plain @click="copyResult">复制结果</el-button>
      </div>
    </el-card>

    <!-- 空态 -->
    <el-card v-else shadow="never" class="leaf">
      <el-empty description="输入减字序列，点击「开始句读」" />
    </el-card>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import { segmentJudou } from '../api/index.js'
import { logInfo, logWarn } from '../logger.js'

const EXAMPLES = {
  1: 'gou_3 da_9_gou_4 tiao_7 san_tiao_7',
  2: 'gou_3 da_9_gou_4 tiao_7 san_tiao_7 gou_4 ming_10_gou_5 tiao_6 da_9_gou_3',
  3: 'da_9_gou_4 zhuang gou_3 tiao_5 zhuang san_tiao_7',
  4: 'gou_3 cuo_ming_10_gou_4_san_tiao_6 tiao_7 ming_10_tiao_4 san_tiao_6'
}

export default {
  name: 'Judou',
  data() {
    return {
      rawInput: '',
      parsed: [],
      segments: [],
      loading: false,
      fromBackend: false
    }
  },
  methods: {
    parseInput() {
      const raw = (this.rawInput || '').trim()
      if (!raw) return []
      return raw.split(/[\s,，、;；\n]+/).filter(Boolean)
    },

    fillExample(n) {
      this.rawInput = EXAMPLES[n] || ''
      logInfo('填充句读示例', `#${n}`)
    },

    async doSegment() {
      const chars = this.parseInput()
      if (!chars.length) {
        ElMessage.warning('请输入至少一个减字 key')
        return
      }
      this.parsed = chars
      this.loading = true
      try {
        const res = await segmentJudou(chars)
        const body = res && res.data
        if (!body || !body.success || !body.data || !Array.isArray(body.data.segments)) {
          throw new Error('返回结构异常')
        }
        this.segments = body.data.segments
        this.fromBackend = true
        logInfo('句读完成（后端）', `共 ${this.segments.length} 条`)
      } catch (e) {
        logWarn('句读接口不可用，回退本地假规则', e && e.message)
        this.segments = this.fakeSegments(chars)
        this.fromBackend = false
        logInfo('句读完成（演示）', `共 ${this.segments.length} 条`)
      } finally {
        this.loading = false
      }
    },

    // 本地假规则兜底：每8字E / 每4字S / 其余C；置信度<0.6标U
    fakeSegments(chars) {
      const TAU = 0.6
      return chars.map((key, i) => {
        let label, conf
        if ((i + 1) % 8 === 0) { label = 'E'; conf = 0.78 }
        else if ((i + 1) % 4 === 0) { label = 'S'; conf = 0.71 }
        else { label = 'C'; conf = 0.85 }
        if (conf < TAU) label = 'U'
        return { index: i, class_key: key, label, confidence: conf }
      })
    },

    markOf(label) {
      return { C: '·', S: '，', L: '。', E: '‖', U: '？' }[label] || '·'
    },

    clearAll() {
      this.rawInput = ''
      this.parsed = []
      this.segments = []
      this.fromBackend = false
      logInfo('清除句读结果')
    },

    async copyResult() {
      const text = this.segments.map(s =>
        `${String(s.index + 1).padStart(2, '0')}. ${s.class_key}  [${s.label}]  ${(s.confidence * 100).toFixed(0)}%`
      ).join('\n')
      try {
        await navigator.clipboard.writeText(text)
        ElMessage.success('已复制到剪贴板')
      } catch (e) {
        logWarn('剪贴板复制失败', e && e.message)
        ElMessage.warning('复制失败，请手动选择')
      }
    }
  }
}
</script>

<style scoped>
.judou { padding: 4px 0; }
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
.blk2 {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.18em;
  margin: 22px 0 12px;
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--line-soft);
}
.blk-orn {
  color: var(--zheshi);
  font-size: 9px;
  margin-right: 6px;
  vertical-align: 2px;
}

.tip {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12.5px;
  color: var(--ink-faint);
  line-height: 1.9;
  margin-bottom: 10px;
}
.tip-key {
  font-family: 'Courier New', monospace;
  color: var(--zheshi-deep);
}

.quick-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0 4px;
}
.quick-row .lbl {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 13px;
  color: var(--ink-soft);
  letter-spacing: 0.18em;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}
.cnt {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 12.5px;
  color: var(--ink-faint);
  letter-spacing: 0.1em;
}

/* 结果卡 */
.result-card { margin-top: 16px; }

/* 图例 */
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 14px;
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 12.5px;
  letter-spacing: 0.08em;
  color: var(--ink-soft);
}
.legend .lg::before {
  content: '';
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-right: 6px;
  vertical-align: 0;
  border-radius: 1px;
  border: 1px solid;
}
.lg-c::before { background: var(--zhuqing); border-color: var(--zhuqing-deep); }
.lg-s::before { background: var(--jin);    border-color: var(--wood); }
.lg-l::before { background: var(--zheshi); border-color: var(--zheshi-deep); }
.lg-e::before { background: var(--zhusha); border-color: var(--zhusha-deep); }
.lg-u::before { background: #a89b84;       border-color: var(--ink-faint); }

/* 标签序列 */
.seg-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.seg-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 76px;
  padding: 8px 10px 6px;
  background-color: rgba(246, 238, 215, 0.55);
  border: 1px solid var(--line);
  border-left-width: 4px;
  border-radius: 2px;
  transition: transform 0.15s ease;
}
.seg-item:hover { transform: translateY(-1px); }

.seg-idx {
  font-family: 'Courier New', monospace;
  font-size: 10.5px;
  color: var(--ink-faint);
  line-height: 1;
  margin-bottom: 4px;
}
.seg-key {
  font-family: 'Courier New', monospace;
  font-size: 11px;
  color: var(--ink);
  margin-bottom: 4px;
  word-break: break-all;
  text-align: center;
  max-width: 100px;
}
.seg-label {
  font-family: 'STXingkai', '华文行楷', 'STKaiti', 'KaiTi', serif;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.1;
}
.seg-conf {
  font-family: 'Courier New', monospace;
  font-size: 10.5px;
  color: var(--ink-faint);
  margin-top: 4px;
}

.seg-c { border-left-color: var(--zhuqing); }
.seg-c .seg-label { color: var(--zhuqing-deep); }
.seg-s { border-left-color: var(--jin); }
.seg-s .seg-label { color: #6d5626; }
.seg-l { border-left-color: var(--zheshi); }
.seg-l .seg-label { color: var(--zheshi-deep); }
.seg-e { border-left-color: var(--zhusha); background-color: rgba(138, 53, 42, 0.06); }
.seg-e .seg-label { color: var(--zhusha-deep); }
.seg-u { border-left-color: #a89b84; }
.seg-u .seg-label { color: var(--ink-faint); }

/* 演奏流 */
.flow {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 13.5px;
  line-height: 2.2;
  background-color: rgba(246, 238, 215, 0.55);
  border: 1px solid var(--line);
  border-left: 3px solid var(--zheshi);
  border-radius: 2px;
  padding: 12px 14px;
  word-break: break-all;
}
.flow-key {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: var(--ink);
  margin-right: 2px;
}
.flow-mark {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-weight: 700;
  margin: 0 6px 0 2px;
  letter-spacing: 0;
}
.mk-s { color: var(--jin); }
.mk-l { color: var(--zheshi-deep); }
.mk-e { color: var(--zhusha-deep); }
.mk-u { color: var(--ink-faint); }

.actions { margin-top: 16px; display: flex; gap: 10px; }
</style>