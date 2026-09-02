<script setup lang="ts">
import { ref } from 'vue'
import { useMessage } from 'naive-ui'

const message = useMessage()

// 文件与图片状态
const fileList = ref<File[]>([])
const currentImage = ref<string | null>(null)
const resultImage = ref<string | null>(null)
const filePath = ref<string>('')
const isProcessing = ref(false)

// 去水印参数
const threshold = ref(200)
const contrast = ref(1.5)
const denoise = ref(true)
// 默认使用最优秀的背景归一化算法
const mode = ref<string>('bg_normalize')
const inpaintRadius = ref(5)
const inpaintMethod = ref<string>('telea')

// 当前操作模式
const activeTab = ref<string>('tile')

// 处理文件上传
const handleFileSelect = (files: FileList | null) => {
  if (!files || files.length === 0) return
  const file = files[0]
  if (!file.type.startsWith('image/')) {
    message.warning('请上传图片文件')
    return
  }
  fileList.value = [file]
  // 获取 Electron 本地文件绝对路径（如果有）
  filePath.value = (file as any).path || ''

  const reader = new FileReader()
  reader.onload = (e) => {
    currentImage.value = e.target?.result as string
    resultImage.value = null
  }
  reader.readAsDataURL(file)
}

// 拖拽上传
const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  handleFileSelect(e.dataTransfer?.files ?? null)
}

const handleDragOver = (e: DragEvent) => {
  e.preventDefault()
}

// 点击选择文件
const fileInput = ref<HTMLInputElement | null>(null)
const triggerFileSelect = () => {
  fileInput.value?.click()
}

// 执行去平铺水印
const removeTileWatermark = async () => {
  if (!currentImage.value) {
    message.warning('请先上传图片')
    return
  }

  isProcessing.value = true
  try {
    // 优先使用本地文件路径（速度最快），否则回退到 base64
    const inputSource = filePath.value || currentImage.value

    const res = await window.electron.ipcRenderer.invoke('py:call', {
      method: 'watermark.remove_tile',
      params: {
        input: inputSource,
        threshold: threshold.value,
        contrast: contrast.value,
        denoise: denoise.value,
        mode: mode.value
      }
    })

    if (res?.image_base64) {
      resultImage.value = res.image_base64
      message.success('去水印完成')
    } else {
      throw new Error('未收到处理结果')
    }
  } catch (err: any) {
    message.error(err?.message || '去水印失败，请检查 Python 依赖是否安装')
  } finally {
    isProcessing.value = false
  }
}

// 保存结果图片
const saveResult = () => {
  if (!resultImage.value) return
  const a = document.createElement('a')
  a.href = resultImage.value
  a.download = `去水印_${fileList.value[0]?.name || 'result.png'}`
  a.click()
  message.success('图片已保存')
}

// 模式选项
const modeOptions = [
  { label: '✨ 智能背景归一化 (扫描全能王算法，平铺水印推荐)', value: 'bg_normalize' },
  { label: '🔴 红色印章 / 批改红叉消除 (色彩差分算法)', value: 'remove_red' },
  { label: '📄 标准二值化 (黑白试卷)', value: 'binary' },
  { label: '📱 自适应局部阈值 (拍照试卷)', value: 'adaptive' },
  { label: '🎨 色彩通道过滤 (浅蓝/彩色水印)', value: 'color_filter' }
]

const methodOptions = [
  { label: 'Telea 快速修补 (推荐)', value: 'telea' },
  { label: 'Navier-Stokes 流体扩散', value: 'ns' }
]
</script>

