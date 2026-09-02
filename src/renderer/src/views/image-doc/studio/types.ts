/**
 * 图片工作台 (Image Studio) 数据模型与类型定义
 */

export type FilterPresetType =
  | 'none'
  // 文档办公类
  | 'scanner_whiten' // 扫描仪白底化 (消除试卷阴影灰底)
  | 'pure_bw' // 纯净黑白二值化 (极致打印省墨)
  | 'ink_boost' // 蓝黑手写笔墨水增强
  | 'doc_contrast' // 昏暗文档高光对比
  // 艺术美化类
  | 'vintage' // 复古胶片
  | 'warm_sunlight' // 明亮暖阳
  | 'cool_nordic' // 清冷北欧
  | 'cinematic' // 电影青橙质感
  | 'polaroid' // 拍立得复古
  | 'classic_mono' // 经典黑白影调

export type CropAspectRatio = 'free' | '1:1' | '4:3' | '3:4' | '16:9' | '9:16' | 'A4'

export type WatermarkPosition = 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left' | 'center' | 'tile'

export interface CropRect {
  x: number
  y: number
  width: number
  height: number
}

export interface MosaicRect {
  id: string
  x: number
  y: number
  width: number
  height: number
  size: number // 颗粒度
}

export interface DrawingPath {
  id: string
  color: string
  width: number
  points: number[] // [x0, y0, x1, y1, ...]
  isHighlighter?: boolean
}

export interface WatermarkSettings {
  enabled: boolean
  text: string
  color: string
  fontSize: number
  opacity: number
  position: WatermarkPosition
}

export interface WatermarkCleanSettings {
  cleanFaintWatermark: boolean // 消除浅灰色背景平铺水印
  cleanRedStamp: boolean // 自动去除红色印章/红笔批改痕迹
  sensitivity: number // 灵敏度 100 ~ 250
}

export interface ResizeSettings {
  enabled: boolean
  mode: 'pixel' | 'percent' | 'max-edge'
  targetWidth: number
  targetHeight: number
  percent: number
  maxEdge: number
  lockAspectRatio: boolean
}

export interface ExportSettings {
  format: 'image/jpeg' | 'image/png' | 'image/webp'
  quality: number // 0.1 ~ 1.0 (例如 0.85)
  filenameSuffix: string // 如 "_已处理"
}

export interface ImageRecipe {
  // 1. 构图变换
  rotation: number // 0, 90, 180, 270
  flipH: boolean
  flipV: boolean
  crop?: CropRect

  // 2. 预设滤镜与专业调色
  filterPreset: FilterPresetType
  brightness: number // -100 ~ 100 (0 为无调整)
  contrast: number // -100 ~ 100
  saturation: number // -100 ~ 100
  exposure: number // -100 ~ 100
  temperature: number // -100 (冷) ~ 100 (暖)
  hue: number // 0 ~ 360
  sharpen: boolean // 边缘锐化

  // 3. 去水印与智能修复
  watermarkClean: WatermarkCleanSettings
  inpaintMaskBase64?: string // 涂抹生成的 Base64 Mask 蒙版 (供 LaMa AI 擦除)

  // 4. 涂抹批注与隐私
  mosaics: MosaicRect[]
  drawings: DrawingPath[]

  // 5. 尺寸调整
  resize: ResizeSettings

  // 6. 水印与签名叠加
  watermark: WatermarkSettings

  // 7. 导出配置
  export: ExportSettings
}

export interface ImageItem {
  id: string
  file?: File
  name: string
  filePath?: string
  originalUrl: string
  previewUrl: string
  width: number
  height: number
  sizeBytes: number
  // 该图片独立的编辑配方 (Recipe)
  recipe: ImageRecipe
  status: 'idle' | 'processing' | 'done' | 'error'
  errorMsg?: string
  progress?: number
}

export type ActiveToolType =
  | 'filter' // 预设滤镜
  | 'color' // 专业调色
  | 'watermark-clean' // 智能去水印 & AI 橡皮擦
  | 'crop-resize' // 尺寸与裁剪
  | 'annotate' // 标注与马赛克
  | 'watermark-overlay' // 水印与印章

export function createDefaultRecipe(): ImageRecipe {
  return {
    rotation: 0,
    flipH: false,
    flipV: false,
    crop: undefined,
    filterPreset: 'none',
    brightness: 0,
    contrast: 0,
    saturation: 0,
    exposure: 0,
    temperature: 0,
    hue: 0,
    sharpen: false,
    watermarkClean: {
      cleanFaintWatermark: false,
      cleanRedStamp: false,
      sensitivity: 200
    },
    inpaintMaskBase64: undefined,
    mosaics: [],
    drawings: [],
    resize: {
      enabled: false,
      mode: 'percent',
      targetWidth: 1920,
      targetHeight: 1080,
      percent: 100,
      maxEdge: 2048,
      lockAspectRatio: true
    },
    watermark: {
      enabled: false,
      text: '内部资料 请勿外传',
      color: '#ff0000',
      fontSize: 24,
      opacity: 0.35,
      position: 'bottom-right'
    },
    export: {
      format: 'image/jpeg',
      quality: 0.9,
      filenameSuffix: '_edit'
    }
  }
}
