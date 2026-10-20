<!-- -*- coding: utf-8 -*- -->
<!--
  根组件（泠弦智谱 V1）

  顶部古籍书名区（行楷书名 + 朱砂双印 + 琴弦分隔纹），
  下方四枚仿木牌签条，对应 router 四条路由：
    单字释读 / 整谱打谱 / 减字库 / 智能句读。

  作者：@Wujee
  更新日期：2026-10-13
  版本：1.3.0（4 Tab + 路由视图）
-->

<template>
  <div class="app">
    <!-- 顶部书题 -->
    <header class="scroll-header">
      <div class="title-row">
        <div class="seal-side"><span>泠</span><span>弦</span></div>
        <div class="title-block">
          <h1 class="main-title">泠弦智谱</h1>
          <div class="sub-title">古琴减字谱 · 释读与打谱</div>
        </div>
        <div class="seal-side"><span>智</span><span>谱</span></div>
      </div>
      <div class="header-rule">
        <span class="rule-line"></span>
        <span class="rule-orn">❖</span>
        <span class="rule-line"></span>
      </div>
    </header>

    <!-- 仿木牌导航（4 Tab） -->
    <nav class="scroll-nav">
      <div v-for="t in tabs" :key="t.key"
           class="nav-item"
           :class="{ active: route.path === t.path }"
           @click="go(t.path)">
        {{ t.label }}
      </div>
    </nav>

    <!-- 主体（路由视图） -->
    <main class="scroll-main">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>

    <footer class="scroll-footer">
      <span>泠弦智谱 · 传承古琴减字谱释读</span>
    </footer>
  </div>
</template>

<script setup>
/*
 * 根组件：书名区 + 4 Tab 木牌导航 + 路由视图。
 * keep-alive：切 Tab 时保留各页状态（上传图、画框等不丢）。
 */
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const tabs = [
  { key: 'single',    label: '单字释读', path: '/single' },
  { key: 'sheet',     label: '整谱打谱', path: '/sheet' },
  { key: 'knowledge', label: '减 字 库', path: '/knowledge' },
  { key: 'judou',     label: '智能句读', path: '/judou' }
]

function go(path) {
  if (route.path !== path) router.push(path)
}
</script>