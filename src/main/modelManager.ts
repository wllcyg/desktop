/**
 * AI 本地模型管理器 (Main Process)
 *
 * 1. 负责检查 %APPDATA%/toolbox/models/ 与 resources/models/ 中的模型文件状态
 * 2. 支持流式 HTTP 下载模型，支持国内镜像源容灾
 * 3. 实时通过 WebContents 广播下载进度 (已下载字节、总大小、百分比、速度 MB/s)
 * 4. 支持模型文件安全删除与空间释放
 */

import { app, ipcMain, BrowserWindow } from 'electron'
import { join } from 'path'
import { existsSync, mkdirSync, createWriteStream, promises as fsPromises, statSync } from 'fs'
import { get as httpGet, RequestOptions } from 'http'
import { get as httpsGet } from 'https'
import { parse as parseUrl } from 'url'

export interface ModelMetadata {
  id: string
  name: string
  tag: string
  description: string
  filename: string
  sizeBytes: number
  sizeFormatted: string
  urls: string[]
  isEssential: boolean
}

// 3 大核心顶尖模型清单
export const MODEL_REGISTRY: Record<string, ModelMetadata> = {
  lama: {
    id: 'lama',
    name: 'Big-LaMa 深度图像修复引擎',
    tag: '消除脑补 · 笔画缝合',
    description: '业内顶尖傅里叶卷积修复模型，用于顽固大水印消除、红印擦除后断裂笔画与表格横线无痕脑补。',
    filename: 'lama.onnx',
    sizeBytes: 208 * 1024 * 1024,
    sizeFormatted: '208 MB',
    urls: [
      'https://hf-mirror.com/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx',
      'https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx',
      'https://hf-mirror.com/Carve/LaMa-ONNX/resolve/main/lama.onnx',
      'https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama.onnx'
    ],
    isEssential: true
  },
  ocr_det: {
    id: 'ocr_det',
    name: 'PP-OCRv4 极速文字定位引擎',
    tag: '自动水印定位 · 公式文字检测',
    description: '百度飞桨 DBNet 极速文字检测模型，毫秒级自动检出图中倾斜水印文字，亦用于后续方程式识别。',
    filename: 'ch_PP-OCRv4_det_infer.onnx',
    sizeBytes: 4.6 * 1024 * 1024,
    sizeFormatted: '4.6 MB',
    urls: [
      'https://modelscope.cn/models/RapidAI/RapidOCR/resolve/master/PP-OCRv4/ch_PP-OCRv4_det_infer.onnx',
      'https://hf-mirror.com/SWHL/RapidOCR/resolve/main/PP-OCRv4/ch_PP-OCRv4_det_infer.onnx',
      'https://huggingface.co/SWHL/RapidOCR/resolve/main/PP-OCRv4/ch_PP-OCRv4_det_infer.onnx'
    ],
    isEssential: false
  },
  docres: {
    id: 'docres',
    name: 'DocRes 试卷与文档光影净化引擎',
    tag: '手部死黑阴影消除 · 白底增强',
    description: 'CVPR 顶会通用文档画质恢复模型，专治手机拍试卷时的浓重手影、光斑折痕，一键还原扫描仪白底。',
    filename: 'docres_shadow.onnx',
    sizeBytes: 43 * 1024 * 1024,
    sizeFormatted: '43 MB',
    urls: [
      'https://mirror.ghproxy.com/https://github.com/fabio-sim/DocShadow-ONNX-TensorRT/releases/download/v1.0.0/docshadow_sd7k.onnx',
      'https://ghfast.top/https://github.com/fabio-sim/DocShadow-ONNX-TensorRT/releases/download/v1.0.0/docshadow_sd7k.onnx',
      'https://github.com/fabio-sim/DocShadow-ONNX-TensorRT/releases/download/v1.0.0/docshadow_sd7k.onnx'
    ],
    isEssential: false
  }
}

// 获取模型实际存储的主目录 (用户数据目录优先，保证 Windows 写权限)
export function getModelsStorageDir(): string {
  const userDir = join(app.getPath('userData'), 'models')
  if (!existsSync(userDir)) {
    mkdirSync(userDir, { recursive: true })
  }
  return userDir
}

// 获取所有可能的模型搜索路径列表
export function getModelSearchPaths(filename: string): string[] {
  const rootDir = process.cwd()
  return [
    join(getModelsStorageDir(), filename),
    join(rootDir, 'resources', 'models', filename),
    join(process.resourcesPath || '', 'models', filename),
    join(process.resourcesPath || '', 'resources', 'models', filename)
  ]
}

