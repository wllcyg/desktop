<script setup lang="ts">
import ToolSkeleton from '@renderer/components/ToolSkeleton.vue'
</script>

<template>
  <ToolSkeleton
    title="PDF 转 Word"
    category="图片/文档处理类"
    description="将教辅、试卷等 PDF 文档高质量转换为可编辑的 Word (.docx) 文件，排版尽量保持一致。"
    :is-mvp="true"
    tech-stack="PyMuPDF / pdfplumber"
  />
</template>
