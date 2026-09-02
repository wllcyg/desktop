<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  ChevronBackOutline,
  ChevronForwardOutline,
  DownloadOutline
} from '@vicons/ionicons5'
import { ImageItem } from '../types'
import { useZoomPan } from '../composables/useZoomPan'

const props = defineProps<{
  show: boolean
  currentItem: ImageItem | null
  imageList: ImageItem[]
  selectedIndex: number
  initialMode?: 'result' | 'compare' | 'original'
}>()

const emit = defineEmits<{
  (e: 'update:show', val: boolean): void
  (e: 'update:selectedIndex', index: number): void
  (e: 'save-current'): void
}>()

const previewMode = ref<'result' | 'compare' | 'original'>('result')

watch(
  () => props.show,
  (val) => {
    if (val) {
      previewMode.value = props.initialMode || 'result'
      handleZoomReset()
    }
  }
)

const {
  zoomScale,
  panX,
  panY,
  isDragging,
  handleZoomIn,
  handleZoomOut,
  handleZoomReset,
  handleViewerWheel,
  handleMouseDown,
  handleMouseMove,
  handleMouseUp,
  handleDoubleClick
} = useZoomPan(1)

const prevImage = () => {
  if (props.selectedIndex > 0) {
    emit('update:selectedIndex', props.selectedIndex - 1)
    handleZoomReset()
  }
}

const nextImage = () => {
  if (props.selectedIndex < props.imageList.length - 1) {
    emit('update:selectedIndex', props.selectedIndex + 1)
    handleZoomReset()
  }
}
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    style="width: 92vw; max-width: 1400px; height: 90vh; border-radius: 16px; display: flex; flex-direction: column;"
    content-style="flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 0; overflow: hidden;"
    :bordered="false"
    size="small"
    :segmented="{ content: true, footer: true }"
    @update:show="(v) => emit('update:show', v)"
  >
    <template #header>
      <div class="modal-header-box">
        <div class="m-left">
          <span class="m-title">{{ currentItem?.name }}</span>
          <n-tag v-if="currentItem?.status === 'done'" type="success" size="tiny" round>
            去水印完成
          </n-tag>
          <span class="m-counter">({{ selectedIndex + 1 }} / {{ imageList.length }})</span>
        </div>

        <!-- 模式切换 -->
        <div class="m-center">
          <n-radio-group v-model:value="previewMode" size="small">
            <n-radio-button value="result" :disabled="!currentItem?.resultUrl">
              ✨ 去水印高清效果
            </n-radio-button>
            <n-radio-button value="compare" :disabled="!currentItem?.resultUrl">
              🌗 左右双屏对比
            </n-radio-button>
            <n-radio-button value="original">
              📄 原始图片
            </n-radio-button>
          </n-radio-group>
        </div>

        <!-- 缩放控制与单张下载 -->
        <div class="m-right">
          <n-button-group size="tiny">
            <n-button secondary @click="handleZoomOut">- 缩小</n-button>
            <n-button secondary @click="handleZoomReset">{{ Math.round(zoomScale * 100) }}%</n-button>
            <n-button secondary @click="handleZoomIn">+ 放大</n-button>
          </n-button-group>

          <n-button
            v-if="currentItem?.resultUrl"
            type="primary"
            size="tiny"
            @click="emit('save-current')"
          >
            <template #icon><n-icon :component="DownloadOutline" /></template>
            下载本图
          </n-button>
        </div>
      </div>
    </template>

    <!-- 弹窗主视口 -->
    <div
      class="modal-viewer-body"
      :class="{ 'is-grabbing': isDragging, 'is-zoomed': zoomScale > 1 }"
      @wheel="handleViewerWheel"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseUp"
      @dblclick="handleDoubleClick"
    >
      <button
        v-if="imageList.length > 1"
        class="nav-btn prev-btn"
        :disabled="selectedIndex === 0"
        title="上一张图片 (←)"
        @click.stop="prevImage"
      >
        <n-icon size="24" :component="ChevronBackOutline" />
      </button>

      <!-- 模式 1：去水印高清结果图 -->
      <div v-if="previewMode === 'result'" class="single-viewer-container">
        <div
          class="zoomable-wrapper"
          :style="{ transform: `translate(${panX}px, ${panY}px) scale(${zoomScale})` }"
        >
          <img
            v-if="currentItem?.resultUrl"
            :src="currentItem.resultUrl"
            class="modal-main-img"
            alt="result-large"
            draggable="false"
          />
        </div>
      </div>

      <!-- 模式 2：左右双屏对比 -->
      <div v-else-if="previewMode === 'compare'" class="compare-viewer-container">
        <div class="half-screen">
          <div class="screen-badge original-badge">原图</div>
          <div
            class="zoomable-wrapper"
            :style="{ transform: `translate(${panX}px, ${panY}px) scale(${zoomScale})` }"
          >
            <img
              v-if="currentItem?.previewUrl"
              :src="currentItem.previewUrl"
              class="modal-main-img"
              alt="original-large"
              draggable="false"
            />
          </div>
        </div>
        <div class="screen-divider" />
        <div class="half-screen">
          <div class="screen-badge result-badge">去水印效果</div>
          <div
            class="zoomable-wrapper"
            :style="{ transform: `translate(${panX}px, ${panY}px) scale(${zoomScale})` }"
          >
            <img
              v-if="currentItem?.resultUrl"
              :src="currentItem.resultUrl"
              class="modal-main-img"
              alt="result-large"
              draggable="false"
            />
          </div>
        </div>
      </div>

      <!-- 模式 3：原始图片 -->
      <div v-else class="single-viewer-container">
        <div
          class="zoomable-wrapper"
          :style="{ transform: `translate(${panX}px, ${panY}px) scale(${zoomScale})` }"
        >
          <img
            v-if="currentItem?.previewUrl"
            :src="currentItem.previewUrl"
            class="modal-main-img"
            alt="original-large"
            draggable="false"
          />
        </div>
      </div>

      <button
        v-if="imageList.length > 1"
        class="nav-btn next-btn"
        :disabled="selectedIndex === imageList.length - 1"
        title="下一张图片 (→)"
        @click.stop="nextImage"
      >
        <n-icon size="24" :component="ChevronForwardOutline" />
      </button>
    </div>
  </n-modal>
