<!-- -*- coding: utf-8 -*- -->
<!--
  单减字识别页面（泠弦智谱 V1）

  上传单个减字图片 → 开始识别 → 输出 Top-3 候选与
  置信度，点选候选查看指法解析（左右手/徽位/释义）。

  数据来源判断型：优先调用后端 /api/char/predict；
  后端未启动 / 报错 / 未就绪时自动回退内置假数据，
  页面顶部以标签标明「后端识别 / 演示数据」，保证可独立演示。

  作者：
      @Wujee

  更新日期：2026-10-12
  版本：1.1.0

  许可证：内部使用，未经许可不得传播。
-->

<template>
  <div class="single-char">
    <el-row :gutter="14">
      <!-- 上传与预览 -->
      <el-col :xs="24" :sm="10">
        <el-card shadow="never">
          <div class="blk">单个减字图片</div>
          <el-upload :auto-upload="false" show-file-list="false"
                     accept=".png,.jpg,.jpeg" :on-change="onPick"
                     class="up">
            <div class="drop">
              <img v-if="imageUrl" :src="imageUrl" class="preview" alt="单字" />
              <div v-else class="drop-tip">点击选择减字图</div>
            </div>
          </el-upload>
          <el-button type="primary" style="width:100%;margin-top:12px"
                     :disabled="!imageUrl" :loading="recognizing" @click="recognize">
            开始识别
          </el-button>
        </el-card>
      </el-col>

      <!-- 识别结果 -->
      <el-col :xs="24" :sm="14">
        <el-card shadow="never">
          <div v-if="!result" class="empty">上传减字并点击「开始识别」<br />查看识别结果与指法解析</div>

          <template v-else>
            <div class="blk">
              识别候选（Top-3）
              <el-tag size="small" :type="fromBackend ? 'success' : 'warning'" class="src-tag">
                {{ fromBackend ? '后端识别' : '演示数据' }}
              </el-tag>
            </div>
            <el-radio-group v-model="pick" @change="reparse">
              <el-radio v-for="c in result" :key="c[0]" :label="c[0]"
                        border size="small" class="cand">
                {{ c[0] }} <span class="conf">{{ (c[1] * 100).toFixed(0) }}%</span>
              </el-radio>
            </el-radio-group>

            <div class="blk">指法解析</div>
            <div class="parse">
              <div>右手：{{ parse.right_hand.finger }} · {{ parse.right_hand.string }}</div>
              <div>左手：{{ parse.left_hand.finger }} · {{ parse.left_hand.hui }}</div>
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
import { predictSingle } from '../api/index.js'
import { logInfo, logWarn } from '../logger.js'

// 弦序 / 徽位数字转中文
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
      fromBackend: false,
      recognizing: false
    }
  },
  methods: {
    onPick(file) {
      this.rawFile = file.raw
      this.imageUrl = URL.createObjectURL(file.raw)
      this.result = null
      this.fromBackend = false
      logInfo('选择单减字图', file.name)
    },
    async recognize() {
      if (!this.rawFile) return
      this.recognizing = true
      try {
        // 优先调用后端真实接口
        const res = await predictSingle(this.rawFile)
        const body = res && res.data
        if (!body || !body.success || !body.data || !Array.isArray(body.data.candidates)) {
          throw new Error('后端返回结构异常')
        }
        this.result = body.data.candidates.map(c => [c.class_key, c.confidence])
        this.pick = body.data.top_key || this.result[0][0]
        this.parse = this.fmtParse(body.data.parse_result, this.pick)
        this.fromBackend = true
        logInfo('单减字识别完成（后端）', this.pick)
      } catch (e) {
        // 后端不可用：回退内置假数据
        logWarn('后端单字识别不可用，回退演示数据', e && e.message)
        ElMessage.warning('后端未连接或识别异常，当前使用演示数据')
        this.result = [
          ['da_9_gou_4', 0.82],
          ['san_tiao_7', 0.11],
          ['gou_5', 0.04]
        ]
        this.pick = this.result[0][0]
        this.parse = this.fakeParse(this.pick)
        this.fromBackend = false
        logInfo('单减字识别完成（演示）', this.pick)
      } finally {
        this.recognizing = false
      }
    },
    // 把后端 parse_result 归一化为模板展示结构（兼容左右手为 null、string 为数字）
    fmtParse(p, key) {
      if (!p) return this.fakeParse(key)
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
    fakeParse(key) {
      return {
        right_hand: { finger: '勾', string: '三弦' },
        left_hand: { finger: '散音（不按弦）', hui: '—' },
        meaning: '【演示数据】右手中指向内弹三弦，散音，无需左手按弦。'
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
.blk { font-size: 12.5px; font-weight: 700; color: var(--ink-soft); margin: 6px 0 10px; }
.src-tag { margin-left: 8px; }
.up { width: 100%; }
.drop {
  width: 100%; min-height: 220px;
  border: 1.5px dashed var(--line); border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(184,134,11,0.05); overflow: hidden;
}
.drop-tip { color: var(--ink-soft); font-size: 13px; }
.preview { max-width: 100%; max-height: 300px; }
.empty { color: var(--ink-soft); font-size: 13px; text-align: center; line-height: 2; padding: 60px 0; }
.cand { display: flex; margin: 0 8px 8px 0; }
.conf { color: var(--ink-soft); font-size: 11px; }
.parse { font-size: 12.5px; line-height: 1.9; background: rgba(184,134,11,0.07); border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; }
.parse .meaning { color: var(--zhusha); margin-top: 4px; }
</style>
