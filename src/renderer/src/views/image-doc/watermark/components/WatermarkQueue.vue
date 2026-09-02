<script setup lang="ts">
import { computed } from 'vue'
import {
  SparklesOutline,
  DownloadOutline,
  AddOutline,
  CloseOutline,
  ImagesOutline,
  CheckmarkCircleOutline,
  AlertCircleOutline
} from '@vicons/ionicons5'
import { ImageItem } from '../types'

const props = defineProps<{
  imageList: ImageItem[]
  selectedIndex: number
  isBatchProcessing: boolean
  isExporting: boolean
}>()

const emit = defineEmits<{
  (e: 'update:selectedIndex', index: number): void
  (e: 'start-batch'): void
  (e: 'save-all'): void
  (e: 'trigger-upload'): void
  (e: 'remove-item', index: number, ev: Event): void
}>()

const completedCount = computed(() => {
  return props.imageList.filter((item) => item.status === 'done').length
})
</script>

<template>
  <div class="sidebar-panel">
    <!-- 批量操作按钮区 -->
    <div class="action-card">
      <n-button
        type="primary"
        block
        size="large"
        class="glow-button"
        :loading="isBatchProcessing"
        @click="emit('start-batch')"
      >
        <template #icon>
          <n-icon :component="SparklesOutline" />
        </template>
        智能一键去水印 ({{ imageList.length }} 张)
      </n-button>

      <!-- 显著的一键下载全部按钮 -->
      <n-button
        v-if="completedCount > 0"
        type="success"
        block
        size="medium"
        class="download-all-btn"
        :loading="isExporting"
        @click="emit('save-all')"
      >
        <template #icon>
          <n-icon :component="DownloadOutline" />
        </template>
        一键导出全部图片 ({{ completedCount }})
      </n-button>

      <div class="btn-row">
        <n-button
          secondary
          block
          :disabled="isBatchProcessing"
          @click="emit('trigger-upload')"
        >
          <template #icon>
            <n-icon :component="AddOutline" />
          </template>
          添加更多
        </n-button>
      </div>
    </div>

    <!-- 图片队列列表 -->
    <div class="queue-list-container">
      <div class="queue-header">
        <div class="queue-title-row">
          <n-icon :component="ImagesOutline" />
          <span class="queue-title">图片列表 ({{ imageList.length }})</span>
        </div>
        <span class="queue-count">已完成: {{ completedCount }}/{{ imageList.length }}</span>
      </div>

      <div class="queue-scroll">
        <div
          v-for="(item, index) in imageList"
          :key="item.id"
          class="queue-item"
          :class="{ 'is-selected': selectedIndex === index }"
          @click="emit('update:selectedIndex', index)"
        >
          <div class="thumb-box">
            <img :src="item.resultUrl || item.previewUrl" alt="thumb" />
          </div>
          <div class="item-info">
            <span class="item-name" :title="item.name">{{ item.name }}</span>
            <div class="item-status">
              <n-tag v-if="item.status === 'done'" size="tiny" type="success" round>
                <template #icon><n-icon :component="CheckmarkCircleOutline" /></template>
                已完成
              </n-tag>
              <n-tag v-else-if="item.status === 'processing'" size="tiny" type="info" round>
                处理中...
              </n-tag>
              <n-tag v-else-if="item.status === 'error'" size="tiny" type="error" round>
                <template #icon><n-icon :component="AlertCircleOutline" /></template>
                失败
              </n-tag>
              <n-tag v-else size="tiny" depth="3" round>待处理</n-tag>
            </div>
          </div>
          <n-button
            quaternary
            circle
            size="tiny"
            class="del-btn"
            @click="(e) => emit('remove-item', index, e)"
          >
            <template #icon>
              <n-icon :component="CloseOutline" />
            </template>
          </n-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sidebar-panel {
  width: 280px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-shrink: 0;
  height: 100%;
}

.action-card {
  background: #ffffff;
  border-radius: 10px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.glow-button {
  font-weight: 600;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border: none;
}

.download-all-btn {
  font-weight: 600;
}

.btn-row {
  display: flex;
  gap: 8px;
}

.queue-list-container {
  flex: 1;
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.queue-header {
  padding: 10px 14px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
}

.queue-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #334155;
}

.queue-title {
  font-size: 13px;
  font-weight: 600;
}

.queue-count {
  font-size: 11px;
  color: #64748b;
}

.queue-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
  background: #fcfcfc;
  cursor: pointer;
  transition: all 0.15s ease;
}

.queue-item:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.queue-item.is-selected {
  background: #eff6ff;
  border-color: #93c5fd;
}

.thumb-box {
  width: 42px;
  height: 42px;
  border-radius: 6px;
  overflow: hidden;
  background: #f1f5f9;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.thumb-box img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.item-name {
  font-size: 12px;
  font-weight: 500;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-status {
  display: flex;
}

.del-btn {
  opacity: 0.5;
  transition: opacity 0.15s;
}

.del-btn:hover {
  opacity: 1;
}
</style>
