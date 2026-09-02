<script setup lang="ts">
import {
  NTabs,
  NTabPane,
  NSlider,
  NSwitch,
  NInputNumber,
  NRadioGroup,
  NRadioButton,
  NButton,
  NInput,
  NColorPicker,
  NSelect,
  NIcon,
  NDivider
} from 'naive-ui'
import {
  ColorPaletteOutline,
  OptionsOutline,
  SparklesOutline,
  CropOutline,
  WaterOutline,
  RefreshOutline,
  TrashOutline,
  ImageOutline,
  DocumentTextOutline,
  ContrastOutline,
  CreateOutline,
  SunnyOutline,
  FilmOutline,
  FlameOutline,
  SnowOutline,
  VideocamOutline,
  CameraOutline,
  MoonOutline,
  FlashOutline
} from '@vicons/ionicons5'
import { ImageRecipe, ActiveToolType, FilterPresetType, WatermarkPosition } from '../types'

const props = defineProps<{
  recipe: ImageRecipe
  activeTool: ActiveToolType
  brushSize: number
  hasMaskDrawn: boolean
  isProcessing: boolean
}>()

const emit = defineEmits<{
  (e: 'update:activeTool', tool: ActiveToolType): void
  (e: 'update:brushSize', size: number): void
  (e: 'start-auto-clean'): void
  (e: 'start-inpaint'): void
  (e: 'clear-mask'): void
  (e: 'reset-recipe'): void
}>()

// 预设滤镜卡片清单 (使用原生 Ionicons)
const filterPresets: Array<{ id: FilterPresetType; name: string; tag: string; icon: any }> = [
  { id: 'none', name: '原图效果', tag: '无滤镜', icon: ImageOutline },
  { id: 'scanner_whiten', name: '扫描仪白底', tag: '试卷去灰底', icon: DocumentTextOutline },
  { id: 'pure_bw', name: '纯净黑白', tag: '二值化省墨', icon: ContrastOutline },
  { id: 'ink_boost', name: '笔墨增强', tag: '手写字强化', icon: CreateOutline },
  { id: 'doc_contrast', name: '文档高光', tag: '暗光补救', icon: SunnyOutline },
  { id: 'vintage', name: '复古胶片', tag: '温暖怀旧', icon: FilmOutline },
  { id: 'warm_sunlight', name: '明亮暖阳', tag: '通透金黄', icon: FlameOutline },
  { id: 'cool_nordic', name: '清冷北欧', tag: '青蓝高级感', icon: SnowOutline },
  { id: 'cinematic', name: '电影青橙', tag: '高阶色调', icon: VideocamOutline },
  { id: 'polaroid', name: '拍立得', tag: '柔和泛白', icon: CameraOutline },
  { id: 'classic_mono', name: '经典黑白', tag: '艺术影调', icon: MoonOutline }
]

const watermarkPositions: Array<{ label: string; value: WatermarkPosition }> = [
  { label: '右下角', value: 'bottom-right' },
  { label: '居中', value: 'center' },
  { label: '全屏平铺', value: 'tile' },
  { label: '左下角', value: 'bottom-left' },
  { label: '右上角', value: 'top-right' },
  { label: '左上角', value: 'top-left' }
]

const rotateLeft = () => {
  props.recipe.rotation = (props.recipe.rotation - 90 + 360) % 360
}

const rotateRight = () => {
  props.recipe.rotation = (props.recipe.rotation + 90) % 360
}
</script>

