"""
去水印核心算法服务模块

提供两大核心能力：
1. 试卷/文档平铺浅色水印消除（阈值 + 色彩通道过滤）
2. 交互式蒙版修补（OpenCV Inpainting）
两者可组合使用：先全局去浅色水印 → 再局部涂抹修补残留 LOGO/印章
"""

import cv2
import numpy as np
from typing import Optional


def remove_light_watermark(
    img: np.ndarray,
    threshold: int = 200,
    contrast: float = 1.5,
    denoise: bool = True,
    mode: str = "binary",
) -> np.ndarray:
    """
    试卷/课件平铺浅色文字水印消除算法

    核心原理：水印颜色浅（灰度高），题目文字颜色深（灰度低），
    通过阈值分割将浅色水印像素推为纯白，保留深色字迹。

    Args:
        img: 输入图片 (BGR)
        threshold: 灰度阈值 (0-255)，值越小去水印越激进，默认 200
        contrast: 对比度增强倍数，默认 1.5
        denoise: 是否做轻微降噪平滑
        mode: 处理模式
              - "binary": 简单全局二值化（速度最快，适合黑白试卷）
              - "adaptive": 自适应阈值（适合光照不均匀的拍照试卷）
              - "color_filter": 色彩通道过滤（适合彩色水印如浅蓝/浅红）

    Returns:
        处理后的图片 (BGR)
    """
    if mode == "binary":
        return _remove_by_binary_threshold(img, threshold, contrast, denoise)
    elif mode == "adaptive":
        return _remove_by_adaptive_threshold(img, contrast, denoise)
    elif mode == "color_filter":
        return _remove_by_color_filter(img, threshold, contrast, denoise)
    else:
        return _remove_by_binary_threshold(img, threshold, contrast, denoise)


def _remove_by_binary_threshold(
    img: np.ndarray, threshold: int, contrast: float, denoise: bool
) -> np.ndarray:
    """全局二值化模式：最快速，适合标准黑白试卷"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 对比度增强：拉开深色文字与浅色水印的差距
    enhanced = cv2.convertScaleAbs(gray, alpha=contrast, beta=0)

    # 全局阈值：高于 threshold 的浅色水印像素 → 纯白 255
    _, binary = cv2.threshold(enhanced, threshold, 255, cv2.THRESH_BINARY)

    if denoise:
        # 轻微形态学闭运算，消除孤立噪点
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # 灰度图转回三通道 BGR
    result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    return result


def _remove_by_adaptive_threshold(
    img: np.ndarray, contrast: float, denoise: bool
) -> np.ndarray:
    """自适应阈值模式：适合手机拍照的光照不均匀试卷"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 对比度增强
    enhanced = cv2.convertScaleAbs(gray, alpha=contrast, beta=0)

    if denoise:
        enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)

    # 自适应阈值：自动适配局部光照差异
    binary = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
    )

    result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    return result


def _remove_by_color_filter(
    img: np.ndarray, threshold: int, contrast: float, denoise: bool
) -> np.ndarray:
    """色彩通道过滤模式：适合带有浅蓝/浅红/浅灰彩色水印的课件图片"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    # 低饱和度 + 高亮度的像素大概率是浅色水印
    # 饱和度低于 50 且亮度高于 threshold 的区域视为水印
    watermark_mask = ((s < 60) & (v > threshold)).astype(np.uint8) * 255

    # 膨胀掩膜，扩大水印覆盖范围避免残留边缘
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    watermark_mask = cv2.dilate(watermark_mask, kernel, iterations=1)

    # 将水印区域替换为纯白
    result = img.copy()
    result[watermark_mask == 255] = [255, 255, 255]

    if denoise:
        # 对替换区域做轻微高斯模糊使边缘过渡更自然
        blurred = cv2.GaussianBlur(result, (3, 3), 0)
        result = np.where(
            watermark_mask[:, :, np.newaxis] == 255, blurred, result
        )

    # 对比度增强
    result = cv2.convertScaleAbs(result, alpha=contrast, beta=0)

    return result


def inpaint_with_mask(
    img: np.ndarray,
    mask: np.ndarray,
    radius: int = 5,
    method: str = "telea",
) -> np.ndarray:
    """
    交互式蒙版修补算法

    根据前端用户画笔涂抹生成的 Mask 掩膜，对标记区域进行纹理重建修复。
    适用于去除角落 LOGO、印章、二维码、红笔批改痕迹等。

    Args:
        img: 原始图片 (BGR)
        mask: 二值化掩膜 (单通道，白色 255 表示需要修补的区域)
        radius: 修补半径，值越大修补范围越广但越模糊，默认 5
        method: 修补算法
                - "telea": Telea 快速行进算法（速度快，边缘锐利）
                - "ns": Navier-Stokes 流体扩散算法（大面积修补更自然）

    Returns:
        修补后的图片 (BGR)
    """
    # 确保 mask 是单通道灰度图
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

    # 二值化掩膜（确保只有 0 和 255）
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    # 形态学膨胀掩膜：消除画笔涂抹锯齿，扩大修补边界 1-2 像素
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.dilate(mask, kernel, iterations=1)

    # 选择修补算法
    flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS

    # 执行修补
    result = cv2.inpaint(img, mask, inpaintRadius=radius, flags=flag)

    return result


def combined_remove(
    img: np.ndarray,
    mask: Optional[np.ndarray] = None,
    threshold: int = 200,
    contrast: float = 1.5,
    denoise: bool = True,
    mode: str = "binary",
    inpaint_radius: int = 5,
    inpaint_method: str = "telea",
) -> np.ndarray:
    """
    组合去水印：先全局去平铺浅色水印 → 再局部蒙版修补残留 LOGO/印章

    两步串联流水线，一次调用同时完成两类水印的清除。

    Args:
        img: 原始图片 (BGR)
        mask: 可选的涂抹掩膜，为 None 则跳过修补步骤
        threshold: 浅色水印灰度阈值
        contrast: 对比度增强倍数
        denoise: 是否降噪
        mode: 浅色水印去除模式 (binary / adaptive / color_filter)
        inpaint_radius: 修补半径
        inpaint_method: 修补算法 (telea / ns)

    Returns:
        处理后的图片 (BGR)
    """
    # 第一步：全局去浅色平铺水印
    result = remove_light_watermark(img, threshold, contrast, denoise, mode)

    # 第二步：如果有涂抹蒙版，则对残留区域做局部修补
    if mask is not None:
        result = inpaint_with_mask(result, mask, inpaint_radius, inpaint_method)

    return result
