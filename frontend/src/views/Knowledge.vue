<!-- -*- coding: utf-8 -*- -->
<template>
  <div class="kb">
    <el-row :gutter="16">
      <!-- 左：列表 -->
      <el-col :xs="24" :sm="10">
        <el-card shadow="never" class="leaf">
          <div class="blk"><span class="blk-orn">○</span> 检 索</div>

          <div class="search-row">
            <el-input v-model="q" placeholder="输入指法/弦/徽位/中文名称"
                      clearable @keyup.enter="doSearch" />
            <el-button type="primary" plain @click="doSearch">搜 索</el-button>
          </div>

          <div class="filter-row">
            <span class="lbl">类 型</span>
            <el-radio-group v-model="charType" size="small" @change="loadList">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="散音">散音</el-radio-button>
              <el-radio-button label="按音">按音</el-radio-button>
              <el-radio-button label="泛音">泛音</el-radio-button>
              <el-radio-button label="装饰音">装饰音</el-radio-button>
              <el-radio-button label="复合音">复合音</el-radio-button>
            </el-radio-group>
          </div>

          <div class="blk2">
            <span v-if="loading">载入中…</span>
            <span v-else>共 {{ list.length }} 条</span>
            <el-tag size="small" type="success" class="src-tag">本地知识库</el-tag>
          </div>

          <ul class="kb-list">
            <li v-for="item in list" :key="item.char_key"
                :class="{ active: cur && cur.char_key === item.char_key }"
                @click="cur = item">
              <span class="kb-cn">{{ item.display }}</span>
              <span class="kb-type">{{ item.type }}</span>
            </li>
            <li v-if="!list.length && !loading" class="kb-empty">
              未找到匹配的减字
            </li>
          </ul>
        </el-card>
      </el-col>

      <!-- 右：详情 -->
      <el-col :xs="24" :sm="14">
        <el-card shadow="never" class="leaf">
          <div v-if="!cur" class="empty">
            从左侧选择一个减字<br />查看其指法释义与乐理说明
          </div>

          <template v-else>
            <div class="p-title">
              <span class="p-display">{{ cur.display }}</span>
              <el-tag size="small" type="info">{{ cur.type }}</el-tag>
            </div>

            <div class="blk"><span class="blk-orn">○</span> 指法释义</div>
            <div class="parse">
              <div class="parse-row">
                <span class="k">右 手</span>{{ cur.right_hand_text }}
              </div>
              <div class="parse-row">
                <span class="k">左 手</span>{{ cur.left_hand_text }}
              </div>
              <div class="meaning">{{ cur.desc }}</div>
            </div>

            <div class="blk"><span class="blk-orn">○</span> 音 色</div>
            <div class="flags">
              <span class="flag" :class="{ on: cur.is_san }">散音</span>
              <span class="flag" :class="{ on: cur.is_fan }">泛音</span>
              <span class="flag" :class="{ on: !cur.is_san && !cur.is_fan }">按音</span>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'
import { getKbList, searchKb } from '../api/index.js'

export default {
  name: 'Knowledge',
  data() {
    return {
      q: '',
      charType: '',
      loading: false,
      list: [],
      cur: null
    }
  },
  mounted() {
    this.loadList()
  },
  methods: {
    async loadList() {
      this.loading = true
      try {
        const res = await getKbList(this.charType || undefined)
        const body = res && res.data
        const dict = (body && body.success && body.data) || {}
        this.list = Object.values(dict)
        this.cur = this.list[0] || null
      } catch (e) {
        ElMessage.error('知识库加载失败，请联系开发人员检查')
        this.list = []
        this.cur = null
      } finally {
        this.loading = false
      }
    },
    async doSearch() {
      const q = (this.q || '').trim()
      if (!q) return this.loadList()
      this.loading = true
      try {
        const res = await searchKb(q)
        const body = res && res.data
        const dict = (body && body.success && body.data) || {}
        this.list = Object.values(dict)
        this.cur = this.list[0] || null
      } catch (e) {
        ElMessage.error('搜索失败，请联系开发人员检查')
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.kb { padding: 4px 0; }
.leaf :deep(.el-card__body) { padding: 18px 20px; }

.blk {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.18em;
  margin: 4px 0 12px;
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--line-soft);
}
.blk-orn {
  color: var(--zheshi);
  font-size: 9px;
  margin-right: 6px;
  vertical-align: 2px;
}
.blk2 {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 12.5px;
  color: var(--ink-soft);
  letter-spacing: 0.1em;
  margin: 14px 0 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.src-tag { letter-spacing: 0.05em; }

.search-row { display: flex; gap: 8px; margin-bottom: 12px; }
.search-row .el-input { flex: 1; }

.filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
}
.filter-row .lbl {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 13px;
  color: var(--ink-soft);
  letter-spacing: 0.18em;
}

.kb-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 460px;
  overflow-y: auto;
  border-top: 1px solid var(--line-soft);
}
.kb-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 8px;
  border-bottom: 1px dashed var(--line-soft);
  cursor: pointer;
  transition: background-color 0.2s ease;
  font-size: 13px;
}
.kb-list li:hover { background-color: rgba(246, 238, 215, 0.6); }
.kb-list li.active {
  background-color: rgba(139, 90, 60, 0.1);
  border-left: 3px solid var(--zheshi);
  padding-left: 6px;
}
.kb-cn {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 14px;
  letter-spacing: 0.1em;
  flex: 1;
}
.kb-type {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 11.5px;
  color: var(--ink-faint);
}
.kb-empty {
  justify-content: center;
  color: var(--ink-faint);
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  letter-spacing: 0.15em;
  padding: 24px 0;
}

.empty {
  color: var(--ink-faint);
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 13px;
  text-align: center;
  line-height: 2.2;
  padding: 80px 0;
  letter-spacing: 0.12em;
}
.p-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--line-soft);
}
.p-display {
  font-family: 'STXingkai', '华文行楷', 'STKaiti', 'KaiTi', serif;
  font-size: 30px;
  color: var(--ink);
  letter-spacing: 0.18em;
}

.parse {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 13px;
  line-height: 2;
  background-color: rgba(246, 238, 215, 0.55);
  border: 1px solid var(--line);
  border-left: 3px solid var(--zheshi);
  border-radius: 2px;
  padding: 12px 14px;
}
.parse-row .k {
  display: inline-block;
  width: 56px;
  color: var(--ink-faint);
  font-family: 'STKaiti', 'KaiTi', serif;
  letter-spacing: 0.3em;
}
.parse .meaning {
  color: var(--zhusha-deep);
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--line-soft);
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  letter-spacing: 0.06em;
}

.flags { display: flex; gap: 10px; }
.flag {
  font-family: 'STKaiti', 'KaiTi', '楷体', serif;
  font-size: 13px;
  letter-spacing: 0.14em;
  padding: 3px 12px;
  border: 1px solid var(--line-deep);
  border-radius: 2px;
  color: var(--ink-faint);
  background: transparent;
}
.flag.on {
  color: var(--zhusha-deep);
  border-color: var(--zhusha);
  background-color: rgba(138, 53, 42, 0.08);
}
</style>
