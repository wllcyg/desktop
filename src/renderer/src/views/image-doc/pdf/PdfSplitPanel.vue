<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import {
  DocumentTextOutline,
  FolderOpenOutline,
  InformationCircleOutline,
  ReaderOutline
} from '@vicons/ionicons5'
import {
  SplitDocInfo,
  formatFileSize,
  selectPdfFilesSafely,
  openPath
} from './types'

const message = useMessage()
const dialog = useDialog()

const currentSplitDoc = ref<SplitDocInfo | null>(null)
const isSplitting = ref<boolean>(false)
const isLoadingSplitDoc = ref<boolean>(false)

// 拆分模式: 'by_chunk' | 'by_range' | 'by_odd_even' | 'by_toc'
const splitMode = ref<'by_chunk' | 'by_range' | 'by_odd_even' | 'by_toc'>('by_chunk')
const chunkPageSize = ref<number>(1)
const customRangeStr = ref<string>('1-2, 3-5')
const mergeRangeResult = ref<boolean>(false)

const handleSelectSplitDoc = async () => {
  try {
    const filePaths = await selectPdfFilesSafely(false)
    if (!filePaths || filePaths.length === 0) return
    loadSplitDoc(filePaths[0])
  } catch (err: any) {
    message.error(`选择文件失败: ${err.message}`)
  }
}

const handleSplitDrop = (e: DragEvent) => {
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
    loadSplitDoc(filePath)
  }
}

const loadSplitDoc = async (pdfPath: string) => {
  isLoadingSplitDoc.value = true
  try {
    // @ts-ignore
    const res = await window.electron?.ipcRenderer?.invoke('py:call', {
      method: 'pdf.get_info',
      params: { path: pdfPath, include_thumbnails: false }
    })
    currentSplitDoc.value = {
      name: res.file_name,
      path: res.file_path,
      size: res.file_size,
      totalPages: res.total_pages,
      hasToc: res.has_toc,
      toc: res.toc || []
    }
    if (res.total_pages >= 2) {
      customRangeStr.value = `1-${Math.min(2, res.total_pages)}, ${Math.min(3, res.total_pages)}-${res.total_pages}`
    } else {
      customRangeStr.value = '1'
    }
  } catch (err: any) {
    message.error(`解析 PDF 失败: ${err.message}`)
    currentSplitDoc.value = null
  } finally {
    isLoadingSplitDoc.value = false
  }
}

// 拆分预估数量
const estimatedSplitCount = computed(() => {
  if (!currentSplitDoc.value) return 0
  const total = currentSplitDoc.value.totalPages

  if (splitMode.value === 'by_chunk') {
    const size = Math.max(1, chunkPageSize.value)
    return Math.ceil(total / size)
  } else if (splitMode.value === 'by_range') {
    if (mergeRangeResult.value) return 1
    const parts = customRangeStr.value.split(/[,，]/).filter((p) => p.trim())
    return parts.length
  } else if (splitMode.value === 'by_odd_even') {
    return total >= 2 ? 2 : 1
  } else if (splitMode.value === 'by_toc') {
    const l1 = currentSplitDoc.value.toc.filter((t) => t.level === 1)
    return l1.length
  }
  return 0
})

// 执行拆分
const handleExecuteSplit = async () => {
  if (!currentSplitDoc.value) {
    message.warning('请先导入需要拆分的 PDF 文件')
    return
  }

  if (splitMode.value === 'by_toc') {
    const l1 = currentSplitDoc.value.toc.filter((t) => t.level === 1)
    if (l1.length === 0) {
      message.error('该文档没有检测到一级目录大纲，无法按章节拆分')
      return
    }
  }

  // @ts-ignore
  const outputDir: string = await window.electron?.ipcRenderer?.invoke('dialog:select-directory')
  if (!outputDir) return

  isSplitting.value = true
  try {
    let params: Record<string, any> = {}
    if (splitMode.value === 'by_chunk') {
      params = { chunk_size: chunkPageSize.value }
    } else if (splitMode.value === 'by_range') {
      params = { range_str: customRangeStr.value, merge_result: mergeRangeResult.value }
    } else if (splitMode.value === 'by_odd_even') {
      params = {}
    } else if (splitMode.value === 'by_toc') {
      params = {}
    }

    // @ts-ignore
    const res = await window.electron?.ipcRenderer?.invoke('py:call', {
      method: 'pdf.split',
      params: {
        path: currentSplitDoc.value.path,
        split_mode: splitMode.value,
        params,
        output_dir: outputDir
      }
    })

    if (res.success) {
      dialog.success({
        title: 'PDF 拆分完成',
        content: `成功生成 ${res.total_files} 个 PDF 文件，已保存至目标目录。`,
        positiveText: '打开输出目录',
        negativeText: '知道了',
        onPositiveClick: () => {
          openPath(outputDir)
        }
      })
    }
  } catch (err: any) {
    dialog.error({
      title: '拆分失败',
      content: err.message || '拆分过程中发生异常'
    })
  } finally {
    isSplitting.value = false
  }
}
</script>

