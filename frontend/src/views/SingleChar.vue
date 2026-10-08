<!-- -*- coding: utf-8 -*- -->
<!--
  单减字识别页面（泠弦智谱 V1 · 纯前端演示）

  上传单个减字图片 → 开始识别 → 输出 Top-3 候选与
  置信度，点选候选查看指法解析（左右手/徽位/释义）。
  不依赖后端；接入后端时仅替换识别数据来源。

  作者：
      @Wujee

  创建日期：2026-10-1
  版本：1.0.0

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
                     :disabled="!imageUrl" @click="recognize">
            开始识别
          </el-button>
        </el-card>
      </el-col>

      <!-- 识别结果 -->
      <el-col :xs="24" :sm="14">
        <el-card shadow="never">
          <div v-if="!result" class="empty">上传减字并点击「开始识别」<br />查看识别结果与指法解析</div>

          <template v-else>
            <div class="blk">识别候选（Top-3）</div>
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
 * 单减字识别逻辑：纯前端假数据；埋点 logger.js，
 * 后端接入后日志统一 mlnlog。
 */
import { logInfo, logWarn } from '../logger.js'

export default {
  name: 'SingleChar',
  data() {
    return {
      imageUrl: '',
      result: null,
      pick: '',
      parse: null
    }
  },
  methods: {
    onPick(file) {
      this.imageUrl = URL.createObjectURL(file.raw)
      this.result = null
      logInfo('选择单减字图', file.name)
    },
    recognize() {
      // V1 假识别：固定 Top-3
      this.result = [
        ['da_9_gou_4', 0.82],
        ['san_tiao_7', 0.11],
        ['gou_5', 0.04]
      ]
      this.pick = this.result[0][0]
      this.parse = this.fakeParse(this.pick)
      logInfo('单减字识别完成', this.pick)
    },
    fakeParse(key) {
      return {
        right_hand: { finger: '勾', string: '三弦' },
        left_hand: { finger: '—', hui: '—' },
        meaning: '右手中指向内弹三弦，散音，无需左手按弦。'
      }
    },
    reparse(key) {
      this.parse = {
        right_hand: { finger: '—', string: '—' },
        left_hand: { finger: '—', hui: '—' },
        meaning: '【演示数据】切换候选后，接入后端返回真实释义。'
      }
      logWarn('切换单字候选', key)
    }
  }
}
</script>

<style scoped>
.blk { font-size: 12.5px; font-weight: 700; color: var(--ink-soft); margin: 6px 0 10px; }
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
