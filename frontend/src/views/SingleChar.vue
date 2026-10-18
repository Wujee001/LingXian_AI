<!-- -*- coding: utf-8 -*- -->
<!--
  单减字释读页面（泠弦智谱 V1）

  上传单个减字图片 → 开始释读 → 输出 Top-3 候选与
  置信度，点选候选查看指法释义（左右手/徽位/释义）。

  数据来源判断型：优先调用后端 /api/char/predict；
  后端未启动 / 报错 / 未就绪时自动回退内置假数据，
  页面顶部以标签标明「后端识别 / 演示数据」，保证可独立演示。

  作者：@zlx @Wujee
  更新日期：2026-10-13
  版本：1.1.0
-->

<template>
  <div class="single-char">
    <el-row :gutter="16">
      <!-- 上传与预览 -->
      <el-col :xs="24" :sm="10">
        <el-card shadow="never" class="leaf">
          <div class="blk"><span class="blk-orn">○</span> 上传减字</div>
          <el-upload :auto-upload="false" show-file-list="false"
                     accept=".png,.jpg,.jpeg" :on-change="onPick"
                     class="up">
            <div class="drop">
              <img v-if="imageUrl" :src="imageUrl" class="preview" alt="单字" />
              <div v-else class="drop-tip">
                <div class="tip-char">琴</div>
                <div>点击选取减字谱图片</div>
              </div>
            </div>
          </el-upload>
          <el-button type="primary" style="width:100%;margin-top:14px"
                     :disabled="!imageUrl" :loading="recognizing" @click="recognize">
            开始释读
          </el-button>
          <div class="engine-bar">
            <span class="engine-lbl">识别引擎</span>
            <el-radio-group v-model="engine" size="small">
              <el-radio-button label="auto">自动</el-radio-button>
              <el-radio-button label="yolo">本地模型</el-radio-button>
              <el-radio-button label="qwen">多模态</el-radio-button>
            </el-radio-group>
          </div>
        </el-card>
      </el-col>

      <!-- 识别结果 -->
      <el-col :xs="24" :sm="14">
        <el-card shadow="never" class="leaf">
          <div v-if="!result" class="empty">
            上传减字图片，点击「开始释读」<br />于此处查看识别候选与指法释义
          </div>

          <template v-else>
            <div class="blk">
              <span class="blk-orn">○</span> 识别候选
              <el-tag size="small" :type="fromBackend ? 'success' : 'warning'" class="src-tag">
                {{ sourceLabel }}
              </el-tag>
              <el-button size="small" plain class="retry-btn" :loading="recognizing"
                         @click="recognize('qwen')">
                多模态重认
              </el-button>
            </div>
            <div v-if="source === 'stage2'" class="stage2-hint">
              <strong>八字段视觉识别候选（尚未人工确认）</strong>
              <p>模型逐项猜测减字明写的信息。NA＝本框未明写，不表示散音或已继承徽位。</p>
              <div class="attributes-grid">
                <div v-for="f in attributeFields" :key="f[0]" class="attribute-field">
                  <label>{{ f[1] }}</label>
                  <el-select v-model="selectedAttrs[f[0]]" size="small" filterable
                             allow-create default-first-option @change="onAttributeChanged">
                    <el-option v-for="op in (attributesTop3[f[0]] || [])" :key="op.value"
                               :value="op.value" :label="op.value + '（' + (op.score * 100).toFixed(0) + '%）'" />
                  </el-select>
                </div>
              </div>
              <el-button type="success" size="small" style="width:100%;margin-top:12px"
                         :disabled="confirmed" @click="confirmAttributes">
                {{ confirmed ? '已人工确认并保存' : '人工核对后确认并保存' }}
              </el-button>
            </div>
            <el-radio-group v-if="source !== 'stage2' && result.length" v-model="pick" @change="reparse">
              <el-radio v-for="c in result" :key="c[0]" :label="c[0]"
                        border size="small" class="cand">
                {{ c[0] }} <span class="conf">{{ (c[1] * 100).toFixed(0) }}%</span>
              </el-radio>
            </el-radio-group>

            <div class="blk"><span class="blk-orn">○</span> {{ source === 'stage2' ? '指法属性候选解释' : '指法释义' }}</div>
            <div class="parse" v-if="parse">
              <div class="parse-row">
                <span class="k">右 手</span>{{ parse.right_hand.finger }} · {{ parse.right_hand.string }}
              </div>
              <div class="parse-row">
                <span class="k">左 手</span>{{ parse.left_hand.finger }} · {{ parse.left_hand.hui }}
              </div>
              <div class="meaning">{{ parse.meaning }}</div>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
