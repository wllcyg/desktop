<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMessage } from 'naive-ui'
import {
  SparklesOutline,
  DownloadOutline,
  CloudUploadOutline,
  AddOutline,
  TrashOutline,
  SettingsOutline,
  CheckmarkCircleOutline,
  AlertCircleOutline,
  SearchOutline,
  ExpandOutline,
  EyeOutline
} from '@vicons/ionicons5'
import { ImageItem, fileToBase64 } from './watermark/types'
import WatermarkQueue from './watermark/components/WatermarkQueue.vue'
import CompareModal from './watermark/components/CompareModal.vue'

const message = useMessage()

// 图片任务队列
const imageList = ref<ImageItem[]>([])
const selectedIndex = ref<number>(0)
const isBatchProcessing = ref<boolean>(false)
const isExporting = ref<boolean>(false)
const showAdvanced = ref<boolean>(false)

// 高级微调参数
const sensitivity = ref<number>(200)
const contrast = ref<number>(1.3)
const autoCleanRed = ref<boolean>(true)

// 弹窗大图预览状态
const isPreviewOpen = ref<boolean>(false)
const previewModalMode = ref<'result' | 'compare' | 'original'>('result')

const openPreviewModal = (mode: 'result' | 'compare' | 'original' = 'result') => {
  if (!currentItem.value) return
  if (mode === 'result' && !currentItem.value.resultUrl) {
    message.info('该图片尚未处理，展示原图预览')
    previewModalMode.value = 'original'
  } else {
    previewModalMode.value = mode
  }
  isPreviewOpen.value = true
}

// 当前选中的图片项
const currentItem = computed<ImageItem | null>(() => {
  if (imageList.value.length === 0) return null
  return imageList.value[selectedIndex.value] || imageList.value[0]
})

const completedCount = computed(() => {
  return imageList.value.filter((item) => item.status === 'done').length
})

