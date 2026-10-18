<!-- -*- coding: utf-8 -*- -->
<!--
  登录页

  账号由管理员分配，不开放注册。

  作者：@zlxaaa
  创建日期：2026-10-18
  版本：1.0.0
-->

<template>
  <div class="login-wrap">
    <el-card shadow="never" class="leaf login-card">
      <div class="blk"><span class="blk-orn">○</span> 登 录</div>

      <el-input
        v-model="username"
        placeholder="用户名"
        clearable
        @keyup.enter="submit"
      />
      <el-input
        v-model="password"
        type="password"
        placeholder="密码"
        show-password
        style="margin-top:12px"
        @keyup.enter="submit"
      />

      <el-button
        type="primary"
        :loading="loading"
        style="width:100%;margin-top:18px"
        @click="submit"
      >
        登 录
      </el-button>

      <div class="hint">账号由管理员分配，不开放注册</div>
    </el-card>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import { login } from '../api/index.js'
import { setAuth } from '../store/auth.js'
import { logInfo, logWarn } from '../logger.js'

export default {
  name: 'Login',
  data() {
    return { username: '', password: '', loading: false }
  },
  methods: {
    async submit() {
      const u = (this.username || '').trim()
      const p = this.password || ''
      if (!u || !p) {
        ElMessage.warning('请输入用户名和密码')
        return
      }
      this.loading = true
      try {
        const res = await login(u, p)
        const body = res && res.data
        if (!body || !body.success || !body.data) {
          throw new Error('返回结构异常')
        }
        setAuth(body.data.token, body.data.user)
        logInfo('登录成功', body.data.user.username)
        const redirect = this.$route.query.redirect
        this.$router.replace(redirect && redirect.startsWith('/') ? redirect : '/single')
      } catch (e) {
        const detail = e?.response?.data?.detail || '登录失败'
        ElMessage.error(detail)
        logWarn('登录失败', detail)
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped>
.login-wrap {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}
.login-card {
  width: 380px;
  max-width: 90vw;
}
.blk {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.18em;
  margin: 4px 0 14px;
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--line-soft);
}
.blk-orn {
  color: var(--zheshi);
  font-size: 9px;
  margin-right: 6px;
  vertical-align: 2px;
}
.hint {
  margin-top: 14px;
  text-align: center;
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 12px;
  color: var(--ink-faint);
  letter-spacing: 0.1em;
}
</style>