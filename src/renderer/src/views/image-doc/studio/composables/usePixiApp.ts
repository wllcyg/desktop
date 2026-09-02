/**
 * PixiJS Application 生命周期、纹理管理、视口手势与导出器
 */

import { ref } from 'vue'
// 必须在所有 pixi.js 导入之前引入：为 Electron CSP 环境提供不依赖 eval 的着色器编译
import 'pixi.js/unsafe-eval'
import {
  Application,
  Sprite,
  Container,
  Graphics,
  Text,
  TextStyle,
  Texture,
  ImageSource
} from 'pixi.js'
import { ImageRecipe, DrawingPath } from '../types'
import { useFilterPipeline } from './useFilterPipeline'

export function usePixiApp() {
  const isInitialized = ref(false)
  const zoomLevel = ref(1.0) // 1.0 = 100%
  const currentImageDims = ref({ width: 0, height: 0 })

  let app: Application | null = null
  let imageSprite: Sprite | null = null
  let currentTexture: Texture | null = null

  // 容器分层
  const rootContainer = new Container()
  const imageContainer = new Container()
  const inpaintMaskGraphics = new Graphics()
  const drawingsGraphics = new Graphics()
  const watermarkContainer = new Container()

  const { buildFilterList } = useFilterPipeline()

  /**
   * 初始化 PixiJS Application
   */
  const initApp = async (canvasEl: HTMLCanvasElement, width: number, height: number) => {
    if (app) return

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

    rootContainer.addChild(imageContainer)
    rootContainer.addChild(drawingsGraphics)
    rootContainer.addChild(inpaintMaskGraphics)
    rootContainer.addChild(watermarkContainer)

    app.stage.addChild(rootContainer)
    isInitialized.value = true
  }

  /**
   * 调整画布视口尺寸
   */
  const resizeViewport = (width: number, height: number) => {
    if (!app || !app.renderer) return
    app.renderer.resize(width, height)
  }

  /**
   * 加载图片纹理 (使用 HTMLImageElement + ImageSource 保证 Blob URL 100% 正确解码与创建纹理)
   */
  const loadImage = async (url: string): Promise<{ width: number; height: number }> => {
    if (!app) throw new Error('PixiJS App not initialized')

    // 1. 使用原生 HTMLImageElement 异步解码图片 (支持 Blob URL, Data URL, http, file 等所有格式)
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.src = url
    await img.decode()

    const w = img.naturalWidth
    const h = img.naturalHeight

    // 2. 使用 PixiJS v8 的 ImageSource 包装并创建 Texture
    const source = new ImageSource({
      resource: img,
      width: w,
      height: h,
      resolution: 1,
      autoGenerateMipmaps: false
    })
    const loadedTexture = new Texture({ source })
    currentTexture = loadedTexture

    if (!imageSprite) {
      imageSprite = new Sprite(loadedTexture)
      imageSprite.anchor.set(0.5, 0.5)
      imageContainer.addChild(imageSprite)
    } else {
      // 优雅重置旧滤镜并换绑新纹理，避免触发 WebGL BindGroup 销毁告警
      imageSprite.filters = []
      imageSprite.texture = loadedTexture
      imageSprite.visible = true
    }

    currentImageDims.value = { width: w, height: h }

    // 默认居中
    imageSprite.x = 0
    imageSprite.y = 0

    return { width: w, height: h }
  }

  /**
   * 清空画布中的图片与所有图层
   */
  const clearImage = () => {
    if (imageSprite) {
      imageSprite.filters = []
      imageSprite.visible = false
    }
    currentTexture = null
    inpaintMaskGraphics.clear()
    drawingsGraphics.clear()
    watermarkContainer.removeChildren()
    currentImageDims.value = { width: 0, height: 0 }
    zoomLevel.value = 1.0
  }

  /**
   * 应用编辑配方 (滤镜、变换、水印、涂抹)
   */
  const applyRecipe = (recipe: ImageRecipe, isComparingOriginal = false) => {
    if (!imageSprite) return

    if (isComparingOriginal) {
      // 临时对比原图：移除所有滤镜与变换
      imageSprite.filters = []
      imageSprite.rotation = 0
      imageSprite.scale.set(1, 1)
      watermarkContainer.visible = false
      drawingsGraphics.visible = false
      return
    }

    watermarkContainer.visible = true
    drawingsGraphics.visible = true

    // 1. 滤镜渲染
    imageSprite.filters = buildFilterList(recipe)

    // 2. 几何变换 (旋转与翻转)
    const rad = (recipe.rotation * Math.PI) / 180
    imageSprite.rotation = rad
    const scaleX = recipe.flipH ? -1 : 1
    const scaleY = recipe.flipV ? -1 : 1
    imageSprite.scale.set(scaleX, scaleY)

    // 3. 绘制文字/水印叠加
    renderWatermark(recipe)

    // 4. 绘制画笔与涂鸦
    renderDrawings(recipe.drawings)
  }

  /**
   * 渲染文字水印
   */
  const renderWatermark = (recipe: ImageRecipe) => {
    watermarkContainer.removeChildren()
    if (!recipe.watermark?.enabled || !recipe.watermark.text || !currentTexture) return

    const { text, color, fontSize, opacity, position } = recipe.watermark
    const style = new TextStyle({
      fontFamily: 'Inter, system-ui, sans-serif',
      fontSize,
      fill: color,
      fontWeight: 'bold',
      dropShadow: {
        alpha: 0.3,
        blur: 2,
        distance: 1
      }
    })

    const wmText = new Text({ text, style })
    wmText.alpha = opacity

    const halfW = currentTexture.width / 2
    const halfH = currentTexture.height / 2
    const margin = 24

    switch (position) {
      case 'top-left':
        wmText.anchor.set(0, 0)
        wmText.x = -halfW + margin
        wmText.y = -halfH + margin
        watermarkContainer.addChild(wmText)
        break
      case 'top-right':
        wmText.anchor.set(1, 0)
        wmText.x = halfW - margin
        wmText.y = -halfH + margin
        watermarkContainer.addChild(wmText)
        break
      case 'bottom-left':
        wmText.anchor.set(0, 1)
        wmText.x = -halfW + margin
        wmText.y = halfH - margin
        watermarkContainer.addChild(wmText)
        break
      case 'bottom-right':
        wmText.anchor.set(1, 1)
        wmText.x = halfW - margin
        wmText.y = halfH - margin
        watermarkContainer.addChild(wmText)
        break
      case 'center':
        wmText.anchor.set(0.5, 0.5)
        wmText.x = 0
        wmText.y = 0
        watermarkContainer.addChild(wmText)
        break
      case 'tile':
        // 45° 倾斜全屏平铺
        for (let y = -halfH; y < halfH; y += fontSize * 4) {
          for (let x = -halfW; x < halfW; x += text.length * fontSize * 1.2) {
            const tileText = new Text({ text, style })
            tileText.anchor.set(0.5, 0.5)
            tileText.rotation = -Math.PI / 6
            tileText.alpha = opacity
            tileText.x = x
            tileText.y = y
            watermarkContainer.addChild(tileText)
          }
        }
        break
    }
  }

  /**
   * 渲染涂鸦与标注
   */
  const renderDrawings = (drawings: DrawingPath[]) => {
    drawingsGraphics.clear()
    if (!drawings || drawings.length === 0) return

    for (const d of drawings) {
      if (d.points.length < 4) continue
      const colorNum = parseInt(d.color.replace('#', ''), 16) || 0xff0000
      drawingsGraphics.moveTo(d.points[0], d.points[1])
      for (let i = 2; i < d.points.length; i += 2) {
        drawingsGraphics.lineTo(d.points[i], d.points[i + 1])
      }
      drawingsGraphics.stroke({
        width: d.width,
        color: colorNum,
        alpha: d.isHighlighter ? 0.35 : 1.0,
        cap: 'round',
        join: 'round'
      })
    }
  }

  type StrokePoint = { x: number; y: number; radius: number }
  let inpaintStrokes: StrokePoint[][] = []
  let currentStroke: StrokePoint[] = []

  /**
   * 开始一条新的 AI 橡皮擦涂抹笔画
   */
  const beginInpaintStroke = () => {
    currentStroke = []
    inpaintStrokes.push(currentStroke)
  }

  /**
   * 绘制/追加 AI 橡皮擦涂抹笔触 (半透明红)
   */
  const drawInpaintBrush = (x: number, y: number, radius: number) => {
    inpaintMaskGraphics.circle(x, y, radius).fill({ color: 0xff3b30, alpha: 0.5 })
    const point = { x, y, radius }
    if (currentStroke.length > 0) {
      const prev = currentStroke[currentStroke.length - 1]
      // 在画板上绘制连线，消除快速拖动断点
      inpaintMaskGraphics
        .moveTo(prev.x, prev.y)
        .lineTo(x, y)
        .stroke({ width: radius * 2, color: 0xff3b30, alpha: 0.5, cap: 'round', join: 'round' })
    }
    currentStroke.push(point)
  }

  /**
   * 清除 AI 橡皮擦涂抹图层
   */
  const clearInpaintMask = () => {
    inpaintMaskGraphics.clear()
    inpaintStrokes = []
    currentStroke = []
  }

  /**
   * 导出 AI 涂抹产生的 1:1 物理像素纯黑白二值 Mask Base64 (纯白 255 为修复区域，纯黑 0 为保留背景)
   */
  const exportInpaintMaskBase64 = async (): Promise<string | null> => {
    if (!currentTexture || inpaintStrokes.length === 0) return null

    const imgW = currentTexture.width
    const imgH = currentTexture.height
    const canvas = document.createElement('canvas')
    canvas.width = imgW
    canvas.height = imgH
    const ctx = canvas.getContext('2d')
    if (!ctx) return null

    // 1. 底层填纯黑 (0 = 保持原样背景)
    ctx.fillStyle = '#000000'
    ctx.fillRect(0, 0, imgW, imgH)

    // 2. 涂抹区域填纯白 (255 = Inpaint 修复区域)
    ctx.fillStyle = '#ffffff'
    ctx.strokeStyle = '#ffffff'
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'

    const halfW = imgW / 2
    const halfH = imgH / 2

    for (const stroke of inpaintStrokes) {
      if (stroke.length === 0) continue
      if (stroke.length === 1) {
        const p = stroke[0]
        ctx.beginPath()
        ctx.arc(p.x + halfW, p.y + halfH, p.radius, 0, Math.PI * 2)
        ctx.fill()
      } else {
        ctx.lineWidth = stroke[0].radius * 2
        ctx.beginPath()
        ctx.moveTo(stroke[0].x + halfW, stroke[0].y + halfH)
        for (let i = 1; i < stroke.length; i++) {
          ctx.lineTo(stroke[i].x + halfW, stroke[i].y + halfH)
        }
        ctx.stroke()
      }
    }

    return canvas.toDataURL('image/png')
  }

  /**
   * 高保真渲染并导出 Blob
   */
  const exportBlob = async (recipe: ImageRecipe): Promise<Blob> => {
    if (!app || !currentTexture) throw new Error('App 未就绪')

    // 确保当前配方已应用
    applyRecipe(recipe)

    const format = recipe.export?.format || 'image/jpeg'
    const quality = recipe.export?.quality ?? 0.9

    // 使用 PixiJS 提取容器图像
    const canvas = (await app.renderer.extract.canvas(rootContainer)) as HTMLCanvasElement

    return new Promise<Blob>((resolve, reject) => {
      if (!canvas || typeof canvas.toBlob !== 'function') {
        return reject(new Error('Canvas toBlob 不可用'))
      }
      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob)
          else reject(new Error('导出图片 Blob 失败'))
        },
        format,
        quality
      )
    })
  }

  /**
   * 销毁 App
   */
  const destroyApp = () => {
    if (app) {
      app.destroy(true, { children: true, texture: true })
      app = null
      imageSprite = null
      currentTexture = null
      isInitialized.value = false
    }
  }

  return {
    isInitialized,
    zoomLevel,
    currentImageDims,
    rootContainer,
    imageSprite,
    initApp,
    resizeViewport,
    loadImage,
    clearImage,
    applyRecipe,
    beginInpaintStroke,
    drawInpaintBrush,
    clearInpaintMask,
    exportInpaintMaskBase64,
    exportBlob,
    destroyApp
  }
}
