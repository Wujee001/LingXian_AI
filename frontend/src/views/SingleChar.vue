<!-- -*- coding: utf-8 -*- -->
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
              <el-tag size="small" type="success" class="src-tag">本地模型识别</el-tag>
              <el-button size="small" plain type="warning" class="retry-btn"
                         @click="openCorrectDialog">
                识别有误，手动修正
              </el-button>
            </div>
            <el-radio-group v-model="pick">
              <el-radio v-for="c in result" :key="c[0]" :label="c[0]"
                        border size="small" class="cand">
                {{ parse.display_name }} <span class="conf">{{ (c[1] * 100).toFixed(0) }}%</span>
              </el-radio>
            </el-radio-group>

            <div class="blk"><span class="blk-orn">○</span> 指法释义</div>
            <div class="parse">
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

    <!-- 手动修正弹窗 -->
    <el-dialog v-model="correctDialogVisible" title="手动修正识别结果" width="420px">
      <el-form label-width="90px">
        <el-form-item label="原识别结果">
          <el-input v-model="pick" disabled />
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
import { predictSingle, submitCorrection } from '../api/index.js'
import { logInfo, logWarn } from '../logger.js'

const XIAN = ['', '一', '二', '三', '四', '五', '六', '七']
const HUI_MAP = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十', 11: '十一', 12: '十二', 13: '十三' }

export default {
  name: 'SingleChar',
  data() {
    return {
      rawFile: null,
      imageUrl: '',
      result: null,
      pick: '',
      parse: null,
      recognizing: false,
      correctDialogVisible: false,
      correctKey: '',
      submitting: false,
      currentImageUrl: ''
    }
  },
  methods: {
    onPick(file) {
      this.rawFile = file.raw
      this.imageUrl = URL.createObjectURL(file.raw)
      this.result = null
      logInfo('选择单减字图', file.name)
    },
    async recognize() {
      if (!this.rawFile) return
      this.recognizing = true
      try {
        const res = await predictSingle(this.rawFile)
        const body = res && res.data
        if (!body || !body.success || !body.data || !Array.isArray(body.data.candidates)) {
          throw new Error('后端返回结构异常')
        }
        this.result = body.data.candidates
        this.currentImageUrl = body.data.image_url || ''
        this.pick = body.data.top_key || this.result[0][0]
        this.parse = this.fmtParse(body.data.parse_result)
        logInfo('单减字本地识别完成', this.pick)
      } catch (e) {
        logWarn('单字识别失败', e && e.message)
        ElMessage.error('识别服务异常，请联系开发人员检查')
      } finally {
        this.recognizing = false
      }
    },
    fmtParse(p) {
      if (!p) {
        return {
          right_hand: { finger: '—', string: '—' },
          left_hand: { finger: '—', hui: '—' },
          meaning: '暂未收录该减字释义'
        }
      }
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
    openCorrectDialog() {
      this.correctKey = this.pick
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
          image_url: this.currentImageUrl,
          index: 0,
          origin_key: this.pick,
          confirmed_key: this.correctKey.trim()
        })
        ElMessage.success('反馈已提交，感谢您的修正')
        this.correctDialogVisible = false
      } catch (e) {
        ElMessage.error('反馈提交失败，请联系开发人员')
      } finally {
        this.submitting = false
      }
    }
  }
}
</script>

<style scoped>
.single-char { padding: 4px 0; }
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
