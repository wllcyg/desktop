<script setup lang="ts">
import { ref } from 'vue'
import {
  NButton,
  NIcon,
  NTag,
  NTooltip,
  NPopconfirm
} from 'naive-ui'
import {
  AddOutline,
  TrashOutline,
  CheckmarkCircle,
  CloseCircle,
  ImagesOutline
} from '@vicons/ionicons5'
import { ImageItem } from '../types'

const props = defineProps<{
  items: ImageItem[]
  activeId: string | null
}>()

const emit = defineEmits<{
  (e: 'select-item', id: string): void
  (e: 'add-files', files: FileList | File[]): void
  (e: 'remove-item', id: string): void
  (e: 'clear-all'): void
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const isDraggingOver = ref(false)

const triggerFileInput = () => {
  fileInputRef.value?.click()
}

const handleFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    emit('add-files', target.files)
    target.value = ''
  }
}

const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  isDraggingOver.value = false
  if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
    emit('add-files', e.dataTransfer.files)
  }
}

const formatSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const getRecipeBadges = (item: ImageItem): string[] => {
  const badges: string[] = []
  const r = item.recipe
  if (r.filterPreset !== 'none') badges.push('滤镜')
  if (r.rotation !== 0) badges.push(`${r.rotation}°`)
  if (r.watermarkClean?.cleanFaintWatermark || r.watermarkClean?.cleanRedStamp) badges.push('去水印')
  if (r.watermark?.enabled) badges.push('水印')
  if (r.resize?.enabled) badges.push('缩放')
  return badges
}
</script>

<template>
  <div
    class="image-queue-sidebar"
    :class="{ 'drag-over': isDraggingOver }"
    @dragover.prevent="isDraggingOver = true"
    @dragleave.prevent="isDraggingOver = false"
    @drop="handleDrop"
  >
    <!-- 头部操作栏 -->
    <div class="sidebar-header">
      <div class="header-title">
        <n-icon size="16" color="#0284c7"><ImagesOutline /></n-icon>
        <span>待处理 ({{ items.length }})</span>
      </div>

      <div class="header-actions">
        <n-button size="tiny" type="primary" secondary @click="triggerFileInput">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          添加
        </n-button>

        <n-popconfirm v-if="items.length > 0" @positive-click="emit('clear-all')">
          <template #trigger>
            <n-button size="tiny" quaternary type="error">清空</n-button>
          </template>
          确认清空待处理图片列表吗？
        </n-popconfirm>
      </div>

      <input
        ref="fileInputRef"
        type="file"
        multiple
        accept="image/png,image/jpeg,image/webp,image/bmp"
        style="display: none"
        @change="handleFileChange"
      />
    </div>

    <!-- 列表容器 -->
    <div class="queue-list">
      <div
        v-for="item in items"
        :key="item.id"
        class="queue-item"
        :class="{ active: item.id === activeId }"
        @click="emit('select-item', item.id)"
      >
        <div class="thumb-wrap">
          <img :src="item.previewUrl" :alt="item.name" class="thumb-img" />
          <div v-if="item.status === 'done'" class="status-badge done">
            <n-icon color="#10b981"><CheckmarkCircle /></n-icon>
          </div>
          <div v-else-if="item.status === 'error'" class="status-badge error">
            <n-icon color="#ef4444"><CloseCircle /></n-icon>
          </div>
        </div>

        <div class="item-info">
          <span class="item-name" :title="item.name">{{ item.name }}</span>
          <div class="item-meta">
            <span class="file-size">{{ formatSize(item.sizeBytes) }}</span>
            <div class="badge-list">
              <n-tag
                v-for="(b, idx) in getRecipeBadges(item)"
                :key="idx"
                size="tiny"
                type="info"
                round
                :bordered="false"
              >
                {{ b }}
              </n-tag>
            </div>
          </div>
        </div>

        <div class="item-actions" @click.stop>
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button quaternary circle size="tiny" type="error" @click="emit('remove-item', item.id)">
                <template #icon><n-icon><TrashOutline /></n-icon></template>
              </n-button>
            </template>
            移除此项
          </n-tooltip>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="items.length === 0" class="queue-empty" @click="triggerFileInput">
        <div class="empty-icon-box">
          <n-icon size="24" color="#0284c7"><ImagesOutline /></n-icon>
        </div>
        <p class="empty-title">拖拽多张图片到这里</p>
        <p class="empty-sub">或点击上方【添加】按钮</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.image-queue-sidebar {
  width: 260px;
  height: 100%;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  user-select: none;
  transition: all 0.2s ease;
}

.image-queue-sidebar.drag-over {
  background: #f0f9ff;
  border-right-color: #0284c7;
}

.sidebar-header {
  padding: 12px 14px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.queue-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.queue-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.queue-item:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.queue-item.active {
  background: #f0f9ff;
  border-color: #0284c7;
  box-shadow: 0 0 0 1px #0284c7;
}

.thumb-wrap {
  position: relative;
  width: 50px;
  height: 50px;
  border-radius: 6px;
  overflow: hidden;
  background: #e2e8f0;
  border: 1px solid #cbd5e1;
  flex-shrink: 0;
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.status-badge {
  position: absolute;
  bottom: 2px;
  right: 2px;
  font-size: 14px;
  line-height: 1;
  background: #ffffff;
  border-radius: 50%;
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
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-meta {
  font-size: 11px;
  color: #64748b;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-size {
  color: #94a3b8;
}

.badge-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.item-actions {
  opacity: 0;
  transition: opacity 0.2s ease;
}

.queue-item:hover .item-actions {
  opacity: 1;
}

.queue-empty {
  margin-top: 50px;
  border: 1px dashed #cbd5e1;
  background: #f8fafc;
  border-radius: 12px;
  padding: 26px 16px;
  text-align: center;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.queue-empty:hover {
  border-color: #0284c7;
  background: #f0f9ff;
  color: #0284c7;
}

.empty-icon-box {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 10px auto;
}

.empty-title {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 4px 0;
}

.empty-sub {
  font-size: 11px;
  margin: 0;
  color: #94a3b8;
}
</style>
