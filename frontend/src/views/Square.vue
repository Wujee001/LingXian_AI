<!-- -*- coding: utf-8 -*- -->
<!--
  广场：公开笔记 / 公开历史（登录可见）；管理员可隐藏

  作者：@zlxaaa
  创建日期：2026-10-18
  版本：1.0.0
-->
<template>
  <div class="square">
    <el-card shadow="never" class="leaf">
      <div class="toolbar">
        <el-radio-group v-model="tab" @change="reload">
          <el-radio-button label="notes">公开笔记</el-radio-button>
          <el-radio-button label="history">公开历史</el-radio-button>
        </el-radio-group>
        <div class="toolbar-right">
          <el-input v-model="q" placeholder="搜索" clearable style="width:220px"
                    @keyup.enter="reload" />
          <el-button plain @click="reload">刷新</el-button>
        </div>
      </div>

      <el-table :data="items" v-loading="loading" style="width:100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="作者" width="120">
          <template #default="{ row }">{{ row.username || '—' }}</template>
        </el-table-column>
        <el-table-column label="快照/标题" min-width="220">
          <template #default="{ row }">
            <template v-if="tab === 'notes'">
              <span class="title">{{ titleOf(row) }}</span>
            </template>
            <template v-else>
              <span class="mono">{{ summaryOf(row) }}</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column v-if="tab === 'history'" label="缩略图" width="90">
          <template #default="{ row }">
            <el-image v-if="row.thumb_url || row.image_url"
                      :src="row.thumb_url || row.image_url"
                      :preview-src-list="[row.image_url || row.thumb_url]"
                      fit="cover" style="width:56px;height:56px;border:1px solid var(--line-soft)"
                      preview-teleported />
            <span v-else class="muted">无</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" plain @click="openDetail(row)">详情</el-button>
            <el-button v-if="isAdmin" size="small" type="warning" plain
                       @click="hide(row)">隐藏</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination v-if="total > pageSize"
                     style="margin-top:14px;justify-content:flex-end"
                     layout="prev, pager, next, total"
                     :current-page="page" :page-size="pageSize" :total="total"
                     @current-change="onPage" />
    </el-card>

    <!-- 详情 -->
    <el-dialog v-model="detailVisible" title="详情" width="820px" top="6vh">
      <template v-if="cur">
        <div class="v-head">
          <span>#{{ cur.id }}</span>
          <el-tag size="small">{{ cur.username || '—' }}</el-tag>
          <span class="muted">{{ cur.created_at }}</span>
        </div>
        <template v-if="tab === 'notes'">
          <MarkdownView :content="cur.content_md" />
        </template>
        <template v-else>
          <div v-if="cur.image_url" class="d-img">
            <el-image :src="cur.image_url" fit="contain"
                      style="max-width:100%;max-height:360px"
                      :preview-src-list="[cur.image_url]" preview-teleported />
          </div>
          <pre class="json">{{ prettyParse(cur) }}</pre>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import MarkdownView from '../components/MarkdownView.vue'
import {
  squareNotes, squareHistory, adminHideNote, adminHideHistory,
} from '../api/index.js'
import { auth } from '../store/auth.js'

export default {
  name: 'Square',
  components: { MarkdownView },
  data() {
    return {
      tab: 'notes',
      items: [], total: 0, page: 1, pageSize: 20, q: '',
      loading: false, detailVisible: false, cur: null,
    }
  },
  computed: {
    isAdmin() { return auth.user && auth.user.role === 'admin' },
  },
  mounted() { this.reload() },
  methods: {
    async reload() {
      this.loading = true
      this.page = 1
      try {
        const fn = this.tab === 'notes' ? squareNotes : squareHistory
        const res = await fn(this.page, this.pageSize, this.q)
        const data = (res.data && res.data.data) || {}
        this.items = data.items || []
        this.total = data.total || 0
      } catch (e) {
        ElMessage.error('加载失败')
      } finally { this.loading = false }
    },
    onPage(p) {
      this.page = p
      this.reload2()
    },
    async reload2() {
      this.loading = true
      try {
        const fn = this.tab === 'notes' ? squareNotes : squareHistory
        const res = await fn(this.page, this.pageSize, this.q)
        const data = (res.data && res.data.data) || {}
        this.items = data.items || []
        this.total = data.total || 0
      } finally { this.loading = false }
    },
    titleOf(row) {
      if (row.title && row.title.trim()) return row.title
      const first = (row.content_md || '').split('\n').map(s => s.trim()).find(Boolean) || '（无标题）'
      return first.replace(/^#+\s*/, '').slice(0, 40)
    },
    summaryOf(row) {
      const p = row.parse || {}
      if (row.query_type === 'single') {
        return p.top_key || (p.attributes_selected && p.attributes_selected.rh) || '（属性候选）'
      }
      return `检测 ${(p.items || []).length} 框 · ${p.source || '-'}`
    },
    prettyParse(row) {
      try { return JSON.stringify(row.parse || {}, null, 2) } catch { return '（无法序列化）' }
    },
    openDetail(row) { this.cur = row; this.detailVisible = true },
    async hide(row) {
      try {
        if (this.tab === 'notes') await adminHideNote(row.id)
        else await adminHideHistory(row.id)
        ElMessage.success('已隐藏')
        this.detailVisible = false
        this.reload()
      } catch (e) {
        ElMessage.error((e?.response?.data?.detail) || '操作失败')
      }
    },
  },
}
</script>

<style scoped>
.square { padding: 4px 0; }
.leaf :deep(.el-card__body) { padding: 18px 20px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px; }
.toolbar-right { display: flex; gap: 8px; align-items: center; }
.title { font-family: 'STKaiti', 'KaiTi', '楷体', serif; font-size: 14px; letter-spacing: 0.06em; }
.mono { font-family: 'Courier New', monospace; font-size: 12px; }
.muted { color: var(--ink-faint); font-size: 12px; }
.v-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px dashed var(--line-soft); }
.d-img { display: flex; justify-content: center; background: rgba(246, 238, 215, 0.55); border: 1px solid var(--line); padding: 8px; margin-bottom: 6px; }
.json { font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.7; background: rgba(246, 238, 215, 0.55); border: 1px solid var(--line); border-left: 3px solid var(--zheshi); padding: 12px 14px; max-height: 340px; overflow: auto; white-space: pre-wrap; word-break: break-all; }
</style>