# 基于 PixiJS 的图片批量处理与轻量编辑工作台 (Image Studio) 实施计划

## 1. 项目定位与背景
将现有的单调“图片批量压缩”模块升级为 **“图片批量处理与轻量编辑工作台 (Image Studio)”**。
借助 **PixiJS (WebGL 2D 加速引擎)** 与 **Python 后端 (Big-LaMa AI 引擎)** 强强联合，在普通 Windows/Mac 电脑上实现大图毫秒级硬件加速渲染、**“预设艺术/试卷滤镜库”**、自由拉框裁剪、文字印章叠加、**“全自动去水印 & AI 智能涂抹橡皮擦”**，以及将单图编辑动作**“一键同步应用至全部图片并批量导出”**的核心能力。

---

## 2. 技术选型与协同架构

### 2.1 依赖包
```bash
# 渲染核心：PixiJS v8（最新一代，纯 WebGL/WebGPU，体积轻量）
npm install pixi.js@^8.0.0
```

### 2.2 双引擎协同优势
1. **GPU 硬件加速（PixiJS）**：手机拍摄的 4K/8K 大图平滑 60fps 缩放、平移，数十款滤镜着色器毫秒级实时无卡顿切换；
2. **纯前端极速滤镜与去水印（PixiJS Shader）**：通过 GPU 色彩矩阵（ColorMatrixFilter）与自定义着色器，秒级完成试卷扫描白底化、胶片滤镜调色、浅灰水印消除与红印滤除；
3. **AI 深度无痕擦除（Big-LaMa ONNX）**：复杂底图、花纹背景等重度水印，用户在 PixiJS 画布上涂抹生成 Mask 选区，一键调用 Python 的 Big-LaMa 傅里叶卷积模型进行高质量无痕脑补还原。

---

## 3. 核心功能设计

### 3.1 七大核心编辑能力矩阵
```
┌────────────────────────────────────────────────────────────────────────┐
│                      图片批量处理与轻量编辑工作台                        │
├───────────────────┬────────────────────────────────────────────────────┤
│ 1. 裁剪与构图     │ 自由拉框裁剪、常用比例(1:1, 4:3, 16:9, A4试卷)、90°旋转、水平/垂直翻转 │
├───────────────────┼────────────────────────────────────────────────────┤
│ 2. 预设滤镜库     │ ① 文档类：扫描仪白底、纯净黑白(二值化)、墨水增强、高对比文档          │
│                   │ ② 艺术类：复古胶片、明亮暖阳、清冷北欧、电影青橙、拍立得、经典黑白    │
├───────────────────┼────────────────────────────────────────────────────┤
│ 3. 专业画质调色   │ 曝光度、亮度、对比度、饱和度、色温(冷/暖)、色相旋转、边缘锐化、暗角  │
├───────────────────┼────────────────────────────────────────────────────┤
│ 4. 去水印与AI修复 │ ① 试卷浅灰水印过滤 ② 红印红痕一键清除 ③ AI画笔涂抹智能无痕擦除(LaMa) │
├───────────────────┼────────────────────────────────────────────────────┤
│ 5. 标注与隐私遮挡 │ 局部马赛克/高斯模糊(遮挡试卷考号/姓名)、红笔圈画、荧光笔高亮、文字标注  │
├───────────────────┼────────────────────────────────────────────────────┤
│ 6. 水印与签名叠加 │ 自定义文字水印、校徽/教研组印章图片叠加、透明度与平铺模式           │
├───────────────────┼────────────────────────────────────────────────────┤
│ 7. 批量预设与导出 │ 【杀手锏】将当前图的编辑动作“一键同步至所有图片”，批量格式转换/压缩   │
└───────────────────┴────────────────────────────────────────────────────┘
```

---

## 4. 前端架构与模块拆分（遵循单文件 < 700 行规范）

