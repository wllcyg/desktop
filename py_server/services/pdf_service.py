"""
PDF 核心处理服务 (基于 PyMuPDF / fitz)
包含：信息与缩略图提取、多文件合并、规则拆分、页面可视化重排与旋转
"""

import os
import re
import pymupdf as fitz  # PyMuPDF
import base64
from typing import List, Dict, Any, Optional, Tuple


def _parse_page_range_string(range_str: str, max_pages: int) -> List[int]:
    """
    解析页码字符串（1-based），返回 0-based 页面索引列表
    例如: "1-3, 5, 8-10" -> [0, 1, 2, 4, 7, 8, 9]
    若为空、"全部"、"all" 等则返回全选
    """
    if not range_str or not range_str.strip():
        return list(range(max_pages))

    s = range_str.strip().lower()
    if s in ["全部", "all", "全量", "全部页面", "all pages", "*"]:
        return list(range(max_pages))

    pages = set()
    parts = range_str.replace("，", ",").split(",")

    has_valid_part = False
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) == 2:
                try:
                    start = int(bounds[0].strip())
                    end = int(bounds[1].strip())
                    if start <= end:
                        for p in range(start, end + 1):
                            if 1 <= p <= max_pages:
                                pages.add(p - 1)
                        has_valid_part = True
                except ValueError:
                    pass
        else:
            try:
                p = int(part)
                if 1 <= p <= max_pages:
                    pages.add(p - 1)
                has_valid_part = True
            except ValueError:
                pass

    if not has_valid_part:
        return list(range(max_pages))

    return sorted(list(pages))


