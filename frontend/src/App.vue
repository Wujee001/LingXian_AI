<!-- -*- coding: utf-8 -*- -->
<!--
  根组件（泠弦智谱 V2 · 古籍抄本）

  顶部题签（书名签条 + 琴弦纹），木牌式导航，
  主体按"打开的古籍册页"布局。整体弱化 AI 科技感，
  向传统琴馆抄本靠拢。

  作者：
      @Wujee

  创建日期：2026-10-1
  版本：2.0.0

  许可证：内部使用，未经许可不得传播。
-->

<template>
  <div class="app">
    <!-- 顶部题签区 -->
    <header class="gu-header">
      <div class="title-plaque">
        <div class="plaque-inner">
          <h1 class="gu-title">泠 弦 智 谱</h1>
          <div class="gu-subtitle">古琴减字谱 · 查询与打谱</div>
        </div>
      </div>

      <!-- 古琴轮廓 + 琴弦 -->
      <div class="guqin-svg" aria-hidden="true">
        <svg viewBox="0 0 220 44" preserveAspectRatio="xMidYMid meet">
          <path
            d="M10,22 C10,15 18,11 32,11 L188,11 C202,11 210,15 210,22
               C210,29 202,33 188,33 L32,33 C18,33 10,29 10,22 Z"
            fill="none" stroke="currentColor" stroke-width="1.1" opacity="0.45"/>
          <line x1="28" y1="17" x2="192" y2="17" stroke="currentColor" stroke-width="0.55" opacity="0.35"/>
          <line x1="28" y1="22" x2="192" y2="22" stroke="currentColor" stroke-width="0.55" opacity="0.35"/>
          <line x1="28" y1="27" x2="192" y2="27" stroke="currentColor" stroke-width="0.55" opacity="0.35"/>
          <rect x="14" y="13" width="3" height="18" fill="currentColor" opacity="0.3"/>
        </svg>
      </div>
    </header>

    <!-- 木牌导航 -->
    <nav class="gu-nav">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="nav-plaque"
        :class="{ active: tab === t.key }"
        @click="tab = t.key"
      >
        <span class="plaque-text">{{ t.label }}</span>
      </button>
    </nav>

    <!-- 主体：打开的古籍册页 -->
    <main class="gu-main">
      <SingleChar v-show="tab === 'single'" />
      <WholeSheet v-show="tab === 'sheet'" />
      <KbSearch   v-show="tab === 'kb'" />
    </main>

    <!-- 页脚 -->
    <footer class="gu-footer">
      <span class="foot-mark">❖</span>
      <span>泠弦智谱 · 仿古抄本 · 内部使用</span>
      <span class="foot-mark">❖</span>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SingleChar from './views/SingleChar.vue'
import WholeSheet from './views/WholeSheet.vue'
import KbSearch from './views/KbSearch.vue'

const tabs = [
  { key: 'single', label: '单减字识别' },
  { key: 'sheet',  label: '整谱打谱' },
  { key: 'kb',     label: '减字检索' }
]

const tab = ref('single')
</script>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ===== 题签 ===== */
.gu-header {
  padding: 40px 16px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.title-plaque {
  display: inline-block;
  padding: 20px 56px;
  background: var(--paper-warm);
  border: 2px solid var(--zheshi-deep);
  position: relative;
  /* 双线边框（内白线 + 外赭石线） */
  box-shadow:
    inset 0 0 0 4px var(--paper-warm),
    inset 0 0 0 5px var(--zheshi-deep),
    0 2px 8px rgba(80, 60, 30, 0.12);
}

.plaque-inner {
  padding: 0 4px;
  text-align: center;
}

.gu-title {
  margin: 0;
  font-family: var(--font-brush);
  font-size: 34px;
  font-weight: 400;
  letter-spacing: 14px;
  color: var(--ink);
  text-indent: 14px; /* 抵消尾字后空隙 */
  line-height: 1.2;
}

.gu-subtitle {
  margin-top: 8px;
  font-family: var(--font-brush);
  font-size: 13px;
  color: var(--ink-mute);
  letter-spacing: 6px;
  text-indent: 6px;
}

.guqin-svg {
  width: 220px;
  height: 44px;
  color: var(--zheshi);
  opacity: 0.85;
}
.guqin-svg svg { width: 100%; height: 100%; display: block; }

/* ===== 木牌导航 ===== */
.gu-nav {
  width: 100%;
  max-width: 1240px;
  margin: 4px auto 0;
  padding: 0 24px;
  display: flex;
  gap: 10px;
  justify-content: center;
  border-bottom: 1px solid var(--line);
  position: relative;
}

/* 导航底部中央回纹分隔 */
.gu-nav::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 140px;
  height: 3px;
  background:
    repeating-linear-gradient(
      90deg,
      var(--zheshi) 0px, var(--zheshi) 6px,
      transparent 6px, transparent 9px
    );
  opacity: 0.55;
}

.nav-plaque {
  font-family: var(--font-brush);
  font-size: 16px;
  letter-spacing: 4px;
  color: var(--ink-soft);
  background: transparent;
  border: 1px solid transparent;
  border-bottom: none;
  padding: 12px 30px 13px;
  cursor: pointer;
  position: relative;
  top: 1px;
  transition: color .25s ease, background-color .25s ease, border-color .25s ease;
}
.nav-plaque:hover {
  color: var(--zheshi-deep);
  background: rgba(139, 90, 43, 0.06);
}
.nav-plaque.active {
  color: var(--ink);
  background: var(--paper-light);
  border-color: var(--line);
  border-bottom: 1px solid var(--paper-light);
}
.nav-plaque.active::before {
  content: '';
  position: absolute;
  left: 12px; right: 12px;
  bottom: 6px;
  height: 1px;
  background: var(--zhusha);
  opacity: 0.5;
}

.plaque-text { position: relative; }

/* ===== 主体 ===== */
.gu-main {
  flex: 1;
  width: 100%;
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px 24px 40px;
}

/* ===== 页脚 ===== */
.gu-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 20px 0 26px;
  font-family: var(--font-brush);
  font-size: 12px;
  color: var(--ink-mute);
  letter-spacing: 4px;
  border-top: 1px solid var(--line-soft);
  max-width: 1240px;
  width: calc(100% - 48px);
  margin: 0 auto;
}
.foot-mark { color: var(--line-strong); font-size: 10px; }

@media (max-width: 720px) {
  .gu-title { font-size: 24px; letter-spacing: 8px; text-indent: 8px; }
  .gu-subtitle { font-size: 11px; letter-spacing: 3px; text-indent: 3px; }
  .title-plaque { padding: 14px 28px; }
  .gu-nav { gap: 4px; padding: 0 12px; }
  .nav-plaque { padding: 10px 14px 11px; font-size: 14px; letter-spacing: 2px; }
  .gu-main { padding: 16px 12px 28px; }
}
</style>