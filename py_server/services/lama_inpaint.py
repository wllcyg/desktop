"""
LaMa (Large Mask Inpainting) ONNX 深度学习图像修复引擎

基于开源 Big-LaMa 傅里叶卷积图像修复模型：
- 纯 CPU 极速推理 (无需 GPU / PyTorch，基于 ONNX Runtime)
- 自动脑补被水印/污渍遮挡的背景纹理、横线、网格与纸张细节
- 完美适配固定尺寸 (512x512) 与动态尺寸 ONNX 模型，无缝融合原图分辨率
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
    orig_h, orig_w = img.shape[:2]

    # 1. 预处理 Mask 为严格单通道二值图
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask_binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    # 微膨胀掩膜消除笔刷边界残留
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_dilated = cv2.dilate(mask_binary, kernel, iterations=1)

    session = init_lama_session()
    if session is None:
        # 模型未就绪时优雅降级为 OpenCV Telea 算法
        print("[LaMa] 未检测到 lama.onnx 模型，自动降级为 OpenCV 修复算法")
        return cv2.inpaint(img, mask_dilated, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

    try:
        # 2. 读取模型输入尺寸要求 (判断是 512x512 固定尺寸还是动态尺寸)
        inputs_meta = session.get_inputs()
        input_shape = inputs_meta[0].shape
        
        is_fixed_dim = False
        target_h, target_w = 512, 512

        # 检查是否包含固定整数维度
        if len(input_shape) == 4:
            dim_h = input_shape[2]
            dim_w = input_shape[3]
            if isinstance(dim_h, int) and dim_h > 0 and isinstance(dim_w, int) and dim_w > 0:
                is_fixed_dim = True
                target_h, target_w = dim_h, dim_w

        if is_fixed_dim:
            # 固定尺寸模型 (如 512x512)：缩放 -> 推理 -> 双三次还原插值 -> 仅覆盖掩膜区域
            img_input = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_AREA)
            mask_input = cv2.resize(mask_dilated, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
        else:
            # 动态尺寸模型：填充至 8 的倍数
            img_input, _, _ = pad_to_multiple(img, multiple=8)
            mask_input, _, _ = pad_to_multiple(mask_dilated, multiple=8)

        # 3. 归一化与通道转换 (BGR -> RGB, [H, W, C] -> [1, C, H, W], float32 [0, 1])
        img_rgb = cv2.cvtColor(img_input, cv2.COLOR_BGR2RGB)
        img_tensor = (img_rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[np.newaxis, ...]
        mask_tensor = (mask_input.astype(np.float32) / 255.0)[np.newaxis, np.newaxis, ...]

        # 4. ONNX Runtime CPU 推理
        input_names = [inp.name for inp in inputs_meta]
        inputs = {input_names[0]: img_tensor, input_names[1]: mask_tensor}
        outputs = session.run(None, inputs)

        # 5. 后处理 (输出张量转回 uint8 BGR 图像)
        output = outputs[0][0].transpose(1, 2, 0)
        output = np.clip(output * 255.0, 0, 255).astype(np.uint8)
        output_bgr = cv2.cvtColor(output, cv2.COLOR_RGB2BGR)

        if is_fixed_dim:
            # 还原至原图分辨率
            output_full = cv2.resize(output_bgr, (orig_w, orig_h), interpolation=cv2.INTER_LANCZOS4)
        else:
            output_full = output_bgr[:orig_h, :orig_w]

        # 6. 精准像素融合：非掩膜区域 100% 保持原始画质，仅将掩膜区域无痕替换为 AI 修复内容
        result = img.copy()
        result[mask_dilated > 0] = output_full[mask_dilated > 0]
        return result

    except Exception as e:
        print(f"[LaMa] 模型推理发生异常，自动降级为 OpenCV 修复: {e}")
        return cv2.inpaint(img, mask_dilated, inpaintRadius=5, flags=cv2.INPAINT_TELEA)
