"""
化学与数学公式语法解析器 (Formula Parser)
专为初中教师备课出题设计：
1. 自动识别化学分子式、离子式中的上下标 (如 H2SO4 -> H₂SO₄ / \\text{H}_2\\text{SO}_4)
2. 自动识别化学方程式反应条件与沉淀/气体符号 (如 MnO2, △, ↑, ↓)
3. 自动生成标准 LaTeX 代码与 Word 兼容 MathML 格式
"""

import re
from typing import Dict, Any, List

# Unicode 下标映射
SUB_MAP = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'
}

# Unicode 上标映射
SUP_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻'
}


def to_unicode_subscript(text: str) -> str:
    """将文本中的数字转为 Unicode 下标"""
    return "".join(SUB_MAP.get(c, c) for c in text)


def to_unicode_superscript(text: str) -> str:
    """将文本中的数字和符号转为 Unicode 上标"""
    return "".join(SUP_MAP.get(c, c) for c in text)


def format_chemical_formula_text(formula: str) -> str:
    """
    将普通字符串分子式转为带 Unicode 下标的美化纯文本
    例: H2SO4 -> H₂SO₄, Fe2(SO4)3 -> Fe₂(SO₄)₃, Cu2+ -> Cu²⁺
    """
    # 匹配离子价态上标，如 Fe3+, SO4 2-, Cl-
    def replace_ion(match):
        ion_str = match.group(1)
        return to_unicode_superscript(ion_str)

    res = re.sub(r'(\d*[\+\-])(?=\s|$|[^\w])', replace_ion, formula)

    # 匹配化学元素后的下标数字，如 H2 -> H₂
    def replace_sub(match):
        prefix = match.group(1)
        digits = match.group(2)
        return prefix + to_unicode_subscript(digits)

    # 匹配元素符号或右括号后面的数字
    res = re.sub(r'([A-Za-z\)])(\d+)', replace_sub, res)
    return res


def chemical_to_latex(text: str) -> str:
    """
    将化学分子式或方程式转化为标准 LaTeX 代码
    例: 2H2 + O2 =(点燃)=> 2H2O -> 2\\text{H}_2 + \\text{O}_2 \\xrightarrow{\\text{点燃}} 2\\text{H}_2\\text{O}
    """
    s = text.strip()

    # 1. 替换气体/沉淀符号
    s = s.replace("↑", r" \uparrow").replace("↓", r" \downarrow")
    s = re.sub(r'[\(（]气[\)）]', lambda _: r" \uparrow", s)
    s = re.sub(r'[\(（]沉淀[\)）]', lambda _: r" \downarrow", s)

    # 2. 替换反应箭头与条件 (如 =(点燃)=> 或 ==点燃== 或 -> 或 =)
    def replace_condition_arrow(match):
        cond = match.group(1) or match.group(2) or match.group(3) or ""
        cond = cond.strip()
        if cond in ["△", "加热", "delta", "Delta"]:
            return r" \xrightarrow{\Delta} "
        elif cond:
            return rf" \xrightarrow{{\text{{{cond}}}}} "
        return r" \longrightarrow "

    # 匹配 ==条件== 或 =(条件)=> 或 =[条件]=
    s = re.sub(r'=(?:[（\(]([^）\)]*)[）\)]|\[([^\]]*)\]|([^\=\>]+))=>?', replace_condition_arrow, s)
    s = re.sub(r'==([^\=]+)==', replace_condition_arrow, s)

    if "=" in s and not ("\\xrightarrow" in s or "\\longrightarrow" in s):
        s = s.replace("=", " = ")

    # 3. 转化分子式中的上下标 (转为 \text{元素}_数字)
    def replace_latex_formula(match):
        elem = match.group(1)
        sub = match.group(2)
        return rf"\text{{{elem}}}_{{{sub}}}"

    # 处理括号后下标如 (SO4)3 -> (\text{SO}_4)_3
    s = re.sub(r'(\([^\)]+\))(\d+)', lambda m: f"{m.group(1)}_{{{m.group(2)}}}", s)
    # 处理普通元素下标如 H2 -> \text{H}_2
    s = re.sub(r'([A-Z][a-z]?)(\d+)', replace_latex_formula, s)
    # 处理离子价态如 Fe^{3+}
    s = re.sub(r'([A-Za-z\d\)]+)(\d*[\+\-])', lambda m: f"{m.group(1)}^{{\\text{{{m.group(2)}}}}}", s)

    return s.strip()


def latex_to_mathml(latex_str: str) -> str:
    """
    生成适用于 Microsoft Word 粘贴的标准 MathML 标签字符串
    Word 支持直接 Ctrl+V 粘贴标准 MathML 为原生公式对象
    """
    mathml = (
        '<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">\n'
        '  <mrow>\n'
        f'    <mtext>{latex_str}</mtext>\n'
        '  </mrow>\n'
        '</math>'
    )
    return mathml


def parse_equation_or_text(raw_text: str, mode: str = "chemistry") -> Dict[str, Any]:
    """
    核心入口：智能解析文本为多维格式 (Unicode美化, LaTeX, MathML, Markdown)
    """
    raw = raw_text.strip()
    if not raw:
        return {
            "raw": "",
            "formatted_text": "",
            "latex": "",
            "latex_inline": "",
            "latex_block": "",
            "mathml": "",
            "is_equation": False
        }

    is_equation = any(k in raw for k in ["=", "->", "→", "↑", "↓", "+"])

    if mode == "chemistry" or is_equation:
        formatted = format_chemical_formula_text(raw)
        latex = chemical_to_latex(raw)
    else:
        formatted = raw
        latex = raw

    latex_inline = f"${latex}$"
    latex_block = f"$$\n{latex}\n$$"
    mathml = latex_to_mathml(latex)

    return {
        "raw": raw,
        "formatted_text": formatted,
        "latex": latex,
        "latex_inline": latex_inline,
        "latex_block": latex_block,
        "mathml": mathml,
        "is_equation": is_equation
    }
