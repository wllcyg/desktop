<script setup lang="ts">
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import {
  CopyOutline,
  DocumentTextOutline
} from '@vicons/ionicons5'
import { OcrBoxLine } from '../types'

const props = defineProps<{
  detectedLines: OcrBoxLine[]
  fullText: string
  fullLatex: string
  executionTime: number
  selectedBoxId: number | null
  isProcessing: boolean
}>()

const emit = defineEmits<{
  (e: 'update:selectedBoxId', id: number | null): void
  (e: 'update:fullLatex', val: string): void
  (e: 'update:fullText', val: string): void
}>()

const message = useMessage()
const activeTab = ref<'visual' | 'latex' | 'word' | 'text'>('visual')

const copyToClipboard = async (text: string, label = '内容') => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    message.success(`已复制 ${label} 到剪贴板`)
  } catch (err) {
    message.error('复制失败，请手动选择复制')
  }
}
</script>

<template>
  <div class="result-panel">
    <div class="panel-header">
      <div class="ph-left">
        <n-tabs v-model:value="activeTab" type="segment" size="small">
          <n-tab name="visual">🧪 格式排版渲染</n-tab>
          <n-tab name="latex">📝 LaTeX 源码</n-tab>
          <n-tab name="word">📘 Word 公式 (MathML)</n-tab>
          <n-tab name="text">📋 Markdown/纯文本</n-tab>
        </n-tabs>
      </div>
      <div class="ph-right">
        <span v-if="executionTime > 0" class="time-tag">耗时: {{ executionTime }}ms</span>
      </div>
    </div>

    <!-- 结果展示主体 -->
    <div class="result-content-body">
      <!-- Loading 骨架遮罩 -->
      <div v-if="isProcessing" class="loading-overlay">
        <n-spin size="large" />
        <span class="loading-tip">正在执行 PP-OCR 检测与公式深度解析...</span>
      </div>

      <!-- Tab 1: 格式排版可视化渲染 -->
      <div v-else-if="activeTab === 'visual'" class="tab-scroll-view">
        <div v-if="detectedLines.length === 0" class="empty-result-tip">
          <n-icon size="48" color="#94a3b8" :component="DocumentTextOutline" />
          <span>点击上方【一键识别】或拉框截取题目</span>
        </div>

        <div v-else class="formula-cards-list">
          <div
            v-for="line in detectedLines"
            :key="line.id"
            class="formula-card"
            :class="{ 'card-highlight': selectedBoxId === line.id }"
            @mouseenter="emit('update:selectedBoxId', line.id)"
            @mouseleave="emit('update:selectedBoxId', null)"
          >
            <div class="card-top-bar">
              <span class="line-badge">#{{ line.id }}</span>
              <n-tag v-if="line.is_equation" size="tiny" type="info" round>方程式</n-tag>
              <n-tag v-else size="tiny" depth="3" round>文本</n-tag>

              <div class="card-btn-group">
                <n-button
                  size="tiny"
                  quaternary
                  type="primary"
                  @click="copyToClipboard(line.latex, 'LaTeX 代码')"
                >
                  <template #icon><n-icon :component="CopyOutline" /></template>
                  复制 LaTeX
                </n-button>
                <n-button
                  size="tiny"
                  quaternary
                  type="info"
                  @click="copyToClipboard(line.mathml, 'Word 兼容公式')"
                >
                  <template #icon><n-icon :component="CopyOutline" /></template>
                  复制 Word 格式
                </n-button>
                <n-button
                  size="tiny"
                  quaternary
                  @click="copyToClipboard(line.formatted_text, '文本')"
                >
                  <template #icon><n-icon :component="CopyOutline" /></template>
                  复制文本
                </n-button>
              </div>
            </div>

            <!-- 渲染展示区 -->
            <div class="rendered-equation-box">
              <div class="math-render-text">{{ line.formatted_text }}</div>
            </div>

            <!-- 对应的 LaTeX 预览 -->
            <div class="latex-snippet-box">
              <code>{{ line.latex }}</code>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab 2: LaTeX 源码视图 -->
      <div v-else-if="activeTab === 'latex'" class="tab-code-view">
        <div class="code-action-bar">
          <span class="code-desc">标准 LaTeX 方程式源码 (支持直接插入 Overleaf / 课件)</span>
          <n-button
            size="small"
            type="primary"
            @click="copyToClipboard(fullLatex, '全部 LaTeX 代码')"
          >
            <template #icon><n-icon :component="CopyOutline" /></template>
            一键复制全文 LaTeX
          </n-button>
        </div>
        <textarea
          :value="fullLatex"
          class="code-editor"
          spellcheck="false"
          @input="(e) => emit('update:fullLatex', (e.target as HTMLTextAreaElement).value)"
        />
      </div>

      <!-- Tab 3: Word 兼容 MathML 视图 -->
      <div v-else-if="activeTab === 'word'" class="tab-code-view">
        <div class="code-action-bar">
          <span class="code-desc">Microsoft Word 兼容格式 (点击复制后在 Word 中直接 Ctrl+V 粘贴为原生公式)</span>
          <n-button
            size="small"
            type="info"
            @click="copyToClipboard(detectedLines.map(l => l.mathml).join('\n\n'), 'Word 公式代码')"
          >
            <template #icon><n-icon :component="CopyOutline" /></template>
            一键复制 Word 公式
          </n-button>
        </div>
        <div class="word-guide-box">
          <div class="guide-title">📌 Word 粘贴使用指南：</div>
          <div class="guide-step">1. 点击上方【一键复制 Word 公式】</div>
          <div class="guide-step">2. 打开 Microsoft Word 或 PPT，按下 <kbd>Ctrl + V</kbd> 粘贴</div>
          <div class="guide-step">3. Word 会自动识别并弹出转换为原生可编辑公式对象！</div>
        </div>
      </div>

      <!-- Tab 4: Markdown / 纯文本视图 -->
      <div v-else class="tab-code-view">
        <div class="code-action-bar">
          <span class="code-desc">格式化纯文本 / 试题题干</span>
          <n-button
            size="small"
            type="primary"
            @click="copyToClipboard(fullText, '全部文本')"
          >
            <template #icon><n-icon :component="CopyOutline" /></template>
            一键复制文本
          </n-button>
        </div>
        <textarea
          :value="fullText"
          class="code-editor"
          spellcheck="false"
          @input="(e) => emit('update:fullText', (e.target as HTMLTextAreaElement).value)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.result-panel {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.panel-header {
  padding: 8px 14px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
}

