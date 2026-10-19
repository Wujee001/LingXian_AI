<!-- -*- coding: utf-8 -*- -->
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
        <el-button plain :disabled="!items.length || judouLoading" :loading="judouLoading"
                   @click="fetchJudou">智能句读</el-button>
        <el-button plain :disabled="!items.length" @click="clearAll">清 除</el-button>
        <el-button plain :disabled="!items.length" @click="exportResult">
          导出打谱结果
        </el-button>
        <el-tag v-if="items.length" size="small" type="success">本地模型识别</el-tag>
        <span class="fname" v-if="fileName">{{ fileName }}</span>
      </div>
    </el-card>

    <div v-if="items.length" class="work">
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
              {{ cur.status === 'U' ? '待复核' : '已确认' }}
            </el-tag>
          </div>

          <div class="blk"><span class="blk-orn">○</span> 识别候选</div>

          <div v-if="cur.recognizing" class="hint-hint">识别中，请稍候…</div>

          <el-radio-group v-else-if="cur.candidates && cur.candidates.length"
                          v-model="cur.pick" @change="reparse">
            <el-radio v-for="c in cur.candidates" :key="c[0]"
                      :label="c[0]" border size="small" class="cand">
              {{ cur.parse_result.display_name }} <span class="conf">{{ (c[1] * 100).toFixed(0) }}%</span>
            </el-radio>
          </el-radio-group>

          <div v-else class="hint-hint">
            本地模型未给出可靠结果，请手动修正
          </div>

          <div class="blk"><span class="blk-orn">○</span> 指法释义</div>
          <div class="parse">
            <div class="parse-row">
              <span class="k">右 手</span>
              {{ cur.parse_result ? cur.parse_result.right_hand.finger : '—' }} · {{ cur.parse_result ? cur.parse_result.right_hand.string : '—' }}
            </div>
            <div class="parse-row">
              <span class="k">左 手</span>
              {{ cur.parse_result ? cur.parse_result.left_hand.finger : '—' }} · {{ cur.parse_result ? cur.parse_result.left_hand.hui : '—' }}
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
            <el-button type="warning" size="small" @click="openCorrectDialog">识别有误，手动修正</el-button>
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
            {{ it.parse_result.display_name || it.pick }}
          </el-tag>
          <span v-if="it.rhythm && it.rhythm !== 'C'" class="rh">{{ it.rhythm }}</span>
        </template>
      </div>
    </el-card>

    <!-- 手动修正弹窗 -->
    <el-dialog v-model="correctDialogVisible" title="手动修正识别结果" width="420px">
      <el-form label-width="90px">
        <el-form-item label="原识别结果">
          <el-input :value="cur ? cur.pick : ''" disabled />
        </el-form-item>
        <el-form-item label="正确减字">
          <el-input v-model="correctKey" placeholder="请输入正确的减字名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="correctDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCorrect">提交反馈</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import SheetCanvas from '../components/SheetCanvas.vue'
import { uploadSheet, submitCorrection, segmentJudou, predictSingle } from '../api/index.js'
import { logInfo, logWarn } from '../logger.js'

const XIAN = ['', '一', '二', '三', '四', '五', '六', '七']
const HUI_MAP = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十', 11: '十一', 12: '十二', 13: '十三' }