<template>
  <div class="tool-settings-panel">
    <n-tabs
      :value="activeTool"
      type="line"
      animated
      size="small"
      justify-content="space-evenly"
      @update:value="(val) => emit('update:activeTool', val as ActiveToolType)"
    >
      <!-- 1. 预设滤镜 -->
      <n-tab-pane name="filter">
        <template #tab>
          <div class="tab-item-inner">
            <n-icon size="15"><ColorPaletteOutline /></n-icon>
            <span>滤镜</span>
          </div>
        </template>
        <div class="panel-section">
          <div class="preset-grid">
            <div
              v-for="item in filterPresets"
              :key="item.id"
              class="preset-card"
              :class="{ active: recipe.filterPreset === item.id }"
              @click="recipe.filterPreset = item.id"
            >
              <div class="preset-icon-wrap">
                <n-icon size="20">
                  <component :is="item.icon" />
                </n-icon>
              </div>
              <div class="preset-info">
                <span class="preset-name">{{ item.name }}</span>
                <span class="preset-tag">{{ item.tag }}</span>
              </div>
            </div>
          </div>
        </div>
      </n-tab-pane>

      <!-- 2. 专业调色 -->
      <n-tab-pane name="color">
        <template #tab>
          <div class="tab-item-inner">
            <n-icon size="15"><OptionsOutline /></n-icon>
            <span>调色</span>
          </div>
        </template>
        <div class="panel-section form-items">
          <div class="form-row">
            <span class="label">曝光度</span>
            <n-slider v-model:value="recipe.exposure" :min="-100" :max="100" />
            <span class="val">{{ recipe.exposure }}</span>
          </div>

          <div class="form-row">
            <span class="label">亮度</span>
            <n-slider v-model:value="recipe.brightness" :min="-100" :max="100" />
            <span class="val">{{ recipe.brightness }}</span>
          </div>

          <div class="form-row">
            <span class="label">对比度</span>
            <n-slider v-model:value="recipe.contrast" :min="-100" :max="100" />
            <span class="val">{{ recipe.contrast }}</span>
          </div>

          <div class="form-row">
            <span class="label">饱和度</span>
            <n-slider v-model:value="recipe.saturation" :min="-100" :max="100" />
            <span class="val">{{ recipe.saturation }}</span>
          </div>

          <div class="form-row">
            <span class="label">色温冷暖</span>
            <n-slider v-model:value="recipe.temperature" :min="-100" :max="100" />
            <span class="val">{{ recipe.temperature }}</span>
          </div>

          <div class="form-row">
            <span class="label">色相旋转</span>
            <n-slider v-model:value="recipe.hue" :min="0" :max="360" />
            <span class="val">{{ recipe.hue }}°</span>
          </div>

          <n-divider style="margin: 12px 0" />
          <n-button block size="small" secondary @click="emit('reset-recipe')">
            <template #icon><n-icon><RefreshOutline /></n-icon></template>
            重置所有调色参数
          </n-button>
        </div>
      </n-tab-pane>

      <!-- 3. 智能去水印 -->
      <n-tab-pane name="watermark-clean">
        <template #tab>
          <div class="tab-item-inner">
            <n-icon size="15"><SparklesOutline /></n-icon>
            <span>去水印</span>
          </div>
        </template>
        <div class="panel-section form-items">
          <div class="switch-card">
            <div class="switch-info">
              <span class="title">试卷/文档自适应去水印</span>
              <span class="desc">利用 OpenCV 背景归一化消除平铺水印，保留黑字笔画</span>
            </div>
          </div>

          <div class="form-row" style="padding: 0 4px">
            <span class="label">去水印灵敏度</span>
            <n-slider v-model:value="recipe.watermarkClean.sensitivity" :min="100" :max="240" :step="5" />
            <span class="val">{{ recipe.watermarkClean.sensitivity }}</span>
          </div>

          <div class="switch-card">
            <div class="switch-info">
              <span class="title">自动消除红色印章 / 批改痕迹</span>
              <span class="desc">识别并消除红印，智能保留交错黑字</span>
            </div>
            <n-switch v-model:value="recipe.watermarkClean.cleanRedStamp" />
          </div>

          <n-button
            type="primary"
            block
            secondary
            :loading="isProcessing"
            :disabled="isProcessing"
            @click="emit('start-auto-clean')"
          >
            <template #icon><n-icon><FlashOutline /></n-icon></template>
            ⚡ 执行全自动智能去水印与白底化
          </n-button>

          <n-divider style="margin: 12px 0">AI 智能涂抹无痕擦除</n-divider>

          <div class="ai-eraser-box">
            <p class="guide-text">
              在主画板上拿画笔涂抹水印区域，随后点击开始擦除：
            </p>
            <div class="form-row">
              <span class="label">画笔大小</span>
              <n-slider
                :value="brushSize"
                :min="10"
                :max="100"
                @update:value="(v) => emit('update:brushSize', v)"
              />
              <span class="val">{{ brushSize }}px</span>
            </div>

            <div class="action-buttons">
              <n-button
                type="primary"
                block
                :disabled="!hasMaskDrawn || isProcessing"
                :loading="isProcessing"
                @click="emit('start-inpaint')"
              >
                <template #icon><n-icon><SparklesOutline /></n-icon></template>
                开始 AI 智能擦除 (LaMa)
              </n-button>

              <n-button
                block
                secondary
                :disabled="!hasMaskDrawn || isProcessing"
                @click="emit('clear-mask')"
              >
                <template #icon><n-icon><TrashOutline /></n-icon></template>
                清空涂抹区域
              </n-button>
            </div>
          </div>
        </div>
      </n-tab-pane>

      <!-- 4. 尺寸与旋转 -->
      <n-tab-pane name="crop-resize">
        <template #tab>
          <div class="tab-item-inner">
            <n-icon size="15"><CropOutline /></n-icon>
            <span>构图</span>
          </div>
        </template>
        <div class="panel-section form-items">
          <div class="section-title">方向与翻转</div>
          <div class="button-grid">
            <n-button size="small" @click="rotateLeft">↺ 逆时针 90°</n-button>
            <n-button size="small" @click="rotateRight">↻ 顺时针 90°</n-button>
            <n-button
              size="small"
              :type="recipe.flipH ? 'primary' : 'default'"
              @click="recipe.flipH = !recipe.flipH"
            >
              ⇄ 水平镜像
            </n-button>
            <n-button
              size="small"
              :type="recipe.flipV ? 'primary' : 'default'"
              @click="recipe.flipV = !recipe.flipV"
            >
              ⇅ 垂直翻转
            </n-button>
          </div>

          <n-divider style="margin: 12px 0">尺寸缩放 (Resize)</n-divider>

          <div class="switch-card">
            <div class="switch-info">
              <span class="title">启用尺寸调整</span>
            </div>
            <n-switch v-model:value="recipe.resize.enabled" />
          </div>

          <template v-if="recipe.resize.enabled">
            <div class="form-row">
              <span class="label">模式</span>
              <n-radio-group v-model:value="recipe.resize.mode" size="small">
                <n-radio-button value="percent">百分比</n-radio-button>
                <n-radio-button value="max-edge">最长边</n-radio-button>
              </n-radio-group>
            </div>

            <div v-if="recipe.resize.mode === 'percent'" class="form-row">
              <span class="label">缩放比例</span>
              <n-slider v-model:value="recipe.resize.percent" :min="10" :max="200" :step="5" />
              <span class="val">{{ recipe.resize.percent }}%</span>
            </div>

            <div v-else class="form-row">
              <span class="label">最长边限制</span>
              <n-input-number v-model:value="recipe.resize.maxEdge" :min="200" :max="8192" :step="100" />
            </div>
          </template>
        </div>
      </n-tab-pane>

      <!-- 5. 水印与签名 -->
      <n-tab-pane name="watermark-overlay">
        <template #tab>
          <div class="tab-item-inner">
            <n-icon size="15"><WaterOutline /></n-icon>
            <span>水印</span>
          </div>
        </template>
        <div class="panel-section form-items">
          <div class="switch-card">
            <div class="switch-info">
              <span class="title">添加文字水印</span>
            </div>
            <n-switch v-model:value="recipe.watermark.enabled" />
          </div>

          <template v-if="recipe.watermark.enabled">
            <div class="form-col">
              <span class="label">水印内容</span>
              <n-input v-model:value="recipe.watermark.text" placeholder="输入水印文字..." />
            </div>

            <div class="form-row">
              <span class="label">位置</span>
              <n-select v-model:value="recipe.watermark.position" :options="watermarkPositions" size="small" />
            </div>

            <div class="form-row">
              <span class="label">文字大小</span>
              <n-slider v-model:value="recipe.watermark.fontSize" :min="12" :max="72" />
              <span class="val">{{ recipe.watermark.fontSize }}px</span>
            </div>

            <div class="form-row">
              <span class="label">透明度</span>
              <n-slider v-model:value="recipe.watermark.opacity" :min="0.05" :max="1.0" :step="0.05" />
              <span class="val">{{ Math.round(recipe.watermark.opacity * 100) }}%</span>
            </div>

            <div class="form-row">
              <span class="label">颜色</span>
              <n-color-picker v-model:value="recipe.watermark.color" :show-alpha="false" size="small" />
            </div>
          </template>
        </div>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<style scoped>