// 处理文件上传
const handleFilesSelect = (files: FileList | null) => {
  if (!files || files.length === 0) return

  const newItems: ImageItem[] = []
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    if (!file.type.startsWith('image/')) continue

    const id = `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
    const path = (file as any).path || ''
    const previewUrl = URL.createObjectURL(file)

    newItems.push({
      id,
      file,
      name: file.name,
      path,
      previewUrl,
      resultUrl: null,
      status: 'pending'
    })
  }

  if (newItems.length === 0) {
    message.warning('请选择有效的图片文件')
    return
  }

  imageList.value.push(...newItems)
  if (imageList.value.length === newItems.length) {
    selectedIndex.value = 0
  }
  message.info(`已添加 ${newItems.length} 张图片`)
}

const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  handleFilesSelect(e.dataTransfer?.files ?? null)
}

const fileInput = ref<HTMLInputElement | null>(null)
const triggerFileSelect = () => {
  fileInput.value?.click()
}

const clearAll = () => {
  imageList.value.forEach((item) => {
    URL.revokeObjectURL(item.previewUrl)
    if (item.resultUrl && item.resultUrl.startsWith('blob:')) {
      URL.revokeObjectURL(item.resultUrl)
    }
  })
  if (fileInput.value) {
    fileInput.value.value = ''
  }
  imageList.value = []
  selectedIndex.value = 0
}

const removeItem = (index: number, e: Event) => {
  e.stopPropagation()
  const removed = imageList.value.splice(index, 1)[0]
  if (removed) {
    URL.revokeObjectURL(removed.previewUrl)
  }
  if (selectedIndex.value >= imageList.value.length) {
    selectedIndex.value = Math.max(0, imageList.value.length - 1)
  }
}

// 执行全自动去水印
const startAutoRemoval = async () => {
  if (imageList.value.length === 0) {
    message.warning('请先添加图片')
    return
  }

  isBatchProcessing.value = true
  try {
    for (let i = 0; i < imageList.value.length; i++) {
      const item = imageList.value[i]
      if (item.status === 'done') continue

      item.status = 'processing'
      selectedIndex.value = i

      try {
        let inputSource = item.path
        if (!inputSource || !inputSource.includes(':')) {
          inputSource = await fileToBase64(item.file)
        }

        // @ts-ignore
        const res = await window.electron.ipcRenderer.invoke('py:call', {
          method: 'watermark.auto_remove',
          params: {
            input: inputSource,
            sensitivity: sensitivity.value,
            contrast: contrast.value,
            auto_clean_red: autoCleanRed.value
          }
        })

        if (res?.image_base64) {
          item.resultUrl = res.image_base64
          item.status = 'done'
        } else {
          throw new Error('未获取到处理结果')
        }
      } catch (err: any) {
        item.status = 'error'
        item.errorMsg = err?.message || '处理异常'
      }
    }

    message.success(`批量处理完成！已处理 ${completedCount.value}/${imageList.value.length} 张图片`)
  } catch (err: any) {
    message.error(err?.message || '批量处理失败')
  } finally {
    isBatchProcessing.value = false
  }
}

// 保存当前图片
const saveCurrentResult = () => {
  if (!currentItem.value?.resultUrl) return
  const a = document.createElement('a')
  a.href = currentItem.value.resultUrl
  a.download = `去水印_${currentItem.value.name}`
  a.click()
  message.success('已保存当前图片')
}

// 批量保存全部结果
const saveAllResults = async () => {
  const doneItems = imageList.value.filter((item) => item.status === 'done' && item.resultUrl)
  if (doneItems.length === 0) {
    message.warning('暂无处理完成的图片可保存')
    return
  }

  try {
    isExporting.value = true
    // @ts-ignore
    if (window.electron?.ipcRenderer) {
      // @ts-ignore
      const dirPath = await window.electron.ipcRenderer.invoke('dialog:select-directory')
      if (!dirPath) return

      const itemsToSave = doneItems.map((item) => ({
        name: `去水印_${item.name}`,
        base64: item.resultUrl!
      }))

      // @ts-ignore
      const res = await window.electron.ipcRenderer.invoke('file:save-batch', {
        dirPath,
        items: itemsToSave
      })

      if (res?.success) {
        message.success(`成功导出 ${res.count} 张图片至: ${dirPath}`, { duration: 4000 })
      } else {
        throw new Error('批量保存失败')
      }
    } else {
      doneItems.forEach((item) => {
        const a = document.createElement('a')
        a.href = item.resultUrl!
        a.download = `去水印_${item.name}`
        a.click()
      })
      message.success(`正在下载 ${doneItems.length} 张图片`)
    }
  } catch (err: any) {
    message.error(err?.message || '导出图片失败')
  } finally {
    isExporting.value = false
  }
}
</script>

<template>
  <div class="watermark-page">
    <input
      ref="fileInput"
      type="file"
      multiple
      accept="image/*"
      style="display: none"
      @change="
        (e) => {
          handleFilesSelect((e.target as HTMLInputElement).files)
          ;(e.target as HTMLInputElement).value = ''
        }
      "
    />

    <!-- 顶部状态栏 -->
    <div class="top-bar">
      <div class="bar-left">
        <h1 class="bar-title">图片去水印</h1>
        <n-tag type="success" size="small" round>
          <template #icon><n-icon :component="SparklesOutline" /></template>
          全自动 AI 深度引擎
        </n-tag>
        <span class="bar-subtitle">
          自动识别消除试卷平铺浅色水印、背景拍摄阴影及红笔印章批改
        </span>
      </div>
      <div class="bar-right">
        <n-button
          v-if="imageList.length > 0"
          size="small"
          quaternary
          @click="showAdvanced = !showAdvanced"
        >
          <template #icon>
            <n-icon :component="SettingsOutline" />
          </template>
          {{ showAdvanced ? '收起微调' : '参数微调' }}
        </n-button>
        <n-button
          v-if="imageList.length > 0"
          size="small"
          quaternary
          type="error"
          :disabled="isBatchProcessing"
          @click="clearAll"
        >
          <template #icon>
            <n-icon :component="TrashOutline" />
          </template>
          清空列表
        </n-button>
      </div>
    </div>

    <!-- 高级微调折叠面板 -->
    <n-collapse-transition :show="showAdvanced">
      <n-card size="small" class="advanced-panel" :bordered="false">
        <div class="advanced-grid">
          <div class="adv-item">
            <span class="adv-label">去水印灵敏度: {{ sensitivity }}</span>
            <n-slider v-model:value="sensitivity" :min="120" :max="240" :step="5" style="width: 160px" />
          </div>
          <div class="adv-item">
            <span class="adv-label">文字黑度增强: {{ contrast }}x</span>
            <n-slider v-model:value="contrast" :min="1.0" :max="2.0" :step="0.1" style="width: 140px" />
          </div>
          <div class="adv-item">
            <n-checkbox v-model:checked="autoCleanRed">自动抹除红色印章与批改红笔痕迹</n-checkbox>
          </div>
        </div>
      </n-card>
    </n-collapse-transition>

    <!-- 主工作区 -->
    <div class="main-layout">
      <!-- 空状态 -->
      <div
        v-if="imageList.length === 0"
        class="empty-drop-container"
        @drop="handleDrop"
        @dragover.prevent
        @click="triggerFileSelect"
      >
        <div class="empty-content">
          <n-icon size="64" color="#94a3b8" :component="CloudUploadOutline" />
          <div class="empty-title">点击或拖拽图片到此处</div>
          <div class="empty-desc">支持单张或批量拖入多份试卷、课件图片 (JPG / PNG / WebP)</div>
          <n-button type="primary" size="large" class="upload-btn">
            <template #icon>
              <n-icon :component="AddOutline" />
            </template>
            选择图片文件 (支持批量)
          </n-button>
        </div>
      </div>

      <!-- 图片列表与对比工作台 -->
      <div v-else class="workspace-container">
        <!-- 左侧：队列列表 -->
        <WatermarkQueue
          :image-list="imageList"
          :selected-index="selectedIndex"
          :is-batch-processing="isBatchProcessing"
          :is-exporting="isExporting"
          @update:selected-index="(i) => (selectedIndex = i)"
          @start-batch="startAutoRemoval"
          @save-all="saveAllResults"
          @trigger-upload="triggerFileSelect"
          @remove-item="removeItem"
        />

        <!-- 右侧：当前选中图片的前后对比大视口 -->
        <div class="viewport-panel">
          <div class="viewport-header">
            <div class="vp-left">
              <span class="vp-title">{{ currentItem?.name }}</span>
              <n-tag v-if="currentItem?.status === 'done'" type="success" size="small" round>
                <template #icon><n-icon :component="CheckmarkCircleOutline" /></template>
                去水印成功
              </n-tag>
            </div>
            <div class="vp-right">
              <n-button
                v-if="currentItem?.resultUrl"
                size="small"
                secondary
                type="info"
                @click="openPreviewModal('compare')"
              >
                <template #icon>
                  <n-icon :component="ExpandOutline" />
                </template>
                弹窗高清对比
              </n-button>
              <n-button
                v-if="currentItem?.resultUrl"
                type="primary"
                size="small"
                @click="saveCurrentResult"
              >
                <template #icon>
                  <n-icon :component="DownloadOutline" />
                </template>
                下载当前图片
              </n-button>
            </div>
          </div>

          <!-- 双屏对比视口 -->
          <div class="compare-view">
            <!-- 原图卡片 -->
            <div
              class="view-card clickable-card"
              title="点击弹窗放大查看原图"
              @click="openPreviewModal('original')"
            >
              <div class="view-tag original-tag">原始图片</div>
              <div class="card-action-hint">
                <n-icon :component="SearchOutline" size="14" /> 点击放大
              </div>
              <div class="view-content">
                <img
                  v-if="currentItem?.previewUrl"
                  :src="currentItem.previewUrl"
                  alt="original"
                  class="preview-image"
                />
              </div>
            </div>

            <!-- 处理结果卡片 -->
            <div class="view-card">
              <div class="view-tag result-tag">去水印效果</div>
              <div
                class="view-content"
                :class="{ 'has-result': !!currentItem?.resultUrl }"
              >
                <div
                  v-if="currentItem?.resultUrl"
                  class="result-img-wrapper"
                  title="点击全屏弹窗对比"
                  @click="openPreviewModal('result')"
                >
                  <img
                    :src="currentItem.resultUrl"
                    alt="result"
                    class="preview-image"
                  />
                  <div class="result-hover-mask">
                    <div class="mask-badge">
                      <n-icon :component="EyeOutline" size="18" />
                      <span>点击全屏弹窗预览</span>
                    </div>
                  </div>
                </div>
                <div v-else class="status-placeholder">
                  <n-spin v-if="currentItem?.status === 'processing'" size="large" />
                  <div v-else-if="currentItem?.status === 'error'" class="error-box">
                    <n-icon size="32" :component="AlertCircleOutline" />
                    <span>处理失败</span>
                    <n-text depth="3">{{ currentItem?.errorMsg }}</n-text>
                  </div>
                  <div v-else class="pending-box">
                    <n-icon size="40" color="#0284c7" :component="SparklesOutline" />
                    <span>点击左侧【智能一键去水印】即可处理</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 高清弹窗预览模态框 -->
    <CompareModal
      v-model:show="isPreviewOpen"
      :current-item="currentItem"
      :image-list="imageList"
      :selected-index="selectedIndex"
      :initial-mode="previewModalMode"
      @update:selected-index="(i) => (selectedIndex = i)"
      @save-current="saveCurrentResult"
    />
  </div>
</template>

<style scoped>
.watermark-page { display: flex; flex-direction: column; height: 100%; width: 100%; background: #f8fafc; padding: 16px 20px 20px 20px; box-sizing: border-box; overflow: hidden; }
.top-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-shrink: 0; }
.bar-left { display: flex; align-items: center; gap: 10px; }
.bar-title { margin: 0; font-size: 18px; font-weight: 700; color: #0f172a; }
.bar-subtitle { font-size: 12px; color: #64748b; margin-left: 6px; }
.bar-right { display: flex; align-items: center; gap: 8px; }
.advanced-panel { margin-bottom: 12px; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; }
.advanced-grid { display: flex; align-items: center; gap: 24px; }
.adv-item { display: flex; align-items: center; gap: 8px; }
.adv-label { font-size: 12px; color: #475569; font-weight: 500; }
.main-layout { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.empty-drop-container { flex: 1; display: flex; align-items: center; justify-content: center; background: #ffffff; border: 2px dashed #cbd5e1; border-radius: 12px; cursor: pointer; transition: all 0.2s; }
.empty-drop-container:hover { border-color: #3b82f6; background: #f8faff; }
.empty-content { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.empty-title { font-size: 16px; font-weight: 600; color: #1e293b; }
.empty-desc { font-size: 13px; color: #94a3b8; }
.upload-btn { margin-top: 8px; }
.workspace-container { flex: 1; min-height: 0; display: flex; gap: 16px; }
.viewport-panel { flex: 1; background: #ffffff; border-radius: 10px; border: 1px solid #e2e8f0; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04); }
.viewport-header { padding: 10px 16px; border-bottom: 1px solid #f1f5f9; display: flex; align-items: center; justify-content: space-between; background: #f8fafc; }
.vp-left { display: flex; align-items: center; gap: 10px; }
.vp-title { font-size: 13px; font-weight: 600; color: #1e293b; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vp-right { display: flex; align-items: center; gap: 8px; }
.compare-view { flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 12px; min-height: 0; background: #f1f5f9; }
.view-card { background: #ffffff; border-radius: 8px; position: relative; display: flex; flex-direction: column; overflow: hidden; border: 1px solid #e2e8f0; }
.clickable-card { cursor: pointer; transition: all 0.2s; }
.clickable-card:hover { border-color: #3b82f6; box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15); }
.view-tag { position: absolute; top: 10px; left: 10px; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; z-index: 10; }
.original-tag { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
.result-tag { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
.card-action-hint { position: absolute; top: 10px; right: 10px; font-size: 11px; color: #64748b; background: rgba(255, 255, 255, 0.85); padding: 2px 6px; border-radius: 4px; display: flex; align-items: center; gap: 4px; z-index: 10; }
.view-content { flex: 1; display: flex; align-items: center; justify-content: center; overflow: hidden; padding: 12px; position: relative; }
.preview-image { max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 4px; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08); }
.result-img-wrapper { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; position: relative; cursor: pointer; }
.result-hover-mask { position: absolute; inset: 0; background: rgba(0, 0, 0, 0.25); display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.2s; border-radius: 4px; }
.result-img-wrapper:hover .result-hover-mask { opacity: 1; }
.mask-badge { background: rgba(0, 0, 0, 0.75); color: #ffffff; padding: 6px 12px; border-radius: 20px; font-size: 12px; display: flex; align-items: center; gap: 6px; backdrop-filter: blur(4px); }
.status-placeholder { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }
.pending-box, .error-box { display: flex; flex-direction: column; align-items: center; gap: 8px; color: #64748b; font-size: 13px; }
.error-box { color: #ef4444; }
</style>
