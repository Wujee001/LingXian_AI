<!-- -*- coding: utf-8 -*- -->
<!--
  管理员工作台（仅管理员）

  Tab 1「用户」：列表 + 添加 + 禁用/启用 + 重置密码
  Tab 2「被隐藏内容」：查看完整内容 + 解除隐藏（笔记 / 历史）
  Tab 3「审计日志」：add/disable/enable/reset/hide/unhide 六类动作流水

  作者：@zlxaaa
  创建日期：2026-10-18
  版本：1.2.0（3 tab 管理台）
-->

<template>
  <div class="admin-users">
    <el-card shadow="never" class="leaf">
      <el-tabs v-model="tab" @tab-change="onTabChange">

        <!-- ============ Tab 1：用户 ============ -->
        <el-tab-pane label="用户" name="users">
          <div class="toolbar">
            <div class="blk"><span class="blk-orn">○</span> 用 户 管 理</div>
            <el-button type="primary" @click="openAdd">添加用户</el-button>
          </div>

          <el-table :data="users" style="width:100%" v-loading="loading">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="username" label="用户名" min-width="120" />
            <el-table-column label="角色" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="row.role === 'admin' ? 'danger' : 'info'">
                  {{ row.role }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.disabled ? 'info' : 'success'">
                  {{ row.disabled ? '禁用' : '正常' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180" />
            <el-table-column label="操作" width="260">
              <template #default="{ row }">
                <el-button
                  size="small"
                  plain
                  :disabled="row.id === (auth.user && auth.user.id)"
                  @click="toggleDisabled(row)"
                >
                  {{ row.disabled ? '启用' : '禁用' }}
                </el-button>
                <el-button size="small" plain @click="openReset(row)">重置密码</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- ============ Tab 2：被隐藏内容 ============ -->
        <el-tab-pane label="被隐藏内容" name="hidden">
          <div class="toolbar">
            <div class="blk"><span class="blk-orn">○</span> 被 隐 藏 内 容</div>
            <el-radio-group v-model="hiddenType" size="small" @change="reloadHidden">
              <el-radio-button label="notes">笔记</el-radio-button>
              <el-radio-button label="history">历史</el-radio-button>
            </el-radio-group>
          </div>

          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="解除隐藏后恢复为「私有」，是否重新公开由用户自行决定"
            style="margin-bottom:12px"
          />

          <el-table :data="hiddenItems" style="width:100%" v-loading="hiddenLoading">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column label="作者" width="120">
              <template #default="{ row }">{{ row.username || '—' }}</template>
            </el-table-column>
            <el-table-column label="标题/摘要" min-width="220">
              <template #default="{ row }">
                <span class="mono">{{ summaryOf(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="updated_at" label="更新时间" width="170"
                             v-if="hiddenType === 'notes'" />
            <el-table-column prop="created_at" label="创建时间" width="170"
                             v-if="hiddenType === 'history'" />
            <el-table-column label="操作" width="240">
              <template #default="{ row }">
                <el-button size="small" plain @click="openHiddenDetail(row)">查看</el-button>
                <el-button size="small" type="success" plain @click="unhide(row)">
                  解除隐藏
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-if="hiddenTotal > hiddenPageSize"
            style="margin-top:14px;justify-content:flex-end"
            layout="prev, pager, next, total"
            :current-page="hiddenPage"
            :page-size="hiddenPageSize"
            :total="hiddenTotal"
            @current-change="onHiddenPage"
          />
        </el-tab-pane>

        <!-- ============ Tab 3：审计日志 ============ -->
        <el-tab-pane label="审计日志" name="audit">
          <div class="toolbar">
            <div class="blk"><span class="blk-orn">○</span> 操 作 审 计</div>
            <el-button plain @click="fetchAudit">刷新</el-button>
          </div>

          <el-table :data="auditItems" style="width:100%" v-loading="auditLoading">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column label="管理员" width="120">
              <template #default="{ row }">{{ row.admin_name || ('#' + row.admin_id) }}</template>
            </el-table-column>
            <el-table-column label="动作" width="130">
              <template #default="{ row }">
                <el-tag size="small" :type="actionType(row.action)">
                  {{ actionLabel(row.action) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="目标" min-width="200">
              <template #default="{ row }">
                <span class="mono">{{ targetOf(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="180" />
            <el-table-column label="详情" width="120">
              <template #default="{ row }">
                <el-button v-if="row.detail" size="small" plain
                           @click="showAuditDetail(row)">查看</el-button>
                <span v-else class="muted">—</span>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-if="auditTotal > auditPageSize"
            style="margin-top:14px;justify-content:flex-end"
            layout="prev, pager, next, total"
            :current-page="auditPage"
            :page-size="auditPageSize"
            :total="auditTotal"
            @current-change="onAuditPage"
          />
        </el-tab-pane>

      </el-tabs>
    </el-card>

    <!-- 添加用户 -->
    <el-dialog v-model="addVisible" title="添加用户" width="420px">
      <el-input v-model="addForm.username" placeholder="用户名（2~32 字符）" />
      <el-input
        v-model="addForm.password"
        type="password"
        show-password
        placeholder="密码（≥8 位）"
        style="margin-top:12px"
      />
      <el-radio-group v-model="addForm.role" style="margin-top:12px">
        <el-radio-button label="user">普通用户</el-radio-button>
        <el-radio-button label="admin">管理员</el-radio-button>
      </el-radio-group>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitAdd">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 -->
    <el-dialog v-model="resetVisible" title="重置密码" width="420px">
      <p class="reset-user">用户：{{ resetUser && resetUser.username }}</p>
      <el-input v-model="resetPwd" type="password" show-password
                placeholder="新密码（≥8 位）" />
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitReset">确定</el-button>
      </template>
    </el-dialog>

    <!-- 隐藏内容详情 -->
    <el-dialog v-model="hiddenDetailVisible" title="隐藏内容详情" width="820px" top="6vh">
      <template v-if="hiddenCur">
        <div class="v-head">
          <span>#{{ hiddenCur.id }}</span>
          <el-tag size="small">{{ hiddenCur.username || '—' }}</el-tag>
          <span class="muted">{{ hiddenCur.created_at }}</span>
        </div>
        <template v-if="hiddenType === 'notes'">
          <MarkdownView :content="hiddenCur.content_md || ''" />
        </template>
        <template v-else>
          <div v-if="hiddenCur.image_url" class="d-img">
            <el-image :src="hiddenCur.image_url" fit="contain"
                      style="max-width:100%;max-height:360px"
                      :preview-src-list="[hiddenCur.image_url]" preview-teleported />
          </div>
          <pre class="json">{{ prettyJson(hiddenCur.parse) }}</pre>
        </template>
      </template>
    </el-dialog>

    <!-- 审计详情 JSON -->
    <el-dialog v-model="auditDetailVisible" title="审计详情" width="600px">
      <pre class="json">{{ auditDetailText }}</pre>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import MarkdownView from '../components/MarkdownView.vue'
import {
  adminListUsers,
  adminCreateUser,
  adminPatchUser,
  adminResetPassword,
  adminListHiddenNotes,
  adminListHiddenHistory,
  adminUnhideNote,
  adminUnhideHistory,
  adminAudit,
} from '../api/index.js'
import { auth } from '../store/auth.js'
import { logInfo, logWarn } from '../logger.js'

const ACTION_LABELS = {
  add_user: '添加用户',
  disable_user: '禁用用户',
  enable_user: '启用用户',
  reset_password: '重置密码',
  hide_content: '隐藏内容',
  unhide_content: '解除隐藏',
}
const ACTION_TYPES = {
  add_user: 'success',
  disable_user: 'warning',
  enable_user: 'success',
  reset_password: 'warning',
  hide_content: 'danger',
  unhide_content: 'success',
}

export default {
  name: 'AdminUsers',
  components: { MarkdownView },
  data() {
    return {
      auth,
      tab: 'users',

      // Tab 1
      users: [],
      loading: false,
      saving: false,
      addVisible: false,
      addForm: { username: '', password: '', role: 'user' },
      resetVisible: false,
      resetUser: null,
      resetPwd: '',

      // Tab 2
      hiddenType: 'notes',
      hiddenItems: [],
      hiddenTotal: 0,
      hiddenPage: 1,
      hiddenPageSize: 20,
      hiddenLoading: false,
      hiddenDetailVisible: false,
      hiddenCur: null,

      // Tab 3
      auditItems: [],
      auditTotal: 0,
      auditPage: 1,
      auditPageSize: 20,
      auditLoading: false,
      auditDetailVisible: false,
      auditDetailText: '',
    }
  },
  mounted() {
    this.load()
  },
  methods: {
    /* ---------- Tab 1：用户 ---------- */
    async load() {
      this.loading = true
      try {
        const res = await adminListUsers()
        this.users = (res.data && res.data.data && res.data.data.items) || []
      } catch (e) {
        ElMessage.error('加载用户列表失败')
        logWarn('加载用户失败', e && e.message)
      } finally {
        this.loading = false
      }
    },
    openAdd() {
      this.addForm = { username: '', password: '', role: 'user' }
      this.addVisible = true
    },
    async submitAdd() {
      const u = (this.addForm.username || '').trim()
      if (u.length < 2) return ElMessage.warning('用户名至少 2 位')
      if (this.addForm.password.length < 8) return ElMessage.warning('密码至少 8 位')
      this.saving = true
      try {
        await adminCreateUser(u, this.addForm.password, this.addForm.role)
        ElMessage.success('已创建用户')
        logInfo('管理员创建用户', u)
        this.addVisible = false
        this.load()
      } catch (e) {
        ElMessage.error((e?.response?.data?.detail) || '创建失败')
      } finally {
        this.saving = false
      }
    },
    async toggleDisabled(row) {
      const next = !row.disabled
      try {
        await adminPatchUser(row.id, next)
        ElMessage.success(next ? '已禁用' : '已启用')
        logInfo(next ? '管理员禁用用户' : '管理员启用用户', row.username)
        this.load()
      } catch (e) {
        ElMessage.error((e?.response?.data?.detail) || '操作失败')
      }
    },
    openReset(row) {
      this.resetUser = row
      this.resetPwd = ''
      this.resetVisible = true
    },
    async submitReset() {
      if (this.resetPwd.length < 8) return ElMessage.warning('密码至少 8 位')
      this.saving = true
      try {
        await adminResetPassword(this.resetUser.id, this.resetPwd)
        ElMessage.success('密码已重置')
        logInfo('管理员重置密码', this.resetUser.username)
        this.resetVisible = false
      } catch (e) {
        ElMessage.error((e?.response?.data?.detail) || '重置失败')
      } finally {
        this.saving = false
      }
    },

    /* ---------- Tab 2：被隐藏内容 ---------- */
    async reloadHidden() {
      this.hiddenPage = 1
      await this.fetchHidden()
    },
    async fetchHidden() {
      this.hiddenLoading = true
      try {
        const fn = this.hiddenType === 'notes' ? adminListHiddenNotes : adminListHiddenHistory
        const res = await fn(this.hiddenPage, this.hiddenPageSize)
        const data = (res.data && res.data.data) || {}
        this.hiddenItems = data.items || []
        this.hiddenTotal = data.total || 0
      } catch (e) {
        ElMessage.error('加载被隐藏内容失败')
        logWarn('加载被隐藏失败', e && e.message)
      } finally {
        this.hiddenLoading = false
      }
    },
    onHiddenPage(p) {
      this.hiddenPage = p
      this.fetchHidden()
    },
    summaryOf(row) {
      if (this.hiddenType === 'notes') {
        const t = (row.title || '').trim()
        if (t) return t
        const first = (row.content_md || '').split('\n').map(s => s.trim()).find(Boolean) || '（无标题）'
        return first.replace(/^#+\s*/, '').slice(0, 40)
      }
      const p = row.parse || {}
      if (row.query_type === 'single') {
        return p.top_key || (p.attributes_selected && p.attributes_selected.rh) || '（属性候选）'
      }
      return `检测 ${(p.items || []).length} 框 · ${p.source || '-'}`
    },
    openHiddenDetail(row) {
      this.hiddenCur = row
      this.hiddenDetailVisible = true
    },
    prettyJson(obj) {
      try { return JSON.stringify(obj || {}, null, 2) } catch { return '（无法序列化）' }
    },
    async unhide(row) {
      try {
        if (this.hiddenType === 'notes') await adminUnhideNote(row.id)
        else await adminUnhideHistory(row.id)
        ElMessage.success('已解除隐藏，恢复为私有')
        logInfo('管理员解除隐藏', `${this.hiddenType}#${row.id}`)
        this.hiddenDetailVisible = false
        this.fetchHidden()
      } catch (e) {
        ElMessage.error((e?.response?.data?.detail) || '解除失败')
      }
    },

    /* ---------- Tab 3：审计日志 ---------- */
    async fetchAudit() {
      this.auditLoading = true
      try {
        const res = await adminAudit(this.auditPage, this.auditPageSize)
        const data = (res.data && res.data.data) || {}
        this.auditItems = data.items || []
        this.auditTotal = data.total || 0
      } catch (e) {
        ElMessage.error('加载审计日志失败')
        logWarn('加载审计失败', e && e.message)
      } finally {
        this.auditLoading = false
      }
    },
    onAuditPage(p) {
      this.auditPage = p
      this.fetchAudit()
    },
    actionLabel(a) { return ACTION_LABELS[a] || a },
    actionType(a) { return ACTION_TYPES[a] || 'info' },
    targetOf(row) {
      const parts = []
      if (row.target_user) parts.push(`user#${row.target_user}`)
      if (row.target_type && row.target_id) parts.push(`${row.target_type}#${row.target_id}`)
      return parts.join(' · ') || '—'
    },
    showAuditDetail(row) {
      try {
        this.auditDetailText = JSON.stringify(row.detail, null, 2)
      } catch {
        this.auditDetailText = '（无法序列化）'
      }
      this.auditDetailVisible = true
    },

    /* ---------- tab 切换时懒加载 ---------- */
    onTabChange(name) {
      if (name === 'hidden' && this.hiddenItems.length === 0) this.fetchHidden()
      if (name === 'audit' && this.auditItems.length === 0) this.fetchAudit()
    },
  },
}
</script>

<style scoped>
.admin-users { padding: 4px 0; }
.leaf :deep(.el-card__body) { padding: 18px 20px; }

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}
.blk {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.18em;
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--line-soft);
}
.blk-orn {
  color: var(--zheshi);
  font-size: 9px;
  margin-right: 6px;
  vertical-align: 2px;
}
.reset-user {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  color: var(--ink-soft);
  margin: 0 0 10px;
}
.mono { font-family: 'Courier New', monospace; font-size: 12px; }
.muted { color: var(--ink-faint); font-size: 12px; }
.v-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px dashed var(--line-soft); }
.d-img { display: flex; justify-content: center; background: rgba(246, 238, 215, 0.55); border: 1px solid var(--line); padding: 8px; margin-bottom: 6px; }
.json {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.7;
  background: rgba(246, 238, 215, 0.55);
  border: 1px solid var(--line);
  border-left: 3px solid var(--zheshi);
  padding: 12px 14px;
  max-height: 360px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>