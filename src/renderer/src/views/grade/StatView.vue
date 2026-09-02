<script setup lang="ts">
import ToolSkeleton from '@renderer/components/ToolSkeleton.vue'
</script>

<template>
  <ToolSkeleton
    title="成绩单自动统计"
    category="成绩与数据统计类"
    description="导入考试原始 Excel 成绩表，自动计算年级/班级均分、及格率、优秀率、排名与分数段分布。"
    tech-stack="pandas + openpyxl"
  />
</template>