// 检查某个模型是否存在 (必须大于 100KB，排除 HTML 错误页)
export function getExistingModelPath(filename: string): string | null {
  const paths = getModelSearchPaths(filename)
  for (const p of paths) {
    if (existsSync(p)) {
      try {
        const stat = statSync(p)
        if (stat.size > 100 * 1024) {
          return p
        }
      } catch (e) {
        // ignore
      }
    }
  }
  return null
}

// 当前活跃的下载任务
interface ActiveDownload {
  modelId: string
  req: any
  destPath: string
  tempPath: string
  startTime: number
  lastBytes: number
  lastSpeedCalcTime: number
  speed: number // bytes per sec
}

const activeDownloads = new Map<string, ActiveDownload>()

/**
 * 广播下载进度至所有窗口
 */
function broadcastProgress(
  modelId: string,
  payload: {
    status: 'downloading' | 'completed' | 'error' | 'canceled'
    downloaded: number
    total: number
    percent: number
    speedText: string
    errorMsg?: string
  }
): void {
  const windows = BrowserWindow.getAllWindows()
  for (const win of windows) {
    if (!win.isDestroyed()) {
      win.webContents.send(`model:progress:${modelId}`, payload)
      win.webContents.send('model:progress', { modelId, ...payload })
    }
  }
}

/**
 * 支持重定向的 HTTP/HTTPS 下载器
 */
function downloadFile(
  urlStr: string,
  tempPath: string,
  modelId: string,
  expectedTotal: number,
  redirectCount = 0
): Promise<void> {
  return new Promise((resolve, reject) => {
    if (redirectCount > 8) {
      return reject(new Error('重定向次数过多'))
    }

    const parsed = parseUrl(urlStr)
    const isHttps = parsed.protocol === 'https:'
    const httpModule = isHttps ? httpsGet : httpGet

    const options: RequestOptions & { rejectUnauthorized?: boolean } = {
      ...parsed,
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Toolbox/0.1.0'
      },
      timeout: 30000,
      // 允许自签名或镜像代理证书
      rejectUnauthorized: false
    }

    const req = httpModule(options, (res) => {
      // 收到有效响应，清除建立连接的初始超时
      req.setTimeout(0)

      // 全面支持 301, 302, 303, 307, 308 重定向
      if (
        res.statusCode &&
        res.statusCode >= 300 &&
        res.statusCode < 400 &&
        res.headers.location
      ) {
        const nextUrl = new URL(res.headers.location, urlStr).toString()
        console.log(`[ModelManager] 重定向 (${res.statusCode}) -> ${nextUrl}`)
        return downloadFile(nextUrl, tempPath, modelId, expectedTotal, redirectCount + 1)
          .then(resolve)
          .catch(reject)
      }

      if (res.statusCode !== 200) {
        return reject(new Error(`下载响应状态码异常: ${res.statusCode}`))
      }

      const contentType = res.headers['content-type'] || ''
      if (contentType.includes('text/html')) {
        return reject(new Error('下载链接返回了 HTML 网页而非二进制模型文件'))
      }

      const totalBytes =
        parseInt(res.headers['content-length'] || `${expectedTotal}`, 10) || expectedTotal
      const fileStream = createWriteStream(tempPath)

      let downloadedBytes = 0
      let lastCalcTime = Date.now()
      let bytesSinceLastCalc = 0
      let currentSpeedText = '0 MB/s'

      const activeItem: ActiveDownload = {
        modelId,
        req,
        destPath: tempPath,
        tempPath,
        startTime: Date.now(),
        lastBytes: 0,
        lastSpeedCalcTime: Date.now(),
        speed: 0
      }
      activeDownloads.set(modelId, activeItem)

      res.on('data', (chunk: Buffer) => {
        downloadedBytes += chunk.length
        bytesSinceLastCalc += chunk.length

        const now = Date.now()
        if (now - lastCalcTime >= 500) {
          const speedBps = (bytesSinceLastCalc / (now - lastCalcTime)) * 1000
          currentSpeedText = `${(speedBps / (1024 * 1024)).toFixed(1)} MB/s`
          lastCalcTime = now
          bytesSinceLastCalc = 0

          const percent = Math.min(100, Math.round((downloadedBytes / totalBytes) * 100))
          broadcastProgress(modelId, {
            status: 'downloading',
            downloaded: downloadedBytes,
            total: totalBytes,
            percent,
            speedText: currentSpeedText
          })
        }
      })

      fileStream.on('finish', () => {
        fileStream.close(() => {
          activeDownloads.delete(modelId)

          // 校验下载大小：小于 100KB 说明是错误页或中断文件
          if (downloadedBytes < 100 * 1024) {
            return reject(new Error(`下载文件大小异常 (${downloadedBytes} 字节)，文件不完整`))
          }

          broadcastProgress(modelId, {
            status: 'completed',
            downloaded: downloadedBytes,
            total: totalBytes,
            percent: 100,
            speedText: '完成'
          })
          resolve()
        })
      })

      fileStream.on('error', (err) => {
        activeDownloads.delete(modelId)
        reject(err)
      })

      res.pipe(fileStream)
    })

    req.on('error', (err) => {
      activeDownloads.delete(modelId)
      reject(err)
    })

    req.on('timeout', () => {
      req.destroy()
      activeDownloads.delete(modelId)
      reject(new Error('下载连接建立超时'))
    })
  })
}

