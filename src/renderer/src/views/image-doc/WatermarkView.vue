<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMessage } from 'naive-ui'
import {
  SparklesOutline,
  DownloadOutline,
  CloudUploadOutline,
  AddOutline,
  TrashOutline,
  CloseOutline,
  SettingsOutline,
  CheckmarkCircleOutline,
  ImagesOutline,
  AlertCircleOutline,
  SearchOutline,
  ExpandOutline,
  ChevronBackOutline,
  ChevronForwardOutline,
  EyeOutline
} from '@vicons/ionicons5'

const message = useMessage()

interface ImageItem {
  id: string
  file: File
  name: string
  path: string
  previewUrl: string
  resultUrl: string | null
  status: 'pending' | 'processing' | 'done' | 'error'
  errorMsg?: string
}

// 图片任务队列
const imageList = ref<ImageItem[]>([])
const selectedIndex = ref<number>(0)
const isBatchProcessing = ref<boolean>(false)
const showAdvanced = ref<boolean>(false)

// 高级微调参数 (99% 场景使用默认值即可)
const sensitivity = ref<number>(200)
const contrast = ref<number>(1.3)
const autoCleanRed = ref<boolean>(true)

// 弹窗大图预览状态 (支持无级滚轮缩放与平移拖拽)
const isPreviewOpen = ref<boolean>(false)
const previewMode = ref<'result' | 'compare' | 'original'>('result')
const zoomScale = ref<number>(1)
const panX = ref<number>(0)
const panY = ref<number>(0)
const isDragging = ref<boolean>(false)
const dragStart = { x: 0, y: 0 }

const openPreviewModal = (mode: 'result' | 'compare' | 'original' = 'result') => {
  if (!currentItem.value) return
  if (mode === 'result' && !currentItem.value.resultUrl) {
    message.info('该图片尚未处理，展示原图预览')
    previewMode.value = 'original'
  } else {
    previewMode.value = mode
  }
  handleZoomReset()
  isPreviewOpen.value = true
}

const handleZoomIn = () => {
  zoomScale.value = Math.min(4.0, Number((zoomScale.value + 0.25).toFixed(2)))
}

const handleZoomOut = () => {
  zoomScale.value = Math.max(0.3, Number((zoomScale.value - 0.25).toFixed(2)))
}

const handleZoomReset = () => {
  zoomScale.value = 1
  panX.value = 0
  panY.value = 0
}

const handleViewerWheel = (e: WheelEvent) => {
  e.preventDefault()
  if (e.deltaY < 0) {
    handleZoomIn()
  } else {
    handleZoomOut()
  }
}

const handleMouseDown = (e: MouseEvent) => {
  if (e.button !== 0) return
  isDragging.value = true
  dragStart.x = e.clientX - panX.value
  dragStart.y = e.clientY - panY.value
}

const handleMouseMove = (e: MouseEvent) => {
  if (!isDragging.value) return
  panX.value = e.clientX - dragStart.x
  panY.value = e.clientY - dragStart.y
}

const handleMouseUp = () => {
  isDragging.value = false
}

const handleDoubleClick = () => {
  if (zoomScale.value === 1) {
    zoomScale.value = 2
  } else {
    handleZoomReset()
  }
}

const prevPreviewImage = () => {
  if (selectedIndex.value > 0) {
    selectedIndex.value--
    handleZoomReset()
  }
}

const nextPreviewImage = () => {
  if (selectedIndex.value < imageList.value.length - 1) {
    selectedIndex.value++
    handleZoomReset()
  }
}

// 当前选中的图片项
const currentItem = computed<ImageItem | null>(() => {
  if (imageList.value.length === 0) return null
  return imageList.value[selectedIndex.value] || imageList.value[0]
})

// 统计
const completedCount = computed(() => {
  return imageList.value.filter((item) => item.status === 'done').length
})

// 处理文件上传（支持多选）
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

// 拖拽上传
const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  handleFilesSelect(e.dataTransfer?.files ?? null)
}

const handleDragOver = (e: DragEvent) => {
  e.preventDefault()
}

const fileInput = ref<HTMLInputElement | null>(null)
const triggerFileSelect = () => {
  fileInput.value?.click()
}

// 清空列表
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

// 移除单项
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

// 将 File 对象转换为 Base64 字符串辅助函数
const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = (err) => reject(err)
    reader.readAsDataURL(file)
  })
}

