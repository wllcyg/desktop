"""
生成初中化学教师常用测试水印图片脚本
包含 3 类真实教学场景图片：
1. paper_tiled_watermark.png - 试卷背景斜向平铺浅灰/浅蓝版权水印
2. paper_corner_logo.png - 右下角彩色机构 LOGO + 红色印章水印
3. paper_handwritten_mark.png - 试卷错题红笔打叉与批改红痕
"""

import os
from PIL import Image, ImageDraw, ImageFont


def get_chinese_font(size=20):
    font_paths = [
        r"C:\Windows\Fonts\msyh.ttc",   # 微软雅黑
        r"C:\Windows\Fonts\simhei.ttf", # 黑体
        r"C:\Windows\Fonts\simsun.ttc", # 宋体
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def create_sample_1_tiled():
    """生成：全屏斜向平铺浅色水印试卷"""
    w, h = 900, 1100
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    font_title = get_chinese_font(26)
    font_body = get_chinese_font(18)
    font_watermark = get_chinese_font(28)

    # 1. 试卷题目内容 (深黑色清晰正文)
    draw.text((260, 40), "2026年九年级化学期中测试卷", fill=(20, 20, 20), font=font_title)
    draw.line((60, 90, 840, 90), fill=(80, 80, 80), width=2)

    content = [
        "一、选择题（本题共 5 小题，每小题 2 分，共 10 分）",
        "1. 下列变化中，属于化学变化的是（    ）",
        "   A. 冰雪融化       B. 钢铁生锈       C. 矿石粉碎       D. 酒精挥发",
        "",
        "2. 下列化学方程式书写完全正确的是（    ）",
        "   A. C + O₂ === CO₂ ↑                 B. 2KMnO₄  △===  K₂MnO₄ + MnO₂ + O₂↑",
        "   C. 4P + 5O₂ === 2P₂O₅              D. Fe + CuSO₄ === FeSO₄ + Cu↓",
        "",
        "二、填空与简答题",
        "3. 根据如图所示的实验装置，回答有关问题：",
        "   (1) 写出标号仪器的名称：a. 试管，b. 铁架台；",
        "   (2) 实验室用过氧化氢溶液和二氧化锰制取氧气，反应的化学方程式为：",
        "       2H₂O₂  MnO₂===  2H₂O + O₂↑，",
        "       其中二氧化锰起 ________ 作用；",
        "   (3) 若用高锰酸钾制取氧气，应在试管口塞一团棉花，防止 ______________。"
    ]

    y = 120
    for line in content:
        draw.text((80, y), line, fill=(30, 30, 30), font=font_body)
        y += 34

    # 2. 绘制斜向平铺浅灰色/浅蓝色文字水印 (满屏重复)
    watermark_layer = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    watermark_draw = ImageDraw.Draw(watermark_layer)

    text = "学科网内部资料 严禁外传 仅供备课参考"
    for row in range(-2, 10):
        for col in range(-1, 5):
            pos_x = col * 320 + (row % 2) * 80
            pos_y = row * 140
            # 创建单条旋转水印
            txt_img = Image.new("RGBA", (500, 100), (255, 255, 255, 0))
            d_txt = ImageDraw.Draw(txt_img)
            d_txt.text((20, 20), text, fill=(185, 200, 220, 130), font=font_watermark)
            rotated_txt = txt_img.rotate(25, expand=True)
            watermark_layer.paste(rotated_txt, (pos_x, pos_y), rotated_txt)

    img.paste(watermark_layer, (0, 0), watermark_layer)
    return img


def create_sample_2_corner_logo():
    """生成：右下角网站 LOGO + 右上角绝密印章水印"""
    w, h = 900, 1000
    img = Image.new("RGB", (w, h), color=(253, 253, 254))
    draw = ImageDraw.Draw(img)

    font_title = get_chinese_font(24)
    font_body = get_chinese_font(18)
    font_seal = get_chinese_font(16)
    font_logo = get_chinese_font(20)

    # 试卷正文
    draw.text((300, 50), "初中化学方程式专项训练", fill=(15, 23, 42), font=font_title)
    draw.line((60, 95, 840, 95), fill=(100, 116, 139), width=1)

    questions = [
        "1. 碳酸钙与稀盐酸反应：CaCO₃ + 2HCl === CaCl₂ + H₂O + CO₂↑",
        "2. 铁与稀硫酸反应：Fe + H₂SO₄ === FeSO₄ + H₂↑",
        "3. 氢氧化钠与硫酸铜反应：2NaOH + CuSO₄ === Cu(OH)₂↓ + Na₂SO₄",
        "4. 工业炼铁原理：Fe₂O₃ + 3CO  高温===  2Fe + 3CO₂",
        "5. 甲烷在空气中燃烧：CH₄ + 2O₂  点燃===  CO₂ + 2H₂O"
    ]

    y = 140
    for q in questions:
        draw.text((80, y), q, fill=(30, 41, 59), font=font_body)
        y += 60

    # 右上角红色印章 (用于测试局部修补)
    draw.ellipse((700, 30, 830, 90), outline=(220, 38, 38), width=3)
    draw.text((720, 48), "★ 绝密绝密 ★", fill=(220, 38, 38), font=font_seal)

    # 右下角大号彩色 LOGO 水印 (用于测试画笔选区修补)
    draw.rectangle((600, 820, 840, 940), fill=(239, 246, 255), outline=(59, 130, 246), width=2)
    draw.text((620, 840), "菁优中考网 题库专用", fill=(37, 99, 235), font=font_logo)
    draw.text((630, 880), "扫码查看名师解析与视频", fill=(100, 116, 139), font=get_chinese_font(13))

    return img


def create_sample_3_red_marks():
    """生成：学生作业批改红叉、红圈等涂鸦水印"""
    w, h = 900, 900
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    font_title = get_chinese_font(22)
    font_body = get_chinese_font(18)
    font_mark = get_chinese_font(24)

    draw.text((80, 60), "课后作业：写出下列反应的化学方程式", fill=(15, 23, 42), font=font_title)

    draw.text((80, 140), "题目：镁条在空气中燃烧", fill=(51, 65, 85), font=font_body)
    draw.text((80, 190), "学生答案：Mg + O2 === MgO2", fill=(100, 116, 139), font=font_body)

    # 红笔打大叉
    draw.line((180, 175, 420, 230), fill=(225, 29, 72), width=5)
    draw.line((420, 175, 180, 230), fill=(225, 29, 72), width=5)
    draw.text((450, 185), "系数错误! -2分", fill=(225, 29, 72), font=font_mark)

    draw.text((80, 300), "题目：水电解实验", fill=(51, 65, 85), font=font_body)
    draw.text((80, 350), "学生答案：2H2O === 2H2 + O2 (漏了通电条件和气体符号)", fill=(100, 116, 139), font=font_body)
    # 红笔圈注
    draw.ellipse((220, 335, 480, 390), outline=(225, 29, 72), width=4)

    return img


if __name__ == "__main__":
    out_dir = r"D:\self\desktop\test_images"
    os.makedirs(out_dir, exist_ok=True)

    img1 = create_sample_1_tiled()
    path1 = os.path.join(out_dir, "测试1_试卷全屏平铺浅色水印.png")
    img1.save(path1)

    img2 = create_sample_2_corner_logo()
    path2 = os.path.join(out_dir, "测试2_角落LOGO与绝密印章.png")
    img2.save(path2)

    img3 = create_sample_3_red_marks()
    path3 = os.path.join(out_dir, "测试3_错题红笔批改痕迹.png")
    img3.save(path3)

    print(f"3 张复杂水印测试图片已成功生成到: {out_dir}")
