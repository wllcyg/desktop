"""
下载 LaMa (Large Mask Inpainting) ONNX 模型脚本
将模型保存至 resources/models/lama.onnx
"""

import os
import sys
import urllib.request

MODELS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "resources", "models")
)
MODEL_PATH = os.path.join(MODELS_DIR, "lama.onnx")

# 精确有效的国内与官方 CDN 下载源
MODEL_URLS = [
    # 国内高速 hf-mirror (Carve/LaMa-ONNX)
    "https://hf-mirror.com/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx",
    # GitHub Sanster models release
    "https://github.com/Sanster/models/releases/download/add_big_lama/big-lama.onnx",
    # Hugging Face 官方源
    "https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx",
]


def download_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        percent = min(100.0, (downloaded / total_size) * 100)
        mb_down = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        sys.stdout.write(f"\r[下载中] {percent:.1f}% ({mb_down:.1f}MB / {mb_total:.1f}MB)")
        sys.stdout.flush()


def download_lama():
    os.makedirs(MODELS_DIR, exist_ok=True)

    if os.path.isfile(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 50 * 1024 * 1024:
        print(f"[LaMa] 模型已存在: {MODEL_PATH} ({os.path.getsize(MODEL_PATH) / 1024 / 1024:.1f} MB)")
        return True

    print(f"[LaMa] 开始下载模型到: {MODEL_PATH}")
    # 添加浏览器标准 User-Agent，避免某些 CDN 拦截 Python 脚本
    opener = urllib.request.build_opener()
    opener.addheaders = [
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    ]
    urllib.request.install_opener(opener)

    for url in MODEL_URLS:
        try:
            print(f"[LaMa] 正在从高速源下载: {url}")
            urllib.request.urlretrieve(url, MODEL_PATH, reporthook=download_progress)
            print("\n[LaMa] 下载完成！模型已就绪 ✓")
            return True
        except Exception as e:
            print(f"\n[LaMa] 当前下载源失败 ({e})，正在自动切换下一镜像源...")
            if os.path.exists(MODEL_PATH):
                try:
                    os.remove(MODEL_PATH)
                except Exception:
                    pass

    print("[LaMa] 所有下载源均连接失败，请检查网络设置。")
    return False


if __name__ == "__main__":
    download_lama()
