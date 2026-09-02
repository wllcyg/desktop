<script setup lang="ts">
import { ref } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import {
  GridOutline,
  RefreshOutline,
  TrashOutline,
  ArrowUpOutline,
  ArrowDownOutline,
  DownloadOutline,
  SyncOutline
} from '@vicons/ionicons5'
import {
  SplitDocInfo,
  OrganizePageItem,
  formatFileSize,
  selectPdfFilesSafely,
  selectSavePathSafely,
  openPath,
  showInFolder
} from './types'

const message = useMessage()
const dialog = useDialog()

const currentOrganizeDoc = ref<SplitDocInfo | null>(null)
const pageCards = ref<OrganizePageItem[]>([])
const isLoadingThumbnails = ref<boolean>(false)
const isExportingOrganize = ref<boolean>(false)

const handleSelectOrganizeDoc = async () => {
  try {
    const filePaths = await selectPdfFilesSafely(false)
    if (!filePaths || filePaths.length === 0) return
    loadOrganizeDoc(filePaths[0])
  } catch (err: any) {
    message.error(`选择文件失败: ${err.message}`)
  }
}

const handleOrganizeDrop = (e: DragEvent) => {
  e.preventDefault()
  if (!e.dataTransfer?.files || e.dataTransfer.files.length === 0) return
  const file = Array.from(e.dataTransfer.files).find((f) => f.name.toLowerCase().endsWith('.pdf'))
  if (!file) {
    message.warning('请拖拽有效的 PDF 文件')
    return
  }
  // @ts-ignore
  const filePath = file.path
  if (filePath) {
    loadOrganizeDoc(filePath)
  }
}

const loadOrganizeDoc = async (pdfPath: string) => {
  isLoadingThumbnails.value = true
  try {
    // @ts-ignore
    const res = await window.electron?.ipcRenderer?.invoke('py:call', {
      method: 'pdf.get_info',
      params: { path: pdfPath, include_thumbnails: true, max_thumb_size: 260 }
    })

    currentOrganizeDoc.value = {
      name: res.file_name,
      path: res.file_path,
      size: res.file_size,
      totalPages: res.total_pages,
      hasToc: res.has_toc,
      toc: res.toc || []
    }

    pageCards.value = res.pages.map((p: any) => ({
      id: `p_${p.page_index}_${Math.random().toString(36).substring(2, 6)}`,
      originalPageIndex: p.page_index,
      pageNumber: p.page_number,
      rotationDelta: 0,
      thumbnail: p.thumbnail,
      width: p.width,
      height: p.height
    }))
  } catch (err: any) {
    message.error(`加载页面缩略图失败: ${err.message}`)
    currentOrganizeDoc.value = null
    pageCards.value = []
  } finally {
    isLoadingThumbnails.value = false
  }
}

// 旋转单页
const rotatePage = (index: number, angle: number) => {
  if (!pageCards.value[index]) return
  pageCards.value[index].rotationDelta = (pageCards.value[index].rotationDelta + angle + 360) % 360
}

// 移除单页
const removePageCard = (index: number) => {
  pageCards.value.splice(index, 1)
}

// 页面位移
const movePageCard = (index: number, direction: 'left' | 'right') => {
  if (direction === 'left' && index > 0) {
    const temp = pageCards.value[index]
    pageCards.value[index] = pageCards.value[index - 1]
    pageCards.value[index - 1] = temp
  } else if (direction === 'right' && index < pageCards.value.length - 1) {
    const temp = pageCards.value[index]
    pageCards.value[index] = pageCards.value[index + 1]
    pageCards.value[index + 1] = temp
  }
}

// 批量旋转全部
const rotateAllPages = (angle: number) => {
  pageCards.value.forEach((p) => {
    p.rotationDelta = (p.rotationDelta + angle + 360) % 360
  })
}

// 重置页面排列和旋转
const resetPageCards = () => {
  if (!currentOrganizeDoc.value) return
  loadOrganizeDoc(currentOrganizeDoc.value.path)
}

// 导出重排后的 PDF
const handleExportOrganizedPdf = async () => {
  if (!currentOrganizeDoc.value || pageCards.value.length === 0) {
    message.warning('请保留至少一个页面后再导出')
    return
  }

  const defaultName = `${currentOrganizeDoc.value.name.replace(/\.pdf$/i, '')}_已重排.pdf`
  const savePath = await selectSavePathSafely(defaultName)
  if (!savePath) return

  isExportingOrganize.value = true
  try {
    const pageConfigs = pageCards.value.map((p) => ({
      page_index: p.originalPageIndex,
      rotation: p.rotationDelta
    }))

    // @ts-ignore
    const res = await window.electron?.ipcRenderer?.invoke('py:call', {
      method: 'pdf.reorganize',
      params: {
        path: currentOrganizeDoc.value.path,
        pages: pageConfigs,
        output_path: savePath
      }
    })

    if (res.success) {
      dialog.success({
        title: '导出成功',
        content: `成功生成新 PDF（共 ${res.total_pages} 页，文件大小: ${formatFileSize(res.file_size)}）。`,
        positiveText: '打开文件',
        negativeText: '打开所在目录',
        onPositiveClick: () => {
          openPath(savePath)
        },
        onNegativeClick: () => {
          showInFolder(savePath)
        }
      })
    }
  } catch (err: any) {
    dialog.error({
      title: '导出失败',
      content: err.message || '导出过程中发生异常'
    })
  } finally {
    isExportingOrganize.value = false
  }
}
</script>