export default {
  name: 'WholeSheet',
  components: { SheetCanvas },
  data() {
    return {
      rawFile: null,
      imageUrl: '',
      fileName: '',
      items: [],
      selectedIdx: null,
      backendImageUrl: '',
      detecting: false,
      judouLoading: false,
      correctDialogVisible: false,
      correctKey: '',
      submitting: false
    }
  },
  computed: {
    cur() {
      return this.selectedIdx === null ? null : this.items[this.selectedIdx]
    }
  },
  methods: {
    onPick(file) {
      this.rawFile = file.raw
      this.imageUrl = URL.createObjectURL(file.raw)
      this.fileName = file.name
      this.items = []
      this.selectedIdx = null
      this.backendImageUrl = ''
      logInfo('上传减字谱', file.name)
    },

    async genBoxes() {
      if (!this.rawFile) return
      this.detecting = true
      try {
        const res = await uploadSheet(this.rawFile)
        const body = res && res.data
        if (!body || !body.success || !body.data || !Array.isArray(body.data.items)) {
          throw new Error('后端返回结构异常')
        }
        this.items = body.data.items.map(it => ({
          x: it.box.x,
          y: it.box.y,
          w: it.box.w,
          h: it.box.h,
          status: it.status || 'A',
          candidates: it.candidates || [],
          pick: (it.candidates && it.candidates[0] && it.candidates[0][0]) || 'unknown',
          raw_label: it.raw_label || '',
          rhythm: 'C',
          rhythmConf: null,
          parse_result: this.fmtParse(it.parse_result),
          recognizing: false
        }))
        this.backendImageUrl = body.data.image_url || ''
        logInfo('整谱本地检测完成', `共 ${this.items.length} 框`)
        if (!this.items.length) ElMessage.info('未检测到减字框，请更换清晰谱图')
      } catch (e) {
        logWarn('整谱检测失败', e && e.message)
        ElMessage.error('识别服务异常，请联系开发人员检查')
      } finally {
        this.detecting = false
      }
      if (this.items.length) await this.fetchJudou()
    },

    async onBoxAdded(idx) {
      const it = this.items[idx]
      if (!it) return
      it.recognizing = true
      logInfo('手动画框，开始识别', `index=${idx}`)
      try {
        const file = await this.cropByBox(this.imageUrl, it)
        const res = await predictSingle(file)
        const body = res && res.data
        if (!body || !body.success || !body.data || !Array.isArray(body.data.candidates)) {
          throw new Error('识别返回异常')
        }
        it.candidates = body.data.candidates
        it.pick = body.data.top_key || (it.candidates[0] && it.candidates[0][0]) || 'unknown'
        it.parse_result = this.fmtParse(body.data.parse_result)
        if (it.candidates.length) {
          it.status = (it.candidates[0][1] >= 0.6) ? 'A' : 'U'
        }
        logInfo('手动框识别完成', it.pick)
      } catch (e) {
        logWarn('手动框识别失败', e && e.message)
        it.candidates = []
        it.pick = 'unknown'
        it.parse_result = this.emptyParse()
        it.status = 'U'
        ElMessage.error('识别失败，请联系开发人员检查')
      } finally {
        it.recognizing = false
      }
    },

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
        meaning: '暂未识别，请手动修正'
      }
    },

    async fetchJudou() {
      if (!this.items.length) return
      this.judouLoading = true
      try {
        const chars = this.items.map(it => it.pick)
        const res = await segmentJudou(chars)
        const body = res && res.data
        const segs = (body && body.success && body.data && body.data.segments) || []
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
        logWarn('句读接口不可用，节奏默认C', e && e.message)
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
          string: rh.string != null ? (XIAN[rh.string] || String(rh.string)) + '弦' : '—'
        },
        left_hand: lh
          ? { finger: lh.finger || '—', hui: lh.hui != null ? (HUI_MAP[lh.hui] || String(lh.hui)) + '徽' : '—' }
          : { finger: '散音（不按弦）', hui: '—' },
        meaning: p.meaning || '暂未收录该减字释义'
      }
    },

    onSelect(i) {
      this.selectedIdx = i
      if (i !== null) logInfo('选中减字', this.items[i].pick)
    },
    reparse(key) {
      this.cur.status = 'U'
      logWarn('切换识别候选', key)
    },

    onRhythmChange(v) {
      logInfo('调整句读', `${this.cur.pick} → ${v}`)
    },

    async confirmItem() {
      this.cur.status = 'A'
      logInfo('确认减字', this.cur.pick)
    },

    openCorrectDialog() {
      this.correctKey = this.cur.pick
      this.correctDialogVisible = true
    },

    async submitCorrect() {
      if (!this.correctKey.trim()) {
        ElMessage.warning('请输入正确的减字名称')
        return
      }
      this.submitting = true
      try {
        await submitCorrection({
          image_url: this.backendImageUrl,
          index: this.selectedIdx,
          box: { x: this.cur.x, y: this.cur.y, w: this.cur.w, h: this.cur.h },
          origin_key: this.cur.pick,
          confirmed_key: this.correctKey.trim()
        })
        ElMessage.success('反馈已提交，感谢您的修正')
        this.cur.pick = this.correctKey.trim()
        this.cur.status = 'U'
        this.correctDialogVisible = false
      } catch (e) {
        ElMessage.error('反馈提交失败，请联系开发人员')
      } finally {
        this.submitting = false
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
        return `${String(i + 1).padStart(2, '0')}. ${it.pick}${rh}`
      })
      const text = `泠弦智谱 · 打谱结果\n源文件：${this.fileName}\n数据来源：本地模型\n\n${lines.join('\n')}\n`
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

.actions { margin-top: 18px; display: flex; gap: 10px; flex-wrap: wrap; }

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
