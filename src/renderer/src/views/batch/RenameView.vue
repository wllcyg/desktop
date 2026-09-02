<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import {
  SparklesOutline,
  AddOutline,
  TrashOutline,
  ReloadOutline,
  DocumentTextOutline
} from '@vicons/ionicons5'
import {
  RenameFileItem,
  RenameMode,
  PatternRuleConfig,
  ReplaceRuleConfig,
  AffixRuleConfig,
  RollbackRecord,
  selectAnyFilesSafely,
  parseFilePath
} from './rename/types'
import { useRenameRule } from './rename/composables/useRenameRule'
import RenameRulePanel from './rename/components/RenameRulePanel.vue'
import RenamePreviewTable from './rename/components/RenamePreviewTable.vue'

const message = useMessage()
const dialog = useDialog()

// 文件列表
const fileList = ref<RenameFileItem[]>([])
const isProcessing = ref<boolean>(false)
const lastRollbackStack = ref<RollbackRecord[]>([])

// 规则模式
const currentMode = ref<RenameMode>('pattern')

const patternConfig = reactive<PatternRuleConfig>({
  template: '[原文件名]_[序号2位]',
  startNumber: 1,
  step: 1,
  digits: 2,
  datePattern: 'YYYY-MM-DD'
})

const replaceConfig = reactive<ReplaceRuleConfig>({
  findText: '',
  replaceText: '',
  useRegex: false,
  caseSensitive: false
})

const affixConfig = reactive<AffixRuleConfig>({
  prefix: '',
  suffix: '',
  trimLeftCount: 0,
  trimRightCount: 0,
  extCase: 'keep'
})

// 使用规则计算 Composable
const { computedList, hasConflict, changedCount } = useRenameRule(
  fileList,
  currentMode,
  patternConfig,
  replaceConfig,
  affixConfig
)

