<script setup lang="ts">
import ToolSkeleton from '@renderer/components/ToolSkeleton.vue'
</script>

<template>
  <ToolSkeleton
    title="图片去水印"
    category="图片/文档处理类"
    description="批量清除下载课件、习题图片上的各类水印与印章，保留原图清晰度。"
    :is-mvp="true"
    tech-stack="OpenCV / lama-cleaner"
  />
</template>
