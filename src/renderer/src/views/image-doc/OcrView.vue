<script setup lang="ts">
import ToolSkeleton from '@renderer/components/ToolSkeleton.vue'
</script>

<template>
  <ToolSkeleton
    title="图片转文字 / 公式识别 (OCR)"
    category="图片/文档处理类"
    description="拍照的化学方程式、试卷题目、分子结构式快速转换为可编辑文字或 LaTeX 公式。"
    :is-mvp="true"
    tech-stack="PaddleOCR / RapidOCR"
  />
</template>
