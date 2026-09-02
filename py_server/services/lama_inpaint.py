"""
LaMa (Large Mask Inpainting) ONNX 深度学习图像修复引擎

基于开源 Big-LaMa 傅里叶卷积图像修复模型：
- 纯 CPU 极速推理 (无需 GPU / PyTorch，基于 ONNX Runtime)
- 自动脑补被水印/污渍遮挡的背景纹理、横线、网格与纸张细节
- 支持任意分辨率输入 (自动 pad 到 8 的倍数并自适应还原)
"""

import os
import sys
import cv2
import numpy as np

from services.model_hub import (
    get_model_path as hub_get_model_path,
    is_model_installed as hub_is_installed,
    get_or_create_session as hub_get_session,
)


def get_model_path() -> str:
    """获取模型文件路径，优先使用 model_hub 统一解析"""
    return hub_get_model_path("lama")


def is_lama_available() -> bool:
    """检查 LaMa 模型文件是否已就绪"""
    return hub_is_installed("lama")


def init_lama_session():
    """惰性获取 ONNX Runtime Session"""
    return hub_get_session("lama")


def pad_to_multiple(img: np.ndarray, multiple: int = 8):
    """将图像高宽填充至 8 的整数倍"""
    h, w = img.shape[:2]
    new_h = ((h + multiple - 1) // multiple) * multiple
    new_w = ((w + multiple - 1) // multiple) * multiple

    pad_bottom = new_h - h
    pad_right = new_w - w

    if pad_bottom > 0 or pad_right > 0:
        if len(img.shape) == 3:
            img_padded = cv2.copyMakeBorder(
                img, 0, pad_bottom, 0, pad_right, cv2.BORDER_REFLECT
            )
        else:
            img_padded = cv2.copyMakeBorder(
                img, 0, pad_bottom, 0, pad_right, cv2.BORDER_CONSTANT, value=0
            )
        return img_padded, h, w
    return img, h, w


def lama_inpaint(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    使用 LaMa 深度学习模型执行图像修复

    Args:
        img: 输入图片 (BGR 格式, uint8, shape: [H, W, 3])
        mask: 涂抹掩膜 (单通道灰度图, uint8, shape: [H, W], 255=需要修复的区域)

    Returns:
        修复后的图片 (BGR 格式, uint8)
    """
    session = init_lama_session()
    if session is None:
        # 模型未就绪时优雅降级为 OpenCV Telea 算法
        print("[LaMa] 未检测到 lama.onnx 模型，自动降级为 OpenCV 修复算法")
        flag = cv2.INPAINT_TELEA
        return cv2.inpaint(img, mask, inpaintRadius=5, flags=flag)

    # 1. 预处理 Mask
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    # 微膨胀掩膜消除画笔边缘残留
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.dilate(mask, kernel, iterations=1)

    # 2. 图像填充到 8 的整数倍
    img_padded, orig_h, orig_w = pad_to_multiple(img, multiple=8)
    mask_padded, _, _ = pad_to_multiple(mask, multiple=8)

    # 3. 归一化与通道转换 (BGR -> RGB, [H, W, C] -> [1, C, H, W], float32 [0, 1])
    img_rgb = cv2.cvtColor(img_padded, cv2.COLOR_BGR2RGB)
    img_tensor = (img_rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[np.newaxis, ...]
    mask_tensor = (mask_padded.astype(np.float32) / 255.0)[np.newaxis, np.newaxis, ...]

    # 4. ONNX Runtime CPU 推理
    input_names = [inp.name for inp in session.get_inputs()]
    inputs = {input_names[0]: img_tensor, input_names[1]: mask_tensor}
    outputs = session.run(None, inputs)

    # 5. 后处理 (输出张量转回 uint8 BGR 图像并裁切回原尺寸)
    output = outputs[0][0].transpose(1, 2, 0)
    output = np.clip(output * 255.0, 0, 255).astype(np.uint8)
    output_bgr = cv2.cvtColor(output, cv2.COLOR_RGB2BGR)

    # 裁切回原图尺寸
    result = output_bgr[:orig_h, :orig_w]
    return result