.tool-settings-panel {
  width: 320px;
  height: 100%;
  background: #ffffff;
  border-left: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  user-select: none;
}

.tab-item-inner {
  display: flex;
  align-items: center;
  gap: 4px;
}

.panel-section {
  padding: 16px 14px;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.preset-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.preset-card:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.preset-card.active {
  background: #f0f9ff;
  border-color: #0284c7;
  box-shadow: 0 0 0 1px #0284c7;
}

.preset-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0284c7;
  flex-shrink: 0;
}

.preset-card.active .preset-icon-wrap {
  background: #0284c7;
  color: #ffffff;
  border-color: #0284c7;
}

.preset-info {
  display: flex;
  flex-direction: column;
}

.preset-name {
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
}

.preset-tag {
  font-size: 11px;
  color: #64748b;
}

.form-items {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.form-row .label {
  width: 68px;
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
  flex-shrink: 0;
}

.form-row .val {
  width: 44px;
  font-size: 12px;
  color: #0f172a;
  font-weight: 600;
  text-align: right;
  flex-shrink: 0;
}

.form-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-col .label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
}

.switch-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.switch-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.switch-info .title {
  font-size: 13px;
  font-weight: 500;
  color: #0f172a;
}

.switch-info .desc {
  font-size: 11px;
  color: #64748b;
}

.ai-eraser-box {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.guide-text {
  font-size: 12px;
  color: #64748b;
  margin: 0;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.button-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
</style>