<template>
  <div class="pane-grid">
    <!-- 左侧/主体：文档选择与拆分模式 -->
    <div class="main-list-card">
      <div class="card-toolbar">
        <div class="toolbar-left">
          <span class="toolbar-title">待拆分 PDF 来源</span>
        </div>
        <div class="toolbar-right">
          <n-button
            v-if="currentSplitDoc"
            size="small"
            secondary
            type="primary"
            @click="handleSelectSplitDoc"
          >
            更换文档
          </n-button>
        </div>
      </div>

      <!-- 未导入时 -->
      <div
        v-if="!currentSplitDoc"
        class="drop-empty-zone"
        @dragover.prevent
        @drop="handleSplitDrop"
        @click="handleSelectSplitDoc"
      >
        <div class="empty-icon-circle">
          <n-icon size="42" color="#3B82F6"><DocumentTextOutline /></n-icon>
        </div>
        <p class="empty-title">点击或拖拽单个 PDF 文件到此处进行拆分</p>
        <p class="empty-desc">支持按固定页数、按页码范围区间、奇偶页分离、按大纲章节拆分</p>
      </div>

      <!-- 已导入时展示详情与拆分配置 -->
      <div v-else class="split-setup-container">
        <!-- 文件摘要栏 -->
        <div class="doc-summary-bar">
          <div class="doc-summary-left">
            <div class="doc-badge-icon">
              <n-icon size="24" color="#3B82F6"><DocumentTextOutline /></n-icon>
            </div>
            <div>
              <div class="doc-title-text" :title="currentSplitDoc.path">
                {{ currentSplitDoc.name }}
              </div>
              <div class="doc-meta-sub">
                <span>总页数: <strong>{{ currentSplitDoc.totalPages }}</strong> 页</span>
                <span class="dot-divider">·</span>
                <span>大小: {{ formatFileSize(currentSplitDoc.size) }}</span>
                <span class="dot-divider">·</span>
                <span v-if="currentSplitDoc.hasToc" class="toc-badge-text">
                  含大纲书签 ({{ currentSplitDoc.toc.filter(t=>t.level===1).length }} 个章节)
                </span>
                <span v-else class="text-gray-400">无内嵌大纲</span>
              </div>
            </div>
          </div>
          <n-button quaternary size="small" type="error" @click="currentSplitDoc = null">
            移除
          </n-button>
        </div>

        <!-- 拆分模式选择卡片组 -->
        <div class="split-modes-section">
          <div class="section-title-bar">选择拆分策略</div>

          <div class="modes-card-grid">
            <!-- 模式 1: 按固定页数 -->
            <div
              class="mode-select-card"
              :class="{ active: splitMode === 'by_chunk' }"
              @click="splitMode = 'by_chunk'"
            >
              <div class="mode-header">
                <div class="mode-radio-icon" />
                <span class="mode-name">按固定页数拆分</span>
              </div>
              <p class="mode-tip">每 N 页切分为一个独立文件（如每 1 页拆一个）</p>

              <div v-if="splitMode === 'by_chunk'" class="mode-custom-input" @click.stop>
                <span class="input-tip">每隔页数:</span>
                <n-input-number
                  v-model:value="chunkPageSize"
                  size="small"
                  :min="1"
                  :max="currentSplitDoc.totalPages"
                  style="width: 110px"
                />
                <span class="unit-text">页 / 份</span>
              </div>
            </div>

            <!-- 模式 2: 按自定义页码区间 -->
            <div
              class="mode-select-card"
              :class="{ active: splitMode === 'by_range' }"
              @click="splitMode = 'by_range'"
            >
              <div class="mode-header">
                <div class="mode-radio-icon" />
                <span class="mode-name">按自定义页码区间</span>
              </div>
              <p class="mode-tip">提取指定页码段（例如: 1-3, 5, 8-10）</p>

              <div v-if="splitMode === 'by_range'" class="mode-custom-input vertical" @click.stop>
                <n-input
                  v-model:value="customRangeStr"
                  size="small"
                  placeholder="例如: 1-3, 5, 8-10"
                />
                <div class="range-switch-row">
                  <n-checkbox v-model:checked="mergeRangeResult" size="small">
                    将提取的所有页合并为一个独立文件
                  </n-checkbox>
                </div>
              </div>
            </div>

            <!-- 模式 3: 奇偶页分离 -->
            <div
              class="mode-select-card"
              :class="{ active: splitMode === 'by_odd_even' }"
              @click="splitMode = 'by_odd_even'"
            >
              <div class="mode-header">
                <div class="mode-radio-icon" />
                <span class="mode-name">奇数 / 偶数页分离</span>
              </div>
              <p class="mode-tip">将奇数页与偶数页分别导出为 2 份文档</p>
            </div>

            <!-- 模式 4: 按目录大纲章节 -->
            <div
              class="mode-select-card"
              :class="{
                active: splitMode === 'by_toc',
                disabled: !currentSplitDoc.hasToc
              }"
              @click="currentSplitDoc.hasToc && (splitMode = 'by_toc')"
            >
              <div class="mode-header">
                <div class="mode-radio-icon" />
                <span class="mode-name">按大纲书签章节拆分</span>
              </div>
              <p class="mode-tip">
                {{
                  currentSplitDoc.hasToc
                    ? `按 ${currentSplitDoc.toc.filter((t) => t.level === 1).length} 个一级大纲切分并以章节命名`
                    : '当前 PDF 无目录大纲书签，不可用'
                }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：拆分预估与执行卡片 -->
    <div class="side-config-card">
      <div class="config-header">
        <n-icon size="18" color="#3B82F6"><ReaderOutline /></n-icon>
        <span>拆分产物预估</span>
      </div>

      <div class="config-body">
        <div class="estimate-stat-box">
          <div class="stat-number-text">{{ estimatedSplitCount }}</div>
          <div class="stat-desc-text">预计生成 PDF 文件数量</div>
        </div>

        <div class="summary-list-box">
          <div class="summary-row">
            <span class="k">来源文档:</span>
            <span class="v" :title="currentSplitDoc?.name || '-'">{{ currentSplitDoc?.name || '未选择' }}</span>
          </div>
          <div class="summary-row">
            <span class="k">文档总页数:</span>
            <span class="v">{{ currentSplitDoc ? `${currentSplitDoc.totalPages} 页` : '-' }}</span>
          </div>
          <div class="summary-row">
            <span class="k">拆分策略:</span>
            <span class="v font-medium">
              {{
                splitMode === 'by_chunk'
                  ? `按每 ${chunkPageSize} 页切分`
                  : splitMode === 'by_range'
                    ? `区间提取 (${mergeRangeResult ? '合并单文件' : '切为多个文件'})`
                    : splitMode === 'by_odd_even'
                      ? '奇数页/偶数页分别导出'
                      : '按一级大纲章节拆分'
              }}
            </span>
          </div>
        </div>

        <div class="info-alert-box">
          <n-icon size="16" color="#3B82F6"><InformationCircleOutline /></n-icon>
          <span>点击下方按钮选择目标保存文件夹，系统将在后台完成秒级切分。</span>
        </div>
      </div>

      <div class="config-footer">
        <n-button
          type="primary"
          block
          size="large"
          :loading="isSplitting"
          :disabled="!currentSplitDoc || estimatedSplitCount === 0"
          @click="handleExecuteSplit"
        >
          <template #icon>
            <n-icon><FolderOpenOutline /></n-icon>
          </template>
          选择目标目录并拆分
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

.split-setup-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.doc-summary-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
}

