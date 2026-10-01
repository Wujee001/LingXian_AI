<!-- -*- coding: utf-8 -*- -->
<!--
  整谱画布组件（泠弦智谱 V1）

  显示整谱图与检测框，支持：点击选中框、拖拽移动框、
  删除框、添加模式下手动画新框。坐标全部归一化(0~1)，
  随图片缩放自适应。框样式：A已确认竹青实线、U待复核
  朱砂虚线、未处理古金实线、选中朱砂高亮。

  作者：
      @Wujee

  创建日期：2026-10-1
  版本：1.0.0

  许可证：内部使用，未经许可不得传播。
-->

<template>
  <div class="sheet-wrap">
    <div class="toolbar">
      <el-button size="small" :type="addMode ? 'primary' : ''" plain
                 @click="toggleAdd">
        {{ addMode ? '画框中 · 在图上拖拽' : '添加框' }}
      </el-button>
      <el-button size="small" plain :disabled="selected === null"
                 @click="removeBox">删除选中框</el-button>
      <span class="legend">
        <i class="lg-a"></i>已确认
        <i class="lg-u"></i>待复核
        <i class="lg-n"></i>未处理
      </span>
    </div>

    <div ref="stage" class="stage"
         @mousedown="onDown" @mousemove="onMove" @mouseup="onUp"
         @mouseleave="onUp">
      <img ref="img" :src="imageUrl" class="sheet-img" alt="整谱" draggable="false" />

      <div v-for="(b, i) in boxes" :key="i"
           class="box" :class="boxClass(b, i)" :style="boxStyle(b)"
           @mousedown.stop="startDrag($event, i)">
        <span class="idx">{{ i + 1 }}</span>
      </div>

      <div v-if="drawing" class="box drawing" :style="boxStyle(draftBox)"></div>
    </div>
  </div>
</template>

<script>
/*
 * 画布交互逻辑；操作埋点见 logger.js，后端日志统一 mlnlog。
 */
import { logInfo } from '../logger.js'

export default {
  name: 'SheetCanvas',
  props: {
    imageUrl: { type: String, default: '' },
    boxes: { type: Array, default: () => [] }
  },
  emits: ['select', 'update:boxes'],
  data() {
    return {
      selected: null,
      addMode: false,
      dragIdx: null,
      dragOff: null,
      drawing: false,
      startPt: null,
      draftBox: null
    }
  },
  methods: {
    toggleAdd() {
      this.addMode = !this.addMode
      logInfo(this.addMode ? '进入画框模式' : '退出画框模式')
    },
    norm(e) {
      const r = this.$refs.stage.getBoundingClientRect()
      return {
        x: Math.min(Math.max((e.clientX - r.left) / r.width, 0), 1),
        y: Math.min(Math.max((e.clientY - r.top) / r.height, 0), 1)
      }
    },
    boxStyle(b) {
      return {
        left: b.x * 100 + '%',
        top: b.y * 100 + '%',
        width: b.w * 100 + '%',
        height: b.h * 100 + '%'
      }
    },
    boxClass(b, i) {
      return {
        selected: i === this.selected,
        'st-a': b.status === 'A',
        'st-u': b.status === 'U',
        'st-n': !b.status
      }
    },
    onDown(e) {
      const p = this.norm(e)
      if (this.addMode) {
        this.drawing = true
        this.startPt = p
        this.draftBox = { x: p.x, y: p.y, w: 0, h: 0 }
      } else {
        this.selected = null
        this.$emit('select', null)
      }
    },
    onMove(e) {
      const p = this.norm(e)
      if (this.drawing) {
        this.draftBox = this.rectOf(this.startPt, p)
      } else if (this.dragIdx !== null) {
        const b = this.boxes[this.dragIdx]
        b.x = Math.min(Math.max(p.x - this.dragOff.x, 0), 1 - b.w)
        b.y = Math.min(Math.max(p.y - this.dragOff.y, 0), 1 - b.h)
      }
    },
    onUp() {
      if (this.drawing) {
        if (this.draftBox.w > 0.02 && this.draftBox.h > 0.02) {
          this.boxes.push({ ...this.draftBox, status: 'A' })
          logInfo('手动新增框', this.draftBox)
        }
        this.drawing = false
      }
      this.dragIdx = null
    },
    startDrag(e, i) {
      if (this.addMode) return
      const p = this.norm(e)
      const b = this.boxes[i]
      this.selected = i
      this.dragIdx = i
      this.dragOff = { x: p.x - b.x, y: p.y - b.y }
      this.$emit('select', i)
    },
    removeBox() {
      if (this.selected === null) return
      this.boxes.splice(this.selected, 1)
      this.selected = null
      this.$emit('select', null)
      logInfo('删除选中框')
    },
    rectOf(a, b) {
      return {
        x: Math.min(a.x, b.x),
        y: Math.min(a.y, b.y),
        w: Math.abs(a.x - b.x),
        h: Math.abs(a.y - b.y)
      }
    }
  }
}
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.legend { font-size: 12px; color: var(--ink-soft); display: flex; align-items: center; }
.legend i { width: 14px; height: 10px; border-radius: 2px; display: inline-block; margin: 0 4px 0 12px; }
.lg-a { background: var(--zhuqing); }
.lg-u { background: var(--zhusha); }
.lg-n { background: var(--jin); }

.stage { position: relative; width: 100%; user-select: none; }
.sheet-img { width: 100%; display: block; border-radius: 10px; border: 1px solid var(--line); }

.box { position: absolute; box-sizing: border-box; border: 1.6px solid var(--jin); cursor: move; }
.box .idx {
  position: absolute; top: -1px; left: -1px;
  background: rgba(43, 38, 32, 0.7); color: #f5efe1;
  font-size: 10px; padding: 0 5px; line-height: 15px;
}
.st-a { border-color: var(--zhuqing); }
.st-u { border-color: var(--zhusha); border-style: dashed; }
.st-n { border-color: var(--jin); }
.selected { border: 2.4px solid var(--zhusha) !important; box-shadow: 0 0 0 2px rgba(178, 58, 46, 0.22); }
.drawing { border: 1.6px dashed var(--zhusha); background: rgba(178, 58, 46, 0.08); }
</style>