<template>
  <div class="organize-wrapper">
    <!-- 未导入状态 -->
    <div
      v-if="!currentOrganizeDoc"
      class="drop-empty-zone full-height-zone"
      @dragover.prevent
      @drop="handleOrganizeDrop"
      @click="handleSelectOrganizeDoc"
    >
      <div class="empty-icon-circle">
        <n-icon size="46" color="#3B82F6"><GridOutline /></n-icon>
      </div>
      <p class="empty-title">点击或拖拽 PDF 文件到此处开启可视化页面重排</p>
      <p class="empty-desc">渲染全部页面高清缩略图，支持自由调序、顺/逆时针旋转 90°、单页删减</p>
    </div>

    <!-- 已导入：工具栏 + 页面网格流 -->
    <div v-else class="organize-workspace">
      <!-- 顶部批量操作栏 -->
      <div class="organize-top-toolbar">
        <div class="top-tool-left">
          <span class="organize-doc-title" :title="currentOrganizeDoc.path">{{ currentOrganizeDoc.name }}</span>
          <n-tag size="small" type="info" :bordered="false">
            保留 <strong>{{ pageCards.length }}</strong> / 原 {{ currentOrganizeDoc.totalPages }} 页
          </n-tag>
        </div>

        <div class="top-tool-right">
          <n-button size="small" quaternary @click="rotateAllPages(90)">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            全选顺时针 90°
          </n-button>
          <n-button size="small" quaternary @click="resetPageCards">
            <template #icon>
              <n-icon><SyncOutline /></n-icon>
            </template>
            重置排列
          </n-button>
          <n-button size="small" secondary type="primary" @click="handleSelectOrganizeDoc">
            更换文档
          </n-button>
          <n-button
            size="small"
            type="primary"
            :loading="isExportingOrganize"
            :disabled="pageCards.length === 0"
            @click="handleExportOrganizedPdf"
          >
            <template #icon>
              <n-icon><DownloadOutline /></n-icon>
            </template>
            导出新 PDF
          </n-button>
        </div>
      </div>

      <!-- 缩略图网格卡片容器 -->
      <div v-if="isLoadingThumbnails" class="loading-grid-container">
        <n-spin size="large" description="正在极速渲染页面缩略图..." />
      </div>

      <div v-else class="page-thumbnail-grid">
        <div
          v-for="(page, pIdx) in pageCards"
          :key="page.id"
          class="page-card-item"
        >
          <!-- 顶部页码标与操作 -->
          <div class="card-header-bar">
            <span class="page-index-pill">
              #{{ pIdx + 1 }} <span class="sub-num">(原P{{ page.pageNumber }})</span>
            </span>
            <span v-if="page.rotationDelta !== 0" class="rotation-tag">
              {{ page.rotationDelta }}°
            </span>
          </div>

          <!-- 缩略图展示区域 (动态绑定旋转角度) -->
          <div class="thumbnail-wrapper">
            <img
              :src="page.thumbnail"
              alt="Page Thumbnail"
              class="thumb-img"
              :style="{ transform: `rotate(${page.rotationDelta}deg)` }"
            />
          </div>

          <!-- 底部操作工具条 -->
          <div class="card-bottom-actions">
            <button
              class="action-icon-btn"
              title="左移"
              :disabled="pIdx === 0"
              @click="movePageCard(pIdx, 'left')"
            >
              <n-icon size="14"><ArrowUpOutline style="transform: rotate(-90deg)" /></n-icon>
            </button>
            <button
              class="action-icon-btn"
              title="逆时针旋转 90°"
              @click="rotatePage(pIdx, -90)"
            >
              <n-icon size="14"><RefreshOutline style="transform: scaleX(-1)" /></n-icon>
            </button>
            <button
              class="action-icon-btn"
              title="顺时针旋转 90°"
              @click="rotatePage(pIdx, 90)"
            >
              <n-icon size="14"><RefreshOutline /></n-icon>
            </button>
            <button
              class="action-icon-btn"
              title="右移"
              :disabled="pIdx === pageCards.length - 1"
              @click="movePageCard(pIdx, 'right')"
            >
              <n-icon size="14"><ArrowDownOutline style="transform: rotate(-90deg)" /></n-icon>
            </button>
            <button
              class="action-icon-btn danger"
              title="删除该页"
              @click="removePageCard(pIdx)"
            >
              <n-icon size="14"><TrashOutline /></n-icon>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.organize-wrapper {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.drop-empty-zone {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #ffffff;
}

.drop-empty-zone:hover {
  border-color: #3b82f6;
  background: #f8faff;
}

.empty-icon-circle {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: #eff6ff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.empty-title {
  margin: 0 0 6px 0;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.empty-desc {
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
}

.organize-workspace {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
}

.organize-top-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid #f1f5f9;
  background: #fafafa;
}

.top-tool-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.organize-doc-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-tool-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.loading-grid-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-thumbnail-grid {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  align-content: flex-start;
}

.page-card-item {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.page-card-item:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.12);
  transform: translateY(-2px);
}

.card-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
}

.page-index-pill {
  font-size: 12px;
  font-weight: 700;
  color: #1e293b;
}

.sub-num {
  font-size: 11px;
  font-weight: 400;
  color: #94a3b8;
}

.rotation-tag {
  font-size: 11px;
  font-weight: 600;
  color: #3b82f6;
  background: #eff6ff;
  padding: 1px 4px;
  border-radius: 4px;
}

.thumbnail-wrapper {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  padding: 8px;
  overflow: hidden;
}

.thumb-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
  border-radius: 2px;
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.card-bottom-actions {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 6px;
  border-top: 1px solid #f1f5f9;
  background: #ffffff;
}

.action-icon-btn {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.action-icon-btn:hover:not(:disabled) {
  background: #eff6ff;
  color: #3b82f6;
}

.action-icon-btn.danger:hover:not(:disabled) {
  background: #fee2e2;
  color: #ef4444;
}

.action-icon-btn:disabled {
  opacity: 0.25;
  cursor: not-allowed;
}
</style>