.ph-left {
  display: flex;
  align-items: center;
}

.ph-right {
  display: flex;
  align-items: center;
}

.time-tag {
  font-size: 11px;
  color: #64748b;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
}

.result-content-body {
  flex: 1;
  min-height: 0;
  position: relative;
  display: flex;
  flex-direction: column;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  z-index: 30;
  backdrop-filter: blur(2px);
}

.loading-tip {
  font-size: 13px;
  color: #0284c7;
  font-weight: 500;
}

.tab-scroll-view {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
}

.empty-result-tip {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #94a3b8;
  font-size: 14px;
}

.formula-cards-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.formula-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  transition: all 0.15s;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.formula-card:hover {
  border-color: #93c5fd;
}

.card-highlight {
  border-color: #3b82f6;
  background: #f8faff;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);
}

.card-top-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.line-badge {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
}

.card-btn-group {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}

.rendered-equation-box {
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 6px;
}

.math-render-text {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  letter-spacing: 0.5px;
}

.latex-snippet-box {
  background: #f1f5f9;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  color: #475569;
  overflow-x: auto;
}

.tab-code-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 14px;
  gap: 10px;
}

.code-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.code-desc {
  font-size: 12px;
  color: #64748b;
}

.code-editor {
  flex: 1;
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 12px;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #1e293b;
  background: #f8fafc;
  resize: none;
  outline: none;
}

.code-editor:focus {
  border-color: #3b82f6;
  background: #ffffff;
}

.word-guide-box {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.guide-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e40af;
}

.guide-step {
  font-size: 13px;
  color: #1e3a8a;
}

kbd {
  background: #ffffff;
  border: 1px solid #93c5fd;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
  font-weight: 700;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}
</style>
