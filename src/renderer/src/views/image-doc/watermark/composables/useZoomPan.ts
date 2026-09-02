/**
 * 图像无级缩放与平移手势 Composable
 */
import { ref } from 'vue'

export function useZoomPan(initialScale = 1) {
  const zoomScale = ref<number>(initialScale)
  const panX = ref<number>(0)
  const panY = ref<number>(0)
  const isDragging = ref<boolean>(false)
  const dragStart = { x: 0, y: 0 }

  const handleZoomIn = () => {
    zoomScale.value = Math.min(4.0, Number((zoomScale.value + 0.25).toFixed(2)))
  }

  const handleZoomOut = () => {
    zoomScale.value = Math.max(0.3, Number((zoomScale.value - 0.25).toFixed(2)))
  }

  const handleZoomReset = () => {
    zoomScale.value = 1
    panX.value = 0
    panY.value = 0
  }

  const handleViewerWheel = (e: WheelEvent) => {
    e.preventDefault()
    if (e.deltaY < 0) {
      handleZoomIn()
    } else {
      handleZoomOut()
    }
  }

  const handleMouseDown = (e: MouseEvent) => {
    if (e.button !== 0) return
    isDragging.value = true
    dragStart.x = e.clientX - panX.value
    dragStart.y = e.clientY - panY.value
  }

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging.value) return
    panX.value = e.clientX - dragStart.x
    panY.value = e.clientY - dragStart.y
  }

  const handleMouseUp = () => {
    isDragging.value = false
  }

  const handleDoubleClick = () => {
    if (zoomScale.value === 1) {
      zoomScale.value = 2
    } else {
      handleZoomReset()
    }
  }

  return {
    zoomScale,
    panX,
    panY,
    isDragging,
    handleZoomIn,
    handleZoomOut,
    handleZoomReset,
    handleViewerWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleDoubleClick
  }
}
