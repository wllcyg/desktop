/**
 * 去水印模块公共类型定义
 */

export interface ImageItem {
  id: string
  file: File
  name: string
  path: string
  previewUrl: string
  resultUrl: string | null
  status: 'pending' | 'processing' | 'done' | 'error'
  errorMsg?: string
}

// 将 File 对象转换为 Base64 字符串辅助函数
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = (err) => reject(err)
    reader.readAsDataURL(file)
  })
}