def get_pdf_info(pdf_path: str, include_thumbnails: bool = False, max_thumb_size: int = 240) -> Dict[str, Any]:
    """
    获取 PDF 基础元信息，可选生成每一页的缩略图 (Base64)
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"未找到指定的 PDF 文件: {pdf_path}")

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    # 提取大纲目录
    toc = doc.get_toc()  # [[lvl, title, page_no], ...]
    toc_list = []
    for item in toc:
        toc_list.append({
            "level": item[0],
            "title": item[1],
            "page": item[2]
        })

    # 文件大小
    file_size = os.path.getsize(pdf_path)

    pages_info = []
    for idx in range(total_pages):
        page = doc[idx]
        rect = page.rect
        page_dict = {
            "page_index": idx,
            "page_number": idx + 1,
            "width": round(rect.width, 2),
            "height": round(rect.height, 2),
            "rotation": page.rotation
        }

        if include_thumbnails:
            # 计算缩放比，生成轻量缩略图
            scale = max_thumb_size / max(rect.width, rect.height, 1)
            matrix = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img_bytes = pix.tobytes("jpeg", jpg_quality=80)
            b64 = "data:image/jpeg;base64," + base64.b64encode(img_bytes).decode("utf-8")
            page_dict["thumbnail"] = b64

        pages_info.append(page_dict)

    doc.close()

    return {
        "file_name": os.path.basename(pdf_path),
        "file_path": pdf_path,
        "file_size": file_size,
        "total_pages": total_pages,
        "has_toc": len(toc_list) > 0,
        "toc": toc_list,
        "pages": pages_info
    }


def merge_pdfs(
    file_configs: List[Dict[str, Any]],
    output_path: str,
    auto_generate_toc: bool = True,
    compress: bool = True
) -> Dict[str, Any]:
    """
    合并多个 PDF 文件
    file_configs 结构:
    [
        {
            "path": "D:/a.pdf",
            "title": "章节名称 / 文件名",
            "page_range": "1-5, 8"  # 可选，为空则取全部
        }, ...
    ]
    """
    if not file_configs:
        raise ValueError("请至少提供一个需要合并的 PDF 文件")

    merged_doc = fitz.open()
    toc = []
    current_page_number = 1

    for item in file_configs:
        path = item.get("path")
        if not path or not os.path.isfile(path):
            raise FileNotFoundError(f"文件不存在: {path}")

        src_doc = fitz.open(path)
        total_p = len(src_doc)
        title = item.get("title") or os.path.splitext(os.path.basename(path))[0]

        range_str = item.get("page_range", "")
        selected_pages = _parse_page_range_string(range_str, total_p)

        if not selected_pages:
            src_doc.close()
            continue

        if auto_generate_toc:
            toc.append([1, title, current_page_number])

        for p_idx in selected_pages:
            merged_doc.insert_pdf(src_doc, from_page=p_idx, to_page=p_idx)
            current_page_number += 1

        src_doc.close()

    if len(merged_doc) == 0:
        merged_doc.close()
        raise ValueError("合并后的文档页数为空，请检查页码选择范围")

    if auto_generate_toc and toc:
        merged_doc.set_toc(toc)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # garbage=3: 清理未使用/冗余的对象，deflate=True 压缩流
    merged_doc.save(
        output_path,
        garbage=3 if compress else 0,
        deflate=compress
    )
    total_pages = len(merged_doc)
    merged_doc.close()

    return {
        "success": True,
        "output_path": output_path,
        "total_pages": total_pages,
        "file_size": os.path.getsize(output_path)
    }


def split_pdf(
    pdf_path: str,
    split_mode: str,
    params: Dict[str, Any],
    output_dir: str
) -> Dict[str, Any]:
    """
    PDF 规则拆分
    split_mode:
      - 'by_chunk': 按固定页数拆分 (params: { "chunk_size": 1 })
      - 'by_range': 按页码区间拆分 (params: { "range_str": "1-3, 5, 8-10", "merge_result": False })
      - 'by_odd_even': 奇偶页拆分
      - 'by_toc': 按大纲一级书签章节拆分
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"未找到指定的 PDF 文件: {pdf_path}")

    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    src_doc = fitz.open(pdf_path)
    total_pages = len(src_doc)
    
    created_files = []

    if total_pages == 0:
        src_doc.close()
        raise ValueError("PDF 文档为空")

    if split_mode == "by_chunk":
        chunk_size = int(params.get("chunk_size", 1))
        if chunk_size < 1:
            chunk_size = 1

        for i in range(0, total_pages, chunk_size):
            start = i
            end = min(i + chunk_size - 1, total_pages - 1)
            sub_doc = fitz.open()
            sub_doc.insert_pdf(src_doc, from_page=start, to_page=end)

            if chunk_size == 1:
                filename = f"{base_name}_第{start+1}页.pdf"
            else:
                filename = f"{base_name}_第{start+1}-{end+1}页.pdf"
            
            out_file = os.path.join(output_dir, filename)
            sub_doc.save(out_file, garbage=3, deflate=True)
            sub_doc.close()
            created_files.append({
                "path": out_file,
                "name": filename,
                "pages": f"{start+1}-{end+1}" if start != end else f"{start+1}"
            })

    elif split_mode == "by_range":
        range_str = params.get("range_str", "")
        merge_result = bool(params.get("merge_result", False))
        
        parts = [p.strip() for p in range_str.replace("，", ",").split(",") if p.strip()]
        if not parts:
            src_doc.close()
            raise ValueError("请提供合法的页码范围，例如: 1-3, 5, 8-10")

        if merge_result:
            # 合并提取为一个新文件
            selected = _parse_page_range_string(range_str, total_pages)
            if not selected:
                src_doc.close()
                raise ValueError("指定的页码范围在文档中不存在")
            
            sub_doc = fitz.open()
            for pno in selected:
                sub_doc.insert_pdf(src_doc, from_page=pno, to_page=pno)
            
            filename = f"{base_name}_提取页码.pdf"
            out_file = os.path.join(output_dir, filename)
            sub_doc.save(out_file, garbage=3, deflate=True)
            sub_doc.close()
            created_files.append({
                "path": out_file,
                "name": filename,
                "pages": f"共 {len(selected)} 页"
            })
        else:
            # 每一个区间/单页拆为一个独立文件
            for part in parts:
                selected = _parse_page_range_string(part, total_pages)
                if not selected:
                    continue
                sub_doc = fitz.open()
                for pno in selected:
                    sub_doc.insert_pdf(src_doc, from_page=pno, to_page=pno)
                
                filename = f"{base_name}_第{part}页.pdf"
                out_file = os.path.join(output_dir, filename)
                sub_doc.save(out_file, garbage=3, deflate=True)
                sub_doc.close()
                created_files.append({
                    "path": out_file,
                    "name": filename,
                    "pages": part
                })

    elif split_mode == "by_odd_even":
        # 奇数页 (1, 3, 5...)
        odd_pages = [p for p in range(total_pages) if (p + 1) % 2 == 1]
        # 偶数页 (2, 4, 6...)
        even_pages = [p for p in range(total_pages) if (p + 1) % 2 == 0]

        if odd_pages:
            odd_doc = fitz.open()
            for pno in odd_pages:
                odd_doc.insert_pdf(src_doc, from_page=pno, to_page=pno)
            odd_name = f"{base_name}_奇数页.pdf"
            odd_path = os.path.join(output_dir, odd_name)
            odd_doc.save(odd_path, garbage=3, deflate=True)
            odd_doc.close()
            created_files.append({"path": odd_path, "name": odd_name, "pages": f"共 {len(odd_pages)} 页"})

        if even_pages:
            even_doc = fitz.open()
            for pno in even_pages:
                even_doc.insert_pdf(src_doc, from_page=pno, to_page=pno)
            even_name = f"{base_name}_偶数页.pdf"
            even_path = os.path.join(output_dir, even_name)
            even_doc.save(even_path, garbage=3, deflate=True)
            even_doc.close()
            created_files.append({"path": even_path, "name": even_name, "pages": f"共 {len(even_pages)} 页"})

    elif split_mode == "by_toc":
        toc = src_doc.get_toc()
        level1_toc = [item for item in toc if item[0] == 1]
        if not level1_toc:
            src_doc.close()
            raise ValueError("该 PDF 没有检测到一级大纲目录书签，无法按大纲拆分")

        for idx, item in enumerate(level1_toc):
            _, title, start_page = item
            start_idx = max(0, start_page - 1)
            if idx + 1 < len(level1_toc):
                end_idx = min(total_pages - 1, level1_toc[idx + 1][2] - 2)
            else:
                end_idx = total_pages - 1

            if start_idx > end_idx:
                continue

            sub_doc = fitz.open()
            sub_doc.insert_pdf(src_doc, from_page=start_idx, to_page=end_idx)
            # 过滤非法文件名字符
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', title).strip()
            filename = f"{idx + 1:02d}_{safe_title}.pdf"
            out_file = os.path.join(output_dir, filename)
            sub_doc.save(out_file, garbage=3, deflate=True)
            sub_doc.close()
            created_files.append({
                "path": out_file,
                "name": filename,
                "pages": f"第{start_idx+1}-{end_idx+1}页 ({title})"
            })

    else:
        src_doc.close()
        raise ValueError(f"不支持的拆分模式: {split_mode}")

    src_doc.close()

    return {
        "success": True,
        "output_dir": output_dir,
        "total_files": len(created_files),
        "files": created_files
    }


