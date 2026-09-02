<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import {
  NButton,
  NButtonGroup,
  NIcon,
  NTooltip,
  NSpin
} from 'naive-ui'
import {
  ScanOutline,
  EyeOutline,
  ContractOutline
} from '@vicons/ionicons5'
import { ImageItem, ActiveToolType, CropRect } from '../types'
import { usePixiApp } from '../composables/usePixiApp'

const props = defineProps<{
  activeItem: ImageItem | null
  activeTool: ActiveToolType
  brushSize: number
  isProcessing: boolean
}>()

const emit = defineEmits<{
  (e: 'mask-drawn'): void
  (e: 'crop-change', crop: CropRect | undefined): void
  (e: 'update-recipe'): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const isComparing = ref(false)
const isDragging = ref(false)
const isDrawingMask = ref(false)
const isSpacePressed = ref(false)
const panOffset = ref({ x: 0, y: 0 })
const startDragPos = ref({ x: 0, y: 0 })

const {
  isInitialized,
  zoomLevel,
  currentImageDims,
  rootContainer,
  initApp,
  resizeViewport,
  loadImage,
  clearImage,
  applyRecipe,
  beginInpaintStroke,
  drawInpaintBrush,
  clearInpaintMask,
  exportInpaintMaskBase64,
  exportBlob,
  destroyApp
} = usePixiApp()

// 监听活动项与图片切换 (支持列表点击切换与原图变更)
watch(
  () => [props.activeItem?.id, props.activeItem?.originalUrl] as const,
  async ([newId, newUrl]) => {
    if (newId && newUrl && isInitialized.value) {
      try {
        await loadImage(newUrl)
        fitToScreen()
        if (props.activeItem) {
          applyRecipe(props.activeItem.recipe)
        }
      } catch (err) {
        console.error('加载图片纹理失败:', err)
      }
    } else if (!newId && isInitialized.value) {
      clearImage()
    }
  }
)

// 监听配方更新
watch(
  () => props.activeItem?.recipe,
  (newRecipe) => {
    if (newRecipe && isInitialized.value) {
      applyRecipe(newRecipe, isComparing.value)
    }
  },
  { deep: true }
)

// 监听原图对比
watch(isComparing, (val) => {
  if (props.activeItem && isInitialized.value) {
    applyRecipe(props.activeItem.recipe, val)
  }
})

// 空格键监听 (支持去水印涂抹模式下按住空格漫游画布)
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
  if (e.code === 'Space' && !e.repeat) {
    e.preventDefault()
    isSpacePressed.value = true
  }
}

const handleKeyUp = (e: KeyboardEvent) => {
  if (e.code === 'Space') {
    isSpacePressed.value = false
  }
}

const handleWindowBlur = () => {
  isSpacePressed.value = false
  isDragging.value = false
}

