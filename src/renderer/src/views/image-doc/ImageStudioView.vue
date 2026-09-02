<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import {
  ImageItem,
  ImageRecipe,
  ActiveToolType,
  createDefaultRecipe
} from './studio/types'
import ImageQueueSidebar from './studio/components/ImageQueueSidebar.vue'
import EditorCanvas from './studio/components/EditorCanvas.vue'
import ToolSettingsPanel from './studio/components/ToolSettingsPanel.vue'
import BatchActionToolbar from './studio/components/BatchActionToolbar.vue'

const message = useMessage()
const dialog = useDialog()

const items = ref<ImageItem[]>([])
const activeId = ref<string | null>(null)
const activeTool = ref<ActiveToolType>('filter')
const brushSize = ref(40)
const hasMaskDrawn = ref(false)
const isProcessing = ref(false)
const isExporting = ref(false)

const canvasRef = ref<InstanceType<typeof EditorCanvas> | null>(null)

// 导出全局设置
const exportSettings = ref({
  format: 'image/jpeg' as 'image/jpeg' | 'image/png' | 'image/webp',
  quality: 0.9,
  filenameSuffix: '_edit'
})

// 当前选中的图片项
const activeItem = computed(() => {
  return items.value.find((it) => it.id === activeId.value) || null
})

// 选中的配方
const activeRecipe = computed(() => {
  return activeItem.value?.recipe || createDefaultRecipe()
})

