<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useMessage } from 'naive-ui'
import {
  HardwareChipOutline,
  CloudDownloadOutline,
  CheckmarkCircle,
  AlertCircle,
  PlayOutline,
  TrashOutline,
  RefreshOutline,
  FolderOpenOutline,
  SpeedometerOutline,
  LayersOutline,
  SparklesOutline
} from '@vicons/ionicons5'

const message = useMessage()

interface ModelItem {
  id: string
  name: string
  tag: string
  description: string
  filename: string
  sizeBytes: number
  sizeFormatted: string
  isEssential: boolean
  isDownloaded: boolean
  localPath: string | null
  actualSizeBytes: number
  isDownloading: boolean
  downloadPercent?: number
  downloadSpeed?: string
  isVerifying?: boolean
  isReadyRunning?: boolean
  warmupCostMs?: number
  lastError?: string
}

const models = ref<ModelItem[]>([])
const storageDir = ref<string>('')
const isLoading = ref<boolean>(false)

// 统计数据
const installedCount = computed(() => models.value.filter((m) => m.isDownloaded).length)
const totalDiskBytes = computed(() =>
  models.value.reduce((acc, cur) => acc + (cur.isDownloaded ? cur.actualSizeBytes || cur.sizeBytes : 0), 0)
)
const totalDiskFormatted = computed(() => {
  const mb = totalDiskBytes.value / (1024 * 1024)
  if (mb > 1024) {
    return `${(mb / 1024).toFixed(2)} GB`
  }
  return `${mb.toFixed(1)} MB`
})

// 加载所有模型状态 (同时同步磁盘文件与 Python 内存常驻会话)
const fetchModelStatus = async () => {
  if (!window.electron?.ipcRenderer) return
  try {
    isLoading.value = true
    const res = await window.electron.ipcRenderer.invoke('model:get-all-status')

    // 尝试获取 Python 端的实际载入状态
    let pyStatusMap: Record<string, any> = {}
    try {
      const pyRes = await window.electron.ipcRenderer.invoke('py:call', {
        method: 'model.get_status',
        params: {}
      })
      if (pyRes && typeof pyRes === 'object') {
        pyStatusMap = pyRes
      }
    } catch (e) {
      // ignore
    }

    if (res?.models) {
      storageDir.value = res.storageDir || ''
      models.value = res.models.map((m: any) => {
        const existing = models.value.find((e) => e.id === m.id)
        const pyLoaded = Boolean(pyStatusMap[m.id]?.loaded)
        return {
          ...m,
          downloadPercent: existing?.downloadPercent || 0,
          downloadSpeed: existing?.downloadSpeed || '',
          isVerifying: false,
          isReadyRunning: pyLoaded || existing?.isReadyRunning || false,
          warmupCostMs: existing?.warmupCostMs,
          lastError: existing?.lastError
        }
      })
    }
  } catch (err: any) {
    console.error('获取模型状态失败:', err)
  } finally {
    isLoading.value = false
  }
}

// 启动/校验指定模型
const verifyAndStartModel = async (item: ModelItem) => {
  if (!item.isDownloaded) {
    message.warning('请先下载模型后再执行启动校验')
    return
  }

  item.isVerifying = true
  item.lastError = undefined

  try {
    const res = await window.electron.ipcRenderer.invoke('py:call', {
      method: 'model.verify_and_start',
      params: { model_id: item.id }
    })

    if (res?.success) {
      item.isReadyRunning = true
      item.warmupCostMs = res.warmup_cost_ms
      message.success(`【${item.name}】已成功启动并完成热加载验证 (耗时: ${res.warmup_cost_ms}ms)`)
    } else {
      item.isReadyRunning = false
      item.lastError = res?.error || '启动校验失败'
      message.error(`【${item.name}】启动异常: ${item.lastError}`)
    }
  } catch (err: any) {
    item.isReadyRunning = false
    item.lastError = err?.message || '通信异常'
    message.error(`启动失败: ${item.lastError}`)
  } finally {
    item.isVerifying = false
  }
}