.doc-summary-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.doc-badge-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.doc-title-text {
  font-size: 14px;
  font-weight: 700;
  color: #1e3a8a;
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-meta-sub {
  font-size: 12px;
  color: #3b82f6;
  margin-top: 2px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot-divider {
  color: #93c5fd;
}

.toc-badge-text {
  color: #059669;
  font-weight: 500;
}

.split-modes-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title-bar {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.modes-card-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.mode-select-card {
  border: 1.5px solid #e2e8f0;
  background: #ffffff;
  border-radius: 10px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mode-select-card:hover:not(.disabled) {
  border-color: #93c5fd;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.08);
}

.mode-select-card.active {
  border-color: #3b82f6;
  background: #f8faff;
}

.mode-select-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f8fafc;
}

.mode-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-radio-icon {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid #cbd5e1;
  background: #ffffff;
  transition: all 0.15s ease;
}

.mode-select-card.active .mode-radio-icon {
  border-color: #3b82f6;
  background: #3b82f6;
  box-shadow: inset 0 0 0 2.5px #ffffff;
}

.mode-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.mode-tip {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.4;
}

.mode-custom-input {
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px dashed #e2e8f0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.mode-custom-input.vertical {
  flex-direction: column;
  align-items: stretch;
}

.range-switch-row {
  margin-top: 4px;
}

.input-tip {
  font-size: 12px;
  color: #64748b;
}

.unit-text {
  font-size: 12px;
  color: #64748b;
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

.estimate-stat-box {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}

.stat-number-text {
  font-size: 28px;
  font-weight: 800;
  color: #1d4ed8;
}

.stat-desc-text {
  font-size: 12px;
  color: #3b82f6;
  margin-top: 2px;
}

.summary-list-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #f8fafc;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #475569;
}

.summary-row .k {
  color: #94a3b8;
}

.summary-row .v {
  font-weight: 600;
  color: #1e293b;
  max-width: 170px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
