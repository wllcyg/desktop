<script setup lang="ts">
import {
  NButton,
  NIcon,
  NSelect,
  NTooltip,
  NPopconfirm
} from 'naive-ui'
import {
  FlashOutline,
  DownloadOutline,
  ImageOutline
} from '@vicons/ionicons5'
import { ExportSettings } from '../types'

const props = defineProps<{
  itemCount: number
  exportSettings: ExportSettings
  isExporting: boolean
}>()

const emit = defineEmits<{
  (e: 'sync-all'): void
  (e: 'start-batch-export'): void
  (e: 'update:exportFormat', format: 'image/jpeg' | 'image/png' | 'image/webp'): void
  (e: 'update:exportQuality', quality: number): void
}>()

const formatOptions = [
  { label: 'JPG (相片/试卷)', value: 'image/jpeg' },
  { label: 'PNG (无损透明)', value: 'image/png' },
  { label: 'WebP (极小体积)', value: 'image/webp' }
]

const qualityOptions = [
  { label: '100% 极高画质', value: 1.0 },
  { label: '90% 高清推荐', value: 0.9 },
  { label: '75% 网页平衡', value: 0.75 },
  { label: '50% 极限压缩', value: 0.5 }
]
</script>

<template>
  <div class="batch-action-toolbar">
    <div class="toolbar-left">
      <div class="studio-logo">
        <div class="logo-icon-wrap">
          <n-icon size="18" color="#0284c7"><ImageOutline /></n-icon>
        </div>
        <div class="logo-text-wrap">
          <span class="title">图片工作台</span>
          <span class="sub-tag">Image Studio</span>
        </div>
      </div>
    </div>

    <div class="toolbar-right">
      <!-- 格式选择 -->
      <div class="setting-item">
        <span class="label">导出格式</span>
        <n-select
          :value="exportSettings.format"
          :options="formatOptions"
          size="small"
          style="width: 145px"
          @update:value="(val) => emit('update:exportFormat', val)"
        />
      </div>

      <!-- 质量选择 -->
      <div class="setting-item">
        <span class="label">画质</span>
        <n-select
          :value="exportSettings.quality"
          :options="qualityOptions"
          size="small"
          style="width: 135px"
          @update:value="(val) => emit('update:exportQuality', val)"
        />
      </div>

      <!-- 一键同步全部按钮 -->
      <n-popconfirm
        :disabled="itemCount <= 1"
        @positive-click="emit('sync-all')"
      >
        <template #trigger>
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button
                secondary
                type="warning"
                size="small"
                :disabled="itemCount <= 1 || isExporting"
              >
                <template #icon><n-icon><FlashOutline /></n-icon></template>
                一键同步至所有图片
              </n-button>
            </template>
            将当前图片已配置的滤镜、去水印与尺寸调整同步应用到列表中的所有图片
          </n-tooltip>
        </template>
        确定要将当前编辑配方应用至列表中的全部 {{ itemCount }} 张图片吗？
      </n-popconfirm>

      <!-- 批量导出按钮 -->
      <n-button
        type="primary"
        size="small"
        :disabled="itemCount === 0 || isExporting"
        :loading="isExporting"
        @click="emit('start-batch-export')"
      >
        <template #icon><n-icon><DownloadOutline /></n-icon></template>
        批量导出全部 ({{ itemCount }})
      </n-button>
    </div>
  </div>
</template>

<style scoped>
.batch-action-toolbar {
  height: 54px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  user-select: none;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
}

.toolbar-left {
  display: flex;
  align-items: center;
}

.studio-logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.studio-logo .title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.studio-logo .sub-tag {
  font-size: 11px;
  font-weight: 600;
  color: #0284c7;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  padding: 2px 7px;
  border-radius: 6px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.setting-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.setting-item .label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}
</style>
