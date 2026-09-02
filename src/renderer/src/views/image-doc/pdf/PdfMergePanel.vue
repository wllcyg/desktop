<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import {
  GitMergeOutline,
  CloudUploadOutline,
  TrashOutline,
  InformationCircleOutline,
  SettingsOutline,
  ChevronUpOutline,
  ChevronDownOutline,
  AddOutline
} from '@vicons/ionicons5'
import {
  MergeFileItem,
  formatFileSize,
  selectPdfFilesSafely,
  selectSavePathSafely,
  openPath,
  showInFolder
} from './types'

const message = useMessage()
const dialog = useDialog()

const mergeFileList = ref<MergeFileItem[]>([])
const isMerging = ref<boolean>(false)
const mergeConfig = reactive({
  autoToc: true,
  compress: true,
  outputFileName: '合并文档.pdf'
})

// 添加 PDF 文件
const handleAddMergeFiles = async () => {
  try {
    const filePaths = await selectPdfFilesSafely(true)
    if (!filePaths || filePaths.length === 0) return

    for (const p of filePaths) {
      if (mergeFileList.value.some((f) => f.path === p)) continue

      const filename = p.split(/[\\/]/).pop() || '未命名.pdf'
      const title = filename.replace(/\.pdf$/i, '')
      const item: MergeFileItem = {
        id: `${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
        name: filename,
        path: p,
        size: 0,
        totalPages: 0,
        pageRange: '全部',
        title: title,
        hasToc: false,
        isLoadingInfo: true
      }
      mergeFileList.value.push(item)
      fetchPdfInfoForMerge(item)
    }
  } catch (err: any) {
    message.error(`选择文件失败: ${err.message}`)
  }
}

// 异步读取信息
const fetchPdfInfoForMerge = async (item: MergeFileItem) => {
  try {
    // @ts-ignore
    const res = await window.electron?.ipcRenderer?.invoke('py:call', {
      method: 'pdf.get_info',
      params: { path: item.path, include_thumbnails: false }
    })
    item.totalPages = res.total_pages
    item.size = res.file_size
    item.hasToc = res.has_toc
  } catch (err: any) {
    console.error('读取 PDF 信息失败:', err)
  } finally {
    item.isLoadingInfo = false
  }
}

// 拖拽上传
const handleMergeDrop = (e: DragEvent) => {
  e.preventDefault()
  if (!e.dataTransfer?.files) return
  const files = Array.from(e.dataTransfer.files).filter((f) => f.name.toLowerCase().endsWith('.pdf'))
  if (files.length === 0) {
    message.warning('请拖拽有效的 PDF 文件')
    return
  }
  for (const f of files) {
    // @ts-ignore
    const filePath = f.path
    if (!filePath || mergeFileList.value.some((item) => item.path === filePath)) continue
    const title = f.name.replace(/\.pdf$/i, '')
    const item: MergeFileItem = {
      id: `${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      name: f.name,
      path: filePath,
      size: f.size,
      totalPages: 0,
      pageRange: '全部',
      title: title,
      hasToc: false,
      isLoadingInfo: true
    }
    mergeFileList.value.push(item)
    fetchPdfInfoForMerge(item)
  }
}

// 排序与列表操作
const moveMergeItem = (index: number, direction: 'up' | 'down') => {
  const list = [...mergeFileList.value]
  const target = list[index]
  if (!target) return
  list.splice(index, 1)
  if (direction === 'up' && index > 0) {
    list.splice(index - 1, 0, target)
  } else if (direction === 'down' && index < list.length) {
    list.splice(index + 1, 0, target)
  }
  mergeFileList.value = list
}

const removeMergeItem = (index: number) => {
  mergeFileList.value.splice(index, 1)
}

const clearMergeList = () => {
  mergeFileList.value = []
}

// 执行合并
const handleExecuteMerge = async () => {
  if (mergeFileList.value.length === 0) {
    message.warning('请先添加至少一个 PDF 文件')
    return
  }

  const saveName = mergeConfig.outputFileName.endsWith('.pdf')
    ? mergeConfig.outputFileName
    : `${mergeConfig.outputFileName}.pdf`
  const savePath = await selectSavePathSafely(saveName)
  if (!savePath) return

  isMerging.value = true
  try {
    const fileConfigs = mergeFileList.value.map((f) => ({
      path: f.path,
      title: f.title || f.name.replace(/\.pdf$/i, ''),
      page_range: f.pageRange === '全部' ? '' : f.pageRange
    }))

    // @ts-ignore
    const res = await window.electron?.ipcRenderer?.invoke('py:call', {
      method: 'pdf.merge',
      params: {
        files: fileConfigs,
        output_path: savePath,
        auto_generate_toc: mergeConfig.autoToc,
        compress: mergeConfig.compress
      }
    })

    if (res.success) {
      dialog.success({
        title: 'PDF 合并完成',
        content: `成功将 ${mergeFileList.value.length} 个文件合并为一份文档（共 ${res.total_pages} 页，大小: ${formatFileSize(res.file_size)}）。`,
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
      title: '合并失败',
      content: err.message || '合并过程中发生异常'
    })
  } finally {
    isMerging.value = false
  }
}
</script>

<template>
  <div class="pane-grid">
    <!-- 左侧/主体：文件列表区 -->
    <div class="main-list-card">
      <div class="card-toolbar">
        <div class="toolbar-left">
          <span class="toolbar-title">待合并文件列表</span>
          <n-badge :value="mergeFileList.length" type="info" :max="99" />
        </div>
        <div class="toolbar-right">
          <n-button size="small" type="primary" secondary @click="handleAddMergeFiles">
            <template #icon>
              <n-icon><AddOutline /></n-icon>
            </template>
            添加 PDF 文件
          </n-button>
          <n-button
            size="small"
            quaternary
            type="error"
            :disabled="mergeFileList.length === 0"
            @click="clearMergeList"
          >
            <template #icon>
              <n-icon><TrashOutline /></n-icon>
            </template>
            清空列表
          </n-button>
        </div>
      </div>

      <!-- 列表或空状态 -->
      <div
        v-if="mergeFileList.length === 0"
        class="drop-empty-zone"
        @dragover.prevent
        @drop="handleMergeDrop"
        @click="handleAddMergeFiles"
      >
        <div class="empty-icon-circle">
          <n-icon size="42" color="#3B82F6"><CloudUploadOutline /></n-icon>
        </div>
        <p class="empty-title">点击或拖拽多个 PDF 文件到此处</p>
        <p class="empty-desc">支持批量添加、列表排序、自定义截取特定页码合并</p>
      </div>

      <div
        v-else
        class="file-item-list"
        @dragover.prevent
        @drop="handleMergeDrop"
      >
        <div
          v-for="(item, index) in mergeFileList"
          :key="item.id"
          class="file-item-card"
        >
          <!-- 序号与拖拽排序按钮 -->
          <div class="item-order-box">
            <span class="order-badge">{{ index + 1 }}</span>
            <div class="order-actions">
              <button
                class="mini-action-btn"
                :disabled="index === 0"
                title="上移"
                @click="moveMergeItem(index, 'up')"
              >
                <n-icon size="13"><ChevronUpOutline /></n-icon>
              </button>
              <button
                class="mini-action-btn"
                :disabled="index === mergeFileList.length - 1"
                title="下移"
                @click="moveMergeItem(index, 'down')"
              >
                <n-icon size="13"><ChevronDownOutline /></n-icon>
              </button>
            </div>
          </div>

          <!-- 文件基本信息与输入项 -->
          <div class="item-info-col">
            <div class="item-header-row">
              <span class="file-name-text" :title="item.path">{{ item.name }}</span>
              <n-tag size="small" :bordered="false" type="info">
                {{ item.isLoadingInfo ? '读取中...' : `${item.totalPages} 页` }}
              </n-tag>
              <span class="file-size-text">{{ formatFileSize(item.size) }}</span>
            </div>

            <div class="item-form-row">
              <div class="form-sub-field flex-2">
                <span class="field-label">大纲目录名:</span>
                <n-input
                  v-model:value="item.title"
                  size="small"
                  placeholder="输入合并后的一级书签标题"
                />
              </div>

              <div class="form-sub-field flex-1">
                <span class="field-label">提取页码:</span>
                <n-input
                  v-model:value="item.pageRange"
                  size="small"
                  placeholder="全部 或 1-3, 5"
                />
              </div>
            </div>
          </div>

          <!-- 右侧删除 -->
          <div class="item-right-actions">
            <n-button
              size="small"
              quaternary
              circle
              type="error"
              title="移除此项"
              @click="removeMergeItem(index)"
            >
              <template #icon>
                <n-icon><TrashOutline /></n-icon>
              </template>
            </n-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：合并配置与执行卡片 -->
    <div class="side-config-card">
      <div class="config-header">
        <n-icon size="18" color="#3B82F6"><SettingsOutline /></n-icon>
        <span>合并导出配置</span>
      </div>

      <div class="config-body">
        <div class="config-item">
          <span class="config-label">默认输出文件名</span>
          <n-input
            v-model:value="mergeConfig.outputFileName"
            size="small"
            placeholder="请输入文件名"
          />
        </div>

        <div class="config-item switch-item">
          <div>
            <div class="switch-title">自动生成大纲书签</div>
            <div class="switch-desc">将各文件目录名自动生成为一级目录书签</div>
          </div>
          <n-switch v-model:value="mergeConfig.autoToc" size="small" />
        </div>

        <div class="config-item switch-item">
          <div>
            <div class="switch-title">压缩与冗余清理</div>
            <div class="switch-desc">深度清理未引用的冗余对象，减小输出体积</div>
          </div>
          <n-switch v-model:value="mergeConfig.compress" size="small" />
        </div>

        <div class="info-alert-box">
          <n-icon size="16" color="#3B82F6"><InformationCircleOutline /></n-icon>
          <span>将按照列表从上到下的顺序进行合并。可在左侧调整顺序。</span>
        </div>
      </div>

      <div class="config-footer">
        <n-button
          type="primary"
          block
          size="large"
          :loading="isMerging"
          :disabled="mergeFileList.length === 0"
          @click="handleExecuteMerge"
        >
          <template #icon>
            <n-icon><GitMergeOutline /></n-icon>
          </template>
          立即开始合并
        </n-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pane-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 16px;
  height: 100%;
  min-height: 0;
}

.main-list-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.card-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  background: #fafafa;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drop-empty-zone {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px dashed #cbd5e1;
  border-radius: 10px;
  margin: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fdfdfd;
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

.file-item-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.file-item-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  transition: all 0.15s ease;
}

.file-item-card:hover {
  border-color: #cbd5e1;
  background: #ffffff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.item-order-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.order-badge {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: #e2e8f0;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.order-actions {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mini-action-btn {
  width: 18px;
  height: 12px;
  border: none;
  background: #e2e8f0;
  color: #475569;
  border-radius: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.mini-action-btn:hover:not(:disabled) {
  background: #3b82f6;
  color: #ffffff;
}

.mini-action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.item-info-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.item-header-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-name-text {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 320px;
}

.file-size-text {
  font-size: 12px;
  color: #94a3b8;
}

.item-form-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.form-sub-field {
  display: flex;
  align-items: center;
  gap: 6px;
}

.flex-1 {
  flex: 1;
}

.flex-2 {
  flex: 1.5;
}

.field-label {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

.side-config-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.config-header {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-body {
  flex: 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.config-label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.switch-item {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
}

.switch-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.switch-desc {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.info-alert-box {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  color: #1e40af;
  line-height: 1.5;
}

.config-footer {
  padding: 16px;
  border-top: 1px solid #f1f5f9;
}
</style>