onMounted(async () => {
  if (canvasRef.value && containerRef.value) {
    const width = containerRef.value.clientWidth || 800
    const height = containerRef.value.clientHeight || 600
    await initApp(canvasRef.value, width, height)

    if (props.activeItem?.originalUrl) {
      try {
        await loadImage(props.activeItem.originalUrl)
        fitToScreen()
        applyRecipe(props.activeItem.recipe)
      } catch (err) {
        console.error('初始化加载图片失败:', err)
      }
    }

    window.addEventListener('resize', handleResize)
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    window.addEventListener('blur', handleWindowBlur)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('keyup', handleKeyUp)
  window.removeEventListener('blur', handleWindowBlur)
  destroyApp()
})

const handleResize = () => {
  if (containerRef.value) {
    resizeViewport(containerRef.value.clientWidth, containerRef.value.clientHeight)
  }
}

// 缩放控制
const handleWheel = (e: WheelEvent) => {
  e.preventDefault()
  const delta = e.deltaY < 0 ? 1.1 : 0.9
  const newZoom = Math.min(Math.max(zoomLevel.value * delta, 0.1), 16)
  zoomLevel.value = parseFloat(newZoom.toFixed(2))
  if (rootContainer) {
    rootContainer.scale.set(zoomLevel.value)
  }
}

// 适应屏幕
const fitToScreen = () => {
  if (!containerRef.value || !currentImageDims.value.width) return
  const cW = containerRef.value.clientWidth - 80
  const cH = containerRef.value.clientHeight - 80
  const scale = Math.min(cW / currentImageDims.value.width, cH / currentImageDims.value.height, 1)
  zoomLevel.value = parseFloat(scale.toFixed(2))
  panOffset.value = { x: 0, y: 0 }
  if (rootContainer) {
    rootContainer.position.set(containerRef.value.clientWidth / 2, containerRef.value.clientHeight / 2)
    rootContainer.scale.set(zoomLevel.value)
  }
}

const resetZoom100 = () => {
  zoomLevel.value = 1.0
  if (rootContainer && containerRef.value) {
    rootContainer.scale.set(1.0)
    rootContainer.position.set(containerRef.value.clientWidth / 2, containerRef.value.clientHeight / 2)
  }
}

// 鼠标交互 (平移 / AI涂抹)
const handleMouseDown = (e: MouseEvent) => {
  // 满足中键按下、按住空格、或非涂抹工具时 -> 抓手平移
  if (e.button === 1 || isSpacePressed.value || props.activeTool !== 'watermark-clean') {
    isDragging.value = true
    startDragPos.value = { x: e.clientX - panOffset.value.x, y: e.clientY - panOffset.value.y }
  } else if (props.activeTool === 'watermark-clean' && e.button === 0) {
    // 涂抹 AI Mask
    isDrawingMask.value = true
    beginInpaintStroke()
    recordBrushPoint(e)
  }
}

const handleMouseMove = (e: MouseEvent) => {
  if (isDragging.value) {
    panOffset.value = {
      x: e.clientX - startDragPos.value.x,
      y: e.clientY - startDragPos.value.y
    }
    if (rootContainer && containerRef.value) {
      rootContainer.position.set(
        containerRef.value.clientWidth / 2 + panOffset.value.x,
        containerRef.value.clientHeight / 2 + panOffset.value.y
      )
    }
  } else if (isDrawingMask.value) {
    recordBrushPoint(e)
  }
}

const handleMouseUp = () => {
  if (isDrawingMask.value) {
    emit('mask-drawn')
  }
  isDragging.value = false
  isDrawingMask.value = false
}

const recordBrushPoint = (e: MouseEvent) => {
  if (!canvasRef.value || !rootContainer) return
  const rect = canvasRef.value.getBoundingClientRect()
  const mouseX = e.clientX - rect.left - rootContainer.x
  const mouseY = e.clientY - rect.top - rootContainer.y
  const localX = mouseX / zoomLevel.value
  const localY = mouseY / zoomLevel.value
  drawInpaintBrush(localX, localY, props.brushSize / 2)
}

defineExpose({
  clearImage,
  clearInpaintMask,
  exportInpaintMaskBase64,
  exportBlob,
  fitToScreen
})
</script>

<template>
  <div
    ref="containerRef"
    class="editor-canvas-container"
    :class="{
      'cursor-space-grab': isSpacePressed && !isDragging,
      'cursor-space-grabbing': isSpacePressed && isDragging,
      'cursor-inpaint': activeTool === 'watermark-clean' && !isSpacePressed,
      'cursor-grab': activeTool !== 'watermark-clean' && !isDragging && !isSpacePressed,
      'cursor-grabbing': activeTool !== 'watermark-clean' && isDragging && !isSpacePressed
    }"
    @wheel="handleWheel"
    @mousedown="handleMouseDown"
    @mousemove="handleMouseMove"
    @mouseup="handleMouseUp"
    @mouseleave="handleMouseUp"
  >
    <!-- 空状态 -->
    <div v-if="!activeItem" class="empty-placeholder">
      <div class="empty-icon-wrap">
        <n-icon size="44" color="#0284c7">
          <ScanOutline />
        </n-icon>
      </div>
      <p class="empty-text">请在左侧列表导入或选择一张图片开始编辑</p>
    </div>

    <!-- WebGL Canvas -->
    <canvas ref="canvasRef" class="pixi-canvas" />

    <!-- 浮动视口工具栏 -->
    <div v-if="activeItem" class="floating-controls">
      <n-button-group size="small">
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button
              :type="isComparing ? 'primary' : 'default'"
              @mousedown="isComparing = true"
              @mouseup="isComparing = false"
              @mouseleave="isComparing = false"
            >
              <template #icon>
                <n-icon><EyeOutline /></n-icon>
              </template>
              按住对比原图
            </n-button>
          </template>
          按住鼠标查看未经处理的原始图片
        </n-tooltip>

        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button @click="fitToScreen">
              <template #icon>
                <n-icon><ContractOutline /></n-icon>
              </template>
              适应画布
            </n-button>
          </template>
          缩放至适合屏幕大小
        </n-tooltip>

        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button @click="resetZoom100">
              {{ Math.round(zoomLevel * 100) }}%
            </n-button>
          </template>
          重置为 100% 原始比例
        </n-tooltip>
      </n-button-group>
    </div>

    <!-- 底部状态指示 -->
    <div v-if="activeItem" class="canvas-statusbar">
      <span class="status-name">{{ activeItem.name }}</span>
      <span class="divider">|</span>
      <span>尺寸: {{ currentImageDims.width }} × {{ currentImageDims.height }}</span>
      <span class="divider">|</span>
      <span class="status-engine">WebGL GPU 加速 (60FPS)</span>
    </div>

    <!-- 处理中蒙版 -->
    <div v-if="isProcessing" class="loading-overlay">
      <n-spin size="large" description="AI 正在处理与渲染中..." />
    </div>
  </div>
</template>

<style scoped>
.editor-canvas-container {
  position: relative;
  width: 100%;
  height: 100%;
  background-color: #f1f5f9;
  background-image: radial-gradient(#cbd5e1 1px, transparent 1px);
  background-size: 18px 18px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
}

.cursor-space-grab {
  cursor: grab !important;
}

.cursor-space-grabbing {
  cursor: grabbing !important;
}

.cursor-inpaint {
  cursor: crosshair;
}

.cursor-grab {
  cursor: grab;
}

.cursor-grabbing {
  cursor: grabbing;
}

.pixi-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.empty-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #64748b;
  z-index: 5;
}

.empty-icon-wrap {
  width: 76px;
  height: 76px;
  border-radius: 18px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.empty-text {
  font-size: 14px;
  font-weight: 500;
}

.floating-controls {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid #e2e8f0;
  padding: 4px;
  border-radius: 8px;
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.canvas-statusbar {
  position: absolute;
  bottom: 12px;
  left: 16px;
  font-size: 12px;
  color: #334155;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border: 1px solid #e2e8f0;
  padding: 5px 12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 10;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.status-name {
  font-weight: 600;
  color: #0f172a;
}

.status-engine {
  color: #0284c7;
  font-weight: 500;
}

.divider {
  color: #cbd5e1;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}
</style>
