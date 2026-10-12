<!-- -*- coding: utf-8 -*- -->
<!--
  单减字识别页（泠弦智谱 V2）

  册页布局：左页贴减字图，右页示候选与指法释义。
  接入 api/index.js；URL 带 ?mock=1 时降级本地假数据。

  作者：
      @Wujee

  创建日期：2026-10-1
  版本：2.0.0

  许可证：内部使用，未经许可不得传播。
-->

<template>
  <section class="book">
    <!-- 左页 -->
    <div class="page page-left">
      <div class="page-head">
        <span class="page-head-num">上</span>
        <span class="page-head-title">减字原图</span>
      </div>

      <el-upload
        :auto-upload="false"
        show-file-list="false"
        accept=".png,.jpg,.jpeg"
        :on-change="onPick"
        class="up"
      >
        <div class="drop" :class="{ 'has-img': !!imageUrl }">
          <img v-if="imageUrl" :src="imageUrl" class="preview" alt="单字" />
          <div v-else class="drop-tip">
            <div class="drop-frame">
              <span>减</span>
            </div>
            <div class="drop-text">此处贴减字图</div>
            <div class="drop-hint">支持 PNG / JPG</div>
          </div>
        </div>
      </el-upload>

      <div class="page-actions">
        <el-button
          type="primary"
          class="btn-wide"
          :disabled="!imageUrl"
          :loading="loading"
          @click="recognize"
        >
          {{ loading ? '识别中…' : '开 始 识 别' }}
        </el-button>
      </div>
    </div>

    <!-- 中缝 -->
    <div class="spine" aria-hidden="true"></div>

    <!-- 右页 -->
    <div class="page page-right">
      <div class="page-head">
        <span class="page-head-num">下</span>
        <span class="page-head-title">识别与释义</span>
      </div>

      <div v-if="!result" class="empty">
        <div class="empty-mark">琴</div>
        <div class="empty-main">贴入减字图，点「开始识别」</div>
        <div class="empty-hint">左页贴图 · 右页出候选与指法</div>
      </div>

      <template v-else>
        <div class="blk">候 选 · Top 3</div>
        <div class="cands">
          <el-radio-group v-model="pick" @change="reparse">
            <el-radio
              v-for="c in result"
              :key="c[0]"
              :value="c[0]"
              border
            >
              <span class="cand-key">{{ c[0] }}</span>
              <span class="conf">{{ (c[1] * 100).toFixed(0) }}%</span>
            </el-radio>
          </el-radio-group>
        </div>

        <div class="blk">指 法 释 义</div>
        <div class="parse">
          <div class="parse-row">
            <span class="parse-label">右手</span>
            <span class="parse-value">
              {{ parse.right_hand.finger }} · {{ parse.right_hand.string }}
            </span>
          </div>
          <div class="parse-row">
            <span class="parse-label">左手</span>
            <span class="parse-value">
              {{ parse.left_hand.finger }} · {{ parse.left_hand.hui }}
            </span>
          </div>
          <div class="deco-divider">
            <span class="deco-mark">· 释义 ·</span>
          </div>
          <div class="meaning">{{ parse.meaning }}</div>
        </div>
      </template>
    </div>
  </section>
</template>

<script>
import { predictSingle } from '../api/index.js'
import { logInfo, logError } from '../logger.js'

const USE_MOCK =
  typeof window !== 'undefined' &&
  new URLSearchParams(window.location.search).get('mock') === '1'

export default {
  name: 'SingleChar',
  data() {
    return {
      imageUrl: '',
      fileRaw: null,
      result: null,
      pick: '',
      parse: null,
      loading: false
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
      this.result = null
      this.parse = null
      logInfo('选择单减字图', file.name)
    },
    async recognize() {
      if (!this.fileRaw) return
      this.loading = true
      try {
        const data = USE_MOCK
          ? this.mockResult()
          : await predictSingle(this.fileRaw)
        this.applyResult(data)
        logInfo('单减字识别完成', this.pick)
      } catch (e) {
        logError('单减字识别失败', e?.message)
      } finally {
        this.loading = false
      }
    },
    applyResult(data) {
      if (!data) return
      this.result = data.candidates || []
      if (this.result.length) {
        this.pick = this.result[0][0]
        this.parse = data.parse_result || this.fakeParse()
      }
    },
    mockResult() {
      return {
        candidates: [
          ['da_9_gou_4', 0.82],
          ['san_tiao_7', 0.11],
          ['gou_5', 0.04]
        ],
        parse_result: this.fakeParse()
      }
    },
    fakeParse() {
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
      logInfo('切换单字候选', key)
    }
  }
}
</script>