</template>

<style scoped>
.modal-header-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.m-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.m-title {
  font-size: 14px;
  font-weight: 600;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.m-counter {
  font-size: 12px;
  color: #94a3b8;
}

.m-center {
  display: flex;
  align-items: center;
}

.m-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-viewer-body {
  flex: 1;
  width: 100%;
  height: 100%;
  position: relative;
  background: #0f172a;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  cursor: grab;
}

.modal-viewer-body.is-grabbing {
  cursor: grabbing;
}

.single-viewer-container,
.compare-viewer-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.half-screen {
  flex: 1;
  height: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.screen-divider {
  width: 2px;
  height: 100%;
  background: rgba(255, 255, 255, 0.15);
  z-index: 10;
}

.screen-badge {
  position: absolute;
  top: 14px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  z-index: 20;
  backdrop-filter: blur(8px);
}

.original-badge {
  left: 14px;
  background: rgba(0, 0, 0, 0.6);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.result-badge {
  right: 14px;
  background: rgba(16, 185, 129, 0.8);
  color: #ffffff;
}

.zoomable-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.05s ease-out;
  will-change: transform;
}

.modal-main-img {
  max-width: 90%;
  max-height: 80vh;
  object-fit: contain;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  border-radius: 4px;
}

.nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.4);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 30;
  transition: all 0.2s;
  backdrop-filter: blur(4px);
}

.nav-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.8);
  transform: translateY(-50%) scale(1.1);
}

.nav-btn:disabled {
  opacity: 0.2;
  cursor: not-allowed;
}

.prev-btn {
  left: 16px;
}

.next-btn {
  right: 16px;
}
</style>
