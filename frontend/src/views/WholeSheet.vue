<!-- -*- coding: utf-8 -*- -->
<!--
  整谱打谱页面（泠弦智谱 V1）

  流程：上传减字谱 → 一键画框（检测+分类+解析）→
       自动调用 /api/judou/segment 得到 C/S/L/E 句读 →
       手动画框时自动裁剪该区域调 /api/char/predict 识别 →
       确认或标记复核时回传 /api/sheet/correct。

  作者：@zlx @Wujee
  更新日期：2026-10-13
  版本：1.3.1（2026-10-27 @zjx：区分注册表候选与已有详细词条）
-->

<template>
  <div class="whole-sheet">
    <el-card shadow="never" class="leaf">
      <div class="toolbar">
        <el-upload :auto-upload="false" show-file-list="false"
                   accept=".png,.jpg,.jpeg" :on-change="onPick">
          <el-button type="primary">上传减字谱</el-button>
        </el-upload>
        <el-button type="success" plain :disabled="!imageUrl" :loading="detecting" @click="genBoxes">
          一键画框
        </el-button>
        <el-radio-group v-model="engine" size="small" :disabled="detecting">
          <el-radio-button label="auto">自动</el-radio-button>
          <el-radio-button label="yolo">本地模型</el-radio-button>
          <el-radio-button label="qwen">多模态</el-radio-button>
        </el-radio-group>
        <el-button plain :disabled="!items.length || judouLoading" :loading="judouLoading"
                   @click="fetchJudou">智能句读</el-button>
        <el-button plain :disabled="!items.length" @click="clearAll">清 除</el-button>
        <el-button plain :disabled="!items.length" @click="exportResult">
          导出打谱结果
        </el-button>
        <el-tag v-if="items.length" size="small" :type="fromBackend ? 'success' : 'warning'">
          {{ sourceLabel }}
        </el-tag>
        <span class="fname" v-if="fileName">{{ fileName }}</span>
      </div>
    </el-card>

    <div v-if="imageUrl" class="work">
      <el-card shadow="never" class="canvas-card leaf">
        <SheetCanvas :image-url="imageUrl" v-model:boxes="items"
                     @select="onSelect" @box-added="onBoxAdded" />
      </el-card>

      <el-card shadow="never" class="panel-card leaf">
        <div v-if="cur === null" class="empty">点击左侧任一框<br />查看释读与释义</div>

        <template v-else>
          <div class="p-title">
            <span>第 {{ selectedIdx + 1 }} 字</span>
            <el-tag size="small" :type="cur.status === 'U' ? 'danger' : 'success'">
              {{ cur.status === 'A' ? '已人工确认' : '待复核' }}
            </el-tag>
          </div>

          <div class="blk"><span class="blk-orn">○</span> 识别候选</div>

          <div v-if="cur.detection_confidence != null" class="hint-hint">
            定位置信度 {{ (cur.detection_confidence * 100).toFixed(0) }}% · 指法为独立模型候选
          </div>
          <div v-if="cur.attributes_top3 && Object.keys(cur.attributes_top3).length" class="attributes-grid">
            <div v-for="f in attributeFields" :key="f[0]" class="attribute-field">
              <label>{{ f[1] }}</label>
              <el-select v-model="cur.attributes_selected[f[0]]" size="small"
                         filterable allow-create default-first-option
                         @change="onAttributeChanged">
                <el-option v-for="op in (cur.attributes_top3[f[0]] || [])"
                           :key="op.value" :label="op.value + '（' + (op.score * 100).toFixed(0) + '%）'"
                           :value="op.value" />
              </el-select>
            </div>
            <p class="model-caution">八字段是 AI 猜测，NA 表示字中未明写；可手动修改后点击「确认」。</p>
            <div class="manual-key-row">
              <label>完整减字知识库键（选填）</label>
              <el-input v-model="cur.pick" size="small" placeholder="可选：如 ming_10_gou_4"
                        @change="onKeyChanged" />
              <span class="model-caution">新增类别仅有目录名称，确认类别不等于已有详细释义；句读仍需已有详细词条。</span>
            </div>
          </div>
          <!-- 识别中 -->
          <div v-if="cur.recognizing" class="hint-hint">识别中，请稍候…</div>

          <!-- 有候选 -->
          <el-radio-group v-else-if="cur.candidates && cur.candidates.length"
                          v-model="cur.pick" @change="reparse">
            <el-radio v-for="c in cur.candidates" :key="c[0]"
                      :label="c[0]" border size="small" class="cand">
              {{ c[0] }} <span class="conf">{{ (c[1] * 100).toFixed(0) }}%</span>
            </el-radio>
          </el-radio-group>

          <!-- 无候选 -->
          <div v-else class="hint-hint">
            <div v-if="cur.raw_label" class="raw-lbl">
              本地模型初判：{{ cur.raw_label }}
            </div>
            模型未提供可直接对应知识库的整字类别。请核对上方属性候选，或选择多模态重认。
            <div class="retry-row">
              <el-button size="small" type="primary" plain class="retry-btn"
                         :loading="cur.recognizing" @click="retryRecognize('qwen')">
                多模态重认
              </el-button>
              <el-button size="small" plain class="retry-btn"
                         :loading="cur.recognizing" @click="retryRecognize()">
                重新识别
              </el-button>
            </div>
          </div>

          <div class="blk"><span class="blk-orn">○</span> 指法释义</div>
          <div class="parse">
            <div class="parse-row">
              <span class="k">右 手</span>
              {{ cur.parse_result?.right_hand?.finger || '—' }} · {{ cur.parse_result?.right_hand?.string ?? '—' }}
            </div>
            <div class="parse-row">
              <span class="k">左 手</span>
              {{ cur.parse_result?.left_hand?.finger || '—' }} · {{ cur.parse_result?.left_hand?.hui ?? '—' }}
            </div>
            <div class="meaning">{{ cur.parse_result ? cur.parse_result.meaning : '暂无释义' }}</div>
          </div>

          <div class="blk">
            <span class="blk-orn">○</span> 节奏 · 句读
            <span v-if="cur.rhythmConf != null" class="conf-inline">
              模型置信度 {{ (cur.rhythmConf * 100).toFixed(0) }}%
            </span>
          </div>
          <el-select v-model="cur.rhythm" size="small" style="width:100%" @change="onRhythmChange">
            <el-option label="连 续（C）" value="C" />
            <el-option label="短 停（S）" value="S" />
            <el-option label="长 停（L）" value="L" />
            <el-option label="句 末（E）" value="E" />
            <el-option label="待复核（U）" value="U" />
          </el-select>

          <div class="actions">
            <el-button type="success" size="small" @click="confirmItem">确 认</el-button>
            <el-button type="warning" size="small" @click="markReview">标 记 复 核</el-button>
            <el-button size="small" plain :loading="cur.recognizing"
                       @click="retryRecognize('qwen')">多模态重认</el-button>
          </div>
        </template>
      </el-card>
    </div>

    <el-card v-else shadow="never" class="blank leaf">
      <el-empty description="请先上传一张减字谱，再点击「一键画框」" />
    </el-card>

    <el-card v-if="items.length" shadow="never" class="seq-card leaf">
      <div class="blk"><span class="blk-orn">○</span> 整谱减字序列（按演奏顺序）</div>
      <div class="seq">
        <template v-for="(it, i) in items" :key="i">
          <el-tag :type="it.status === 'U' ? 'danger' : 'info'" size="small" class="seq-tag">
            {{ it.pick === '待人工确认' ? (it.attributes_selected?.rh || 'NA') + '/' + (it.attributes_selected?.string || 'NA') : it.pick }}
          </el-tag>
          <span v-if="it.rhythm && it.rhythm !== 'C'" class="rh">{{ it.rhythm }}</span>
        </template>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import SheetCanvas from '../components/SheetCanvas.vue'
