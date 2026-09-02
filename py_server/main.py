"""
工具箱 Python 核心服务 (标准输入/输出 JSON-RPC 管道模式)
支持单张与批量全自动智能去水印
"""

import sys
import json
import os
import io
import base64
import traceback

# 强制将标准输入输出流设置为 UTF-8 编码，防止 Windows 控制台乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

import cv2
import numpy as np

from services.watermark_service import (
    auto_remove_watermark,
    inpaint_with_mask,
)
from services.model_hub import (
    verify_and_start_model,
    get_all_models_status,
)


def _read_image(source: str) -> np.ndarray:
    """智能读取图片：支持本地绝对文件路径或 base64 字符串"""
    if os.path.isfile(source):
        with open(source, "rb") as f:
            file_bytes = f.read()
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        b64_str = source
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError(f"无法解析图像数据: {source[:50]}")
    return img


def _save_or_encode_result(img: np.ndarray, output_path: str = None, return_base64: bool = True) -> dict:
    """保存到文件或返回 base64"""
    success, buffer = cv2.imencode(".png", img)
    if not success:
        raise RuntimeError("图像编码失败")

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(buffer.tobytes())

    res = {
        "output_path": output_path,
        "width": img.shape[1],
        "height": img.shape[0],
    }

    if return_base64:
        res["image_base64"] = "data:image/png;base64," + base64.b64encode(buffer.tobytes()).decode("utf-8")

    return res


# ==================== JSON-RPC 接口处理函数 ====================

def handle_ping(params: dict) -> dict:
    return {"status": "ok", "version": "0.1.0"}


def handle_auto_remove_watermark(params: dict) -> dict:
    """单张全自动智能去水印"""
    input_source = params["input"]
    output_path = params.get("output_path")
    sensitivity = int(params.get("sensitivity", 200))
    contrast = float(params.get("contrast", 1.3))
    auto_clean_red = bool(params.get("auto_clean_red", True))

    img = _read_image(input_source)
    result = auto_remove_watermark(img, sensitivity, contrast, auto_clean_red)
    return _save_or_encode_result(result, output_path, return_base64=True)


def handle_batch_remove_watermark(params: dict) -> dict:
    """
    批量多张智能去水印
    params: {
      items: [ { id: "1", input: "D:/a.png", output_path: "D:/out/a.png" }, ... ],
      sensitivity: 200,
      contrast: 1.3,
      auto_clean_red: true,
      return_base64: true
    }
    """
    items = params.get("items", [])
    sensitivity = int(params.get("sensitivity", 200))
    contrast = float(params.get("contrast", 1.3))
    auto_clean_red = bool(params.get("auto_clean_red", True))
    return_base64 = bool(params.get("return_base64", True))

    results = []
    for item in items:
        item_id = item.get("id")
        input_source = item.get("input")
        output_path = item.get("output_path")

        try:
            img = _read_image(input_source)
            processed = auto_remove_watermark(img, sensitivity, contrast, auto_clean_red)
            res = _save_or_encode_result(processed, output_path, return_base64=return_base64)
            results.append({
                "id": item_id,
                "success": True,
                "output_path": output_path,
                "image_base64": res.get("image_base64") if return_base64 else None
            })
        except Exception as e:
            results.append({
                "id": item_id,
                "success": False,
                "error": str(e)
            })

    return {"results": results, "total": len(items)}


def handle_inpaint_watermark(params: dict) -> dict:
    """画笔涂抹修补"""
    input_source = params["input"]
    mask_source = params["mask"]
    output_path = params.get("output_path")
    radius = int(params.get("radius", 5))
    method = params.get("method", "telea")

    img = _read_image(input_source)
    mask = _read_image(mask_source)

    result = inpaint_with_mask(img, mask, radius, method)
    return _save_or_encode_result(result, output_path, return_base64=True)


import importlib
import services.model_hub

def handle_verify_and_start_model(params: dict) -> dict:
    importlib.reload(services.model_hub)
    model_id = params.get("model_id")
    return services.model_hub.verify_and_start_model(model_id)


def handle_get_models_status(params: dict) -> dict:
    importlib.reload(services.model_hub)
    return services.model_hub.get_all_models_status()


import services.ocr_service
import services.formula_parser
import services.pdf_service

