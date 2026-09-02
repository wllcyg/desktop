<script setup lang="ts">
interface Props {
  title: string
  category: string
  description: string
  tags?: string[]
  isMvp?: boolean
  techStack?: string
}

withDefaults(defineProps<Props>(), {
  tags: () => [],
  isMvp: false,
  techStack: ''
})
</script>

<template>
  <div class="tool-skeleton-container">
    <!-- 头部信息卡片 -->
    <div class="tool-header-card">
      <div class="header-main">
        <div class="title-row">
          <h1 class="tool-title">{{ title }}</h1>
          <n-tag v-if="isMvp" type="success" size="small" round> 第一期 MVP </n-tag>
          <n-tag type="info" size="small" round> {{ category }} </n-tag>
        </div>
        <p class="tool-desc">{{ description }}</p>
      </div>
      <div v-if="techStack" class="tech-badge">
        <span class="tech-label">核心技术:</span>
        <n-tag size="small" :bordered="false" type="warning">{{ techStack }}</n-tag>
      </div>
    </div>

    <!-- 主工作区框架轮廓 -->
    <div class="tool-body">
      <slot>
        <div class="tool-placeholder-canvas">
          <n-card class="placeholder-card" :bordered="false">
            <n-empty
              description="模块框架已就绪 / 等待接入业务与 Python 处理逻辑"
              size="large"
            >
              <template #extra>
                <div class="placeholder-info">
                  <n-text depth="3">
                    当前处于基础架构搭建阶段，后续将根据 PRD 逐步实现统一拖拽处理模式。
                  </n-text>
                </div>
              </template>
            </n-empty>
          </n-card>
        </div>
      </slot>
    </div>
  </div>
</template>

<style scoped>
.tool-skeleton-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.tool-header-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 18px 24px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.03);
}

.header-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tool-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #0f172a;
}

.tool-desc {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.tech-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8fafc;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
}

.tech-label {
  font-size: 12px;
  color: #94a3b8;
}

.tool-body {
  flex: 1;
  min-height: 0;
}

.placeholder-card {
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px dashed #cbd5e1;
  background: #ffffff;
}

.placeholder-info {
  margin-top: 8px;
  font-size: 12px;
}
</style>
