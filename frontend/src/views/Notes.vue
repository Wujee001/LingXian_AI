<!-- -*- coding: utf-8 -*- -->
<!--
  我的笔记：列表 + 新建/编辑 + 可见性 + 删除

  作者：@zlxaaa
  创建日期：2026-10-18
  版本：1.0.0
-->
<template>
  <div class="notes">
    <el-card shadow="never" class="leaf">
      <div class="toolbar">
        <div class="blk"><span class="blk-orn">○</span> 我 的 笔 记</div>
        <div class="toolbar-right">
          <el-input v-model="q" placeholder="搜索标题或正文" clearable
                    style="width:220px" @keyup.enter="reload" />
          <el-button plain @click="reload">刷新</el-button>
          <el-button type="primary" @click="openNew">新建笔记</el-button>
        </div>
      </div>

      <el-table :data="items" v-loading="loading" style="width:100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="标题" min-width="200">
          <template #default="{ row }">
            <span class="title">{{ titleOf(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="关联减字" width="160">
          <template #default="{ row }">
            <span class="mono">{{ row.class_key || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="可见性" width="130">
          <template #default="{ row }">
            <el-tag size="small" :type="visType(row.visibility)">
              {{ visLabel(row.visibility) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170" />
        <el-table-column label="操作" width="300">
          <template #default="{ row }">
            <el-button size="small" plain @click="openView(row)">查看</el-button>
            <el-button size="small" plain @click="openEdit(row)">编辑</el-button>
            <el-button size="small" plain
                       v-if="row.visibility !== 'admin_hidden'"
                       @click="toggleVis(row)">
              {{ row.visibility === 'public' ? '设为私有' : '公开' }}
            </el-button>
            <el-button size="small" type="danger" plain @click="confirmDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination v-if="total > pageSize"
                     style="margin-top:14px;justify-content:flex-end"
                     layout="prev, pager, next, total"
                     :current-page="page" :page-size="pageSize" :total="total"
                     @current-change="onPage" />
    </el-card>

    <!-- 编辑/新建 -->
    <el-dialog v-model="editVisible" :title="editId ? '编辑笔记' : '新建笔记'" width="880px" top="5vh">
      <el-input v-model="form.title" placeholder="标题（可空，默认取正文首行）" />
      <el-input v-model="form.class_key" placeholder="关联减字 key（选填）"
                style="margin-top:10px" />
      <div style="margin-top:12px">
        <NoteEditor v-model="form.content_md" />
      </div>
      <el-radio-group v-model="form.visibility" style="margin-top:12px">
        <el-radio-button label="private">私有</el-radio-button>
        <el-radio-button label="public">公开</el-radio-button>
      </el-radio-group>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 只读查看 -->
    <el-dialog v-model="viewVisible" title="查看笔记" width="820px" top="6vh">
      <template v-if="cur">
        <div class="v-head">
          <span class="v-title">{{ titleOf(cur) }}</span>
          <el-tag size="small" :type="visType(cur.visibility)">{{ visLabel(cur.visibility) }}</el-tag>
          <span class="muted" v-if="cur.class_key">关联：{{ cur.class_key }}</span>
        </div>
        <MarkdownView :content="cur.content_md" />
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage, ElMessageBox } from 'element-plus'
import NoteEditor from '../components/NoteEditor.vue'
import MarkdownView from '../components/MarkdownView.vue'
import {
  listNotes, createNote, updateNote, deleteNote, setNoteVisibility,
} from '../api/index.js'
import { logInfo, logWarn } from '../logger.js'

const EMPTY = { title: '', content_md: '', class_key: '', visibility: 'private' }

export default {
  name: 'Notes',
  components: { NoteEditor, MarkdownView },
  data() {
    return {
      items: [], total: 0, page: 1, pageSize: 20, q: '',
      loading: false, saving: false,
      editVisible: false, editId: null,
      form: { ...EMPTY },
      viewVisible: false, cur: null,
    }
  },
  mounted() {
    const ck = this.$route.query.class_key
    this.reload().then(() => {
      if (ck) {
        this.form = { ...EMPTY, class_key: String(ck) }
        this.editId = null
        this.editVisible = true
      }
    })
  },
  methods: {
    async reload() {
      this.loading = true
      try {
        const res = await listNotes(this.page, this.pageSize, this.q)
        const data = (res.data && res.data.data) || {}
        this.items = data.items || []
        this.total = data.total || 0
      } catch (e) {
        ElMessage.error('加载笔记失败')
        logWarn('加载笔记失败', e && e.message)
      } finally {
        this.loading = false
      }
    },
    onPage(p) { this.page = p; this.reload() },
    titleOf(row) {
      if (row.title && row.title.trim()) return row.title
      const first = (row.content_md || '').split('\n').map(s => s.trim()).find(Boolean) || '（无标题）'
      return first.replace(/^#+\s*/, '').slice(0, 40)
    },
    visLabel(v) { return v === 'public' ? '公开' : v === 'admin_hidden' ? '被管理员隐藏' : '私有' },
    visType(v) { return v === 'public' ? 'success' : v === 'admin_hidden' ? 'info' : 'warning' },
    openNew() { this.editId = null; this.form = { ...EMPTY }; this.editVisible = true },
    openEdit(row) {
      this.editId = row.id
      this.form = {
        title: row.title || '',
        content_md: row.content_md || '',
        class_key: row.class_key || '',
        visibility: row.visibility === 'admin_hidden' ? 'private' : row.visibility,
      }
      this.editVisible = true
    },
    openView(row) { this.cur = row; this.viewVisible = true },
    async submitForm() {
      if (!this.form.content_md.trim()) return ElMessage.warning('内容不能为空')
      this.saving = true
      try {
        if (this.editId) {
          await updateNote(this.editId, { ...this.form })
          ElMessage.success('已更新')
        } else {
          await createNote({ ...this.form })
          ElMessage.success('已创建')
        }
        logInfo(this.editId ? '更新笔记' : '新建笔记', this.form.title || '(无标题)')
        this.editVisible = false
        this.reload()
      } catch (e) {
        ElMessage.error((e?.response?.data?.detail) || '保存失败')
      } finally {
        this.saving = false
      }
    },
    async toggleVis(row) {
      const next = row.visibility === 'public' ? 'private' : 'public'
      try {
        await setNoteVisibility(row.id, next)
        ElMessage.success(next === 'public' ? '已公开' : '已设为私有')
        this.reload()
      } catch (e) {
        ElMessage.error((e?.response?.data?.detail) || '操作失败')
      }
    },
    async confirmDelete(row) {
      try {
        await ElMessageBox.confirm(`删除笔记「${this.titleOf(row)}」？`, '确认删除', {
          type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
        })
      } catch { return }
      try {
        await deleteNote(row.id)
        ElMessage.success('已删除')
        this.reload()
      } catch (e) { ElMessage.error('删除失败') }
    },
  },
}
</script>

<style scoped>
.notes { padding: 4px 0; }
.leaf :deep(.el-card__body) { padding: 18px 20px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px; }
.toolbar-right { display: flex; gap: 8px; align-items: center; }
.blk { font-family: 'STKaiti', 'KaiTi', '楷体', serif; font-size: 14px; font-weight: 700; color: var(--ink); letter-spacing: 0.18em; padding-bottom: 6px; border-bottom: 1px dashed var(--line-soft); }
.blk-orn { color: var(--zheshi); font-size: 9px; margin-right: 6px; vertical-align: 2px; }
.title { font-family: 'STKaiti', 'KaiTi', '楷体', serif; font-size: 14px; letter-spacing: 0.06em; }
.mono { font-family: 'Courier New', monospace; font-size: 12px; }
.muted { color: var(--ink-faint); font-size: 12px; }
.v-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px dashed var(--line-soft); }
.v-title { font-family: 'STKaiti', 'KaiTi', '楷体', serif; font-size: 16px; font-weight: 700; color: var(--ink); }
</style>