// 选择文件
const handleAddFiles = async () => {
  try {
    const filePaths = await selectAnyFilesSafely(true)
    if (!filePaths || filePaths.length === 0) return

    for (const p of filePaths) {
      if (fileList.value.some((f) => f.fullPath === p)) continue
      const { dirPath, originalName, baseName, ext } = parseFilePath(p)
      fileList.value.push({
        id: `${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
        originalName,
        baseName,
        ext,
        dirPath,
        fullPath: p,
        newName: originalName,
        newFullPath: p,
        status: 'pending'
      })
    }
  } catch (err: any) {
    message.error(`选择文件失败: ${err.message}`)
  }
}

// 拖拽上传
const handleDropFiles = (e: DragEvent) => {
  e.preventDefault()
  if (!e.dataTransfer?.files) return
  for (const f of Array.from(e.dataTransfer.files)) {
    // @ts-ignore
    const filePath = f.path
    if (!filePath || fileList.value.some((item) => item.fullPath === filePath)) continue
    const { dirPath, originalName, baseName, ext } = parseFilePath(filePath)
    fileList.value.push({
      id: `${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      originalName,
      baseName,
      ext,
      dirPath,
      fullPath: filePath,
      newName: originalName,
      newFullPath: filePath,
      status: 'pending'
    })
  }
}

const removeFileItem = (index: number) => {
  fileList.value.splice(index, 1)
}

const clearAll = () => {
  fileList.value = []
  lastRollbackStack.value = []
}

// 执行重命名
const handleExecuteRename = async () => {
  if (fileList.value.length === 0) {
    message.warning('请先添加需要重命名的文件')
    return
  }

  if (hasConflict.value) {
    message.error('检测到同名冲突，请调整规则消除冲突后再执行')
    return
  }

  const pairsToRename = computedList.value
    .filter((item) => item.isChanged)
    .map((item) => ({
      id: item.id,
      old_path: item.fullPath,
      new_path: item.newFullPath
    }))

  if (pairsToRename.length === 0) {
    message.info('所有文件名均未发生变化，无需重命名')
    return
  }

  isProcessing.value = true
  try {
    // @ts-ignore
    const res = await window.electron.ipcRenderer.invoke('py:call', {
      method: 'file.batch_rename',
      params: { pairs: pairsToRename }
    })

    if (res?.results) {
      const resultMap = new Map<string, any>()
      res.results.forEach((r: any) => resultMap.set(r.id, r))

      // 更新列表项的状态与新路径
      fileList.value.forEach((item) => {
        const r = resultMap.get(item.id)
        if (r) {
          if (r.success) {
            item.status = 'success'
            item.fullPath = item.newFullPath
            const parsed = parseFilePath(item.newFullPath)
            item.originalName = parsed.originalName
            item.baseName = parsed.baseName
            item.ext = parsed.ext
          } else {
            item.status = r.error_type === 'locked' ? 'locked' : 'error'
            item.errorMsg = r.error_msg
          }
        }
      })

      if (res.rollback_records && res.rollback_records.length > 0) {
        lastRollbackStack.value = res.rollback_records
      }

      if (res.failed_count === 0) {
        message.success(`批量重命名完成！成功重命名 ${res.success_count} 个文件`)
      } else {
        dialog.warning({
          title: '重命名部分完成',
          content: `成功 ${res.success_count} 个，失败 ${res.failed_count} 个。\n失败原因通常为【文件正在被 Word/WPS/图片查看器占用】。请关闭占用软件后点击单项重试。`,
          positiveText: '知道了'
        })
      }
    }
  } catch (err: any) {
    message.error(`执行重命名失败: ${err.message}`)
  } finally {
    isProcessing.value = false
  }
}

// 单项重试（针对文件被占用解除后）
const handleRetrySingle = async (item: RenameFileItem) => {
  try {
    // @ts-ignore
    const res = await window.electron.ipcRenderer.invoke('py:call', {
      method: 'file.batch_rename',
      params: {
        pairs: [{ id: item.id, old_path: item.fullPath, new_path: item.newFullPath }]
      }
    })
    const single = res.results?.[0]
    if (single?.success) {
      item.status = 'success'
      item.fullPath = item.newFullPath
      const parsed = parseFilePath(item.newFullPath)
      item.originalName = parsed.originalName
      item.baseName = parsed.baseName
      item.ext = parsed.ext
      message.success(`文件 ${item.originalName} 重命名成功`)
    } else {
      item.status = single?.error_type === 'locked' ? 'locked' : 'error'
      item.errorMsg = single?.error_msg || '重试失败'
      message.error(item.errorMsg!)
    }
  } catch (err: any) {
    message.error(`重试失败: ${err.message}`)
  }
}

// 一键撤销重命名
const handleUndoRename = async () => {
  if (lastRollbackStack.value.length === 0) {
    message.info('当前无可撤销的历史记录')
    return
  }

  try {
    // @ts-ignore
    const res = await window.electron.ipcRenderer.invoke('py:call', {
      method: 'file.undo_rename',
      params: { records: lastRollbackStack.value }
    })

    if (res.success) {
      message.success(`已成功撤销并还原 ${res.restored_count} 个文件！`)
      lastRollbackStack.value = []
      // 重新刷新列表对应文件信息
      fileList.value.forEach((item) => {
        item.status = 'pending'
      })
    } else {
      message.error(`撤销完成但有 ${res.failed_count} 个文件还原失败`)
    }
  } catch (err: any) {
    message.error(`撤销失败: ${err.message}`)
  }
}
</script>

<template>
  <div class="rename-page-container">
    <!-- 顶部状态栏 -->
    <div class="top-header-section">
      <div class="header-left">
        <div class="icon-circle">
          <n-icon size="24" color="#0284C7"><DocumentTextOutline /></n-icon>
        </div>
        <div>
          <h1 class="page-title">文件批量重命名</h1>
          <p class="page-subtitle">按规则批量规范化文件名 · 实时冲突检测 · 智能防占用隔离与一键撤销</p>
        </div>
      </div>

      <div class="header-right">
        <n-button
          v-if="lastRollbackStack.length > 0"
          size="small"
          secondary
          type="warning"
          @click="handleUndoRename"
        >
          <template #icon><n-icon><ReloadOutline /></n-icon></template>
          一键撤销上一步 ({{ lastRollbackStack.length }})
        </n-button>
        <n-button size="small" type="primary" secondary @click="handleAddFiles">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          添加文件
        </n-button>
        <n-button
          size="small"
          quaternary
          type="error"
          :disabled="fileList.length === 0"
          @click="clearAll"
        >
          <template #icon><n-icon><TrashOutline /></n-icon></template>
          清空
        </n-button>
        <n-button
          type="primary"
          size="small"
          :loading="isProcessing"
          :disabled="fileList.length === 0 || hasConflict || changedCount === 0"
          @click="handleExecuteRename"
        >
          <template #icon><n-icon><SparklesOutline /></n-icon></template>
          立即重命名 ({{ changedCount }})
        </n-button>
      </div>
    </div>

    <!-- 主工作区：左侧规则面板 + 右侧实时对比表格 -->
    <div class="main-body-grid">
      <RenameRulePanel
        v-model:mode="currentMode"
        :pattern-config="patternConfig"
        :replace-config="replaceConfig"
        :affix-config="affixConfig"
        class="left-rule-col"
      />

      <RenamePreviewTable
        :file-list="computedList"
        :has-conflict="hasConflict"
        :is-processing="isProcessing"
        class="right-table-col"
        @remove-item="removeFileItem"
        @retry-single="handleRetrySingle"
        @trigger-upload="handleAddFiles"
        @drop-files="handleDropFiles"
      />
    </div>
  </div>
</template>

<style scoped>
.rename-page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: #f8fafc;
  padding: 16px 20px 20px 20px;
  box-sizing: border-box;
  overflow: hidden;
}

.top-header-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.icon-circle {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.page-subtitle {
  margin: 2px 0 0 0;
  font-size: 12px;
  color: #64748b;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.main-body-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 16px;
}

.left-rule-col {
  height: 100%;
}

.right-table-col {
  height: 100%;
}
</style>