```
src/renderer/src/views/image-doc/
├── ImageEditorView.vue                 # 顶层页面主容器与批量导出控制 (~180 行)
└── editor/
    ├── types.ts                        # 动作类型、滤镜预设、配方数据定义 (~130 行)
    ├── composables/
    │   ├── usePixiApp.ts               # PixiJS Application 初始化、视口手势、Mask 绘制 (~200 行)
    │   └── useFilterPipeline.ts        # 预设滤镜矩阵算法与自定义 Shader 流水线 (~180 行)
    └── components/
        ├── EditorCanvas.vue            # PixiJS WebGL 渲染视口、涂抹遮罩与拉框裁剪交互 (~280 行)
        ├── ToolSettingsPanel.vue       # 右侧工具属性调节面板(滤镜/调色/去水印/裁剪/批注/水印) (~290 行)
        ├── ImageQueueSidebar.vue       # 左侧多图任务队列与缩略图列表 (~220 行)
        └── BatchActionToolbar.vue      # 顶层操作栏(一键同步全图、撤销重做、批量导出) (~140 行)
```

---

## 5. 核心代码设计方案

### 5.1 数据模型设计 (`src/renderer/src/views/image-doc/editor/types.ts`)
```typescript
export type FilterPresetType =
  | 'none'
  // 文档办公类
  | 'scanner_whiten'  // 扫描仪白底化
  | 'pure_bw'         // 纯净黑白二值化 (极致打印省墨)
  | 'ink_boost'       // 蓝黑手写笔墨水增强
  | 'doc_contrast'    // 昏暗文档高光对比
  // 艺术美化类
  | 'vintage'         // 复古胶片
  | 'warm_sunlight'   // 明亮暖阳
  | 'cool_nordic'     // 清冷北欧
  | 'cinematic'       // 电影青橙质感
  | 'polaroid'        // 拍立得复古
  | 'classic_mono'    // 经典黑白影调

export interface ImageRecipe {
  // 1. 构图变换
  rotation: number // 0, 90, 180, 270
  flipH: boolean
  flipV: boolean
  cropRect?: { x: number; y: number; width: number; height: number }
  
  // 2. 预设滤镜与专业调色
  filterPreset: FilterPresetType
  brightness: number    // -100 ~ 100
  contrast: number      // -100 ~ 100
  saturation: number    // -100 ~ 100
  exposure: number      // -100 ~ 100
  temperature: number   // -100 (冷) ~ 100 (暖)
  hue: number           // 0 ~ 360
  sharpen: boolean      // 边缘锐化
  vignette: number      // 暗角 0 ~ 100
  
  // 3. 去水印与智能修复
  watermarkClean: {
    cleanFaintWatermark: boolean // 消除浅灰色背景平铺水印
    cleanRedStamp: boolean       // 自动去除红色印章/红笔批改痕迹
    sensitivity: number          // 灵敏度 100 ~ 250
  }
  inpaintMasks?: string          // 涂抹生成的 Base64 Mask 蒙版 (供 LaMa AI 擦除)
  
  // 4. 涂抹批注与隐私
  mosaics: Array<{ x: number; y: number; width: number; height: number }>
  
  // 5. 水印与签名叠加
  watermarkOverlay?: {
    text: string
    color: string
    fontSize: number
    opacity: number
    position: 'bottom-right' | 'center' | 'tile'
  }
  
  // 6. 导出配置
  exportFormat: 'image/jpeg' | 'image/png' | 'image/webp'
  exportQuality: number // 0.1 ~ 1.0
}

export interface ImageItem {
  id: string
  file: File
  name: string
  originalUrl: string
  previewUrl: string
  width: number
  height: number
  recipe: ImageRecipe
  status: 'idle' | 'processing' | 'done' | 'error'
}
```

