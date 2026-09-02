<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import {
  SparklesOutline,
  CopyOutline,
  CloudUploadOutline,
  AddOutline,
  TrashOutline,
  DocumentTextOutline,
  FlaskOutline,
  CropOutline,
  ScanOutline
} from '@vicons/ionicons5'

const message = useMessage()

interface OcrBoxLine {
  id: number
  box: number[] // [x1, y1, x2, y2]
  raw_text: string
  formatted_text: string
  latex: string
  latex_inline: string
  mathml: string
  is_equation: boolean
}

// 状态
const imageFile = ref<File | null>(null)
const imageUrl = ref<string>('')
const isProcessing = ref<boolean>(false)
const ocrMode = ref<'chemistry' | 'math' | 'general'>('chemistry')
const useDocres = ref<boolean>(true)
const activeTab = ref<'visual' | 'latex' | 'word' | 'text'>('visual')

// 识别结果
const detectedLines = ref<OcrBoxLine[]>([])
const fullText = ref<string>('')
const fullLatex = ref<string>('')
const executionTime = ref<number>(0)
const selectedBoxId = ref<number | null>(null)

// 选区与裁剪 (用户自由拖拽拉框)
const isDrawingCrop = ref<boolean>(false)
const cropStart = ref<{ x: number; y: number } | null>(null)
const cropRect = ref<{ x: number; y: number; width: number; height: number } | null>(null)
const imgElementRef = ref<HTMLImageElement | null>(null)

// 复制状态提示
const copiedKey = ref<string>('')
const copyToClipboard = async (text: string, key: string, label = '内容') => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    copiedKey.value = key
    message.success(`已复制 ${label} 到剪贴板`)
    setTimeout(() => {
      if (copiedKey.value === key) copiedKey.value = ''
    }, 2000)
  } catch (err) {
    message.error('复制失败，请手动选择复制')
  }
}

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

const handleDragOver = (e: DragEvent) => {
  e.preventDefault()
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

// 将 File 转为 Base64
const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
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

    // 计算实际图片像素坐标选区
    let crop_box: number[] | null = null
    if (cropRect.value && imgElementRef.value) {
      const img = imgElementRef.value
      const scaleX = img.naturalWidth / img.clientWidth
      const scaleY = img.naturalHeight / img.clientHeight

      crop_box = [
        Math.round(cropRect.value.x * scaleX),
        Math.round(cropRect.value.y * scaleY),
        Math.round((cropRect.value.x + cropRect.value.width) * scaleX),
        Math.round((cropRect.value.y + cropRect.value.height) * scaleY)
      ]
    }

    if (window.electron?.ipcRenderer) {
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
        message.success(
          `识别完成！检出 ${detectedLines.value.length} 处文本/公式 (耗时: ${res.cost_ms}ms)`
        )
      } else {
        throw new Error(res?.error || '识别服务异常')
      }
    } else {
      // 演示模拟响应
      setTimeout(() => {
        const demoEquation = '2KMnO4 =(△)=> K2MnO4 + MnO2 + O2↑'
        detectedLines.value = [
          {
            id: 1,
            box: [20, 30, 300, 70],
            raw_text: demoEquation,
            formatted_text: '2KMnO₄  =(△)=>  K₂MnO₄ ⁺ MnO₂ ⁺ O₂↑',
            latex: '2KMn\\text{O}_{4} \\xrightarrow{\\Delta} \\text{K}_{2}Mn\\text{O}_{4} + Mn\\text{O}_{2} + \\text{O}_{2} \\uparrow',
            latex_inline: '$2KMn\\text{O}_{4} \\xrightarrow{\\Delta} \\text{K}_{2}Mn\\text{O}_{4} + Mn\\text{O}_{2} + \\text{O}_{2} \\uparrow$',
            mathml: '<math xmlns="http://www.w3.org/1998/Math/MathML"><mtext>2KMnO4 =(△)=> K2MnO4 + MnO2 + O2↑</mtext></math>',
            is_equation: true
          }
        ]
        fullText.value = '2KMnO₄  =(△)=>  K₂MnO₄ ⁺ MnO₂ ⁺ O₂↑'
        fullLatex.value = '$$2KMn\\text{O}_{4} \\xrightarrow{\\Delta} \\text{K}_{2}Mn\\text{O}_{4} + Mn\\text{O}_{2} + \\text{O}_{2} \\uparrow$$'
        executionTime.value = 120
      }, 500)
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

// 鼠标自由拉框交互
const startCropDraw = (e: MouseEvent) => {
  if (!imgElementRef.value) return
  const rect = imgElementRef.value.getBoundingClientRect()
  const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width))
  const y = Math.max(0, Math.min(e.clientY - rect.top, rect.height))

  isDrawingCrop.value = true
  cropStart.value = { x, y }
  cropRect.value = { x, y, width: 0, height: 0 }
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

  cropRect.value = { x, y, width, height }
}

