<script setup lang="ts">
import {
  TrashOutline,
  AlertCircleOutline,
  CheckmarkCircleOutline,
  CloudUploadOutline,
  FolderOpenOutline,
  RefreshOutline
} from '@vicons/ionicons5'
import { RenameFileItem } from '../types'

const props = defineProps<{
  fileList: RenameFileItem[]
  hasConflict: boolean
  isProcessing: boolean
}>()

const emit = defineEmits<{
  (e: 'remove-item', index: number): void
  (e: 'retry-single', item: RenameFileItem): void
  (e: 'trigger-upload'): void
  (e: 'drop-files', ev: DragEvent): void
}>()

// 打开文件所在目录
const handleOpenFolder = async (path: string) => {
  // @ts-ignore
  await window.electron?.ipcRenderer?.invoke('shell:show-item-in-folder', path)
}
</script>

<template>
  <div class="preview-table-card">
    <div class="table-header-bar">
      <div class="th-left">
        <span class="th-title">重命名实时对照表</span>
        <n-badge :value="fileList.length" type="info" :max="999" />
      </div>

      <div class="th-right">
        <div v-if="hasConflict" class="conflict-warning-pill">
          <n-icon size="14" color="#EF4444"><AlertCircleOutline /></n-icon>
          <span>检测到重名冲突！请调整规则避免文件覆盖</span>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div
      v-if="fileList.length === 0"
      class="drop-empty-zone"
      @dragover.prevent
      @drop="emit('drop-files', $event)"
      @click="emit('trigger-upload')"
    >
      <div class="empty-icon-circle">
        <n-icon size="42" color="#3B82F6"><CloudUploadOutline /></n-icon>
      </div>
      <p class="empty-title">点击或拖拽任意文件到此处</p>
      <p class="empty-desc">支持批量导入任意格式文件、左侧规则实时计算新名称并预防文件占用</p>
    </div>

    <!-- 数据表格 -->
    <div
      v-else
      class="table-scroll-container"
      @dragover.prevent
      @drop="emit('drop-files', $event)"
    >
      <table class="rename-table">
        <thead>
          <tr>
            <th style="width: 44px">#</th>
            <th style="width: 40%">原文件名</th>
            <th style="width: 40%">重命名后名称</th>
            <th style="width: 120px">状态</th>
            <th style="width: 70px; text-align: center">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(item, idx) in fileList"
            :key="item.id"
            :class="{
              'row-conflict': item.isConflict,
              'row-success': item.status === 'success',
              'row-locked': item.status === 'locked' || item.status === 'error'
            }"
          >
            <!-- 序号 -->
            <td class="col-index">{{ idx + 1 }}</td>

            <!-- 原文件名 -->
            <td class="col-original">
              <span class="filename-text" :title="item.fullPath">{{ item.originalName }}</span>
            </td>

            <!-- 重命名后名称 -->
            <td class="col-new">
              <div class="new-name-box">
                <span
                  class="filename-text"
                  :class="{
                    'text-changed': item.isChanged && !item.isConflict,
                    'text-conflict': item.isConflict,
                    'text-unchanged': !item.isChanged
                  }"
                  :title="item.newFullPath"
                >
                  {{ item.newName }}
                </span>

                <n-tag
                  v-if="item.isConflict"
                  size="tiny"
                  type="error"
                  round
                  class="conflict-tag"
                >
                  同名冲突
                </n-tag>
              </div>
            </td>

            <!-- 状态 -->
            <td class="col-status">
              <n-tag v-if="item.status === 'success'" size="tiny" type="success" round>
                <template #icon><n-icon :component="CheckmarkCircleOutline" /></template>
                已完成
              </n-tag>

              <n-tooltip v-else-if="item.status === 'locked'" trigger="hover">
                <template #trigger>
                  <n-tag size="tiny" type="error" round class="cursor-pointer">
                    <template #icon><n-icon :component="AlertCircleOutline" /></template>
                    文件被占用
                  </n-tag>
                </template>
                {{ item.errorMsg || '文件正在被其他程序打开，请关闭后点击重试' }}
              </n-tooltip>

              <n-tooltip v-else-if="item.status === 'error'" trigger="hover">
                <template #trigger>
                  <n-tag size="tiny" type="warning" round class="cursor-pointer">
                    失败
                  </n-tag>
                </template>
                {{ item.errorMsg }}
              </n-tooltip>

              <n-tag v-else-if="item.isChanged" size="tiny" type="info" round>
                待变更
              </n-tag>

              <n-tag v-else size="tiny" depth="3" round>
                无变动
              </n-tag>
            </td>

            <!-- 操作 -->
            <td class="col-action">
              <div class="action-btn-row">
                <!-- 重试单个被占用的文件 -->
                <button
                  v-if="item.status === 'locked' || item.status === 'error'"
                  class="icon-action-btn"
                  title="关闭占用程序后重试"
                  @click="emit('retry-single', item)"
                >
                  <n-icon size="13" color="#3B82F6"><RefreshOutline /></n-icon>
                </button>

                <!-- 定位文件 -->
                <button
                  class="icon-action-btn"
                  title="在资源管理器中定位"
                  @click="handleOpenFolder(item.status === 'success' ? item.newFullPath : item.fullPath)"
                >
                  <n-icon size="13"><FolderOpenOutline /></n-icon>
                </button>

                <!-- 移除单项 -->
                <button
                  class="icon-action-btn danger"
                  title="从列表移除"
                  @click="emit('remove-item', idx)"
                >
                  <n-icon size="13"><TrashOutline /></n-icon>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.preview-table-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.table-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  background: #fafafa;
}

.th-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.th-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.conflict-warning-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 12px;
  color: #b91c1c;
  font-weight: 600;
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

.table-scroll-container {
  flex: 1;
  overflow-y: auto;
}

.rename-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  text-align: left;
}

.rename-table th {
  background: #f8fafc;
  padding: 10px 12px;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.rename-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f1f5f9;
  color: #1e293b;
}

.rename-table tr:hover td {
  background: #f8fafc;
}

.row-conflict td {
  background: #fff1f2 !important;
}

.row-locked td {
  background: #fffbeb !important;
}

.col-index {
  color: #94a3b8;
  font-weight: 600;
}

.filename-text {
  display: block;
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.new-name-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.text-changed {
  color: #059669;
  font-weight: 600;
}

.text-conflict {
  color: #dc2626;
  font-weight: 700;
}

.text-unchanged {
  color: #64748b;
}

.conflict-tag {
  flex-shrink: 0;
}

.action-btn-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.icon-action-btn {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  border: none;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.icon-action-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.icon-action-btn.danger:hover {
  background: #fee2e2;
  color: #ef4444;
}

.cursor-pointer {
  cursor: pointer;
}
</style>