/*
 * 单减字识别逻辑：后端优先、假数据兜底；
 * 埋点 logger.js，后端业务日志统一 mlnlog。
 */
import { ElMessage } from 'element-plus'
import { predictSingle, parseAttributes, correctSheet } from '../api/index.js'
import { logInfo, logWarn } from '../logger.js'

// 弦序 / 徽位数字转中文
const XIAN = ['', '一', '二', '三', '四', '五', '六', '七']
const HUI_MAP = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十', 11: '十一', 12: '十二', 13: '十三' }
const ATTR_FIELDS = [['rh','右手动作'],['string','弦序'],['lh','左手按指'],
  ['hui_base','徽位'],['hui_frac','徽分'],['mod','技法'],['tone','音类'],['strings','复合弦序']]

export default {
  name: 'SingleChar',
  computed: {
    attributeFields() { return ATTR_FIELDS },
    sourceLabel() {
      if (!this.fromBackend) return '等待后端结果'
      if (this.source === 'stage2') return 'ResNet18 八字段候选 · 待人工核验'
      if (this.source === 'qwen') return '多模态候选 · 待人工核验'
      return '后端识别候选'
    }
  },
  data() {
    return {
      rawFile: null,
      imageUrl: '',
      result: null,
      pick: '',
      parse: null,
      fromBackend: false,
      source: '',
      engine: 'auto',
      recognizing: false,
      attributesTop3: {},
      selectedAttrs: {},
      confirmed: false
    }
  },
  methods: {
    onPick(file) {
      this.rawFile = file.raw
      this.imageUrl = URL.createObjectURL(file.raw)
      this.result = null
      this.attributesTop3 = {}
      this.selectedAttrs = {}
      this.confirmed = false
      this.fromBackend = false
      this.source = ''
      logInfo('选择单减字图', file.name)
    },
    async recognize(forceEngine) {
      if (!this.rawFile) return
      const engine = forceEngine || this.engine
      this.recognizing = true
      try {
        // 优先调用后端真实接口（可手动指定引擎）
        const res = await predictSingle(this.rawFile, engine)
        const body = res && res.data
        if (!body || !body.success || !body.data || !Array.isArray(body.data.candidates)) {
          throw new Error('后端返回结构异常')
        }
        this.result = body.data.candidates.map(c => [c.class_key, c.confidence])
        this.pick = body.data.top_key || (this.result.length ? this.result[0][0] : '')
        this.attributesTop3 = body.data.attributes_top3 || {}
        this.selectedAttrs = { ...(body.data.attributes_selected || {}) }
        this.confirmed = false
        this.parse = this.fmtParse(body.data.parse_result, this.pick)
        this.fromBackend = true
        this.source = body.data.source || 'yolo'
        logInfo('单减字识别完成（后端）', this.pick)
      } catch (e) {
        // 不再静默用演示数据代替真实模型输出。
        logWarn('后端单字识别不可用', e && e.message)
        const detail = e?.response?.data?.detail || e?.message || '请确认已部署 stage2_best.pth'
        ElMessage.error(`识别未完成：${detail}`)
        this.result = null
        this.parse = null
        this.fromBackend = false
        this.source = 'unavailable' 
      } finally {
        this.recognizing = false
      }
    },
    // 把后端 parse_result 归一化为模板展示结构（兼容左右手为 null、string 为数字）
    fmtParse(p, key) {
      if (!p) return { right_hand:{finger:'—',string:'—'}, left_hand:{finger:'—',hui:'—'}, meaning:'暂无有效候选，请检查模型' }
      const rh = p.right_hand || {}
      const lh = p.left_hand
      return {
        right_hand: {
          finger: rh.finger || '—',
          string: rh.string == null ? '—' : (/^[1-7]$/.test(String(rh.string)) ? (XIAN[rh.string] || String(rh.string)) + '弦' : String(rh.string))
        },
        left_hand: lh
          ? { finger: lh.finger || '—', hui: lh.hui == null ? '—' : (/^\d+$/.test(String(lh.hui)) ? (HUI_MAP[lh.hui] || String(lh.hui)) + '徽' : String(lh.hui)) }
          : { finger: '未明写', hui: '—' },
        meaning: p.meaning || '暂未收录该减字释义'
      }
    },
    async onAttributeChanged() {
      this.confirmed = false
      try {
        const res = await parseAttributes(this.selectedAttrs)
        this.parse = this.fmtParse(res.data.data, '')
      } catch (e) {
        logWarn('属性展示刷新失败', e?.message)
      }
    },
    async confirmAttributes() {
      try {
        const res = await correctSheet({
          image_url: null, index: 0, box: null,
          source: 'stage2_single', origin_key: null, confirmed_key: null,
          attributes_selected: this.selectedAttrs,
          attributes_top3: this.attributesTop3,
          note: '用户在单减字页面核对并确认八字段'
        })
        if (!res?.data?.success) throw new Error('保存失败')
        this.confirmed = true
        ElMessage.success('已保存人工核对的属性；不等于自动完成完整谱理解析')
      } catch (e) {
        ElMessage.error('保存人工确认失败，请检查后端')
      }
    },
    reparse(key) {
      // 单字接口仅返回首选的解析，切换候选暂无对应释义，提示以选中项重新识别
      this.parse = {
        right_hand: { finger: '—', string: '—' },
        left_hand: { finger: '—', hui: '—' },
        meaning: '切换候选后，请以该候选重新上传识别以获取真实释义。'
      }
      logWarn('切换单字候选', key)
    }
  }
}
</script>

