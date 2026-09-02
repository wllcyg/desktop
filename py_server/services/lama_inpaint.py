"""
LaMa (Large Mask Inpainting) ONNX 深度学习图像修复引擎

基于开源 Big-LaMa 傅里叶卷积图像修复模型：
- 纯 CPU 极速推理 (无需 GPU / PyTorch，基于 ONNX Runtime)
- 自动脑补被水印/污渍遮挡的背景纹理、横线、网格与纸张细节
- 支持任意分辨率输入 (自动 pad 到 8 的倍数并自适应还原)
"""

import os
import sys
import urllib.request
import cv2
import numpy as np

# 模型存放目录
MODELS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "resources", "models")
)
LAMA_MODEL_PATH = os.path.join(MODELS_DIR, "lama.onnx")

# 官方/镜像 LaMa ONNX 模型下载源 (备用镜像源)
LAMA_MODEL_URLS = [
    "https://github.com/advimman/lama/releases/download/v0.1/big-lama.onnx",
    "https://huggingface.co/anyisalin/big-lama-onnx/resolve/main/lama.onnx",
]

_session = None


def get_model_path() -> str:
    """获取模型文件路径，支持开发环境与生产打包环境"""
    if os.path.isfile(LAMA_MODEL_PATH):
        return LAMA_MODEL_PATH

    # 打包后资源路径兼容
    if getattr(sys, "frozen", False):
        res_path = os.path.join(sys._MEIPASS, "models", "lama.onnx")
        if os.path.isfile(res_path):
            return res_path

    return LAMA_MODEL_PATH


def is_lama_available() -> bool:
    """检查 LaMa 模型文件是否已就绪"""
    return os.path.isfile(get_model_path())


def init_lama_session():
    """惰性初始化 ONNX Runtime Session"""
    global _session
    if _session is not None:
        return _session

    model_path = get_model_path()
    if not os.path.isfile(model_path):
        return None

    try:
        import onnxruntime as ort

        # 配置纯 CPU 高性能执行选项
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = max(2, os.cpu_count() or 4)
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        _session = ort.InferenceSession(
            model_path,
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )
        print(f"[LaMa] ONNX Runtime Session 初始化成功: {model_path}")
        return _session
    except Exception as e:
        print(f"[LaMa] Session 初始化异常: {e}", file=sys.stderr)
        return None


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
