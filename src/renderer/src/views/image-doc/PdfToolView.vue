<script setup lang="ts">
import { ref } from 'vue'
import { GitMergeOutline, GitCommitOutline, GridOutline, LayersOutline } from '@vicons/ionicons5'
import PdfMergePanel from './pdf/PdfMergePanel.vue'
import PdfSplitPanel from './pdf/PdfSplitPanel.vue'
import PdfOrganizePanel from './pdf/PdfOrganizePanel.vue'

// 激活的子标签页
const activeTab = ref<'merge' | 'split' | 'organize'>('merge')
</script>

<template>
  <div class="pdf-tool-container">
    <!-- 顶部标题与模式切换 -->
    <div class="header-section">
      <div class="header-title-group">
        <div class="icon-wrapper">
          <n-icon size="26" color="#3B82F6">
            <LayersOutline />
          </n-icon>
        </div>
        <div>
          <h1 class="main-title">PDF 拆分与合并工具箱</h1>
          <p class="subtitle">高性能原生极速处理 · 矢量无损保真 · 支持多文件拼接、规则拆分与页面重排</p>
        </div>
      </div>

      <n-tabs v-model:value="activeTab" type="segment" class="mode-tabs">
        <n-tab name="merge">
          <div class="tab-label">
            <n-icon size="16"><GitMergeOutline /></n-icon>
            <span>多文件合并 (Merge)</span>
          </div>
        </n-tab>
        <n-tab name="split">
          <div class="tab-label">
            <n-icon size="16"><GitCommitOutline /></n-icon>
            <span>规则拆分 (Split)</span>
          </div>
        </n-tab>
        <n-tab name="organize">
          <div class="tab-label">
            <n-icon size="16"><GridOutline /></n-icon>
            <span>可视化重排 (Organize)</span>
          </div>
        </n-tab>
      </n-tabs>
    </div>

    <!-- 主体区域切换 -->
    <div class="content-body">
      <PdfMergePanel v-if="activeTab === 'merge'" />
      <PdfSplitPanel v-else-if="activeTab === 'split'" />
      <PdfOrganizePanel v-else-if="activeTab === 'organize'" />
    </div>
  </div>
</template>

<style scoped>
.pdf-tool-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background-color: #f8fafc;
  padding: 16px 20px 20px 20px;
  box-sizing: border-box;
  overflow: hidden;
}

.header-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.header-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  display: flex;
  align-items: center;
  justify-content: center;
}

.main-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.subtitle {
  margin: 2px 0 0 0;
  font-size: 12px;
  color: #64748b;
}

.mode-tabs {
  width: 440px;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.content-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>