// 批量添加图片文件
const handleAddFiles = (fileList: FileList | File[]) => {
  const newItems: ImageItem[] = []

  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i]
    if (!file.type.startsWith('image/')) continue

    const id = `img_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
    const url = URL.createObjectURL(file)

    const item: ImageItem = {
      id,
      file,
      name: file.name,
      filePath: (file as any).path || undefined,
      originalUrl: url,
      previewUrl: url,
      width: 0,
      height: 0,
      sizeBytes: file.size,
      recipe: createDefaultRecipe(),
      status: 'idle'
    }

    newItems.push(item)
  }

  if (newItems.length > 0) {
    items.value.push(...newItems)
    // 自动选中最新添加的图片，立即呈现在画板中
    activeId.value = newItems[newItems.length - 1].id
    message.success(`已添加 ${newItems.length} 张图片`)
  }
}

// 移除单项
const handleRemoveItem = (id: string) => {
  const idx = items.value.findIndex((it) => it.id === id)
  if (idx !== -1) {
    const removed = items.value.splice(idx, 1)[0]
    if (removed.originalUrl.startsWith('blob:')) {
      URL.revokeObjectURL(removed.originalUrl)
    }
    if (activeId.value === id) {
      activeId.value = items.value[0]?.id || null
    }
  }
}

// 清空全部
const handleClearAll = () => {
  for (const it of items.value) {
    if (it.originalUrl.startsWith('blob:')) {
      URL.revokeObjectURL(it.originalUrl)
    }
  }
  items.value = []
  activeId.value = null
  message.info('已清空所有待处理图片')
}

// 接收 Mask 绘制事件
const handleMaskDrawn = () => {
  hasMaskDrawn.value = true
}

// 清空 Mask 选区
const handleClearMask = () => {
  canvasRef.value?.clearInpaintMask()
  hasMaskDrawn.value = false
}

// 重置当前图片的配方参数
const handleResetRecipe = () => {
  if (activeItem.value) {
    activeItem.value.recipe = createDefaultRecipe()
    message.info('已重置当前图片的编辑参数')
  }
}

// 辅助函数：将图片源解析为 Python 可直接读取的真实物理路径或 Base64 字符串
const resolveImageSource = async (item: ImageItem): Promise<string> => {
  if (item.filePath && (item.filePath.startsWith('/') || item.filePath.includes(':'))) {
    return item.filePath
  }
  if (item.originalUrl.startsWith('data:image/')) {
    return item.originalUrl
  }
  if (item.file) {
    return await blobToBase64(item.file)
  }
  if (item.originalUrl.startsWith('blob:')) {
    const resp = await fetch(item.originalUrl)
    const blob = await resp.blob()
    return await blobToBase64(blob)
  }
  return item.originalUrl
}

// 触发全自动智能去水印与试卷白底化 (调用 Python OpenCV 自适应背景归一化流水线)
const handleStartAutoRemove = async () => {
  if (!activeItem.value) return

  try {
    isProcessing.value = true
    const inputSource = await resolveImageSource(activeItem.value)

    const res = await window.electron.ipcRenderer.invoke('py:call', {
      method: 'watermark.auto_remove',
      params: {
        input: inputSource,
        sensitivity: activeItem.value.recipe.watermarkClean.sensitivity || 200,
        contrast: 1.3,
        auto_clean_red: activeItem.value.recipe.watermarkClean.cleanRedStamp
      }
    })

    if (res && res.image_base64) {
      activeItem.value.originalUrl = res.image_base64
      activeItem.value.previewUrl = res.image_base64
      message.success('✨ 智能试卷去水印完成，黑字饱满清晰！')
    } else {
      throw new Error(res?.error || '去水印处理异常')
    }
  } catch (err: any) {
    console.error('自动去水印失败:', err)
    message.error(`去水印失败: ${err.message || '请检查 Python 服务'}`)
  } finally {
    isProcessing.value = false
  }
}

// 触发 AI 涂抹去水印 (调用 Python 后端 Big-LaMa)
const handleStartInpaint = async () => {
  if (!activeItem.value || !canvasRef.value) return

  try {
    isProcessing.value = true
    const maskBase64 = await canvasRef.value.exportInpaintMaskBase64()
    if (!maskBase64) {
      message.warning('未能提取到涂抹区域，请先在图片上涂抹水印')
      return
    }

    // 转换原图为 base64 或路径
    const inputSource = await resolveImageSource(activeItem.value)

    const res = await window.electron.ipcRenderer.invoke('py:call', {
      method: 'watermark.inpaint',
      params: {
        input: inputSource,
        mask: maskBase64
      }
    })

    if (res && res.image_base64) {
      activeItem.value.originalUrl = res.image_base64
      activeItem.value.previewUrl = res.image_base64
      handleClearMask()
      message.success('✨ AI 无痕水印擦除完成！')
    } else {
      throw new Error(res?.error || 'AI 修复响应异常')
    }
  } catch (err: any) {
    console.error('AI 去水印失败:', err)
    message.error(`AI 擦除失败: ${err.message || '请确保 Python 依赖就绪'}`)
  } finally {
    isProcessing.value = false
  }
}

// 一键同步当前编辑配方至列表中所有图片
const handleSyncAll = () => {
  if (!activeItem.value) return

  const sourceRecipe = JSON.parse(JSON.stringify(activeItem.value.recipe)) as ImageRecipe

  for (const it of items.value) {
    if (it.id !== activeItem.value.id) {
      it.recipe = JSON.parse(JSON.stringify(sourceRecipe))
    }
  }

  message.success(`已将当前编辑配方一键应用至全部 ${items.value.length} 张图片 ⚡`)
}

// 批量导出全部
const handleStartBatchExport = async () => {
  if (items.value.length === 0) {
    message.warning('请先添加需要导出的图片')
    return
  }

  // 1. 选择保存目录
  let dirPath = ''
  try {
    dirPath = await window.electron.ipcRenderer.invoke('dialog:select-directory')
  } catch (e) {
    // ignore
  }

  if (!dirPath) return

  isExporting.value = true
  let successCount = 0

  try {
    const exportBatchItems: Array<{ name: string; base64: string }> = []

    for (let i = 0; i < items.value.length; i++) {
      const it = items.value[i]
      it.status = 'processing'

      // 切换当前渲染项
      activeId.value = it.id
      // 等待宏任务刷新让 PixiJS 应用对应配方
      await new Promise((r) => setTimeout(r, 120))

      if (canvasRef.value) {
        try {
          const exportBlob = await canvasRef.value.exportBlob(it.recipe)
          const base64 = await blobToBase64(exportBlob)

          // 计算新文件名
          const ext = exportSettings.value.format === 'image/jpeg' ? 'jpg' : exportSettings.value.format === 'image/png' ? 'png' : 'webp'
          const rawName = it.name.replace(/\.[^/.]+$/, '')
          const outputName = `${rawName}${it.recipe.export?.filenameSuffix || '_edit'}.${ext}`

          exportBatchItems.push({
            name: outputName,
            base64
          })

          it.status = 'done'
          successCount++
        } catch (err: any) {
          console.error(`导出图片 ${it.name} 失败:`, err)
          it.status = 'error'
          it.errorMsg = err.message
        }
      }
    }

    // 2. 调用主进程极速批量保存
    if (exportBatchItems.length > 0) {
      await window.electron.ipcRenderer.invoke('file:save-batch', {
        dirPath,
        items: exportBatchItems
      })

      dialog.success({
        title: '批量导出完成 🎉',
        content: `成功导出 ${successCount} / ${items.value.length} 张图片到：\n${dirPath}`,
        positiveText: '打开所在文件夹',
        negativeText: '关闭',
        onPositiveClick: () => {
          window.electron.ipcRenderer.invoke('shell:open-path', dirPath)
        }
      })
    }
  } catch (err: any) {
    message.error(`批量导出过程中断: ${err.message}`)
  } finally {
    isExporting.value = false
  }
}

const blobToBase64 = (blob: Blob): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}
</script>

<template>
  <div class="image-studio-container">
    <!-- 顶部批量操作栏 -->
    <BatchActionToolbar
      :item-count="items.length"
      :export-settings="exportSettings"
      :is-exporting="isExporting"
      @sync-all="handleSyncAll"
      @start-batch-export="handleStartBatchExport"
      @update:export-format="(f) => (exportSettings.format = f)"
      @update:export-quality="(q) => (exportSettings.quality = q)"
    />

    <!-- 主工作区：三栏布局 -->
    <div class="studio-body">
      <!-- 左侧：多图任务队列 -->
      <ImageQueueSidebar
        :items="items"
        :active-id="activeId"
        @select-item="(id) => (activeId = id)"
        @add-files="handleAddFiles"
        @remove-item="handleRemoveItem"
        @clear-all="handleClearAll"
      />

      <!-- 中间：PixiJS WebGL 渲染视口 -->
      <div class="viewport-area">
        <EditorCanvas
          ref="canvasRef"
          :active-item="activeItem"
          :active-tool="activeTool"
          :brush-size="brushSize"
          :is-processing="isProcessing"
          @mask-drawn="handleMaskDrawn"
        />
      </div>

      <!-- 右侧：属性调节与工具面板 -->
      <ToolSettingsPanel
        v-if="activeItem"
        :recipe="activeRecipe"
        :active-tool="activeTool"
        :brush-size="brushSize"
        :has-mask-drawn="hasMaskDrawn"
        :is-processing="isProcessing"
        @update:active-tool="(t) => (activeTool = t)"
        @update:brush-size="(s) => (brushSize = s)"
        @start-auto-clean="handleStartAutoRemove"
        @start-inpaint="handleStartInpaint"
        @clear-mask="handleClearMask"
        @reset-recipe="handleResetRecipe"
      />
    </div>
  </div>
</template>

<style scoped>
.image-studio-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  overflow: hidden;
}

.studio-body {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

.viewport-area {
  flex: 1;
  height: 100%;
  position: relative;
  min-width: 0;
}
</style>
