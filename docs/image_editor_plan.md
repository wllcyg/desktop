# 基于 PixiJS 的图片批量处理与轻量编辑工作台 (Image Studio) 实施计划

## 1. 项目定位与背景
将现有的单调“图片批量压缩”模块升级为 **“图片批量处理与轻量编辑工作台 (Image Studio)”**。
借助 **PixiJS (WebGL 2D 加速引擎)**，在普通 Windows 电脑上实现大图毫秒级硬件加速渲染、滤镜调色（试卷去灰底、黑白增强）、自由裁剪旋转、涂抹批注（马赛克、红笔圈画），以及将单图编辑动作**“一键同步应用至全部图片并批量导出”**的核心能力。

---

## 2. 技术选型与依赖配置

### 2.1 依赖包
```bash
# 渲染核心：PixiJS v8（最新一代，纯 WebGL/WebGPU，体积轻量）
npm install pixi.js@^8.0.0
```

### 2.2 技术选型优势
1. **GPU 硬件加速**：手机拍摄的 4K/8K 试卷大图平滑 60fps 缩放、平移与实时滤镜渲染，彻底告别传统 CPU Canvas 掉帧；
2. **纯前端运行**：不占用后端 Python 资源，无需配置 CUDA/PyTorch，普通电脑极速运行；
3. **着色器滤镜系统**：内置 ColorMatrixFilter（亮度、对比度、黑白二值化、饱和度）与自定义 Shader（试卷白底化）。

---

## 3. 核心功能设计

### 3.1 五大核心编辑能力
```
┌────────────────────────────────────────────────────────────────────────┐
│                      图片批量处理与轻量编辑工作台                        │
├───────────────────┬────────────────────────────────────────────────────┤
│ 1. 裁剪与构图     │ 自由拉框裁剪、常用比例(1:1, 4:3, 16:9, A4试卷)、90°旋转、水平/垂直翻转 │
├───────────────────┼────────────────────────────────────────────────────┤
│ 2. 试卷画质增强   │ 亮度调节、对比度提升、自动去灰底白底化(试卷清晰化)、黑白二值化、锐化    │
├───────────────────┼────────────────────────────────────────────────────┤
│ 3. 标注与隐私遮挡 │ 局部马赛克/高斯模糊(遮挡试卷考号/姓名)、红笔圈画、荧光笔高亮、文字标注  │
├───────────────────┼────────────────────────────────────────────────────┤
│ 4. 水印与签名     │ 自定义文字水印、校徽/教研组印章图片叠加、透明度与平铺模式           │
├───────────────────┼────────────────────────────────────────────────────┤
│ 5. 批量预设与导出 │ 【杀手锏】将当前图的编辑动作“一键同步至所有图片”，批量格式转换/压缩   │
└───────────────────┴────────────────────────────────────────────────────┘
```

---

## 4. 前端架构与模块拆分（遵循单文件 < 700 行规范）

```
src/renderer/src/views/image-doc/
├── ImageEditorView.vue                 # 顶层页面主容器与批量导出控制 (~180 行)
└── editor/
    ├── types.ts                        # 动作类型、滤镜参数、图层数据定义 (~100 行)
    ├── composables/
    │   ├── usePixiApp.ts               # PixiJS Application 初始化、视口手势 (~180 行)
    │   └── useFilterPipeline.ts        # 滤镜着色器与画质增强算法 (~150 行)
    └── components/
        ├── EditorCanvas.vue            # PixiJS WebGL 渲染视口与交互遮罩 (~280 行)
        ├── ToolSettingsPanel.vue       # 右侧工具属性调节面板(调色/裁剪/批注/水印) (~290 行)
        ├── ImageQueueSidebar.vue       # 左侧多图任务队列与缩略图列表 (~220 行)
        └── BatchActionToolbar.vue      # 顶层操作栏(一键同步全图、撤销重做、批量导出) (~140 行)
```

---

## 5. 核心代码设计方案