### 5.2 滤镜流水线与着色器矩阵实现思路 (`useFilterPipeline.ts`)
```typescript
import { ColorMatrixFilter } from 'pixi.js'
import { ImageRecipe } from '../types'

export function useFilterPipeline() {
  const buildFilterList = (recipe: ImageRecipe) => {
    const filters = []
    const colorFilter = new ColorMatrixFilter()

    // 1. 应用预设滤镜基础矩阵
    switch (recipe.filterPreset) {
      case 'scanner_whiten':
        // 提高白色阈值并拉高对比度，消除试卷灰底
        colorFilter.brightness(1.2, false)
        colorFilter.contrast(1.6, false)
        break
      case 'pure_bw':
        // 纯净黑白二值化
        colorFilter.blackAndWhite(false)
        colorFilter.contrast(2.2, false)
        break
      case 'vintage':
        colorFilter.sepia(false)
        colorFilter.brightness(1.05, false)
        colorFilter.desaturate()
        break
      case 'warm_sunlight':
        colorFilter.tint(0xfff4d6, false)
        colorFilter.brightness(1.1, false)
        break
      case 'cool_nordic':
        colorFilter.tint(0xd6f0ff, false)
        colorFilter.contrast(1.15, false)
        break
      case 'classic_mono':
        colorFilter.blackAndWhite(false)
        colorFilter.contrast(1.3, false)
        break
      case 'polaroid':
        colorFilter.predator(0.2, false)
        break
    }

    // 2. 叠加热度/自定义调色微调
    if (recipe.brightness !== 0) {
      colorFilter.brightness(1 + recipe.brightness / 100, false)
    }
    if (recipe.contrast !== 0) {
      colorFilter.contrast(1 + recipe.contrast / 100, false)
    }
    if (recipe.saturation !== 0) {
      if (recipe.saturation < 0) {
        colorFilter.desaturate()
      } else {
        colorFilter.saturate(recipe.saturation / 100, false)
      }
    }
    if (recipe.hue !== 0) {
      colorFilter.hue(recipe.hue, false)
    }

    filters.push(colorFilter)
    return filters
  }

  return { buildFilterList }
}
```

---

## 6. 开发步骤路线图

### 第一步：安装依赖与路由切换
1. 运行 `npm install pixi.js@^8.0.0` 安装依赖；
2. 修改 `src/renderer/src/router/index.ts` 与 `MainLayout.vue`，将 `/image-doc/compress` 路由与菜单名称调整为 **“图片批量编辑 (Image Studio)”**。

### 第二步：创建数据类型与 Composable
1. 创建 `src/renderer/src/views/image-doc/editor/types.ts` 定义图片配方、滤镜枚举与图层接口；
2. 创建 `src/renderer/src/views/image-doc/editor/composables/useFilterPipeline.ts` 实现数十款预设滤镜与调色矩阵组合算法；
3. 创建 `src/renderer/src/views/image-doc/editor/composables/usePixiApp.ts` 封装 PixiJS 画布生命周期、视口交互、AI 涂抹 Mask 提取与批量渲染导出。

### 第三步：开发各子组件
1. **`EditorCanvas.vue`**：挂载 `<canvas>`，处理滚轮缩放、空格抓手拖拽、自由拉框裁剪与 **AI 水印消除笔涂抹**；
2. **`ToolSettingsPanel.vue`**：提供 6 个清晰分类的 Tab：
   - 🎨 **预设滤镜**（试卷扫描白底、纯净黑白、复古胶片、暖阳、冷调等卡片式即点即换）
   - 🎛️ **专业调色**（曝光度、亮度、对比度、饱和度、色温、色相旋转）
   - 🧹 **智能去水印**（浅灰水印消除、红章红痕滤除、AI 涂抹无痕擦除）
   - 📐 **裁剪旋转**（自由裁剪、常用比例、旋转翻转）
   - ✏️ **标注遮挡**（局部马赛克、红笔圈画、荧光笔）
   - 💧 **水印叠加**（自定义文字/图片印章）
3. **`ImageQueueSidebar.vue`**：左侧多图拖拽导入、缩略图列表切换、单项状态；
4. **`BatchActionToolbar.vue`**：顶部【一键应用当前效果至所有图片】、【批量导出图片】按钮。

### 第四步：顶层组装与双引擎联动
1. 在 `ImageEditorView.vue` 中组装上述组件；
2. 当触发“AI 涂抹去水印”时，通过 `py:call` 调用后端的 `handle_inpaint_watermark`（基于 Big-LaMa 模型），将修复后图像无缝回填至 PixiJS；
3. 实现批量导出循环：遍历图片列表，逐个传入 PixiJS 生成 Blob，并通过原生 IPC `file:save-batch` 极速保存到指定目录。

### 第五步：验证与测试
1. 运行 `npm run typecheck` 保证 TypeScript 0 错误；
2. 确认每个新建 `.vue` 组件均在 300 行左右，代码整洁模块化。

---

> 💡 **提示**：该方案融合了“数十款 GPU 即时滤镜”、“纯前端 WebGL 毫秒级轻量操作”与“后端 Big-LaMa 深度无痕修复”，兼顾极速性能与顶级生产力！
