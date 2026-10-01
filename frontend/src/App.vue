<!-- -*- coding: utf-8 -*- -->
<!--
  根组件（泠弦智谱 V1）

  顶部国风标题栏（标题 + 朱砂印章）与功能切换：
  单减字识别 / 整谱打谱（含指法解析与节奏划分）。
  面向古琴学习者；模型权重与参数由后端本地维护。

  作者：
      @Wujee

  创建日期：2026-10-1
  版本：1.0.0

  许可证：内部使用，未经许可不得传播。
-->

<template>
  <div class="app">
    <header class="gu-header">
      <div class="gu-seal">泠弦<br />智谱</div>
      <div>
        <div class="gu-title">泠 弦 智 谱</div>
        <div class="gu-subtitle">古琴减字谱 · 智能识别与打谱</div>
      </div>
    </header>

    <div class="tabs-wrap">
      <el-tabs v-model="tab" class="gu-tabs">
        <el-tab-pane name="single">
          <template #label>
            <span class="tab-label">单减字识别</span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="sheet">
          <template #label>
            <span class="tab-label">整谱打谱 · 节奏划分</span>
          </template>
        </el-tab-pane>
      </el-tabs>
    </div>

    <main class="gu-main">
      <SingleChar v-show="tab === 'single'" />
      <WholeSheet v-show="tab === 'sheet'" />
    </main>
  </div>
</template>

<script setup>
/*
 * 根组件：布局 + 功能切换；日志见 logger.js，后端 mlnlog。
 */
import { ref } from 'vue'
import SingleChar from './views/SingleChar.vue'
import WholeSheet from './views/WholeSheet.vue'

const tab = ref('single')
</script>

<style scoped>
.gu-header {
  display: flex; align-items: center; justify-content: center;
  gap: 16px; padding: 22px 16px 6px;
}
.gu-title {
  font-family: 'KaiTi', 'STKaiti', 'SimSun', serif;
  font-size: 30px; font-weight: 700; letter-spacing: 8px; color: var(--ink);
}
.gu-subtitle {
  font-size: 12.5px; color: var(--ink-soft); letter-spacing: 3px; margin-top: 4px;
}
.gu-seal {
  width: 46px; height: 46px; border-radius: 6px;
  background: var(--zhusha); color: #f7ecd9;
  font-family: 'KaiTi','STKaiti',serif;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; line-height: 1.1; text-align: center;
  box-shadow: 0 2px 6px rgba(178,58,46,0.35);
}

.tabs-wrap { max-width: 1280px; margin: 0 auto; padding: 0 18px; }
.gu-tabs { margin-bottom: 4px; }
.tab-label {
  font-family: 'KaiTi','STKaiti',serif; font-size: 16px; letter-spacing: 3px;
}
.gu-tabs :deep(.el-tabs__item.is-active) { color: var(--zhusha); }
.gu-tabs :deep(.el-tabs__active-bar) { background-color: var(--zhusha); }
.gu-tabs :deep(.el-tabs__item:hover) { color: var(--zhusha); }
.gu-tabs :deep(.el-tabs__nav-wrap::after) { background-color: var(--line); }

.gu-main { max-width: 1280px; margin: 0 auto; padding: 8px 18px 28px; }
</style>
