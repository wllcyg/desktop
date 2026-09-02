"""
AI 模型统一中心 (Model Hub)
负责所有 ONNX 本地模型的动态路径解析、按需加载、运行健康检查与性能监控
"""

import os
import sys
import time
import numpy as np

# 支持的模型清单
KNOWN_MODELS = {
    "lama": {
        "filename": "lama.onnx",
        "name": "Big-LaMa 图像修复引擎",
        "category": "inpainting",
    },
    "ocr_det": {
        "filename": "ch_PP-OCRv4_det_infer.onnx",
        "name": "PP-OCRv4 极速文字定位引擎",
        "category": "ocr",
    },
    "docres": {
        "filename": "docres_shadow.onnx",
        "name": "DocRes 文档光影净化引擎",
        "category": "restoration",
    },
}

# 进程全局常驻会话缓存 (即使业务模块热重载，模型会话也永远常驻内存不销毁)
if not hasattr(sys, "_toolbox_model_sessions"):
    sys._toolbox_model_sessions = {}


def get_user_data_models_dir() -> str:
    """获取 Windows / macOS / Linux 平台通用的用户数据目录下的 models 文件夹"""
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA", "")
        if app_data:
            return os.path.join(app_data, "toolbox", "models")
    elif sys.platform == "darwin":
        home = os.path.expanduser("~")
        return os.path.join(home, "Library", "Application Support", "toolbox", "models")
    else:
        home = os.path.expanduser("~")
        return os.path.join(home, ".config", "toolbox", "models")
    return ""


def get_model_path(model_id: str) -> str:
    """按优先级动态定位模型文件的物理路径"""
    info = KNOWN_MODELS.get(model_id)
    if not info:
        return ""

    filenames = [info["filename"]]
    if model_id == "lama":
        filenames.extend(["lama_fp32.onnx", "big-lama.onnx", "big_lama.onnx"])
    elif model_id == "docres":
        filenames.extend(["docshadow_sd7k.onnx", "docres.onnx"])
    elif model_id == "ocr_det":
        filenames.extend(["detection.onnx", "ppocr_det.onnx"])

    candidates = []
    user_models_dir = get_user_data_models_dir()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

    for fn in filenames:
        # 1. 优先搜索用户的 AppData / UserData 目录
        if user_models_dir:
            candidates.append(os.path.join(user_models_dir, fn))

        # 2. 搜索开发环境下的 resources/models 目录
        candidates.append(os.path.join(project_root, "resources", "models", fn))

        # 3. 搜索 PyInstaller 打包环境
        if getattr(sys, "frozen", False):
            candidates.append(os.path.join(sys._MEIPASS, "models", fn))
            if hasattr(sys, "resourcesPath"):
                candidates.append(os.path.join(sys.resourcesPath, "models", fn))

    for path in candidates:
        if os.path.isfile(path) and os.path.getsize(path) > 1024:
            return path

    return ""


def is_model_installed(model_id: str) -> bool:
    """判断某个模型是否已在本地安装"""
    return bool(get_model_path(model_id))


def get_or_create_session(model_id: str):
    """惰性获取或动态初始化 ONNX Runtime Session (全局单例常驻)"""
    sessions = sys._toolbox_model_sessions
    if model_id in sessions and sessions[model_id] is not None:
        return sessions[model_id]

    model_path = get_model_path(model_id)
    if not model_path:
        return None

    try:
        import onnxruntime as ort

        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = max(2, os.cpu_count() or 4)
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        session = ort.InferenceSession(
            model_path,
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )
        sessions[model_id] = session
        print(f"[ModelHub] 模型 [{model_id}] 常驻会话初始化成功: {model_path}")
        return session
    except Exception as e:
        print(f"[ModelHub] 模型 [{model_id}] 加载失败: {e}", file=sys.stderr)
        return None


def verify_and_start_model(model_id: str) -> dict:
    """
    用户在界面点击“启动/校验”时调用的接口
    若已常驻内存则 0 耗时秒级返回，未载入时安全初始化
    """
    if model_id not in KNOWN_MODELS:
        return {
            "success": False,
            "error": f"未知的模型标识: {model_id}",
            "status": "error",
        }

    # 1. 检查物理文件是否存在
    model_path = get_model_path(model_id)
    if not model_path:
        return {
            "success": False,
            "error": "未检测到模型文件，请先点击下载",
            "status": "not_found",
        }

    file_size_mb = round(os.path.getsize(model_path) / (1024 * 1024), 1)

    # 2. 如果已在内存中常驻就绪，直接秒级返回成功
    sessions = sys._toolbox_model_sessions
    if model_id in sessions and sessions[model_id] is not None:
        return {
            "success": True,
            "status": "ready",
            "model_id": model_id,
            "name": KNOWN_MODELS[model_id]["name"],
            "file_size_mb": file_size_mb,
            "warmup_cost_ms": 0,
            "already_running": True
        }

    # 3. 首次加载初始化 Session
    start_time = time.time()
    try:
        session = get_or_create_session(model_id)
        if session is None:
            raise RuntimeError("ONNX Runtime 初始化失败")

        cost_ms = round((time.time() - start_time) * 1000)
        return {
            "success": True,
            "status": "ready",
            "model_id": model_id,
            "name": KNOWN_MODELS[model_id]["name"],
            "file_size_mb": file_size_mb,
            "warmup_cost_ms": cost_ms,
        }
    except Exception as e:
        print(f"[ModelHub] 启动模型 [{model_id}] 异常: {e}", file=sys.stderr)
        return {
            "success": False,
            "error": f"模型启动失败: {str(e)}",
            "status": "error",
            "model_id": model_id,
        }

        dummy_feed = {}
        for inp in inputs:
            shape = []
            for idx, dim in enumerate(inp.shape):
                if isinstance(dim, int) and dim > 0:
                    shape.append(dim)
                else:
                    if idx == 0:
                        shape.append(1)  # Batch
                    elif idx == 1:
                        # Channel: 若输入名为 mask 或指定单通道则填 1，其余填 3
                        shape.append(1 if "mask" in inp.name.lower() else 3)
                    else:
                        # 空间尺寸 (H, W): 统一提供 512，满足深层卷积网络与反射填充(Reflection Pad)的尺寸要求
                        shape.append(512)

            dtype_map = {
                "tensor(float)": np.float32,
                "tensor(float16)": np.float16,
                "tensor(int64)": np.int64,
                "tensor(int32)": np.int32,
                "tensor(uint8)": np.uint8,
            }
            dtype = dtype_map.get(inp.type, np.float32)
        return {
            "success": True,
            "status": "ready",
            "model_id": model_id,
            "model_path": model_path,
            "file_size_mb": file_size_mb,
            "warmup_cost_ms": cost_ms,
            "message": f"模型常驻就绪 (耗时: {cost_ms}ms)",
        }
    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "model_id": model_id,
            "error": str(e),
            "message": f"模型加载失败: {str(e)}",
        }


def get_all_models_status() -> dict:
    """获取所有模型在 Python 端的全局常驻加载状态"""
    sessions = getattr(sys, "_toolbox_model_sessions", {})
    result = {}
    for mid in KNOWN_MODELS:
        path = get_model_path(mid)
        installed = bool(path)
        is_loaded = mid in sessions and sessions[mid] is not None
        result[mid] = {
            "installed": installed,
            "loaded": is_loaded,
            "path": path,
            "size_mb": round(os.path.getsize(path) / (1024 * 1024), 1) if installed else 0,
        }
    return result