const endCropDraw = () => {
  isDrawingCrop.value = false
  if (cropRect.value && (cropRect.value.width < 10 || cropRect.value.height < 10)) {
    cropRect.value = null // 太小视为误点，清除
  }
}

// 挂载剪贴板监听
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
          class="glow-btn"
          :loading="isProcessing"
          @click="runOcr"
        >
          <template #icon><n-icon :component="SparklesOutline" /></template>
          {{ cropRect ? '识别当前选区' : '一键全图识别' }}
        </n-button>

        <n-button v-if="imageUrl" size="small" quaternary type="error" @click="clearAll">
          <template #icon><n-icon :component="TrashOutline" /></template>
          清空
        </n-button>
      </div>
    </div>

    <!-- 主工作区 -->
    <div class="main-layout">
      <!-- 空状态：拖拽或粘贴区域 -->
      <div
        v-if="!imageUrl"
        class="empty-drop-container"
        @drop="handleDrop"
        @dragover="handleDragOver"
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
                @click="cropRect = null"
              >
                取消选区 (恢复全图)
              </n-button>
              <n-button size="tiny" secondary @click="triggerFileInput">更换图片</n-button>
            </div>
          </div>

          <!-- 图片展示与拉框容器 -->
          <div
            ref="imageContainerRef"
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
                  @click.stop="selectedBoxId = line.id"
                >
                  <span class="box-tag">#{{ line.id }}</span>
                </div>
              </template>
            </div>
          </div>
        </div>

        <!-- 右栏：多格式识别结果展示区 -->
        <div class="result-panel">
          <div class="panel-header">
            <div class="ph-left">
              <n-tabs v-model:value="activeTab" type="segment" size="small">
                <n-tab name="visual">🧪 格式排版渲染</n-tab>
                <n-tab name="latex">📝 LaTeX 源码</n-tab>
                <n-tab name="word">📘 Word 公式 (MathML)</n-tab>
                <n-tab name="text">📋 Markdown/纯文本</n-tab>
              </n-tabs>
            </div>
            <div class="ph-right">
              <span v-if="executionTime > 0" class="time-tag">耗时: {{ executionTime }}ms</span>
            </div>
          </div>

          <!-- 结果展示主体 -->
          <div class="result-content-body">
            <!-- Loading 骨架遮罩 -->
            <div v-if="isProcessing" class="loading-overlay">
              <n-spin size="large" />
              <span class="loading-tip">正在执行 PP-OCR 检测与公式深度解析...</span>
            </div>

            <!-- Tab 1: 格式排版可视化渲染 -->
            <div v-else-if="activeTab === 'visual'" class="tab-scroll-view">
              <div v-if="detectedLines.length === 0" class="empty-result-tip">
                <n-icon size="48" color="#94a3b8" :component="DocumentTextOutline" />
                <span>点击上方【一键识别】或拉框截取题目</span>
              </div>

              <div v-else class="formula-cards-list">
                <div
                  v-for="line in detectedLines"
                  :key="line.id"
                  class="formula-card"
                  :class="{ 'card-highlight': selectedBoxId === line.id }"
                  @mouseenter="selectedBoxId = line.id"
                  @mouseleave="selectedBoxId = null"
                >
                  <div class="card-top-bar">
                    <span class="line-badge">#{{ line.id }}</span>
                    <n-tag v-if="line.is_equation" size="tiny" type="info" round>方程式</n-tag>
                    <n-tag v-else size="tiny" depth="3" round>文本</n-tag>

                    <div class="card-btn-group">
                      <n-button
                        size="tiny"
                        quaternary
                        type="primary"
                        @click="copyToClipboard(line.latex, `latex_${line.id}`, 'LaTeX 代码')"
                      >
                        <template #icon><n-icon :component="CopyOutline" /></template>
                        复制 LaTeX
                      </n-button>
                      <n-button
                        size="tiny"
                        quaternary
                        type="info"
                        @click="copyToClipboard(line.mathml, `word_${line.id}`, 'Word 兼容公式')"
                      >
                        <template #icon><n-icon :component="CopyOutline" /></template>
                        复制 Word 格式
                      </n-button>
                      <n-button
                        size="tiny"
                        quaternary
                        @click="copyToClipboard(line.formatted_text, `txt_${line.id}`, '文本')"
                      >
                        <template #icon><n-icon :component="CopyOutline" /></template>
                        复制文本
                      </n-button>
                    </div>
                  </div>

                  <!-- 渲染展示区 (美化化学式与上下标) -->
                  <div class="rendered-equation-box">
                    <div class="math-render-text">{{ line.formatted_text }}</div>
                  </div>

                  <!-- 对应的 LaTeX 预览 -->
                  <div class="latex-snippet-box">
                    <code>{{ line.latex }}</code>
                  </div>
                </div>
              </div>
            </div>

            <!-- Tab 2: LaTeX 源码视图 -->
            <div v-else-if="activeTab === 'latex'" class="tab-code-view">
              <div class="code-action-bar">
                <span class="code-desc">标准 LaTeX 方程式源码 (支持直接插入 Overleaf / 课件)</span>
                <n-button
                  size="small"
                  type="primary"
                  @click="copyToClipboard(fullLatex, 'full_latex', '全部 LaTeX 代码')"
                >
                  <template #icon><n-icon :component="CopyOutline" /></template>
                  一键复制全文 LaTeX
                </n-button>
              </div>
              <textarea v-model="fullLatex" class="code-editor" spellcheck="false" />
            </div>

            <!-- Tab 3: Word 兼容 MathML 视图 -->
            <div v-else-if="activeTab === 'word'" class="tab-code-view">
              <div class="code-action-bar">
                <span class="code-desc">Microsoft Word 兼容格式 (点击复制后在 Word 中直接 Ctrl+V 粘贴为原生公式)</span>
                <n-button
                  size="small"
                  type="info"
                  @click="copyToClipboard(detectedLines.map(l => l.mathml).join('\n\n'), 'full_mathml', 'Word 公式代码')"
                >
                  <template #icon><n-icon :component="CopyOutline" /></template>
                  一键复制 Word 公式
                </n-button>
              </div>
              <div class="word-guide-box">
                <div class="guide-title">📌 Word 粘贴使用指南：</div>
                <div class="guide-step">1. 点击上方【一键复制 Word 公式】</div>
                <div class="guide-step">2. 打开 Microsoft Word 或 PPT，按下 <kbd>Ctrl + V</kbd> 粘贴</div>
                <div class="guide-step">3. Word 会自动识别并弹出转换为原生可编辑公式对象！</div>
              </div>
            </div>

            <!-- Tab 4: Markdown / 纯文本视图 -->
            <div v-else-if="activeTab === 'text'" class="tab-code-view">
              <div class="code-action-bar">
                <span class="code-desc">Markdown / Unicode 美化文本 (带化学上下标与反应条件)</span>
                <n-button
                  size="small"
                  type="primary"
                  @click="copyToClipboard(fullText, 'full_text', '全部文本')"
                >
                  <template #icon><n-icon :component="CopyOutline" /></template>
                  一键复制全文
                </n-button>
              </div>
              <textarea v-model="fullText" class="code-editor" spellcheck="false" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ocr-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
}

