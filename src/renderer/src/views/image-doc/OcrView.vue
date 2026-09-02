<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import {
  SparklesOutline,
  CloudUploadOutline,
  AddOutline,
  TrashOutline,
  FlaskOutline,
  ScanOutline
} from '@vicons/ionicons5'
import { OcrBoxLine, fileToBase64 } from './ocr/types'
import OcrCropper from './ocr/components/OcrCropper.vue'
import OcrResultPanel from './ocr/components/OcrResultPanel.vue'

const message = useMessage()

// 状态
const imageFile = ref<File | null>(null)
const imageUrl = ref<string>('')
const isProcessing = ref<boolean>(false)
const ocrMode = ref<'chemistry' | 'math' | 'general'>('chemistry')
const useDocres = ref<boolean>(true)

// 识别结果
const detectedLines = ref<OcrBoxLine[]>([])
const fullText = ref<string>('')
const fullLatex = ref<string>('')
const executionTime = ref<number>(0)
const selectedBoxId = ref<number | null>(null)

// 选区与裁剪
const cropRect = ref<{ x: number; y: number; width: number; height: number } | null>(null)
const cropperRef = ref<InstanceType<typeof OcrCropper> | null>(null)

// 加载图片
const handleFileSelect = (files: FileList | null) => {
  if (!files || files.length === 0) return
  const file = files[0]
  if (!file.type.startsWith('image/')) {
    message.warning('请选择有效的图片文件')
    return
  }

  if (imageUrl.value && imageUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(imageUrl.value)
  }

  imageFile.value = file
  imageUrl.value = URL.createObjectURL(file)
  detectedLines.value = []
  fullText.value = ''
  fullLatex.value = ''
  cropRect.value = null
  selectedBoxId.value = null

  // 自动触发识别
  runOcr()
}

// 粘贴板截图监听 (Ctrl+V)
const handlePaste = (e: ClipboardEvent) => {
  const items = e.clipboardData?.items
  if (!items) return

  for (let i = 0; i < items.length; i++) {
    if (items[i].type.startsWith('image/')) {
      const file = items[i].getAsFile()
      if (file) {
        message.info('已捕获剪贴板截图')
        handleFileSelect([file] as unknown as FileList)
        break
      }
    }
  }
}

// 拖拽上传
const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  handleFileSelect(e.dataTransfer?.files ?? null)
}

const fileInputRef = ref<HTMLInputElement | null>(null)
const triggerFileInput = () => {
  fileInputRef.value?.click()
}

const clearAll = () => {
  if (imageUrl.value && imageUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(imageUrl.value)
  }
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
  imageFile.value = null
  imageUrl.value = ''
  detectedLines.value = []
  fullText.value = ''
  fullLatex.value = ''
  cropRect.value = null
  selectedBoxId.value = null
}

// 执行 OCR 识别
const runOcr = async () => {
  if (!imageFile.value) {
    message.warning('请先选择或粘贴图片')
    return
  }

  isProcessing.value = true
  try {
    const base64Str = await fileToBase64(imageFile.value)
    const crop_box = cropperRef.value?.getPixelCropBox() ?? null

    // @ts-ignore
    if (window.electron?.ipcRenderer) {
      // @ts-ignore
      const res = await window.electron.ipcRenderer.invoke('py:call', {
        method: 'ocr.recognize',
        params: {
          image: base64Str,
          crop_box,
          mode: ocrMode.value,
          use_docres: useDocres.value
        }
      })

      if (res?.success) {
        detectedLines.value = res.lines || []
        fullText.value = res.full_text || ''
        fullLatex.value = res.full_latex || ''
        executionTime.value = res.cost_ms || 0
        message.success(`识别完成！检出 ${detectedLines.value.length} 处文本/公式 (耗时: ${res.cost_ms}ms)`)
      } else {
        throw new Error(res?.error || '识别服务异常')
      }
    }
  } catch (err: any) {
    message.error(err?.message || '识别失败')
  } finally {
    isProcessing.value = false
  }
}

// 快速体验样例
const loadDemoChemistry = async () => {
  const canvas = document.createElement('canvas')
  canvas.width = 700
  canvas.height = 240
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  ctx.fillStyle = '#1e293b'
  ctx.font = 'bold 24px "Segoe UI", "Microsoft YaHei", sans-serif'
  ctx.fillText('1. 高锰酸钾制氧气反应方程式：', 30, 55)

  ctx.font = '28px "Consolas", "Segoe UI", sans-serif'
  ctx.fillStyle = '#0369a1'
  ctx.fillText('2KMnO4 =(△)=> K2MnO4 + MnO2 + O2↑', 40, 115)

  ctx.fillStyle = '#1e293b'
  ctx.font = '24px "Segoe UI", "Microsoft YaHei", sans-serif'
  ctx.fillText('2. 硫酸铁与氢氧化钠沉淀反应：', 30, 175)

  ctx.font = '28px "Consolas", "Segoe UI", sans-serif'
  ctx.fillStyle = '#0369a1'
  ctx.fillText('Fe2(SO4)3 + 6NaOH = 2Fe(OH)3↓ + 3Na2SO4', 40, 225)

  canvas.toBlob((blob) => {
    if (blob) {
      const file = new File([blob], '化学试题方程式样例.png', { type: 'image/png' })
      handleFileSelect([file] as unknown as FileList)
    }
  })
}