<style scoped>
/* ===== 册页容器 ===== */
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
/* 边缘做旧 */
.book::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 0% 0%,     rgba(120, 90, 50, 0.10), transparent 6%),
    radial-gradient(circle at 100% 0%,   rgba(120, 90, 50, 0.08), transparent 6%),
    radial-gradient(circle at 0% 100%,   rgba(120, 90, 50, 0.10), transparent 6%),
    radial-gradient(circle at 100% 100%, rgba(120, 90, 50, 0.08), transparent 6%);
  z-index: 3;
}

.page {
  flex: 1 1 50%;
  min-width: 0;
  padding: 28px 34px 34px;
  position: relative;
}

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

/* ===== 页头 ===== */
.page-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding-bottom: 12px;
  margin-bottom: 20px;
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

/* ===== 左页：上传 ===== */
.up { width: 100%; }
.drop {
  width: 100%;
  min-height: 300px;
  border: 1px dashed var(--line-strong);
  border-radius: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--paper-warm);
  overflow: hidden;
  transition: border-color .25s, background-color .25s;
  position: relative;
}
.drop:hover { border-color: var(--zheshi); background: #e6d9bb; }
.drop.has-img {
  border-style: solid;
  border-color: var(--line);
  background: #fbf6e8;
  padding: 14px;
}

.drop-tip { text-align: center; color: var(--ink-mute); }
.drop-frame {
  width: 72px; height: 72px;
  margin: 0 auto 14px;
  border: 2px solid var(--zheshi);
  background: transparent;
  color: var(--zheshi);
  font-family: var(--font-brush);
  font-size: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  border-radius: 2px;
}
/* 印章内框 */
.drop-frame::before {
  content: '';
  position: absolute;
  inset: 4px;
  border: 1px solid var(--zheshi);
  opacity: 0.5;
  border-radius: 1px;
}
.drop-text {
  font-family: var(--font-brush);
  font-size: 15px;
  letter-spacing: 4px;
  color: var(--ink-soft);
}
.drop-hint {
  font-size: 11.5px;
  margin-top: 6px;
  color: var(--ink-faint);
  letter-spacing: 2px;
}
.preview {
  max-width: 100%;
  max-height: 340px;
  display: block;
  margin: 0 auto;
}

.page-actions { margin-top: 22px; }
.btn-wide {
  width: 100%;
  padding: 11px 18px;
  font-size: 15px;
}

/* ===== 右页：结果 ===== */
.blk {
  font-family: var(--font-brush);
  font-size: 13px;
  color: var(--ink-mute);
  letter-spacing: 4px;
  margin: 4px 0 12px;
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

.empty {
  color: var(--ink-mute);
  text-align: center;
  padding: 80px 0 60px;
  line-height: 1.9;
}
.empty-mark {
  width: 74px; height: 74px;
  margin: 0 auto 16px;
  border: 1px solid var(--line-strong);
  border-radius: 2px;
  color: var(--zheshi);
  font-family: var(--font-brush);
  font-size: 40px;
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
  opacity: 0.6;
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
  margin-top: 6px;
  letter-spacing: 2px;
}

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
.parse-value { color: var(--ink); }
.meaning {
  color: var(--ink-soft);
  font-size: 13.5px;
  line-height: 1.9;
}

@media (max-width: 860px) {
  .book { flex-direction: column; }
  .spine { display: none; }
  .page { padding: 22px 18px 26px; }
  .page-right { border-top: 1px solid var(--line-soft); }
}
</style>