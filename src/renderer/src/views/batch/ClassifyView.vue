<script setup lang="ts">
import ToolSkeleton from '@renderer/components/ToolSkeleton.vue'
</script>

<template>
  <ToolSkeleton
    title="文件按班级/学号自动归类"
    category="批量/重复劳动类"
    description="自动扫描识别学生姓名与学号，将混杂的试卷拍照自动整理到对应班级与个人专属文件夹。"
    tech-stack="OCR + 规则分类引擎"
  />
</template>
