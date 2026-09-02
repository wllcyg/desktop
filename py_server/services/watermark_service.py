"""
去水印核心算法服务模块 (全自动智能去水印与批量处理)

采用多阶段自适应图像流水线：
1. 自动检测并消除红色印章/红笔批改
2. 自动大核背景光照归一化 (消除全屏平铺浅色水印与拍摄阴影)
3. 自动高频文字笔画增强 (保留化学公式、下标、符号极细边缘)
"""

import os
import cv2
import numpy as np
from typing import Optional, List, Dict


def auto_remove_watermark(
    img: np.ndarray,
    sensitivity: int = 200,
    contrast: float = 1.3,
    auto_clean_red: bool = True,
) -> np.ndarray:
    """
    全自动傻瓜式去水印算法流水线

    Args:
        img: 输入图片 (BGR)
        sensitivity: 去水印灵敏度 (100-250)，默认 200
        contrast: 文字对比度增强倍数，默认 1.3
        auto_clean_red: 是否自动检测并去除红色印章/批改红痕

    Returns:
        处理后干净清晰的试卷/课件图片 (BGR)
    """
    result = img.copy()

    # 阶段 1：自动检测是否存在红色印章/红笔批改痕迹
    if auto_clean_red:
        b, g, r = cv2.split(result)
        # 计算红色差分图 (R - G)
        red_diff = cv2.subtract(r, g)
        # 统计明显偏红的像素数量
        red_pixel_count = np.count_nonzero(red_diff > 45)
        total_pixels = img.shape[0] * img.shape[1]

        # 如果存在红色印章/批改痕迹 (占像素比大于 0.02% 且小于 25%)
        if 0.0002 < (red_pixel_count / total_pixels) < 0.25:
            _, red_mask = cv2.threshold(red_diff, 45, 255, cv2.THRESH_BINARY)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            red_mask = cv2.dilate(red_mask, kernel, iterations=1)
            # 将红色区域安全填白
            result[red_mask == 255] = [255, 255, 255]

    # 阶段 2：智能背景光照归一化 (核心算法，消除平铺水印与不均光影)
    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

    # 自适应计算核大小
    min_dim = min(img.shape[:2])
    k_size = max(31, (min_dim // 25) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))

    # 大核闭运算提取纸张背景底色
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

    # 归一化相除：原图 / 背景底色，消除浅色平铺文字
    normalized = cv2.divide(gray, bg, scale=255)

    # 阶段 3：阈值判定与文字保留
    if sensitivity < 250:
        _, binary = cv2.threshold(normalized, sensitivity, 255, cv2.THRESH_BINARY)
    else:
        binary = normalized

    # 阶段 4：文字对比度自适应增强
    if contrast != 1.0:
        enhanced = cv2.convertScaleAbs(binary, alpha=contrast, beta=0)
    else:
        enhanced = binary

    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def inpaint_with_mask(
    img: np.ndarray,
    mask: np.ndarray,
    radius: int = 5,
    method: str = "telea",
) -> np.ndarray:
    """
    交互式画笔涂抹修补算法 (用于去除角落特定 LOGO 或大面积污渍)
    """
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.dilate(mask, kernel, iterations=1)

    flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    return cv2.inpaint(img, mask, inpaintRadius=radius, flags=flag)