<style scoped>
.single-char { padding: 4px 0; }

/* 卡片：仿书页 */
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
.src-tag { margin-left: 10px; letter-spacing: 0.05em; }
.retry-btn { float: right; letter-spacing: 0.05em; }

.engine-bar {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
}
.engine-lbl {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 12.5px;
  color: var(--ink-faint);
  letter-spacing: 0.15em;
}

/* 上传区 */
.up { width: 100%; }
.drop {
  width: 100%;
  min-height: 236px;
  border: 1px dashed var(--line-deep);
  border-radius: 2px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: rgba(246, 238, 215, 0.4);
  background-image:
    repeating-linear-gradient(45deg, rgba(139, 90, 60, 0.02) 0 2px, transparent 2px 6px);
  overflow: hidden;
  transition: background-color 0.25s ease;
}
.drop:hover { background-color: rgba(240, 229, 200, 0.55); }
.drop-tip {
  color: var(--ink-faint);
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 13px;
  text-align: center;
  letter-spacing: 0.15em;
}
.tip-char {
  font-family: 'STXingkai', '华文行楷', 'STKaiti', 'KaiTi', serif;
  font-size: 52px;
  color: var(--line-deep);
  opacity: 0.55;
  line-height: 1;
  margin-bottom: 10px;
}
.preview { max-width: 100%; max-height: 300px; }

.empty {
  color: var(--ink-faint);
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 13px;
  text-align: center;
  line-height: 2.2;
  padding: 70px 0;
  letter-spacing: 0.12em;
}

.cand {
  display: flex;
  margin: 0 8px 10px 0;
  font-family: 'SimSun', 'Songti SC', serif;
}
.conf {
  color: var(--ink-faint);
  font-size: 11px;
  margin-left: 4px;
}

.stage2-hint { padding:12px;background:rgba(246,238,215,.6);border:1px solid var(--line-soft);margin:10px 0; }
.stage2-hint p {font-size:12px;line-height:1.6;color:var(--ink-faint)}
.attributes-grid {display:grid;grid-template-columns:1fr 1fr;gap:8px}
.attribute-field label {display:block;font-size:12px;margin-bottom:4px;color:var(--ink-faint)}
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
.parse-row { color: var(--ink); }
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
</style>