// 执行全自动去水印 (支持批量流水线)
const startAutoRemoval = async () => {
  if (imageList.value.length === 0) {
    message.warning('请先添加图片')
    return
  }

  isBatchProcessing.value = true

  try {
    for (let i = 0; i < imageList.value.length; i++) {
      const item = imageList.value[i]
      if (item.status === 'done') continue // 已完成的跳过

      item.status = 'processing'
      // 切换视图到当前正在处理的图片
      selectedIndex.value = i

      try {
        // 优先使用本地磁盘绝对路径，否则转为 Base64 字符串
        let inputSource = item.path
        if (!inputSource || !inputSource.includes(':')) {
          inputSource = await fileToBase64(item.file)
        }

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

// 保存单张结果
const saveCurrentResult = () => {
  if (!currentItem.value?.resultUrl) return
  const a = document.createElement('a')
  a.href = currentItem.value.resultUrl
  a.download = `去水印_${currentItem.value.name}`
  a.click()
  message.success('已保存当前图片')
}

// 批量保存全部结果 (单次弹窗选择目录，极速批量保存)
const isExporting = ref<boolean>(false)
const saveAllResults = async () => {
  const doneItems = imageList.value.filter((item) => item.status === 'done' && item.resultUrl)
  if (doneItems.length === 0) {
    message.warning('暂无处理完成的图片可保存')
    return
  }

  try {
    isExporting.value = true
    // 优先调用 Electron 原生文件夹选择器（仅弹窗 1 次）
    if (window.electron?.ipcRenderer) {
      const dirPath = await window.electron.ipcRenderer.invoke('dialog:select-directory')
      if (!dirPath) {
        // 用户主动取消了选择
        return
      }

      const itemsToSave = doneItems.map((item) => ({
        name: `去水印_${item.name}`,
        base64: item.resultUrl!
      }))

      const res = await window.electron.ipcRenderer.invoke('file:save-batch', {
        dirPath,
        items: itemsToSave
      })

      if (res?.success) {
        message.success(`成功导出 ${res.count} 张图片至: ${dirPath}`, {
          duration: 4000
        })
      } else {
        throw new Error('批量保存失败')
      }
    } else {
      // 纯浏览器降级模式 (单次打包或提示)
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
    <!-- 隐藏的本地文件多选 input -->
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
    >

    <!-- 顶部状态栏 -->
    <div class="top-bar">
      <div class="bar-left">
        <h1 class="bar-title">图片去水印</h1>
        <n-tag type="success" size="small" round>
          <template #icon><n-icon :component="SparklesOutline" /></template>
          全自动 AI 深度引擎 (LaMa)
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

    <!-- 高级微调折叠面板 (默认隐藏，傻瓜式无需设置) -->
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
      <!-- 空状态：全屏拖拽区域 -->
      <div
        v-if="imageList.length === 0"
        class="empty-drop-container"
        @drop="handleDrop"
        @dragover="handleDragOver"
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
        <!-- 左侧：图片列表与批量控制面板 -->
        <div class="sidebar-panel">
          <!-- 批量操作按钮区 -->
          <div class="action-card">
            <n-button
              type="primary"
              block
              size="large"
              class="glow-button"
              :loading="isBatchProcessing"
              @click="startAutoRemoval"
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
              @click="saveAllResults"
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
                @click="triggerFileSelect"
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
                @click="selectedIndex = index"
              >
                <div class="thumb-box">
                  <img :src="item.resultUrl || item.previewUrl" alt="thumb" />
                </div>
                <div class="item-info">
                  <span class="item-name">{{ item.name }}</span>
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
                  @click="(e) => removeItem(index, e)"
                >
                  <template #icon>
                    <n-icon :component="CloseOutline" />
                  </template>
                </n-button>
              </div>
            </div>
          </div>
        </div>

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
                一键下载当前图片
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
                <img :src="currentItem?.previewUrl" alt="original" />
              </div>
            </div>

            <!-- 去水印效果卡片 -->
            <div
              class="view-card"
              :class="{ 'clickable-card': Boolean(currentItem?.resultUrl) }"
              :title="currentItem?.resultUrl ? '点击弹窗高清对比预览' : ''"
              @click="currentItem?.resultUrl && openPreviewModal('result')"
            >
              <div class="view-tag result-tag">去水印效果</div>
              <div v-if="currentItem?.resultUrl" class="card-action-hint highlight">
                <n-icon :component="ExpandOutline" size="14" /> 点击弹窗高清对比
              </div>
              <div class="view-content">
                <div v-if="currentItem?.resultUrl" class="result-image-wrapper">
                  <img :src="currentItem.resultUrl" alt="result" />
                  <div class="image-hover-mask">
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
    <n-modal
      v-model:show="isPreviewOpen"
      preset="card"
      style="width: 92vw; max-width: 1400px; height: 90vh; border-radius: 16px; display: flex; flex-direction: column;"
      content-style="flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 0; overflow: hidden;"
      :bordered="false"
      size="small"
      :segmented="{ content: true, footer: true }"
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
              @click="saveCurrentResult"
            >
              <template #icon><n-icon :component="DownloadOutline" /></template>
              下载本图
            </n-button>
          </div>
        </div>
      </template>

      <!-- 弹窗主视口 (支持鼠标拖拽平移、滚轮缩放、双击放大/重置) -->
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
        <!-- 浮动左翻页按钮 -->
        <button
          v-if="imageList.length > 1"
          class="nav-btn prev-btn"
          :disabled="selectedIndex === 0"
          title="上一张图片 (←)"
          @click.stop="prevPreviewImage"
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

        <!-- 模式 2：左右双屏对比 (双屏同频平移与缩放) -->
        <div v-else-if="previewMode === 'compare'" class="compare-viewer-container">
          <div class="compare-col">
            <div class="col-tag">原始原图</div>
            <div
              class="col-zoomable"
              :style="{ transform: `translate(${panX}px, ${panY}px) scale(${zoomScale})` }"
            >
              <img
                :src="currentItem?.previewUrl"
                class="modal-compare-img"
                alt="orig-compare"
                draggable="false"
              />
            </div>
          </div>
          <div class="compare-divider" />
          <div class="compare-col">
            <div class="col-tag result-col-tag">去水印效果</div>
            <div
              class="col-zoomable"
              :style="{ transform: `translate(${panX}px, ${panY}px) scale(${zoomScale})` }"
            >
              <img
                v-if="currentItem?.resultUrl"
                :src="currentItem.resultUrl"
                class="modal-compare-img"
                alt="res-compare"
                draggable="false"
              />
            </div>
          </div>
        </div>

        <!-- 模式 3：原始高清图 -->
        <div v-else-if="previewMode === 'original'" class="single-viewer-container">
          <div
            class="zoomable-wrapper"
            :style="{ transform: `translate(${panX}px, ${panY}px) scale(${zoomScale})` }"
          >
            <img
              :src="currentItem?.previewUrl"
              class="modal-main-img"
              alt="orig-large"
              draggable="false"
            />
          </div>
        </div>

        <!-- 浮动右翻页按钮 -->
        <button
          v-if="imageList.length > 1"
          class="nav-btn next-btn"
          :disabled="selectedIndex === imageList.length - 1"
          title="下一张图片 (→)"
          @click.stop="nextPreviewImage"
        >
          <n-icon size="24" :component="ChevronForwardOutline" />
        </button>
      </div>

      <template #footer>
        <div class="modal-footer-box">
          <span class="tip-text">💡 提示：支持鼠标滚轮直接缩放；点击上方选项随时切换双屏/单图对比；点击左右箭头可切换上一张/下一张</span>
          <n-button size="small" @click="isPreviewOpen = false">关闭预览</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.watermark-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
}

/* 顶部状态条 */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
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
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.bar-subtitle {
  font-size: 12px;
  color: #64748b;
  margin-left: 6px;
}

.bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 微调面板 */
.advanced-panel {
  background: #f1f5f9;
  border-radius: 10px;
  padding: 10px 16px;
}

.advanced-grid {
  display: flex;
  align-items: center;
  gap: 32px;
  flex-wrap: wrap;
}

.adv-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #334155;
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
  border-color: #0284c7;
  background: #f0f9ff;
}

.empty-content {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.empty-desc {
  font-size: 13px;
  color: #64748b;
  max-width: 420px;
  line-height: 1.5;
}

.upload-btn {
  margin-top: 12px;
  border-radius: 10px;
  padding: 0 24px;
}

/* 工作区容器 */
.workspace-container {
  display: grid;
  grid-template-columns: 290px 1fr;
  gap: 14px;
  height: 100%;
}

/* 左侧栏 */
.sidebar-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
}

.action-card {
  background: #ffffff;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.glow-button {
  font-weight: 600;
  border-radius: 10px;
  box-shadow: 0 4px 12px -2px rgba(2, 132, 199, 0.35);
}

.download-all-btn {
  font-weight: 600;
  border-radius: 10px;
  box-shadow: 0 4px 12px -2px rgba(22, 163, 74, 0.35);
}

.btn-row {
  display: flex;
  gap: 8px;
}

/* 队列列表 */
.queue-list-container {
  flex: 1;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.queue-header {
  padding: 10px 14px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.queue-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.queue-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.queue-count {
  font-size: 11px;
  color: #64748b;
}

.queue-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.queue-item:hover {
  background: #f8fafc;
}

.queue-item.is-selected {
  background: #f0f9ff;
  border-color: #bae6fd;
}

.thumb-box {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  overflow: hidden;
  background: #e2e8f0;
  flex-shrink: 0;
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
  gap: 2px;
}

.item-name {
  font-size: 12px;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.del-btn {
  opacity: 0.4;
  transition: opacity 0.2s;
}

.queue-item:hover .del-btn {
  opacity: 1;
}

/* 右侧大视口 */
.viewport-panel {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.viewport-header {
  padding: 12px 18px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.vp-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.vp-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

/* 对比双屏 */
.compare-view {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 14px;
  min-height: 0;
  background: #f8fafc;
}

.view-card {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.view-tag {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  z-index: 2;
}

.original-tag {
  background: rgba(15, 23, 42, 0.75);
  color: #ffffff;
}

.result-tag {
  background: rgba(2, 132, 199, 0.85);
  color: #ffffff;
}

.view-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  overflow: hidden;
}

.view-content img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  box-shadow: 0 4px 10px -2px rgba(0, 0, 0, 0.05);
}

.status-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #94a3b8;
}

.pending-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #64748b;
}

.error-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: #ef4444;
  font-size: 13px;
}

.clickable-card {
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.clickable-card:hover {
  border-color: #38bdf8;
  box-shadow: 0 8px 20px -4px rgba(2, 132, 199, 0.15);
}

.card-action-hint {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(241, 245, 249, 0.9);
  color: #475569;
  z-index: 2;
  transition: all 0.2s ease;
  pointer-events: none;
}

.card-action-hint.highlight {
  background: rgba(224, 242, 254, 0.95);
  color: #0369a1;
  font-weight: 600;
}

.clickable-card:hover .card-action-hint {
  background: #0284c7;
  color: #ffffff;
}

.result-image-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-hover-mask {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
  border-radius: 6px;
}

.result-image-wrapper:hover .image-hover-mask {
  opacity: 1;
}

.mask-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #ffffff;
  color: #0f172a;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
  transform: translateY(4px);
  transition: transform 0.2s ease;
}

.result-image-wrapper:hover .mask-badge {
  transform: translateY(0);
}

/* 弹窗预览模态框样式 */
.modal-header-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 16px;
}

.m-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.m-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  max-width: 320px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.m-counter {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
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
  position: relative;
  flex: 1;
  min-height: 0;
  background: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  cursor: grab;
  user-select: none;
}

.modal-viewer-body.is-grabbing {
  cursor: grabbing;
}

.modal-viewer-body img {
  user-select: none;
  -webkit-user-drag: none;
  pointer-events: none;
}

/* 浮动翻页按钮 */
.nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: all 0.2s ease;
}

.nav-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.4);
  transform: translateY(-50%) scale(1.08);
}

.nav-btn:disabled {
  opacity: 0.2;
  cursor: not-allowed;
}

.prev-btn {
  left: 20px;
}

.next-btn {
  right: 20px;
}

/* 单图预览视口 */
.single-viewer-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: auto;
}

.zoomable-wrapper {
  transition: transform 0.15s ease-out;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-main-img {
  max-width: 82vw;
  max-height: 72vh;
  object-fit: contain;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  border-radius: 6px;
  background: #ffffff;
}

/* 左右双屏对比视口 */
.compare-viewer-container {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  padding: 20px;
  gap: 16px;
  align-items: center;
  overflow: hidden;
}

.compare-col {
  height: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.col-tag {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(0, 0, 0, 0.65);
  color: #ffffff;
  z-index: 2;
  backdrop-filter: blur(4px);
}

.result-col-tag {
  background: rgba(2, 132, 199, 0.85);
}

.col-zoomable {
  transition: transform 0.15s ease-out;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding: 16px;
}

.modal-compare-img {
  max-width: 100%;
  max-height: 68vh;
  object-fit: contain;
  border-radius: 4px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  background: #ffffff;
}

.compare-divider {
  width: 1px;
  height: 80%;
  background: rgba(255, 255, 255, 0.15);
}

.modal-footer-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.tip-text {
  font-size: 12px;
  color: #64748b;
}
</style>
