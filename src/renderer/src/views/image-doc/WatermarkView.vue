<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMessage } from 'naive-ui'

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
        const inputSource = item.path || item.previewUrl
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

// 批量保存全部结果
const saveAllResults = () => {
  const doneItems = imageList.value.filter((item) => item.status === 'done' && item.resultUrl)
  if (doneItems.length === 0) {
    message.warning('暂无处理完成的图片可保存')
    return
  }

  doneItems.forEach((item, index) => {
    setTimeout(() => {
      const a = document.createElement('a')
      a.href = item.resultUrl!
      a.download = `去水印_${item.name}`
      a.click()
    }, index * 200)
  })

  message.success(`正在批量下载 ${doneItems.length} 张处理好的图片`)
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
      @change="(e) => handleFilesSelect((e.target as HTMLInputElement).files)"
    >

    <!-- 顶部状态栏 -->
    <div class="top-bar">
      <div class="bar-left">
        <h1 class="bar-title">图片去水印</h1>
        <n-tag type="success" size="small" round>全自动智能引擎</n-tag>
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
          ⚙️ {{ showAdvanced ? '收起微调' : '参数微调' }}
        </n-button>
        <n-button
          v-if="imageList.length > 0"
          size="small"
          quaternary
          type="error"
          :disabled="isBatchProcessing"
          @click="clearAll"
        >
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
          <div class="empty-icon">📁</div>
          <div class="empty-title">点击或拖拽图片到此处</div>
          <div class="empty-desc">支持单张或批量拖入多份试卷、课件图片 (JPG / PNG / WebP)</div>
          <n-button type="primary" size="large" class="upload-btn">
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
              ✨ 智能一键去水印 ({{ imageList.length }} 张)
            </n-button>

            <div class="btn-row">
              <n-button
                secondary
                block
                :disabled="isBatchProcessing"
                @click="triggerFileSelect"
              >
                + 添加更多
              </n-button>
              <n-button
                v-if="completedCount > 0"
                type="success"
                secondary
                block
                @click="saveAllResults"
              >
                📦 全部保存 ({{ completedCount }})
              </n-button>
            </div>
          </div>

          <!-- 图片队列列表 -->
          <div class="queue-list-container">
            <div class="queue-header">
              <span class="queue-title">图片列表 ({{ imageList.length }})</span>
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
                    <n-tag v-if="item.status === 'done'" size="tiny" type="success" round>已完成</n-tag>
                    <n-tag v-else-if="item.status === 'processing'" size="tiny" type="info" round>处理中...</n-tag>
                    <n-tag v-else-if="item.status === 'error'" size="tiny" type="error" round>失败</n-tag>
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
                  ✕
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
                去水印成功
              </n-tag>
            </div>
            <div class="vp-right">
              <n-button
                v-if="currentItem?.resultUrl"
                type="primary"
                secondary
                size="small"
                @click="saveCurrentResult"
              >
                💾 保存当前图片
              </n-button>
            </div>
          </div>

          <!-- 双屏对比视口 -->
          <div class="compare-view">
            <!-- 原图卡片 -->
            <div class="view-card">
              <div class="view-tag original-tag">原始图片</div>
              <div class="view-content">
                <img :src="currentItem?.previewUrl" alt="original" />
              </div>
            </div>

            <!-- 去水印效果卡片 -->
            <div class="view-card">
              <div class="view-tag result-tag">去水印效果</div>
              <div class="view-content">
                <img
                  v-if="currentItem?.resultUrl"
                  :src="currentItem.resultUrl"
                  alt="result"
                />
                <div v-else class="status-placeholder">
                  <n-spin v-if="currentItem?.status === 'processing'" size="large" />
                  <div v-else-if="currentItem?.status === 'error'" class="error-box">
                    <span>处理失败</span>
                    <n-text depth="3">{{ currentItem?.errorMsg }}</n-text>
                  </div>
                  <div v-else class="pending-box">
                    <span class="magic-icon">✨</span>
                    <span>点击左侧【智能一键去水印】即可处理</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
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

.empty-icon {
  font-size: 56px;
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

.magic-icon {
  font-size: 32px;
}

.pending-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #64748b;
}

.error-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #ef4444;
  font-size: 13px;
}
</style>