// 一键启动/校验所有已下载模型
const verifyAllInstalled = async () => {
  const installed = models.value.filter((m) => m.isDownloaded)
  if (installed.length === 0) {
    message.warning('当前暂无已下载的模型可启动')
    return
  }

  message.info(`正在依次启动并校验 ${installed.length} 个本地模型...`)
  for (const item of installed) {
    await verifyAndStartModel(item)
  }
}

// 开始下载
const startDownload = async (item: ModelItem) => {
  item.isDownloading = true
  item.downloadPercent = 0
  item.downloadSpeed = '连接中...'
  item.lastError = undefined

  try {
    const res = await window.electron.ipcRenderer.invoke('model:start-download', item.id)
    if (res?.success) {
      message.info(`已开始下载: ${item.name}`)
    }
  } catch (err: any) {
    item.isDownloading = false
    message.error(err?.message || '启动下载失败')
  }
}

// 取消下载
const cancelDownload = async (item: ModelItem) => {
  try {
    await window.electron.ipcRenderer.invoke('model:cancel-download', item.id)
    item.isDownloading = false
    item.downloadPercent = 0
    message.info(`已取消下载: ${item.name}`)
  } catch (err: any) {
    message.error(err?.message || '取消下载失败')
  }
}

// 删除模型文件
const deleteModel = async (item: ModelItem) => {
  try {
    const res = await window.electron.ipcRenderer.invoke('model:delete-file', item.id)
    if (res?.success) {
      item.isDownloaded = false
      item.isReadyRunning = false
      item.localPath = null
      message.success(`已删除 ${item.name}，释放空间`)
      fetchModelStatus()
    } else {
      message.error(res?.message || '删除失败')
    }
  } catch (err: any) {
    message.error(err?.message || '删除失败')
  }
}

// 打开模型存放目录
const openStorageFolder = async () => {
  if (!storageDir.value) return
  try {
    await window.electron.ipcRenderer.invoke('shell:open-path', storageDir.value)
  } catch (err: any) {
    message.error('无法打开目标文件夹')
  }
}

// 监听下载进度广播
let removeProgressListener: (() => void) | null = null

onMounted(() => {
  fetchModelStatus()

  if (window.electron?.ipcRenderer) {
    // 注册全局下载进度监听器
    const handler = (_: any, data: any) => {
      const target = models.value.find((m) => m.id === data.modelId)
      if (target) {
        if (data.status === 'downloading') {
          target.isDownloading = true
          target.downloadPercent = data.percent
          target.downloadSpeed = data.speedText
          target.lastError = undefined // 正常下载中清除旧的重试错误提示
        } else if (data.status === 'completed') {
          target.isDownloading = false
          target.downloadPercent = 100
          target.isDownloaded = true
          target.lastError = undefined
          message.success(`🎉 【${target.name}】下载完成！点击【启动/验证】即可即时载入`)
          fetchModelStatus()
        } else if (data.status === 'error') {
          target.isDownloading = false
          target.lastError = data.errorMsg
          message.error(`【${target.name}】下载失败: ${data.errorMsg || '网络错误'}`)
        } else if (data.status === 'canceled') {
          target.isDownloading = false
        }
      }
    }

    window.electron.ipcRenderer.on('model:progress', handler)
    removeProgressListener = () => {
      window.electron.ipcRenderer.removeAllListeners('model:progress')
    }
  }
})

onUnmounted(() => {
  if (removeProgressListener) {
    removeProgressListener()
  }
})
</script>

