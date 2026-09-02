/**
 * OCR 模块公共类型定义
 */

export interface OcrBoxLine {
  id: number
  box: number[] // [x1, y1, x2, y2]
  raw_text: string
  formatted_text: string
  latex: string
  latex_inline: string
  mathml: string
  is_equation: boolean
}

export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}