<template>
  <div class="watermark-workspace">
    <!-- 顶部工具信息栏 -->
    <div class="tool-header">
      <div class="header-left">
        <h1 class="tool-title">图片去水印</h1>
        <n-tag type="success" size="small" round>MVP</n-tag>
        <n-tag type="info" size="small" round>图片/文档处理</n-tag>
      </div>
      <p class="tool-desc">
        批量清除下载课件、习题图片上的水印。支持试卷平铺浅色文字水印消除与局部涂抹修补两种模式。
      </p>
    </div>

    <!-- 模式切换标签页 -->
    <n-tabs v-model:value="activeTab" type="segment" animated>
      <n-tab-pane name="tile" tab="📄 文档平铺水印消除">
        <div class="workspace-grid">
          <!-- 左侧：参数控制面板 -->
          <div class="control-panel">
            <n-card size="small" :bordered="false" class="param-card">
              <n-space vertical :size="16">
                <div class="param-group">
                  <div class="param-label">处理模式</div>
                  <n-select v-model:value="mode" :options="modeOptions" />
                </div>

                <div class="param-group">
                  <div class="param-label">
                    去水印强度
                    <n-text depth="3" class="param-hint">值越小去得越干净</n-text>
                  </div>
                  <n-slider v-model:value="threshold" :min="100" :max="250" :step="5" />
                  <n-input-number v-model:value="threshold" :min="100" :max="250" size="small" />
                </div>

                <div class="param-group">
                  <div class="param-label">
                    对比度增强
                    <n-text depth="3" class="param-hint">增强文字清晰度</n-text>
                  </div>
                  <n-slider v-model:value="contrast" :min="1.0" :max="3.0" :step="0.1" />
                  <n-input-number v-model:value="contrast" :min="1.0" :max="3.0" :step="0.1" size="small" />
                </div>

                <div class="param-group">
                  <n-checkbox v-model:checked="denoise">降噪平滑（去除孤立杂点）</n-checkbox>
                </div>

                <n-button
                  type="primary"
                  block
                  :loading="isProcessing"
                  :disabled="!currentImage"
                  @click="removeTileWatermark"
                >
                  一键去水印
                </n-button>

                <n-button
                  v-if="resultImage"
                  secondary
                  block
                  @click="saveResult"
                >
                  保存结果图片
                </n-button>
              </n-space>
            </n-card>
          </div>

          <!-- 右侧：图片预览区 -->
          <div class="preview-area">
            <!-- 上传区 -->
            <div
              v-if="!currentImage"
              class="drop-zone"
              @drop="handleDrop"
              @dragover="handleDragOver"
              @click="triggerFileSelect"
            >
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                style="display: none"
                @change="(e) => handleFileSelect((e.target as HTMLInputElement).files)"
              >
              <div class="drop-content">
                <div class="drop-icon">📂</div>
                <div class="drop-text">点击或拖拽图片到此处</div>
                <div class="drop-hint">支持 JPG / PNG / BMP / WebP 格式</div>
              </div>
            </div>

            <!-- 对比预览 -->
            <div v-else class="compare-container">
              <div class="image-panel">
                <div class="panel-label">原始图片</div>
                <div class="image-wrapper">
                  <img :src="currentImage" alt="原始图片" />
                </div>
                <n-button size="small" quaternary @click="triggerFileSelect">
                  更换图片
                </n-button>
                <input
                  ref="fileInput"
                  type="file"
                  accept="image/*"
                  style="display: none"
                  @change="(e) => handleFileSelect((e.target as HTMLInputElement).files)"
                >
              </div>

              <div class="image-panel">
                <div class="panel-label">处理结果</div>
                <div class="image-wrapper">
                  <img v-if="resultImage" :src="resultImage" alt="处理结果" />
                  <div v-else class="result-placeholder">
                    <n-spin v-if="isProcessing" size="large" />
                    <span v-else>等待处理...</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </n-tab-pane>

      <n-tab-pane name="inpaint" tab="🎯 画笔涂抹修补">
        <div class="workspace-grid">
          <!-- 左侧：修补参数 -->
          <div class="control-panel">
            <n-card size="small" :bordered="false" class="param-card">
              <n-space vertical :size="16">
                <div class="param-group">
                  <div class="param-label">修补算法</div>
                  <n-select v-model:value="inpaintMethod" :options="methodOptions" />
                </div>

                <div class="param-group">
                  <div class="param-label">修补半径</div>
                  <n-slider v-model:value="inpaintRadius" :min="1" :max="20" :step="1" />
                  <n-input-number v-model:value="inpaintRadius" :min="1" :max="20" size="small" />
                </div>

                <n-alert type="info" :bordered="false">
                  交互式画布画笔功能正在开发中，当前阶段请先使用"文档平铺水印消除"模式。后续版本将支持直接在图片上涂抹标记水印区域进行精准修补。
                </n-alert>
              </n-space>
            </n-card>
          </div>

          <!-- 右侧：交互画布占位 -->
          <div class="preview-area">
            <div class="drop-zone inpaint-placeholder">
              <div class="drop-content">
                <div class="drop-icon">🎨</div>
                <div class="drop-text">交互式画布涂抹修补</div>
                <div class="drop-hint">
                  画笔功能即将上线：上传图片 → 用画笔涂抹标记 LOGO / 印章 / 二维码区域 → 一键修补
                </div>
              </div>
            </div>
          </div>
        </div>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<style scoped>
.watermark-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.tool-header {
  padding: 18px 24px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.03);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
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

.workspace-grid {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  margin-top: 12px;
}

.control-panel {
  display: flex;
  flex-direction: column;
}

.param-card {
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid rgba(226, 232, 240, 0.8);
}

.param-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-label {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.param-hint {
  font-size: 11px;
  font-weight: 400;
}

.preview-area {
  min-height: 400px;
}

.drop-zone {
  min-height: 400px;
  border: 2px dashed #cbd5e1;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #fafbfc;
  transition: all 0.2s;
}

.drop-zone:hover {
  border-color: #0284c7;
  background: #f0f9ff;
}

.drop-content {
  text-align: center;
}

.drop-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.drop-text {
  font-size: 16px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 4px;
}

.drop-hint {
  font-size: 13px;
  color: #94a3b8;
}

.compare-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  min-height: 400px;
}

.image-panel {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.panel-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.image-wrapper {
  flex: 1;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  border-radius: 8px;
  overflow: hidden;
}

.image-wrapper img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.result-placeholder {
  color: #94a3b8;
  font-size: 14px;
}

.inpaint-placeholder {
  cursor: default;
}
</style>
