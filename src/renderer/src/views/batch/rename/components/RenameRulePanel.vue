<script setup lang="ts">
import {
  CodeSlashOutline,
  SearchOutline,
  TextOutline,
  InformationCircleOutline
} from '@vicons/ionicons5'
import {
  RenameMode,
  PatternRuleConfig,
  ReplaceRuleConfig,
  AffixRuleConfig
} from '../types'

const props = defineProps<{
  mode: RenameMode
  patternConfig: PatternRuleConfig
  replaceConfig: ReplaceRuleConfig
  affixConfig: AffixRuleConfig
}>()

const emit = defineEmits<{
  (e: 'update:mode', mode: RenameMode): void
}>()

// 快捷插入占位符 Tag
const insertTag = (tagText: string) => {
  props.patternConfig.template = (props.patternConfig.template || '') + tagText
}
</script>

<template>
  <div class="rule-panel-card">
    <div class="card-header-bar">
      <span class="header-title">重命名规则配置</span>
    </div>

    <div class="rule-body">
      <!-- 模式选择 Tabs -->
      <n-tabs
        :value="mode"
        type="segment"
        size="small"
        @update:value="(v) => emit('update:mode', v as RenameMode)"
      >
        <n-tab name="pattern">
          <div class="tab-label"><n-icon size="14"><CodeSlashOutline /></n-icon><span>占位符模板</span></div>
        </n-tab>
        <n-tab name="replace">
          <div class="tab-label"><n-icon size="14"><SearchOutline /></n-icon><span>查找与替换</span></div>
        </n-tab>
        <n-tab name="affix">
          <div class="tab-label"><n-icon size="14"><TextOutline /></n-icon><span>前后缀与格式</span></div>
        </n-tab>
      </n-tabs>

      <!-- 模式 1：占位符模板配置 -->
      <div v-if="mode === 'pattern'" class="tab-content-section">
        <div class="form-item">
          <div class="form-label-row">
            <span class="form-label">文件名命名模板</span>
            <span class="label-desc">点击下方标签可直接插入</span>
          </div>
          <n-input
            v-model:value="patternConfig.template"
            placeholder="例如: 初三1班_[序号3位]_[原文件名]"
            size="small"
            clearable
          />
        </div>

        <!-- 快捷 Tag 点击区 -->
        <div class="tags-quick-bar">
          <n-tag
            size="small"
            checkable
            :checked="false"
            class="tag-btn"
            @click="insertTag('[序号]')"
          >
            + [序号]
          </n-tag>
          <n-tag
            size="small"
            checkable
            :checked="false"
            class="tag-btn"
            @click="insertTag('[序号2位]')"
          >
            + [序号2位 (01)]
          </n-tag>
          <n-tag
            size="small"
            checkable
            :checked="false"
            class="tag-btn"
            @click="insertTag('[序号3位]')"
          >
            + [序号3位 (001)]
          </n-tag>
          <n-tag
            size="small"
            checkable
            :checked="false"
            class="tag-btn"
            @click="insertTag('[原文件名]')"
          >
            + [原文件名]
          </n-tag>
          <n-tag
            size="small"
            checkable
            :checked="false"
            class="tag-btn"
            @click="insertTag('[日期]')"
          >
            + [当前日期]
          </n-tag>
        </div>

        <div class="grid-two-cols">
          <div class="form-item">
            <span class="form-label">起始编号</span>
            <n-input-number
              v-model:value="patternConfig.startNumber"
              size="small"
              :min="1"
            />
          </div>
          <div class="form-item">
            <span class="form-label">递增步长</span>
            <n-input-number
              v-model:value="patternConfig.step"
              size="small"
              :min="1"
            />
          </div>
        </div>

        <div class="form-item">
          <span class="form-label">默认补零位数</span>
          <n-select
            v-model:value="patternConfig.digits"
            size="small"
            :options="[
              { label: '不补零 (1, 2, 3...)', value: 1 },
              { label: '两位数 (01, 02, 03...)', value: 2 },
              { label: '三位数 (001, 002, 003...)', value: 3 },
              { label: '四位数 (0001, 0002...)', value: 4 }
            ]"
          />
        </div>
      </div>

      <!-- 模式 2：查找与替换配置 -->
      <div v-else-if="mode === 'replace'" class="tab-content-section">
        <div class="form-item">
          <span class="form-label">查找文本或正则表达式</span>
          <n-input
            v-model:value="replaceConfig.findText"
            placeholder="例如: 【广告标签】 或 \[.*?\]"
            size="small"
            clearable
          />
        </div>

        <div class="form-item">
          <span class="form-label">替换为</span>
          <n-input
            v-model:value="replaceConfig.replaceText"
            placeholder="留空即为批量删除"
            size="small"
            clearable
          />
        </div>

        <div class="options-box">
          <n-checkbox v-model:checked="replaceConfig.useRegex" size="small">
            启用正则表达式匹配 (Regex)
          </n-checkbox>
          <n-checkbox v-model:checked="replaceConfig.caseSensitive" size="small">
            区分大小写 (Case Sensitive)
          </n-checkbox>
        </div>
      </div>

      <!-- 模式 3：前后缀与格式配置 -->
      <div v-else class="tab-content-section">
        <div class="grid-two-cols">
          <div class="form-item">
            <span class="form-label">添加前缀</span>
            <n-input
              v-model:value="affixConfig.prefix"
              placeholder="例如: 2024_"
              size="small"
              clearable
            />
          </div>
          <div class="form-item">
            <span class="form-label">添加后缀</span>
            <n-input
              v-model:value="affixConfig.suffix"
              placeholder="例如: _期末"
              size="small"
              clearable
            />
          </div>
        </div>

        <div class="grid-two-cols">
          <div class="form-item">
            <span class="form-label">移除开头字符数</span>
            <n-input-number
              v-model:value="affixConfig.trimLeftCount"
              size="small"
              :min="0"
            />
          </div>
          <div class="form-item">
            <span class="form-label">移除末尾字符数</span>
            <n-input-number
              v-model:value="affixConfig.trimRightCount"
              size="small"
              :min="0"
            />
          </div>
        </div>

        <div class="form-item">
          <span class="form-label">扩展名大小写处理</span>
          <n-radio-group v-model:value="affixConfig.extCase" size="small">
            <n-radio-button value="keep">保持原样</n-radio-button>
            <n-radio-button value="lower">统一小写 (.jpg)</n-radio-button>
            <n-radio-button value="upper">统一大写 (.JPG)</n-radio-button>
          </n-radio-group>
        </div>
      </div>

      <div class="tips-card">
        <n-icon size="15" color="#3B82F6"><InformationCircleOutline /></n-icon>
        <span>右侧表格将实时呈现重命名后的效果，支持冲突预警与执行后一键撤销。</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rule-panel-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.card-header-bar {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  background: #fafafa;
}

.header-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.rule-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.tab-content-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}

.label-desc {
  font-size: 11px;
  color: #94a3b8;
}

.tags-quick-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-btn {
  cursor: pointer;
  user-select: none;
  font-size: 11px;
}

.tag-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}

.grid-two-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.options-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #f8fafc;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
}

.tips-card {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  color: #1e40af;
  line-height: 1.4;
}
</style>
