<!-- -*- coding: utf-8 -*- -->
<!--
  整谱画布组件（泠弦智谱 V2）

  显示整谱图与检测框，支持：点击选中框、拖拽移动框、
  删除框、添加模式下手动画新框。坐标全部归一化(0~1)，
  随图片缩放自适应。框线用低饱和墨色系，朱砂高亮选中。

  数据流：boxes 只读，所有修改通过 emit('update:boxes') 通知父级。
  拖拽监听挂在 window，避免鼠标划出画布时框卡死。

  作者：
      @Wujee

  创建日期：2026-10-1
  版本：2.0.0

  许可证：内部使用，未经许可不得传播。
-->

<template>
  <div class="sheet-wrap">
    <div class="toolbar">
      <el-button
        size="default"
        :type="addMode ? 'primary' : ''"
        plain
        @click="toggleAdd"
      >
        {{ addMode ? '画框中 · 拖拽作框' : '添 加 框' }}
      </el-button>
      <el-button
        size="default"
        plain
        :disabled="selected === null"
        @click="removeBox"
      >
        删 除 选 中 框
      </el-button>
      <span class="legend">
        <i class="lg-a"></i>已确认
        <i class="lg-u"></i>待复核
        <i class="lg-n"></i>未处理
      </span>
    </div>

    <div
      ref="stage"
      class="stage"
      :class="{ 'add-mode': addMode }"
      @mousedown="onDown"
    >
      <img
        ref="img"
        :src="imageUrl"
        class="sheet-img"
        alt="整谱"
        draggable="false"
      />

      <div
        v-for="(b, i) in boxes"
        :key="i"
        class="box"
        :class="boxClass(b, i)"
        :style="boxStyle(b)"
        @mousedown.stop="startDrag($event, i)"
      >
        <span class="idx">{{ i + 1 }}</span>
      </div>

      <div v-if="drawing" class="box drawing" :style="boxStyle(draftBox)"></div>
    </div>
  </div>
</template>

<script>
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
  beforeUnmount() {
    this.detachDrag()
  },
  methods: {
    toggleAdd() {
      this.addMode = !this.addMode
      if (!this.addMode) {
        this.drawing = false
        this.draftBox = null
      }
      logInfo(this.addMode ? '进入画框模式' : '退出画框模式')
    },
    norm(e) {
      const stage = this.$refs.stage
      if (!stage) return { x: 0, y: 0 }
      const r = stage.getBoundingClientRect()
      if (r.width <= 0 || r.height <= 0) return { x: 0, y: 0 }
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
    emitBoxes(next) {
      this.$emit('update:boxes', next)
    },
    onDown(e) {
      const p = this.norm(e)
      if (this.addMode) {
        this.drawing = true
        this.startPt = p
        this.draftBox = { x: p.x, y: p.y, w: 0, h: 0 }
        this.attachDrag()
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
        if (!b) return
        const nx = Math.min(Math.max(p.x - this.dragOff.x, 0), 1 - b.w)
        const ny = Math.min(Math.max(p.y - this.dragOff.y, 0), 1 - b.h)
        const next = this.boxes.slice()
        next[this.dragIdx] = { ...b, x: nx, y: ny }
        this.emitBoxes(next)
      }
    },
    onUp() {
      if (this.drawing) {
        if (this.draftBox.w > 0.02 && this.draftBox.h > 0.02) {
          const next = this.boxes.concat([{ ...this.draftBox, status: 'A' }])
          this.emitBoxes(next)
          logInfo('手动新增框', this.draftBox)
        }
        this.drawing = false
        this.draftBox = null
      }
      this.dragIdx = null
      this.detachDrag()
    },
    attachDrag() {
      window.addEventListener('mousemove', this.onMove)
      window.addEventListener('mouseup', this.onUp)
    },
    detachDrag() {
      window.removeEventListener('mousemove', this.onMove)
      window.removeEventListener('mouseup', this.onUp)
    },
    startDrag(e, i) {
      if (this.addMode) return
      const p = this.norm(e)
      const b = this.boxes[i]
      if (!b) return
      this.selected = i
      this.dragIdx = i
      this.dragOff = { x: p.x - b.x, y: p.y - b.y }
      this.$emit('select', i)
      this.attachDrag()
    },
    removeBox() {
      if (this.selected === null) return
      const next = this.boxes.filter((_, i) => i !== this.selected)
      this.emitBoxes(next)
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
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.legend {
  font-family: var(--font-brush);
  font-size: 12.5px;
  color: var(--ink-mute);
  display: flex;
  align-items: center;
  margin-left: auto;
  letter-spacing: 2px;
}
.legend i {
  width: 16px;
  height: 10px;
  display: inline-block;
  margin: 0 5px 0 14px;
  border-radius: 1px;
}
.lg-a { background: var(--huiqing); }
.lg-u { background: var(--zhusha); }
.lg-n { background: var(--gujin); }

.stage {
  position: relative;
  width: 100%;
  user-select: none;
  border: 1px solid var(--line);
  border-radius: 2px;
  background: var(--paper-warm);
  overflow: hidden;
}
.stage.add-mode { cursor: crosshair; }
.stage.add-mode .box { cursor: crosshair; }

.sheet-img {
  width: 100%;
  display: block;
  background: #fbf6e8;
}

.box {
  position: absolute;
  box-sizing: border-box;
  border: 1.4px solid var(--gujin);
  cursor: move;
  transition: box-shadow .15s ease, border-color .15s ease;
}
.box .idx {
  position: absolute;
  top: -1px;
  left: -1px;
  background: var(--ink-soft);
  color: #f3ead6;
  font-family: 'Courier New', monospace;
  font-size: 10.5px;
  padding: 0 6px;
  line-height: 15px;
  border-radius: 0 0 2px 0;
  letter-spacing: 0;
}
.st-a { border-color: var(--huiqing); }
.st-u { border-color: var(--zhusha); border-style: dashed; }
.st-n { border-color: var(--gujin); }

.selected {
  border: 2px solid var(--zhusha) !important;
  box-shadow: 0 0 0 2px rgba(156, 58, 46, 0.18);
  z-index: 2;
}

.drawing {
  border: 1.4px dashed var(--zhusha);
  background: rgba(156, 58, 46, 0.08);
  pointer-events: none;
}
</style>