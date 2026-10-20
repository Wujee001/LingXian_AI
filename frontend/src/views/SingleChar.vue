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
            <el-radio-group v-model="pick" @change="updateParse">
              <el-radio v-for="c in result" :key="c[0]" :label="c[0]"
                        border size="small" class="cand">
                {{ getParse(c[0]).display_name }} <span class="conf">{{ (c[1] * 100).toFixed(0) }}%</span>
              </el-radio>
            </el-radio-group>

            <div class="blk"><span class="blk-orn">○</span> 指法释义</div>
            <div class="parse">
              <div class="parse-row">
                <span class="k">右 手</span>{{ parse.right_hand_text }}
              </div>
              <div class="parse-row">
                <span class="k">左 手</span>{{ parse.left_hand_text }}
              </div>
              <div class="meaning">{{ parse.desc }}</div>
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
import { logInfo } from '../logger.js'

export default {
  name: 'SingleChar',
  data() {
    return {
      rawFile: null,
      imageUrl: '',
      result: null,
      pick: '',
      parse: {
        display_name: '—',
        right_hand_text: '—',
        left_hand_text: '—',
        desc: '暂未收录'
      },
      recognizing: false,
      correctDialogVisible: false,
      correctKey: '',
      submitting: false,
      currentImageUrl: '',
      parseCache: {}
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
        this.parseCache[this.pick] = body.data.parse_result
        this.parse = body.data.parse_result
        logInfo('单减字本地识别完成', this.pick)
      } catch (e) {
        ElMessage.error('识别服务异常，请联系开发人员检查')
      } finally {
        this.recognizing = false
      }
    },
    getParse(key) {
      return this.parseCache[key] || {display_name: key}
    },
    updateParse(key) {
      this.parse = this.parseCache[key] || this.parse
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
  overflow: hidden;
}
.tip-char {
  font-family: '华文行楷', 'STXingkai', '行楷', 'STKaiti', '楷体', KaiTi, serif;
  font-size: 58px;
  color: var(--line-deep);
  opacity: 0.6;
  line-height: 1;
  margin-bottom: 10px;
  font-weight: normal;
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
}
</style>
