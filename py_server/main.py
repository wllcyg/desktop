"""
工具箱 Python 核心服务 (标准输入/输出 JSON-RPC 管道模式)

与 Electron 主进程通过 stdin/stdout 进行进程管道通信：
1. 零网络端口占用，零防火墙拦截风险
2. 零 Web 框架依赖 (无需 FastAPI/Uvicorn)，打包体积极小
3. 进程常驻内存，模型与库只加载一次，毫秒级响应
"""

import sys
import json
import os
import io
import base64
import traceback
import cv2
import numpy as np

from services.watermark_service import (
    remove_light_watermark,
    inpaint_with_mask,
    combined_remove,
)


def _read_image(source: str) -> np.ndarray:
    """
    智能读取图片：支持本地绝对文件路径或 base64 字符串
    """
    if os.path.isfile(source):
        # 使用 cv2.imdecode 避免 Windows 中文路径乱码问题
        with open(source, "rb") as f:
            file_bytes = f.read()
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        # 尝试作为 base64 处理
        b64_str = source
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("无法解析图像数据")
    return img


def _save_or_encode_result(img: np.ndarray, output_path: str = None) -> dict:
    """
    如果指定了 output_path 则直接保存到本地文件，同时返回 base64 供前端预览
    """
    success, buffer = cv2.imencode(".png", img)
    if not success:
        raise RuntimeError("图像编码失败")

    # 如果有指定输出文件路径，直接写入本地磁盘（支持中文路径）
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(buffer.tobytes())

    b64_res = "data:image/png;base64," + base64.b64encode(buffer.tobytes()).decode("utf-8")
    return {
        "output_path": output_path,
        "image_base64": b64_res,
        "width": img.shape[1],
        "height": img.shape[0],
    }


# ==================== 接口方法注册表 ====================

def handle_ping(params: dict) -> dict:
    return {"status": "ok", "version": "0.1.0"}


def handle_remove_tile_watermark(params: dict) -> dict:
    input_source = params["input"]
    output_path = params.get("output_path")
    threshold = int(params.get("threshold", 200))
    contrast = float(params.get("contrast", 1.5))
    denoise = bool(params.get("denoise", True))
    mode = params.get("mode", "binary")

    img = _read_image(input_source)
    result = remove_light_watermark(img, threshold, contrast, denoise, mode)
    return _save_or_encode_result(result, output_path)


def handle_inpaint_watermark(params: dict) -> dict:
    input_source = params["input"]
    mask_source = params["mask"]
    output_path = params.get("output_path")
    radius = int(params.get("radius", 5))
    method = params.get("method", "telea")

    img = _read_image(input_source)
    mask = _read_image(mask_source)

    result = inpaint_with_mask(img, mask, radius, method)
    return _save_or_encode_result(result, output_path)


def handle_combined_watermark(params: dict) -> dict:
    input_source = params["input"]
    mask_source = params.get("mask")
    output_path = params.get("output_path")
    threshold = int(params.get("threshold", 200))
    contrast = float(params.get("contrast", 1.5))
    denoise = bool(params.get("denoise", True))
    mode = params.get("mode", "binary")
    inpaint_radius = int(params.get("inpaint_radius", 5))
    inpaint_method = params.get("inpaint_method", "telea")

    img = _read_image(input_source)
    mask = _read_image(mask_source) if mask_source else None

    result = combined_remove(
        img, mask, threshold, contrast, denoise, mode,
        inpaint_radius, inpaint_method,
    )
    return _save_or_encode_result(result, output_path)


METHODS = {
    "ping": handle_ping,
    "watermark.remove_tile": handle_remove_tile_watermark,
    "watermark.inpaint": handle_inpaint_watermark,
    "watermark.combined": handle_combined_watermark,
}


def main():
    # 强制将 stdout 设置为 UTF-8 编码，避免 Windows 控制台编码问题
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")

    # 发送就绪信号给 Electron 主进程
    ready_msg = json.dumps({"jsonrpc": "2.0", "event": "ready", "version": "0.1.0"}, ensure_ascii=False)
    sys.stdout.write(ready_msg + "\n")
    sys.stdout.flush()

    # 主事件循环：按行从 stdin 接收 JSON-RPC 请求
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        req_id = None
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method not in METHODS:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"未知的处理方法: {method}"}
                }
            else:
                result = METHODS[method](params)
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": result
                }
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(e)}
            }

        # 写入 stdout 并立即 flush
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
