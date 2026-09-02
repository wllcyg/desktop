<script setup lang="ts">
import ToolSkeleton from '@renderer/components/ToolSkeleton.vue'
</script>

<template>
  <ToolSkeleton
    title="文件批量重命名"
    category="批量/重复劳动类"
    description="按班级、学号、姓名、考试名称规则，批量规范重命名试卷照片、作业与教案文件。"
    :is-mvp="true"
    tech-stack="Python os / pathlib"
  />
</template>
