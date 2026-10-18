<!-- -*- coding: utf-8 -*- -->
<!--
  Markdown 编辑器封装

  作者：@zlxaaa
  创建日期：2026-10-18
  版本：1.0.0
-->
<template>
  <div class="note-editor">
    <MdEditor v-model="content" :toolbars="toolbars" :preview="true" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'

const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const content = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const toolbars = [
  'bold', 'italic', 'strikeThrough', 'title', 'quote',
  'unorderedList', 'orderedList', 'code', 'link', 'table', '-',
  'revoke', 'next', 'preview', 'fullscreen', 'catalog',
]
</script>

<style scoped>
.note-editor { border: 1px solid var(--line); border-radius: 2px; }
.note-editor :deep(.md-editor) { --md-bk-color: var(--xuan-card); }
</style>