<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import ToolSkeleton from '@renderer/components/ToolSkeleton.vue'

const message = useMessage()
const isChecking = ref(false)
const updateStatusText = ref('当前已是最新版本')

// 手动检查更新
const handleCheckUpdate = async () => {
  isChecking.value = true
  try {
    const res = await window.electron.ipcRenderer.invoke('updater:check')
    if (!res?.success && res?.message) {
      message.warning(res.message)
    }
  } catch (err: any) {
    message.error(err?.message || '检查更新失败')
  } finally {
    isChecking.value = false
  }
}

// 监听主进程广播的更新状态
const onUpdaterMessage = (_: unknown, data: { channel: string; text: string }) => {
  updateStatusText.value = data.text
  if (data.channel === 'available') {
    message.info(data.text)
  } else if (data.channel === 'downloaded') {
    message.success(data.text)
  } else if (data.channel === 'error') {
    message.warning(data.text)
  }
}

onMounted(() => {
  window.electron?.ipcRenderer?.on('updater:message', onUpdaterMessage)
})

onUnmounted(() => {
  window.electron?.ipcRenderer?.removeAllListeners('updater:message')
})
</script>

<template>
  <ToolSkeleton
    title="系统设置与关于"
    category="系统设置"
    description="配置默认文件输出目录、自动更新策略与关于信息。"
  >
    <n-card class="settings-card" :bordered="false">
      <n-space vertical :size="24">
        <div class="setting-item">
          <div class="setting-label">
            <span class="setting-title">默认输出目录</span>
            <span class="setting-desc">转换与处理后的文件默认保存位置</span>
          </div>
          <n-input placeholder="默认保存至源文件同级目录" style="max-width: 360px" />
        </div>

        <n-divider style="margin: 0" />

        <div class="setting-item">
          <div class="setting-label">
            <span class="setting-title">自动更新与版本</span>
            <span class="setting-desc">工具箱 v0.1.2 · {{ updateStatusText }}</span>
          </div>
          <div class="setting-action">
            <n-button
              type="primary"
              secondary
              :loading="isChecking"
              @click="handleCheckUpdate"
            >
              检查更新
            </n-button>
          </div>
        </div>
      </n-space>
    </n-card>
  </ToolSkeleton>
</template>

<style scoped>
.settings-card {
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid rgba(226, 232, 240, 0.8);
}
.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.setting-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.setting-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}
.setting-desc {
  font-size: 13px;
  color: #64748b;
}
.setting-action {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
