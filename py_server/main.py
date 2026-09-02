"""
工具箱 Python 核心服务

本地轻量 HTTP 微服务，为 Electron 桌面应用提供图片处理、文档转换等核心算法能力。
服务仅绑定在 127.0.0.1 本地回环，不对外暴露。
"""

import io
import base64
import traceback

import cv2
import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from services.watermark_service import (
    remove_light_watermark,
    inpaint_with_mask,
    combined_remove,
)

app = FastAPI(title="工具箱核心服务", version="0.1.0")

# 允许来自 Electron 渲染进程的跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_image_from_upload(file_bytes: bytes) -> np.ndarray:
    """将上传的文件字节流解码为 OpenCV BGR 图像"""
    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="无法解析上传的图片文件")
    return img


def _read_image_from_base64(b64_str: str) -> np.ndarray:
    """将 base64 编码字符串解码为 OpenCV BGR 图像"""
    # 去掉可能的 data:image/xxx;base64, 前缀
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    img_bytes = base64.b64decode(b64_str)
    return _read_image_from_upload(img_bytes)


def _encode_image_to_png_bytes(img: np.ndarray) -> bytes:
    """将 OpenCV 图像编码为 PNG 字节流"""
    success, buffer = cv2.imencode(".png", img)
    if not success:
        raise HTTPException(status_code=500, detail="图片编码失败")
    return buffer.tobytes()


@app.get("/api/health")
async def health_check():
    """健康检查接口，供 Electron 主进程探测服务是否就绪"""
    return {"status": "ok", "service": "toolbox-py-server", "version": "0.1.0"}


@app.post("/api/watermark/remove-tile")
async def remove_tile_watermark(
    image: UploadFile = File(..., description="需要去水印的图片文件"),
    threshold: int = Form(200, description="灰度阈值 (0-255)，越小越激进"),
    contrast: float = Form(1.5, description="对比度增强倍数"),
    denoise: bool = Form(True, description="是否降噪平滑"),
    mode: str = Form("binary", description="处理模式: binary / adaptive / color_filter"),
):
    """
    去除试卷/课件平铺浅色文字水印

    适用场景：下载的试卷、教辅课件上大面积斜向重复的浅灰/浅蓝色文字水印。
    """
    try:
        file_bytes = await image.read()
        img = _read_image_from_upload(file_bytes)
        result = remove_light_watermark(img, threshold, contrast, denoise, mode)
        png_bytes = _encode_image_to_png_bytes(result)
        return Response(content=png_bytes, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"去水印处理失败: {str(e)}")


@app.post("/api/watermark/inpaint")
async def inpaint_watermark(
    image: UploadFile = File(..., description="原始图片文件"),
    mask: UploadFile = File(..., description="掩膜图片 (白色=需修补区域)"),
    radius: int = Form(5, description="修补半径 (1-20)"),
    method: str = Form("telea", description="修补算法: telea / ns"),
):
    """
    交互式蒙版修补去水印

    适用场景：用户在前端用画笔涂抹标记的 LOGO、印章、二维码等局部水印区域。
    """
    try:
        img_bytes = await image.read()
        mask_bytes = await mask.read()

        img = _read_image_from_upload(img_bytes)
        mask_img = _read_image_from_upload(mask_bytes)

        result = inpaint_with_mask(img, mask_img, radius, method)
        png_bytes = _encode_image_to_png_bytes(result)
        return Response(content=png_bytes, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"修补处理失败: {str(e)}")


@app.post("/api/watermark/combined")
async def combined_watermark_remove(
    image: UploadFile = File(..., description="原始图片文件"),
    mask: UploadFile = File(None, description="可选的涂抹掩膜图片"),
    threshold: int = Form(200),
    contrast: float = Form(1.5),
    denoise: bool = Form(True),
    mode: str = Form("binary"),
    inpaint_radius: int = Form(5),
    inpaint_method: str = Form("telea"),
):
    """
    组合去水印：先全局去浅色平铺水印 → 再局部蒙版修补

    两步串联，一次请求同时清除两类水印。
    """
    try:
        img_bytes = await image.read()
        img = _read_image_from_upload(img_bytes)

        mask_img = None
        if mask is not None:
            mask_bytes = await mask.read()
            if mask_bytes:
                mask_img = _read_image_from_upload(mask_bytes)

        result = combined_remove(
            img, mask_img, threshold, contrast, denoise, mode,
            inpaint_radius, inpaint_method,
        )
        png_bytes = _encode_image_to_png_bytes(result)
        return Response(content=png_bytes, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"组合去水印失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=18520, log_level="info")