def handle_ocr_recognize(params: dict) -> dict:
    """OCR 识别 (支持全图与局部选区，DocRes 增强联动)"""
    importlib.reload(services.ocr_service)
    importlib.reload(services.formula_parser)

    source = params.get("image")
    if not source:
        raise ValueError("缺少待识别图像输入")

    img = _read_image(source)
    crop_box = params.get("crop_box")
    mode = params.get("mode", "chemistry")
    use_docres = bool(params.get("use_docres", False))

    return services.ocr_service.run_ocr_pipeline(
        img=img,
        crop_box=crop_box,
        mode=mode,
        use_docres=use_docres
    )


def handle_parse_formula(params: dict) -> dict:
    """独立公式/文本解析转换 (转 LaTeX 与 MathML)"""
    importlib.reload(services.formula_parser)
    text = params.get("text", "")
    mode = params.get("mode", "chemistry")
    return services.formula_parser.parse_equation_or_text(text, mode=mode)


def handle_pdf_get_info(params: dict) -> dict:
    """获取 PDF 基础信息及缩略图"""
    importlib.reload(services.pdf_service)
    pdf_path = params.get("path")
    include_thumbnails = bool(params.get("include_thumbnails", False))
    max_thumb_size = int(params.get("max_thumb_size", 240))
    return services.pdf_service.get_pdf_info(
        pdf_path=pdf_path,
        include_thumbnails=include_thumbnails,
        max_thumb_size=max_thumb_size
    )


def handle_pdf_merge(params: dict) -> dict:
    """PDF 多文件合并"""
    importlib.reload(services.pdf_service)
    file_configs = params.get("files", [])
    output_path = params.get("output_path")
    auto_generate_toc = bool(params.get("auto_generate_toc", True))
    compress = bool(params.get("compress", True))
    return services.pdf_service.merge_pdfs(
        file_configs=file_configs,
        output_path=output_path,
        auto_generate_toc=auto_generate_toc,
        compress=compress
    )


def handle_pdf_split(params: dict) -> dict:
    """PDF 规则拆分"""
    importlib.reload(services.pdf_service)
    pdf_path = params.get("path")
    split_mode = params.get("split_mode", "by_chunk")
    split_params = params.get("params", {})
    output_dir = params.get("output_dir")
    return services.pdf_service.split_pdf(
        pdf_path=pdf_path,
        split_mode=split_mode,
        params=split_params,
        output_dir=output_dir
    )


def handle_pdf_reorganize(params: dict) -> dict:
    """PDF 可视化重排与旋转导出"""
    importlib.reload(services.pdf_service)
    pdf_path = params.get("path")
    page_configs = params.get("pages", [])
    output_path = params.get("output_path")
    return services.pdf_service.reorganize_pdf(
        pdf_path=pdf_path,
        page_configs=page_configs,
        output_path=output_path
    )


import services.rename_service

def handle_file_batch_rename(params: dict) -> dict:
    """批量文件重命名 (含占用捕获与隔离)"""
    importlib.reload(services.rename_service)
    rename_pairs = params.get("pairs", [])
    return services.rename_service.batch_rename_files(rename_pairs)


def handle_file_undo_rename(params: dict) -> dict:
    """一键撤销重命名"""
    importlib.reload(services.rename_service)
    records = params.get("records", [])
    return services.rename_service.undo_rename_files(records)


METHODS = {
    "ping": handle_ping,
    "model.verify_and_start": handle_verify_and_start_model,
    "model.get_status": handle_get_models_status,
    "watermark.auto_remove": handle_auto_remove_watermark,
    "watermark.batch_remove": handle_batch_remove_watermark,
    "watermark.inpaint": handle_inpaint_watermark,
    "ocr.recognize": handle_ocr_recognize,
    "ocr.parse_formula": handle_parse_formula,
    "pdf.get_info": handle_pdf_get_info,
    "pdf.merge": handle_pdf_merge,
    "pdf.split": handle_pdf_split,
    "pdf.reorganize": handle_pdf_reorganize,
    "file.batch_rename": handle_file_batch_rename,
    "file.undo_rename": handle_file_undo_rename,
}


def main():
    ready_msg = json.dumps({"jsonrpc": "2.0", "event": "ready", "version": "0.1.0"}, ensure_ascii=False)
    sys.stdout.write(ready_msg + "\n")
    sys.stdout.flush()

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

        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