import { uploadSheet, correctSheet, segmentJudou, predictSingle, parseAttributes, getKbItem } from '../api/index.js'
import { logInfo, logWarn } from '../logger.js'

const ATTR_FIELDS = [
  ['rh','右手动作'],['string','弦序'],['lh','左手按指'],
  ['hui_base','徽位'],['hui_frac','徽分'],['mod','技法'],['tone','音类'],['strings','复合弦序']
]

const XIAN = ['', '一', '二', '三', '四', '五', '六', '七']
const HUI_MAP = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十', 11: '十一', 12: '十二', 13: '十三' }

export default {
  name: 'WholeSheet',
  components: { SheetCanvas },
  computed: {
    attributeFields() { return ATTR_FIELDS },
    cur() { return this.selectedIdx === null ? null : (this.items[this.selectedIdx] || null) },
    sourceLabel() {
      if (this.source === 'stage1_yolo+stage2') return 'YOLO定位 + ResNet18候选（待核）'
      if (this.source === 'stage1_yolo_only') return '仅YOLO定位（指法待填）'
      if (this.source === 'stage1_yolo+qwen') return 'YOLO定位 + 多模态候选（待核）'
      if (this.source === 'unavailable') return '模型不可用 · 请手动画框'
      return '尚未识别'
    }
  },
  data() {
    return {
      rawFile: null,
      imageUrl: '',
      fileName: '',
      items: [],
      selectedIdx: null,
      fromBackend: false,
      source: '',          // stage1_yolo+stage2 / stage1_yolo_only / qwen
      engine: 'auto',      // auto / yolo / qwen（用户手动切换）
      backendImageUrl: '', // 后端保存的谱图地址（随人工修正回传）
      detecting: false,
      judouLoading: false
    }
  },
  methods: {
    onPick(file) {
      this.rawFile = file.raw
      this.imageUrl = URL.createObjectURL(file.raw)
      this.fileName = file.name
      this.items = []
      this.selectedIdx = null
      this.fromBackend = false
      this.source = ''
      this.backendImageUrl = ''
      logInfo('上传减字谱', file.name)
    },

    // 一键画框：后端优先，失败回退模拟框；成功后自动调句读
    async genBoxes() {
      if (!this.rawFile) return
      this.detecting = true
      try {
        const res = await uploadSheet(this.rawFile, this.engine)
        const body = res && res.data
        if (!body || !body.success || !body.data || !Array.isArray(body.data.items)) {
          throw new Error('后端返回结构异常')
        }
        this.items = body.data.items.map(it => ({
          x: it.box.x,
          y: it.box.y,
          w: it.box.w,
          h: it.box.h,
          status: 'U', // 没有人工确认的结果不能自动标为A
          candidates: (it.candidates || []).map(c => [c[0], c[1]]),
          pick: (it.candidates && it.candidates[0] && it.candidates[0][0]) || '待人工确认',
          key_verified: false,
          knowledge_status: 'field_candidate',
          raw_label: it.raw_label || '',
          rhythm: 'U',
          rhythmConf: null,
          parse_result: this.fmtParse(it.parse_result),
          attributes_top3: it.attributes_top3 || {},
          attributes_selected: { ...(it.attributes_selected || {}) },
          detection_confidence: it.detection_confidence,
          review_reasons: it.review_reasons || [],
          recognizing: false
        }))
        this.fromBackend = true
        this.source = body.data.source || 'unavailable'
        this.backendImageUrl = body.data.image_url || ''
        logInfo('整谱检测完成（后端）', `共 ${this.items.length} 框，来源=${this.source}`)
        if (body.data.warning) ElMessage.warning(body.data.warning)
        if (!this.items.length) ElMessage.info('暂无模型框，可在左侧手动添加')
      } catch (e) {
        logWarn('后端整谱检测不可用：不生成假框', e && e.message)
        ElMessage.error('后端不可用：没有产生模型预测框，可手动添加框')
        this.items = []
        this.fromBackend = false
        this.source = 'unavailable' 
      } finally {
        this.detecting = false
      }
      // 不自动运行句读：模型尚未确认减字且旧句读可能为演示规则。
    },

    // 手动画框后：裁剪 → 单字识别（可强制引擎）→ 回填
    async onBoxAdded(idx, forceEngine) {
      const it = this.items[idx]
      if (!it) return
      const engine = forceEngine || 'auto'
      it.recognizing = true
      logInfo('手动画框，开始识别', `index=${idx} engine=${engine}`)
      try {
        const file = await this.cropByBox(this.imageUrl, it)
        const res = await predictSingle(file, engine)
        const body = res && res.data
        if (!body || !body.success || !body.data || !Array.isArray(body.data.candidates)) {
          throw new Error('识别返回异常')
        }
        it.candidates = body.data.candidates.map(c => [c.class_key, c.confidence])
        it.pick = body.data.top_key || (it.candidates[0] && it.candidates[0][0]) || '待人工确认'
        it.parse_result = this.fmtParse(body.data.parse_result)
        it.attributes_top3 = body.data.attributes_top3 || {}
        it.attributes_selected = { ...(body.data.attributes_selected || {}) }
        it.review_reasons = body.data.review_reasons || []
        it.status = 'U'
        it.key_verified = false
        it.knowledge_status = 'field_candidate'
        logInfo('手动框识别完成', it.pick)
      } catch (e) {
        logWarn('手动框识别失败', e && e.message)
        it.candidates = []
        it.pick = '待人工确认'
        it.parse_result = this.emptyParse()
        it.status = 'U'
        ElMessage.warning('新框识别失败，可调整框后重试，或检查后端')
      } finally {
        it.recognizing = false
      }
    },

    // 手动点"重新识别"（forceEngine 可传 qwen 强制多模态）
    async retryRecognize(forceEngine) {
      if (this.selectedIdx === null) return
      await this.onBoxAdded(this.selectedIdx, forceEngine)
    },

    // 用 canvas 从原图裁剪出归一化 box 对应的区域，返回 File
    cropByBox(imageUrl, box) {
      return new Promise((resolve, reject) => {
        const img = new Image()
        img.onload = () => {
          try {
            const nw = img.naturalWidth
            const nh = img.naturalHeight
            const x = Math.max(0, Math.round(box.x * nw))
            const y = Math.max(0, Math.round(box.y * nh))
            const w = Math.max(1, Math.min(nw - x, Math.round(box.w * nw)))
            const h = Math.max(1, Math.min(nh - y, Math.round(box.h * nh)))
            const canvas = document.createElement('canvas')
            canvas.width = w
            canvas.height = h
            const ctx = canvas.getContext('2d')
            ctx.drawImage(img, x, y, w, h, 0, 0, w, h)
            canvas.toBlob(blob => {
              if (!blob) return reject(new Error('canvas 输出为空'))
              resolve(new File([blob], 'crop.png', { type: 'image/png' }))
            }, 'image/png')
          } catch (e) {
            reject(e)
          }
        }
        img.onerror = () => reject(new Error('图片加载失败'))
        img.src = imageUrl
      })
    },

    emptyParse() {
      return {
        right_hand: { finger: '—', string: '—' },
        left_hand: { finger: '—', hui: '—' },
        meaning: '暂未识别，请重新识别或检查后端'
      }
    },

    // 仅提交人工已确认的 class_key；不把属性字典误送到旧句读接口。
    async fetchJudou() {
      if (!this.items.length) return
      if (this.items.some(it => it.status !== 'A' || !it.key_verified)) {
        ElMessage.warning('句读需要每个框都有人工确认且知识库可匹配的完整类别键')
        return
      }
      this.judouLoading = true
      try {
        const chars = this.items.map(it => it.pick)
        const res = await segmentJudou(chars)
        const body = res && res.data
        const segs = (body && body.success && body.data && body.data.segments) || []
        if (body.data.source === 'fake') {
          ElMessage.warning('句读接口返回演示规则，未应用为实际打谱结果')
          return
        }
        if (!Array.isArray(segs) || !segs.length) throw new Error('句读返回为空')
        segs.forEach(s => {
          const it = this.items[s.index]
          if (it) {
            it.rhythm = s.label || 'C'
            it.rhythmConf = typeof s.confidence === 'number' ? s.confidence : null
          }
        })
        logInfo('智能句读完成', `共 ${segs.length} 条`)
      } catch (e) {
        logWarn('句读接口不可用，节奏全部默认 C', e && e.message)
      } finally {
        this.judouLoading = false
      }
    },

    fmtParse(p) {
      if (!p) return this.emptyParse()
      const rh = p.right_hand || {}
      const lh = p.left_hand
      return {
        right_hand: {
          finger: rh.finger || '—',
          string: rh.string == null ? '—' : (/^[1-7]$/.test(String(rh.string)) ? (XIAN[rh.string] || String(rh.string)) + '弦' : String(rh.string))
        },
        left_hand: lh
          ? { finger: lh.finger || '—', hui: lh.hui == null ? '—' : (/^\d+$/.test(String(lh.hui)) ? (HUI_MAP[lh.hui] || String(lh.hui)) + '徽' : String(lh.hui)) }
          : { finger: p.knowledge_status === 'registry_candidate' || p.knowledge_status === 'unknown_key' ? '未核定' : '未明写', hui: '—' },
        meaning: p.meaning || '暂未收录该减字释义'
      }
    },
    onSelect(i) {
      this.selectedIdx = i
      if (i !== null) logInfo('选中减字', this.items[i].pick)
    },
    async onKeyChanged() {
      if (!this.cur) return
      this.cur.status = 'U'
      this.cur.key_verified = false
      this.cur.knowledge_status = 'unresolved'
      const key = (this.cur.pick || '').trim()
      if (!key || key === '待人工确认') return
      try {
        const res = await getKbItem(key)
        const item = res?.data?.data
        if (!item) throw new Error('类别查询结果为空')
        this.cur.parse_result = this.fmtParse(item)
        this.cur.knowledge_status = item.knowledge_status || 'legacy_detail'
        if (this.cur.knowledge_status === 'registry_candidate') {
          // 仅查到目录≠已有完整知识；人工可确认 key，但不能将其作为句读词条。
          ElMessage.warning('已找到候选类别，详细释义待人工复核；确认后仍不自动送入句读')
        } else {
          this.cur.key_verified = true
          ElMessage.success('找到已有详细词条，仍需人工确认')
        }
      } catch (_) {
        ElMessage.warning('类别目录中未找到该key；请检查拼写或仅保存八字段')
      }
    },
    async onAttributeChanged() {
      if (!this.cur) return
      this.cur.status = 'U'
      // 八字段修改后，原整字类别不再当然成立，必须重新核对。
      this.cur.key_verified = false
      this.cur.knowledge_status = 'field_candidate'
      if (this.cur.pick && this.cur.pick !== '待人工确认') this.cur.pick = '待人工确认'
      try {
        const res = await parseAttributes(this.cur.attributes_selected)
        this.cur.parse_result = this.fmtParse(res.data.data)
      } catch (err) {
        logWarn('属性释义刷新失败', err?.message)
      }
    },
    reparse(key) {
      this.cur.parse_result = {
        right_hand: { finger: '—', string: '—' },
        left_hand: { finger: '—', hui: '—' },
        meaning: '切换候选后，该框释义以人工确认为准。'
      }
      this.cur.status = 'U'
      this.cur.key_verified = false
      this.cur.knowledge_status = 'unresolved'
      logWarn('切换识别候选', key)
    },

    onRhythmChange(v) {
      logInfo('调整句读', `${this.cur.pick} → ${v}`)
    },

    async confirmItem() {
      const chosenKey = this.cur.pick && this.cur.pick !== '待人工确认' ? this.cur.pick : null
      if (chosenKey && !this.cur.key_verified) {
        await this.onKeyChanged()
        if (!this.cur.key_verified && this.cur.knowledge_status !== 'registry_candidate') {
          ElMessage.warning('该类别尚未在目录中登记；请清空key后仅保存八字段')
          return
        }
      }
      const ok = await this._reportCorrect(chosenKey)
      if (ok) {
        this.cur.status = 'A'
        if (this.cur.knowledge_status === 'registry_candidate') {
          this.cur.key_verified = false // 不得把仅有目录的类送入自动句读
          ElMessage.success('已记录人工确认的类别；专业释义尚待审核')
        } else {
          ElMessage.success('人工确认已保存')
        }
      }
    },
    async markReview() {
      this.cur.status = 'U'
      logWarn('标记人工复核', this.cur.pick)
      await this._reportCorrect(null)
    },
    async _reportCorrect(confirmedKey) {
      try {
        await correctSheet({
          image_url: this.backendImageUrl,
          index: this.selectedIdx,
          box: { x: this.cur.x, y: this.cur.y, w: this.cur.w, h: this.cur.h },
          origin_key: (this.cur.candidates && this.cur.candidates[0] && this.cur.candidates[0][0]) || null,
          confirmed_key: confirmedKey,
          source: this.source,
          knowledge_status: this.cur.knowledge_status || 'unresolved',
          needs_meaning_review: this.cur.knowledge_status === 'registry_candidate',
          attributes_selected: this.cur.attributes_selected,
          attributes_top3: this.cur.attributes_top3,
          detection_confidence: this.cur.detection_confidence,
          rhythm: this.cur.rhythm
        })
        logInfo('修正回流成功', `index=${this.selectedIdx} key=${confirmedKey}`)
        return true
      } catch (e) {
        logWarn('修正回流失败', e && e.message)
        ElMessage.error('人工确认未保存，请检查后端')
        return false
      }
    },

    clearAll() {
      this.items = []
      this.selectedIdx = null
      logInfo('清除画布')
    },
    exportResult() {
      const lines = this.items.map((it, i) => {
        const rh = it.rhythm && it.rhythm !== 'C' ? `  [${it.rhythm}]` : ''
        return `${String(i + 1).padStart(2, '0')}. ${it.pick || '待人工确认'}${rh}  [${it.status === 'A' ? '人工已确认' : 'AI候选待复核'}]  属性：${JSON.stringify(it.attributes_selected || {})}`
      })
      const text = `泠弦智谱 · 打谱结果\n源文件：${this.fileName}\n数据来源：${this.sourceLabel}
提示：模型属性仅为候选，不代表自动完成谱理、句读；以人工确认记录为准。\n\n${lines.join('\n')}\n`
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
.whole-sheet { padding: 4px 0; }
.leaf :deep(.el-card__body) { padding: 16px 18px; }

.toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.fname {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12px;
  color: var(--ink-faint);
  letter-spacing: 0.02em;
}

.work { display: flex; gap: 16px; margin-top: 16px; flex-wrap: wrap; }
.canvas-card { flex: 2 1 460px; min-width: 0; }
.panel-card { flex: 1 1 300px; min-width: 0; }
.blank { margin-top: 16px; }

.p-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.22em;
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--line-soft);
  margin-bottom: 4px;
}

.blk {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.18em;
  margin: 16px 0 10px;
  padding-bottom: 5px;
  border-bottom: 1px dashed var(--line-soft);
}
.blk-orn {
  color: var(--zheshi);
  font-size: 9px;
  margin-right: 6px;
  vertical-align: 2px;
}
.conf-inline {
  float: right;
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 11.5px;
  font-weight: normal;
  color: var(--ink-faint);
  letter-spacing: 0.02em;
}

.empty {
  color: var(--ink-faint);
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 13px;
  text-align: center;
  line-height: 2.2;
  padding: 46px 0;
  letter-spacing: 0.14em;
}

.hint-hint {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 12.5px;
  color: var(--ink-faint);
  letter-spacing: 0.1em;
  padding: 6px 0;
}
.retry-btn { margin-left: 8px; }
.retry-row { margin-top: 8px; }
.raw-lbl {
  color: var(--zhusha-deep);
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  margin-bottom: 4px;
  letter-spacing: 0.04em;
}

.cand { display: flex; margin: 0 8px 10px 0; font-family: 'SimSun', 'Songti SC', serif; }
.conf { color: var(--ink-faint); font-size: 11px; margin-left: 4px; }

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

.attributes-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:8px 0 12px; }
.attribute-field label { display:block; font-size:12px; margin-bottom:4px; color:var(--ink-faint); }
.model-caution { font-size:11px; line-height:1.6; grid-column:1 / -1; color:var(--zhusha-deep); margin:2px 0; }
.manual-key-row {grid-column:1 / -1;}
.manual-key-row label {font-size:12px;color:var(--ink-faint);display:block;margin-bottom:5px;}
.actions { margin-top: 18px; display: flex; gap: 10px; }

.seq-card { margin-top: 16px; }
.seq { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.seq-tag { font-family: 'Courier New', monospace; letter-spacing: 0; font-size: 11.5px; }
.rh {
  color: var(--zhusha-deep);
  font-family: 'STKaiti', 'KaiTi', serif;
  font-size: 13px;
  font-weight: 700;
  margin: 0 4px;
}
</style>