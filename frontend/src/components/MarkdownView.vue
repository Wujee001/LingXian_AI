<!-- -*- coding: utf-8 -*- -->
<!--
  只读 Markdown 渲染

  后端已在保存时用 nh3 移除 HTML 标签，此处 MdPreview 只渲染
  纯 Markdown，双重保障公开内容不执行脚本。

  作者：@zlxaaa
  创建日期：2026-10-18
  版本：1.0.0
-->
<template>
  <MdPreview :modelValue="content" previewTheme="github" />
</template>

<script setup>
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'

defineProps({
  content: { type: String, default: '' },
})
</script>