<template>
  <div class="model-manager-page">
    <!-- 顶部标题与操作栏 -->
    <div class="header-card">
      <div class="header-left">
        <div class="title-row">
          <n-icon size="24" color="#0284c7" :component="HardwareChipOutline" />
          <h1 class="page-title">AI 本地模型管理中心</h1>
        </div>
        <p class="page-desc">
          采用轻量化按需下载架构。模型完全在本地 CPU 离线运行，零网络回传，隐私安全保障。下载完成后点击「启动」即可热载入。
        </p>
      </div>

      <div class="header-actions">
        <n-button secondary size="small" :loading="isLoading" @click="fetchModelStatus">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新状态
        </n-button>
        <n-button secondary size="small" @click="openStorageFolder">
          <template #icon><n-icon :component="FolderOpenOutline" /></template>
          打开模型目录
        </n-button>
        <n-button
          v-if="installedCount > 0"
          type="primary"
          size="small"
          class="batch-verify-btn"
          @click="verifyAllInstalled"
        >
          <template #icon><n-icon :component="PlayOutline" /></template>
          一键启动/校验已下载模型 ({{ installedCount }})
        </n-button>
      </div>
    </div>

    <!-- 概览指标卡片 -->
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-icon-box bg-blue">
          <n-icon size="22" color="#0284c7" :component="LayersOutline" />
        </div>
        <div class="metric-content">
          <div class="metric-label">已就绪模型</div>
          <div class="metric-value">{{ installedCount }} <span class="metric-unit">/ {{ models.length }} 个</span></div>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon-box bg-emerald">
          <n-icon size="22" color="#059669" :component="SpeedometerOutline" />
        </div>
        <div class="metric-content">
          <div class="metric-label">本地磁盘总占用</div>
          <div class="metric-value">{{ totalDiskFormatted }}</div>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon-box bg-purple">
          <n-icon size="22" color="#7c3aed" :component="SparklesOutline" />
        </div>
        <div class="metric-content">
          <div class="metric-label">推理引擎状态</div>
          <div class="metric-value text-emerald">ONNX Runtime (纯 CPU 极速加速)</div>
        </div>
      </div>
    </div>

    <!-- 模型列表卡片 -->
    <div class="models-container">
      <div v-for="item in models" :key="item.id" class="model-card">
        <!-- 卡片头部 -->
        <div class="card-header">
          <div class="card-title-group">
            <div class="name-row">
              <span class="model-name">{{ item.name }}</span>
              <n-tag v-if="item.isEssential" type="warning" size="tiny" round>核心推荐</n-tag>
              <n-tag size="tiny" type="info" round>{{ item.tag }}</n-tag>
            </div>
            <p class="model-desc">{{ item.description }}</p>
          </div>

          <!-- 状态徽标 -->
          <div class="status-badge-box">
            <n-tag v-if="item.isReadyRunning" type="success" size="small" round>
              <template #icon><n-icon :component="CheckmarkCircle" /></template>
              运行就绪 ({{ item.warmupCostMs }}ms)
            </n-tag>
            <n-tag v-else-if="item.isDownloaded" type="info" size="small" round>
              <template #icon><n-icon :component="CheckmarkCircle" /></template>
              已存盘 (待启动)
            </n-tag>
            <n-tag v-else-if="item.isDownloading" type="warning" size="small" round>
              <template #icon><n-icon :component="CloudDownloadOutline" /></template>
              下载中 {{ item.downloadPercent }}%
            </n-tag>
            <n-tag v-else size="small" depth="3" round>
              未下载 ({{ item.sizeFormatted }})
            </n-tag>
          </div>
        </div>

        <!-- 下载中进度条展示 -->
        <div v-if="item.isDownloading" class="progress-section">
          <div class="progress-header">
            <span class="progress-speed">实时速度: {{ item.downloadSpeed }}</span>
            <span class="progress-percent">{{ item.downloadPercent }}%</span>
          </div>
          <n-progress
            type="line"
            :percentage="item.downloadPercent"
            :show-indicator="false"
            processing
            status="info"
            :height="8"
            border-radius="4px"
          />
        </div>

        <!-- 错误信息提示 -->
        <div v-if="item.lastError" class="error-banner">
          <n-icon :component="AlertCircle" />
          <span>{{ item.lastError }}</span>
        </div>

        <!-- 卡片底部操作与属性 -->
        <div class="card-footer">
          <div class="footer-meta">
            <span class="meta-item">文件: <code>{{ item.filename }}</code></span>
            <span class="meta-item">体积: {{ item.sizeFormatted }}</span>
          </div>

          <div class="footer-actions">
            <!-- 未下载状态：一键下载按钮 -->
            <n-button
              v-if="!item.isDownloaded && !item.isDownloading"
              type="primary"
              size="small"
              class="action-btn"
              @click="startDownload(item)"
            >
              <template #icon><n-icon :component="CloudDownloadOutline" /></template>
              一键高速下载 ({{ item.sizeFormatted }})
            </n-button>

            <!-- 下载中状态：取消下载按钮 -->
            <n-button
              v-if="item.isDownloading"
              size="small"
              type="error"
              quaternary
              @click="cancelDownload(item)"
            >
              取消下载
            </n-button>

            <!-- 已下载状态：启动/校验测试按钮 -->
            <n-button
              v-if="item.isDownloaded"
              type="success"
              secondary
              size="small"
              class="action-btn"
              :loading="item.isVerifying"
              @click="verifyAndStartModel(item)"
            >
              <template #icon><n-icon :component="PlayOutline" /></template>
              {{ item.isReadyRunning ? '重新校验/热载入' : '启动并加载模型' }}
            </n-button>

            <!-- 删除模型按钮 -->
            <n-popconfirm
              v-if="item.isDownloaded"
              positive-text="确认删除"
              negative-text="取消"
              @positive-click="deleteModel(item)"
            >
              <template #trigger>
                <n-button size="small" quaternary type="error">
                  <template #icon><n-icon :component="TrashOutline" /></template>
                  释放空间
                </n-button>
              </template>
              确定要删除该模型吗？删除后相关功能将自动降级为纯算法模式。
            </n-popconfirm>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.model-manager-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  overflow-y: auto;
  padding-right: 4px;
}

