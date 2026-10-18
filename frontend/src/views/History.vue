<!-- -*- coding: utf-8 -*- -->
<!--
  我的历史

  列表 + 搜索 + 分页 + 详情 + 删除 + 可见性切换。
  只显示当前登录用户自己的记录。

  作者：@zlxaaa
  创建日期：2026-10-18
  版本：1.0.0
-->

<template>
  <div class="history">
    <el-card shadow="never" class="leaf">
      <div class="toolbar">
        <div class="blk"><span class="blk-orn">○</span> 我 的 历 史</div>
        <div class="toolbar-right">
          <el-input
            v-model="q"
            placeholder="搜索查询键或解析内容"
            clearable
            style="width: 240px"
            @keyup.enter="reload"
          />
          <el-button type="primary" plain @click="reload">搜 索</el-button>
          <el-button plain @click="reload">刷新</el-button>
        </div>
      </div>

      <el-table :data="items" style="width:100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.query_type === 'sheet' ? 'warning' : 'success'">
              {{ row.query_type === 'sheet' ? '整谱' : '单字' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="快照" width="90">
          <template #default="{ row }">
            <el-image
              v-if="row.thumb_url || row.image_url"
              :src="row.thumb_url || row.image_url"
              :preview-src-list="[row.image_url || row.thumb_url]"
              fit="cover"
              style="width:56px;height:56px;border:1px solid var(--line-soft)"
              preview-teleported
            />
            <span v-else class="muted">无</span>
          </template>
        </el-table-column>
        <el-table-column label="摘要" min-width="180">
          <template #default="{ row }">
            <span class="mono">{{ summaryOf(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="可见性" width="130">
          <template #default="{ row }">
            <el-tag size="small" :type="visType(row.visibility)">
              {{ visLabel(row.visibility) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170" />
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button size="small" plain @click="openDetail(row)">详情</el-button>
            <el-button
              size="small"
              plain
              v-if="row.visibility !== 'admin_hidden'"
              @click="toggleVisibility(row)"
            >
              {{ row.visibility === 'public' ? '设为私有' : '公开' }}
            </el-button>
            <el-button size="small" type="danger" plain @click="confirmDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        style="margin-top:14px;justify-content:flex-end"
        layout="prev, pager, next, total"
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        @current-change="onPage"
      />
    </el-card>

    <!-- 详情 -->
    <el-dialog v-model="detailVisible" title="历史详情" width="720px" top="6vh">
      <template v-if="cur">
        <div class="d-head">
          <span>#{{ cur.id }}</span>
          <el-tag size="small" :type="cur.query_type === 'sheet' ? 'warning' : 'success'">
            {{ cur.query_type === 'sheet' ? '整谱' : '单字' }}
          </el-tag>
          <el-tag size="small" :type="visType(cur.visibility)">{{ visLabel(cur.visibility) }}</el-tag>
          <span class="muted">{{ cur.created_at }}</span>
        </div>

        <div v-if="cur.image_url" class="d-img">
          <el-image
            :src="cur.image_url"
            fit="contain"
            style="max-width:100%;max-height:360px"
            :preview-src-list="[cur.image_url]"
            preview-teleported
          />
        </div>

        <div class="blk2"><span class="blk-orn">○</span> 解析快照</div>
        <pre class="json">{{ prettyParse(cur) }}</pre>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listHistory,
  deleteHistory,
  setHistoryVisibility,
} from '../api/index.js'
import { logInfo, logWarn } from '../logger.js'

export default {
  name: 'History',
  data() {
    return {
      items: [],
      total: 0,
      page: 1,
      pageSize: 20,
      q: '',
      loading: false,
      detailVisible: false,
      cur: null,
    }
  },
  mounted() {
    this.reload()
  },
  methods: {
    async reload() {
      this.loading = true
      try {
        const res = await listHistory(this.page, this.pageSize, this.q)
        const data = (res.data && res.data.data) || {}
        this.items = data.items || []
        this.total = data.total || 0
      } catch (e) {
        ElMessage.error('加载历史失败')
        logWarn('加载历史失败', e && e.message)
      } finally {
        this.loading = false
      }
    },
    onPage(p) {
      this.page = p
      this.reload()
    },
    summaryOf(row) {
      const p = row.parse || {}
      if (row.query_type === 'single') {
        return p.top_key || (p.attributes_selected && p.attributes_selected.rh) || '（属性候选）'
      }
      const n = (p.items || []).length
      return `检测 ${n} 框 · 来源 ${p.source || '-'}`
    },
    visLabel(v) {
      return v === 'public' ? '公开' : v === 'admin_hidden' ? '被管理员隐藏' : '私有'
    },
    visType(v) {
      return v === 'public' ? 'success' : v === 'admin_hidden' ? 'info' : 'warning'
    },
    openDetail(row) {
      this.cur = row
      this.detailVisible = true
    },
    prettyParse(row) {
      try {
        return JSON.stringify(row.parse || {}, null, 2)
      } catch {
        return '（无法序列化）'
      }
    },
    async toggleVisibility(row) {
      const next = row.visibility === 'public' ? 'private' : 'public'
      try {
        await setHistoryVisibility(row.id, next)
        ElMessage.success(next === 'public' ? '已公开' : '已设为私有')
        logInfo('历史可见性切换', `#${row.id} → ${next}`)
        this.reload()
      } catch (e) {
        const detail = e?.response?.data?.detail || '操作失败'
        ElMessage.error(detail)
      }
    },
    async confirmDelete(row) {
      try {
        await ElMessageBox.confirm(`删除历史 #${row.id} 及其快照图？`, '确认删除', {
          type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
        })
      } catch {
        return
      }
      try {
        await deleteHistory(row.id)
        ElMessage.success('已删除')
        logInfo('删除历史', `#${row.id}`)
        this.reload()
      } catch (e) {
        ElMessage.error('删除失败')
      }
    },
  },
}
</script>

<style scoped>
.history { padding: 4px 0; }
.leaf :deep(.el-card__body) { padding: 18px 20px; }

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}
.toolbar-right { display: flex; gap: 8px; align-items: center; }

.blk {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.18em;
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--line-soft);
}
.blk2 {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.18em;
  margin: 16px 0 8px;
  padding-bottom: 5px;
  border-bottom: 1px dashed var(--line-soft);
}
.blk-orn {
  color: var(--zheshi);
  font-size: 9px;
  margin-right: 6px;
  vertical-align: 2px;
}
.mono { font-family: 'Courier New', monospace; font-size: 12px; }
.muted { color: var(--ink-faint); font-size: 12px; }

.d-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.d-img {
  display: flex;
  justify-content: center;
  background: rgba(246, 238, 215, 0.55);
  border: 1px solid var(--line);
  padding: 8px;
  margin-bottom: 6px;
}
.json {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.7;
  background: rgba(246, 238, 215, 0.55);
  border: 1px solid var(--line);
  border-left: 3px solid var(--zheshi);
  padding: 12px 14px;
  max-height: 340px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>