<script setup lang="ts">
import { ref } from 'vue'
import { CropOutline } from '@vicons/ionicons5'
import { OcrBoxLine } from '../types'

const props = defineProps<{
  imageUrl: string
  detectedLines: OcrBoxLine[]
  selectedBoxId: number | null
  cropRect: { x: number; y: number; width: number; height: number } | null
}>()

const emit = defineEmits<{
  (e: 'update:cropRect', rect: { x: number; y: number; width: number; height: number } | null): void
  (e: 'update:selectedBoxId', id: number | null): void
  (e: 'trigger-upload'): void
}>()

const imgElementRef = ref<HTMLImageElement | null>(null)
const isDrawingCrop = ref<boolean>(false)
const cropStart = ref<{ x: number; y: number } | null>(null)

const startCropDraw = (e: MouseEvent) => {
  if (!imgElementRef.value) return
  const rect = imgElementRef.value.getBoundingClientRect()
  const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width))
  const y = Math.max(0, Math.min(e.clientY - rect.top, rect.height))

  isDrawingCrop.value = true
  cropStart.value = { x, y }
  emit('update:cropRect', { x, y, width: 0, height: 0 })
}

const onCropMove = (e: MouseEvent) => {
  if (!isDrawingCrop.value || !cropStart.value || !imgElementRef.value) return
  const rect = imgElementRef.value.getBoundingClientRect()
  const currentX = Math.max(0, Math.min(e.clientX - rect.left, rect.width))
  const currentY = Math.max(0, Math.min(e.clientY - rect.top, rect.height))

  const x = Math.min(cropStart.value.x, currentX)
  const y = Math.min(cropStart.value.y, currentY)
  const width = Math.abs(currentX - cropStart.value.x)
  const height = Math.abs(currentY - cropStart.value.y)

  emit('update:cropRect', { x, y, width, height })
}

const endCropDraw = () => {
  isDrawingCrop.value = false
  if (props.cropRect && (props.cropRect.width < 10 || props.cropRect.height < 10)) {
    emit('update:cropRect', null)
  }
}

// 暴露获取自然像素选区的方法
defineExpose({
  getPixelCropBox: () => {
    if (!props.cropRect || !imgElementRef.value) return null
    const img = imgElementRef.value
    const scaleX = img.naturalWidth / img.clientWidth
    const scaleY = img.naturalHeight / img.clientHeight
    return [
      Math.round(props.cropRect.x * scaleX),
      Math.round(props.cropRect.y * scaleY),
      Math.round((props.cropRect.x + props.cropRect.width) * scaleX),
      Math.round((props.cropRect.y + props.cropRect.height) * scaleY)
    ]
  }
})
</script>

<template>
  <div class="canvas-panel">
    <div class="panel-header">
      <div class="ph-left">
        <n-icon :component="CropOutline" />
        <span class="ph-title">原图与选区 (可按住鼠标自由拉框选区)</span>
      </div>
      <div class="ph-right">
        <n-button
          v-if="cropRect"
          size="tiny"
          secondary
          type="warning"
          @click="emit('update:cropRect', null)"
        >
          取消选区 (恢复全图)
        </n-button>
        <n-button size="tiny" secondary @click="emit('trigger-upload')">更换图片</n-button>
      </div>
    </div>

    <!-- 图片展示与拉框容器 -->
    <div
      class="image-viewport-wrapper"
      @mousedown="startCropDraw"
      @mousemove="onCropMove"
      @mouseup="endCropDraw"
    >
      <div class="image-inner-container">
        <img
          ref="imgElementRef"
          :src="imageUrl"
          alt="ocr-source"
          class="ocr-source-img"
          draggable="false"
        />

        <!-- 用户手动拉取的裁剪框 -->
        <div
          v-if="cropRect"
          class="user-crop-box"
          :style="{
            left: `${cropRect.x}px`,
            top: `${cropRect.y}px`,
            width: `${cropRect.width}px`,
            height: `${cropRect.height}px`
          }"
        >
          <div class="crop-badge">选定识别区域</div>
        </div>

        <!-- PP-OCR 检测出的多边形文本框 -->
        <template v-if="detectedLines.length > 0 && imgElementRef">
          <div
            v-for="line in detectedLines"
            :key="line.id"
            class="detected-line-box"
            :class="{ 'is-selected': selectedBoxId === line.id }"
            :style="{
              left: `${(line.box[0] / imgElementRef.naturalWidth) * imgElementRef.clientWidth}px`,
              top: `${(line.box[1] / imgElementRef.naturalHeight) * imgElementRef.clientHeight}px`,
              width: `${((line.box[2] - line.box[0]) / imgElementRef.naturalWidth) * imgElementRef.clientWidth}px`,
              height: `${((line.box[3] - line.box[1]) / imgElementRef.naturalHeight) * imgElementRef.clientHeight}px`
            }"
            @click.stop="emit('update:selectedBoxId', line.id)"
          >
            <span class="box-tag">#{{ line.id }}</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.canvas-panel {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.panel-header {
  padding: 10px 14px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
}

.ph-left {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #334155;
}

.ph-title {
  font-size: 13px;
  font-weight: 600;
}

.ph-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.image-viewport-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  overflow: auto;
  padding: 16px;
  position: relative;
  user-select: none;
  cursor: crosshair;
}

.image-inner-container {
  position: relative;
  display: inline-block;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.ocr-source-img {
  max-width: 100%;
  max-height: 70vh;
  display: block;
}

.user-crop-box {
  position: absolute;
  border: 2px dashed #0284c7;
  background: rgba(2, 132, 199, 0.15);
  pointer-events: none;
  z-index: 20;
}

.crop-badge {
  position: absolute;
  top: -22px;
  left: 0;
  background: #0284c7;
  color: #ffffff;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
  white-space: nowrap;
}

.detected-line-box {
  position: absolute;
  border: 1.5px solid rgba(16, 185, 129, 0.6);
  background: rgba(16, 185, 129, 0.08);
  cursor: pointer;
  z-index: 10;
  transition: all 0.15s;
}

.detected-line-box:hover {
  border-color: #059669;
  background: rgba(16, 185, 129, 0.2);
}

.detected-line-box.is-selected {
  border-color: #2563eb;
  background: rgba(37, 99, 235, 0.25);
  z-index: 15;
}

.box-tag {
  position: absolute;
  top: -16px;
  left: 0;
  font-size: 9px;
  background: rgba(16, 185, 129, 0.9);
  color: #ffffff;
  padding: 1px 3px;
  border-radius: 2px;
}
</style>