/* 顶部标题栏 */
.header-card {
  background: #ffffff;
  padding: 18px 24px;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.02);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.page-desc {
  margin: 6px 0 0 0;
  font-size: 13px;
  color: #64748b;
  max-width: 650px;
  line-height: 1.5;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.batch-verify-btn {
  box-shadow: 0 2px 8px -1px rgba(2, 132, 199, 0.35);
  font-weight: 600;
}

/* 概览指标栅格 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}

.metric-card {
  background: #ffffff;
  padding: 16px 20px;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  display: flex;
  align-items: center;
  gap: 16px;
}

.metric-icon-box {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bg-blue {
  background: #eff6ff;
}

.bg-emerald {
  background: #ecfdf5;
}

.bg-purple {
  background: #f5f3ff;
}

.metric-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-label {
  font-size: 12px;
  color: #64748b;
}

.metric-value {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.metric-unit {
  font-size: 12px;
  font-weight: normal;
  color: #94a3b8;
}

.text-emerald {
  color: #059669;
  font-size: 14px;
}

/* 模型列表容器 */
.models-container {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.model-card {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  padding: 18px 22px;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);
  display: flex;
  flex-direction: column;
  gap: 14px;
  transition: all 0.2s ease;
}

.model-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.model-name {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
}

.model-desc {
  margin: 6px 0 0 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.status-badge-box {
  flex-shrink: 0;
}

/* 进度条 */
.progress-section {
  background: #f8fafc;
  padding: 12px 14px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #0284c7;
  font-weight: 500;
}

/* 错误提示条 */
.error-banner {
  background: #fef2f2;
  border: 1px solid #fee2e2;
  color: #b91c1c;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 底部操作 */
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
  flex-wrap: wrap;
  gap: 12px;
}

.footer-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #64748b;
}

.footer-meta code {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  color: #334155;
  font-family: monospace;
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.action-btn {
  font-weight: 600;
  border-radius: 8px;
}
</style>