onMounted(() => {
  window.addEventListener('paste', handlePaste)
})

onUnmounted(() => {
  window.removeEventListener('paste', handlePaste)
  if (imageUrl.value && imageUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(imageUrl.value)
  }
})
</script>

<template>
  <div class="ocr-page">
    <input
      ref="fileInputRef"
      type="file"
      accept="image/*"
      style="display: none"
      @change="
        (e) => {
          handleFileSelect((e.target as HTMLInputElement).files)
          ;(e.target as HTMLInputElement).value = ''
        }
      "
    />

    <!-- 顶部状态与工具栏 -->
    <div class="top-bar">
      <div class="bar-left">
        <h1 class="bar-title">试卷转文字 / 公式识别 (OCR)</h1>
        <n-tag type="info" size="small" round>
          <template #icon><n-icon :component="FlaskOutline" /></template>
          初中化学 & 数学公式专项
        </n-tag>
        <n-tag type="success" size="small" round>
          <template #icon><n-icon :component="ScanOutline" /></template>
          PP-OCRv4 + LaTeX 引擎
        </n-tag>
      </div>

      <div class="bar-right">
        <!-- 识别模式选择 -->
        <n-radio-group v-model:value="ocrMode" size="small">
          <n-radio-button value="chemistry">🧪 化学方程式</n-radio-button>
          <n-radio-button value="math">📐 数学公式</n-radio-button>
          <n-radio-button value="general">📄 通用试题文本</n-radio-button>
        </n-radio-group>

        <!-- DocRes 光影净化开关 -->
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-checkbox v-model:checked="useDocres" class="docres-checkbox">
              ✨ DocRes 光影增强
            </n-checkbox>
          </template>
          自动抹平手机拍照的手部死黑阴影与暗角折痕，大幅提升公式上下标识别率
        </n-tooltip>

        <n-button
          v-if="imageUrl"
          type="primary"
          size="small"
          :loading="isProcessing"
          @click="runOcr"
        >
          <template #icon><n-icon :component="SparklesOutline" /></template>
          重新识别
        </n-button>

        <n-button
          v-if="imageUrl"
          quaternary
          size="small"
          type="error"
          @click="clearAll"
        >
          <template #icon><n-icon :component="TrashOutline" /></template>
          清空
        </n-button>
      </div>
    </div>

    <!-- 主工作区 -->
    <div class="main-layout">
      <!-- 空状态 -->
      <div
        v-if="!imageUrl"
        class="empty-drop-container"
        @drop="handleDrop"
        @dragover.prevent
        @click="triggerFileInput"
      >
        <div class="empty-content">
          <n-icon size="64" color="#0284c7" :component="CloudUploadOutline" />
          <div class="empty-title">点击、拖拽或按 Ctrl+V 粘贴试题截图</div>
          <div class="empty-desc">
            支持手机拍摄的试卷题目、课件配图、手写/印刷化学方程式及数学公式 (JPG / PNG / WebP)
          </div>
          <div class="empty-actions" @click.stop>
            <n-button type="primary" size="large" class="upload-btn" @click="triggerFileInput">
              <template #icon><n-icon :component="AddOutline" /></template>
              选择图片文件
            </n-button>
            <n-button secondary size="large" @click="loadDemoChemistry">
              <template #icon><n-icon :component="FlaskOutline" /></template>
              试一试化学方程式样例
            </n-button>
          </div>
        </div>
      </div>

      <!-- 双栏识别工作台 -->
      <div v-else class="workspace-grid">
        <!-- 左栏：原图视口与自由框选画布 -->
        <OcrCropper
          ref="cropperRef"
          :image-url="imageUrl"
          :detected-lines="detectedLines"
          :selected-box-id="selectedBoxId"
          :crop-rect="cropRect"
          @update:crop-rect="(r) => (cropRect = r)"
          @update:selected-box-id="(id) => (selectedBoxId = id)"
          @trigger-upload="triggerFileInput"
        />

        <!-- 右栏：多格式识别结果展示区 -->
        <OcrResultPanel
          :detected-lines="detectedLines"
          :full-text="fullText"
          :full-latex="fullLatex"
          :execution-time="executionTime"
          :selected-box-id="selectedBoxId"
          :is-processing="isProcessing"
          @update:selected-box-id="(id) => (selectedBoxId = id)"
          @update:full-latex="(val) => (fullLatex = val)"
          @update:full-text="(val) => (fullText = val)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.ocr-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: #f8fafc;
  padding: 16px 20px 20px 20px;
  box-sizing: border-box;
  overflow: hidden;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.bar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.docres-checkbox {
  font-size: 12px;
  color: #475569;
}

.main-layout {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.empty-drop-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.empty-drop-container:hover {
  border-color: #0284c7;
  background: #f0f9ff;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  max-width: 500px;
  text-align: center;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.empty-desc {
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.empty-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.workspace-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
</style>