def reorganize_pdf(
    pdf_path: str,
    page_configs: List[Dict[str, Any]],
    output_path: str
) -> Dict[str, Any]:
    """
    页面可视化重组与旋转
    page_configs: [
        {"page_index": 0, "rotation": 90},
        {"page_index": 2, "rotation": 0}, ...
    ]
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"未找到指定的 PDF 文件: {pdf_path}")

    if not page_configs:
        raise ValueError("重排后的页面列表不能为空")

    src_doc = fitz.open(pdf_path)
    total_pages = len(src_doc)
    new_doc = fitz.open()

    for item in page_configs:
        p_idx = int(item["page_index"])
        rotation_delta = int(item.get("rotation", 0))

        if 0 <= p_idx < total_pages:
            # 插入单页
            new_doc.insert_pdf(src_doc, from_page=p_idx, to_page=p_idx)
            new_page = new_doc[-1]
            if rotation_delta != 0:
                # 累加旋转角度 (0, 90, 180, 270)
                current_rot = new_page.rotation
                new_page.set_rotation((current_rot + rotation_delta) % 360)

    src_doc.close()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    new_doc.save(output_path, garbage=3, deflate=True)
    total_new_pages = len(new_doc)
    new_doc.close()

    return {
        "success": True,
        "output_path": output_path,
        "total_pages": total_new_pages,
        "file_size": os.path.getsize(output_path)
    }