/* 顶部状态栏 */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);
}

.bar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
}

.bar-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.docres-checkbox {
  font-size: 13px;
  font-weight: 500;
  color: #334155;
}

.glow-btn {
  font-weight: 600;
  box-shadow: 0 4px 12px -2px rgba(2, 132, 199, 0.35);
}

/* 主内容区 */
.main-layout {
  flex: 1;
  min-height: 0;
}

/* 空状态拖拽区 */
.empty-drop-container {
  height: 100%;
  min-height: 480px;
  border: 2px dashed #cbd5e1;
  border-radius: 16px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.empty-drop-container:hover {
  border-color: #38bdf8;
  background: #f8fafc;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
  max-width: 480px;
  padding: 24px;
}

.empty-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}

.empty-desc {
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
}

.empty-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}

/* 工作台双栏布局 */
.workspace-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  height: 100%;
}

/* 左侧原图视口与画布 */
.canvas-panel {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 10px 16px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
}

.ph-left {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.ph-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-tag {
  font-size: 11px;
  color: #0284c7;
  background: #e0f2fe;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.image-viewport-wrapper {
  flex: 1;
  min-height: 0;
  background: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  padding: 16px;
  user-select: none;
  cursor: crosshair;
}

.image-inner-container {
  position: relative;
  display: inline-block;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
  border-radius: 4px;
}

.ocr-source-img {
  display: block;
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  pointer-events: none;
}

/* 选区与标注框样式 */
.user-crop-box {
  position: absolute;
  border: 2px dashed #38bdf8;
  background: rgba(56, 189, 248, 0.2);
  pointer-events: none;
  z-index: 10;
}

.crop-badge {
  position: absolute;
  top: -24px;
  left: 0;
  background: #0284c7;
  color: #ffffff;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

.detected-line-box {
  position: absolute;
  border: 1.5px solid rgba(34, 197, 94, 0.85);
  background: rgba(34, 197, 94, 0.12);
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.15s ease;
  z-index: 5;
}

.detected-line-box:hover,
.detected-line-box.is-selected {
  border-color: #f59e0b;
  background: rgba(245, 158, 11, 0.25);
  z-index: 8;
}

.box-tag {
  position: absolute;
  top: -16px;
  left: 0;
  background: #16a34a;
  color: #ffffff;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 2px;
}

/* 右侧结果视口 */
.result-panel {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.result-content-body {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(2px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  z-index: 20;
}

.loading-tip {
  font-size: 13px;
  color: #0284c7;
  font-weight: 600;
}

.tab-scroll-view {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
}

.empty-result-tip {
  height: 100%;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #94a3b8;
  font-size: 13px;
}

/* 公式卡片列表 */
.formula-cards-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.formula-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s ease;
}

.formula-card:hover,
.formula-card.card-highlight {
  border-color: #38bdf8;
  background: #f0f9ff;
  box-shadow: 0 4px 14px rgba(2, 132, 199, 0.1);
}

.card-top-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.line-badge {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
}

.card-btn-group {
  margin-left: auto;
  display: flex;
  gap: 4px;
}

.rendered-equation-box {
  padding: 10px 14px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
}

.math-render-text {
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
  letter-spacing: 0.5px;
  font-family: 'Cambria Math', 'Consolas', 'Segoe UI', serif;
}

.latex-snippet-box {
  background: rgba(15, 23, 42, 0.04);
  padding: 4px 8px;
  border-radius: 6px;
}

.latex-snippet-box code {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  color: #475569;
  word-break: break-all;
}

/* 源码编辑器样式 */
.tab-code-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 14px;
  gap: 10px;
  height: 100%;
}

.code-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.code-desc {
  font-size: 12px;
  color: #64748b;
}

.code-editor {
  flex: 1;
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #0f172a;
  resize: none;
  outline: none;
}

.code-editor:focus {
  border-color: #0284c7;
  background: #ffffff;
}

/* Word 指南 */
.word-guide-box {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.guide-title {
  font-size: 14px;
  font-weight: 700;
  color: #0369a1;
}

.guide-step {
  font-size: 13px;
  color: #334155;
}

.guide-step kbd {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 12px;
  font-family: monospace;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
</style>