### 5.1 数据模型设计 (`src/renderer/src/views/image-doc/editor/types.ts`)
```typescript
export interface ImageItem {
  id: string
  file: File
  name: string
  originalUrl: string
  previewUrl: string
  width: number
  height: number
  // 该图片独立的编辑配方 (Recipe)
  recipe: ImageRecipe
  status: 'idle' | 'processing' | 'done' | 'error'
}

export interface ImageRecipe {
  // 1. 构图变换
  rotation: number // 0, 90, 180, 270
  flipH: boolean
  flipV: boolean
  cropRect?: { x: number; y: number; width: number; height: number }
  
  // 2. 调色与画质
  brightness: number    // -100 ~ 100
  contrast: number      // -100 ~ 100
  whiteBalance: boolean // 自动去灰底白底化
  binaryMode: boolean   // 黑白二值化（试卷纯黑白清晰化）
  sharpen: boolean      // 边缘锐化
  
  // 3. 涂抹与水印
  mosaics: Array<{ x: number; y: number; width: number; height: number }>
  watermark?: {
    text: string
    color: string
    fontSize: number
    opacity: number
    position: 'bottom-right' | 'center' | 'tile'
  }
  
  // 4. 导出配置
  exportFormat: 'image/jpeg' | 'image/png' | 'image/webp'
  exportQuality: number // 0.1 ~ 1.0
}
```

### 5.2 PixiJS 视口与滤镜核心实现思路 (`usePixiApp.ts`)
```typescript
import { Application, Assets, Sprite, ColorMatrixFilter, Container } from 'pixi.js'

export function usePixiApp() {
  let app: Application | null = null
  let mainSprite: Sprite | null = null
  const rootContainer = new Container()

  const initApp = async (canvasEl: HTMLCanvasElement, width: number, height: number) => {
    app = new Application()
    await app.init({
      canvas: canvasEl,
      width,
      height,
      backgroundAlpha: 0,
      antialias: true,
      resolution: window.devicePixelRatio || 1,
      autoDensity: true
    })
    app.stage.addChild(rootContainer)
  }

  const applyFilters = (recipe: ImageRecipe) => {
    if (!mainSprite) return
    const filters = []
    
    // 色彩调节
    const colorFilter = new ColorMatrixFilter()
    if (recipe.brightness !== 0) {
      colorFilter.brightness(1 + recipe.brightness / 100, false)
    }
    if (recipe.contrast !== 0) {
      colorFilter.contrast(1 + recipe.contrast / 100, false)
    }
    if (recipe.binaryMode) {
      colorFilter.blackAndWhite(false)
      colorFilter.contrast(2.0, false) // 高对比度实现纯净试卷黑白字
    }
    filters.push(colorFilter)

    mainSprite.filters = filters
  }

  const exportBlob = async (recipe: ImageRecipe): Promise<Blob> => {
    if (!app) throw new Error('App not initialized')
    // 利用 PixiJS 提取高精渲染缓冲
    return await app.renderer.extract.image(rootContainer, recipe.exportFormat, recipe.exportQuality)
  }

  return { initApp, applyFilters, exportBlob }
}
```

---

## 6. 开发步骤路线图（今晚可按此顺序落地）

### 第一步：安装依赖与路由切换
1. 运行 `npm install pixi.js` 安装依赖；
2. 修改 `src/renderer/src/router/index.ts` 与 `MainLayout.vue`，将 `/image-doc/compress` 路由与菜单名称调整为 **“图片批量编辑 (Image Studio)”**。

### 第二步：创建数据类型与 Composable
1. 创建 `src/renderer/src/views/image-doc/editor/types.ts` 定义图片配方与图层接口；
2. 创建 `src/renderer/src/views/image-doc/editor/composables/usePixiApp.ts` 封装 PixiJS 画布初始化、缩放漫游与渲染提取。

### 第三步：开发各子组件
1. **`EditorCanvas.vue`**：挂载 `<canvas>`，处理滚轮缩放、空格抓手拖拽与自由拉框裁剪；
2. **`ToolSettingsPanel.vue`**：提供 4 个 Tab（📐 裁剪旋转、✨ 试卷画质增强、🎨 涂抹标注、💧 水印叠加）；
3. **`ImageQueueSidebar.vue`**：左侧多图拖拽导入、缩略图列表切换、删除单项；
4. **`BatchActionToolbar.vue`**：顶部【一键应用当前效果至所有图片】、【批量导出图片】按钮。

### 第四步：顶层组装与批量导出
1. 在 `ImageEditorView.vue` 中组装上述组件；
2. 实现批量导出循环：遍历图片列表，逐个传入 PixiJS 生成 Blob，并通过原生 IPC `file:save-batch` 极速保存到指定目录。

### 第五步：验证与测试
1. 运行 `npm run typecheck` 保证 TypeScript 0 错误；
2. 运行行数扫描命令确认每个新建 `.vue` 组件均在 300 行左右。

---

> 💡 **提示**：该方案无需引入笨重的外部图像库，依托纯前端 WebGL，内存消耗极低、运行丝滑，今晚按此文档步骤即可顺畅实现！
