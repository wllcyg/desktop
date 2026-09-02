"""
文件批量重命名服务
支持文件占用检测、异常容错隔离与一键撤销回滚
"""

import os
import shutil
from typing import List, Dict, Any


def batch_rename_files(rename_pairs: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    批量重命名文件
    rename_pairs 结构:
    [
        { "id": "1", "old_path": "D:/a.txt", "new_path": "D:/b.txt" },
        ...
    ]
    """
    if not rename_pairs:
        return {"success": True, "results": [], "total": 0, "success_count": 0, "failed_count": 0}

    results = []
    success_count = 0
    failed_count = 0
    rollback_stack = []

    for item in rename_pairs:
        item_id = item.get("id")
        old_path = item.get("old_path")
        new_path = item.get("new_path")

        if not old_path or not new_path:
            results.append({
                "id": item_id,
                "old_path": old_path,
                "new_path": new_path,
                "success": False,
                "error_type": "invalid_path",
                "error_msg": "文件路径无效"
            })
            failed_count += 1
            continue

        # 如果新旧路径完全一致，视作成功且无需移动
        if os.path.abspath(old_path) == os.path.abspath(new_path):
            results.append({
                "id": item_id,
                "old_path": old_path,
                "new_path": new_path,
                "success": True,
                "unchanged": True
            })
            success_count += 1
            continue

        # 检查原文件是否存在
        if not os.path.exists(old_path):
            results.append({
                "id": item_id,
                "old_path": old_path,
                "new_path": new_path,
                "success": False,
                "error_type": "not_found",
                "error_msg": "原文件不存在或已被移除"
            })
            failed_count += 1
            continue

        # 检查目标文件是否已存在（避免覆盖冲突）
        if os.path.exists(new_path) and os.path.abspath(old_path) != os.path.abspath(new_path):
            results.append({
                "id": item_id,
                "old_path": old_path,
                "new_path": new_path,
                "success": False,
                "error_type": "already_exists",
                "error_msg": "目标文件已存在，为防数据覆盖已自动跳过"
            })
            failed_count += 1
            continue

        # 执行重命名与占用异常捕获
        try:
            # 确保目标文件夹存在
            target_dir = os.path.dirname(os.path.abspath(new_path))
            os.makedirs(target_dir, exist_ok=True)

            os.rename(old_path, new_path)

            results.append({
                "id": item_id,
                "old_path": old_path,
                "new_path": new_path,
                "success": True
            })
            success_count += 1
            rollback_stack.append({"old_path": old_path, "new_path": new_path})

        except PermissionError as e:
            # Windows 典型文件独占锁定报错 (WinError 32)
            results.append({
                "id": item_id,
                "old_path": old_path,
                "new_path": new_path,
                "success": False,
                "error_type": "locked",
                "error_msg": "文件正在被其他程序（如 Word/WPS/查看器）占用，请关闭后重试"
            })
            failed_count += 1
        except OSError as e:
            results.append({
                "id": item_id,
                "old_path": old_path,
                "new_path": new_path,
                "success": False,
                "error_type": "os_error",
                "error_msg": f"系统IO错误: {str(e)}"
            })
            failed_count += 1
        except Exception as e:
            results.append({
                "id": item_id,
                "old_path": old_path,
                "new_path": new_path,
                "success": False,
                "error_type": "unknown",
                "error_msg": str(e)
            })
            failed_count += 1

    return {
        "success": failed_count == 0,
        "total": len(rename_pairs),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results,
        "rollback_records": rollback_stack
    }


def undo_rename_files(rollback_records: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    一键撤销重命名 (逆向将 new_path 恢复为 old_path)
    """
    if not rollback_records:
        return {"success": True, "restored_count": 0, "failed_count": 0}

    restored_count = 0
    failed_count = 0
    errors = []

    # 逆序回退
    for record in reversed(rollback_records):
        old_path = record.get("old_path")
        new_path = record.get("new_path")

        if not old_path or not new_path or not os.path.exists(new_path):
            failed_count += 1
            continue

        try:
            os.rename(new_path, old_path)
            restored_count += 1
        except Exception as e:
            failed_count += 1
            errors.append(f"{os.path.basename(new_path)}: {str(e)}")

    return {
        "success": failed_count == 0,
        "restored_count": restored_count,
        "failed_count": failed_count,
        "errors": errors
    }
