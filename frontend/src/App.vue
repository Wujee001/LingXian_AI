<!-- -*- coding: utf-8 -*- -->
<!--
  根组件（泠弦智谱）

  顶部古籍书名区（行楷书名 + 朱砂双印 + 琴弦分隔纹），
  右侧用户栏（登录 / 用户名下拉：我的历史、用户管理、退出），
  下方仿木牌签条，对应 router 四条路由。

  作者：@Wujee
  维护：@zlxaaa
  更新日期：2026-10-18
  版本：1.5.0（登录 + 用户管理入口 + 我的历史入口）
-->

<template>
  <div class="app">
    <!-- 顶部书题 -->
    <header class="scroll-header">
      <!-- 用户栏 -->
      <div class="user-bar">
        <template v-if="auth.user">
          <el-dropdown trigger="click" @command="onCommand">
            <span class="user-trigger">
              {{ auth.user.username }}<span class="caret">▾</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="history">我的历史</el-dropdown-item>
                <el-dropdown-item command="notes">我的笔记</el-dropdown-item>
                <el-dropdown-item
                  v-if="auth.user.role === 'admin'"
                  command="admin"
                >用户管理</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <el-button v-else size="small" type="primary" plain @click="toLogin">登录</el-button>
      </div>

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
 * 根组件：书名区 + 用户栏 + 4 Tab 木牌导航 + 路由视图。
 * keep-alive：切 Tab 时保留各页状态（上传图、画框等不丢）。
 */
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { auth, clearAuth } from './store/auth.js'
import { logout } from './api/index.js'
import { logInfo } from './logger.js'

const route = useRoute()
const router = useRouter()

const tabs = [
  { key: 'single',    label: '单字释读', path: '/single' },
  { key: 'sheet',     label: '整谱打谱', path: '/sheet' },
  { key: 'knowledge', label: '减 字 库', path: '/knowledge' },
  { key: 'judou',     label: '智能句读', path: '/judou' },
  { key: 'square',    label: '广 场',   path: '/square' },
]

function go(path) {
  if (route.path !== path) router.push(path)
}

function toLogin() {
  router.push('/login')
}

async function doLogout() {
  try {
    await logout()
  } catch (_) {
    // token 已失效也照样清本地
  }
  clearAuth()
  logInfo('已退出登录')
  ElMessage.success('已退出')
  router.replace('/login')
}

function onCommand(cmd) {
  if (cmd === 'admin') router.push('/admin/users')
  else if (cmd === 'history') router.push('/history')
  else if (cmd === 'notes') router.push('/notes')
  else if (cmd === 'logout') doLogout()
}
</script>