/**
 * 注册所有的 Model IPC 处理程序
 */
export function setupModelManagerIPC(): void {
  // 1. 获取所有模型的就绪状态
  ipcMain.handle('model:get-all-status', async () => {
    const list: any[] = []
    for (const [id, meta] of Object.entries(MODEL_REGISTRY)) {
      const existingPath = getExistingModelPath(meta.filename)
      const isDownloaded = existingPath !== null
      let actualSize = 0

      if (isDownloaded && existingPath) {
        try {
          actualSize = statSync(existingPath).size
        } catch (e) {
          // ignore
        }
      }

      list.push({
        ...meta,
        isDownloaded,
        localPath: existingPath,
        actualSizeBytes: actualSize,
        isDownloading: activeDownloads.has(id)
      })
    }
    return { models: list, storageDir: getModelsStorageDir() }
  })

  // 2. 开始下载模型 (带镜像源回退机制)
  ipcMain.handle('model:start-download', async (_, modelId: string) => {
    const meta = MODEL_REGISTRY[modelId]
    if (!meta) {
      throw new Error(`未知的模型 ID: ${modelId}`)
    }

    if (activeDownloads.has(modelId)) {
      return { success: true, message: '模型已在下载队列中' }
    }

    const storageDir = getModelsStorageDir()
    const targetPath = join(storageDir, meta.filename)
    const tempPath = join(storageDir, `${meta.filename}.tmp`)

    // 异步下载，不阻塞 IPC
    ;(async () => {
      let lastError: Error | null = null

      for (const url of meta.urls) {
        try {
          console.log(`[ModelManager] 开始下载 ${meta.name} 从: ${url}`)
          await downloadFile(url, tempPath, modelId, meta.sizeBytes)

          // 下载完成，重命名临时文件为正式文件名
          if (existsSync(targetPath)) {
            await fsPromises.unlink(targetPath)
          }
          await fsPromises.rename(tempPath, targetPath)
          console.log(`[ModelManager] ${meta.name} 下载成功并存储于: ${targetPath}`)
          return
        } catch (err: any) {
          console.warn(`[ModelManager] 源 ${url} 下载失败:`, err.message)
          lastError = err
          if (existsSync(tempPath)) {
            try {
              await fsPromises.unlink(tempPath)
            } catch (e) {
              // ignore
            }
          }
        }
      }

      // 所有镜像源均失败
      broadcastProgress(modelId, {
        status: 'error',
        downloaded: 0,
        total: meta.sizeBytes,
        percent: 0,
        speedText: '下载失败',
        errorMsg: lastError?.message || '所有镜像下载源连接失败，请检查网络'
      })
    })()

    return { success: true, message: '已启动后台下载任务' }
  })

  // 3. 取消下载
  ipcMain.handle('model:cancel-download', async (_, modelId: string) => {
    const active = activeDownloads.get(modelId)
    if (active) {
      active.req?.destroy()
      activeDownloads.delete(modelId)
      if (existsSync(active.tempPath)) {
        try {
          await fsPromises.unlink(active.tempPath)
        } catch (e) {
          // ignore
        }
      }
      broadcastProgress(modelId, {
        status: 'canceled',
        downloaded: 0,
        total: 0,
        percent: 0,
        speedText: '已取消'
      })
      return { success: true }
    }
    return { success: false, message: '未找到活跃的下载任务' }
  })

  // 4. 删除本地模型释放空间
  ipcMain.handle('model:delete-file', async (_, modelId: string) => {
    const meta = MODEL_REGISTRY[modelId]
    if (!meta) throw new Error(`未知的模型 ID: ${modelId}`)

    const existingPath = getExistingModelPath(meta.filename)
    if (existingPath && existsSync(existingPath)) {
      await fsPromises.unlink(existingPath)
      return { success: true, message: '模型已成功从本地删除' }
    }
    return { success: false, message: '本地未找到该模型文件' }
  })
}
