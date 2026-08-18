#!/usr/bin/env python3
"""生成示例财报 PDF（虚构公司"星海智能"，数据自洽，供工作流测试用）

用法：
    python generate_sample_report.py
生成 examples/sample-report.pdf。注意：本脚本需要 reportlab（仅测试资产用，
不属于模板运行依赖）。

数据设计说明：故意埋入风险信号，用于验证 LLM 分析能力——
1. 经营现金流(0.87亿) 明显低于净利润(1.32亿)，存在背离
2. 应收账款增速(42.1%) 显著高于营收增速(18.6%)
3. 商誉 3.2 亿元，占总资产约 7%
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

OUT = Path(__file__).resolve().parent / "sample-report.pdf"
W, H = A4
MARGIN = 60


def main() -> None:
    c = canvas.Canvas(str(OUT), pagesize=A4)
    y = H - 70

    def title(t: str) -> None:
        nonlocal y
        c.setFont("STSong-Light", 16)
        c.drawString(MARGIN, y, t)
        y -= 32

    def section(t: str) -> None:
        nonlocal y
        c.setFont("STSong-Light", 13)
        c.drawString(MARGIN, y, t)
        y -= 24

    def para(t: str) -> None:
        nonlocal y
        c.setFont("STSong-Light", 11)
        for line in t.split("\n"):
            c.drawString(MARGIN, y, line)
            y -= 17
            if y < 80:
                c.showPage()
                y = H - 70

    title("星海智能科技股份有限公司")
    title("2025 年年度报告（节选）")
    y -= 10

    section("一、主要会计数据")
    para("营业收入：12.58 亿元，同比增长 18.6%；"
         "归属于上市公司股东的净利润：1.32 亿元，同比增长 5.2%；"
         "扣除非经常性损益的净利润：1.05 亿元；"
         "毛利率：34.2%，较上年同期下降 2.1 个百分点；"
         "加权平均净资产收益率（ROE）：11.8%；"
         "经营活动产生的现金流量净额：0.87 亿元，同比下降 22.3%。")

    section("二、资产负债表主要数据（截至 2025 年 12 月 31 日）")
    para("总资产：45.6 亿元；总负债：26.6 亿元，资产负债率 58.3%；"
         "应收账款：8.9 亿元，同比增长 42.1%；"
         "存货：5.6 亿元，同比增长 25.4%；"
         "商誉：3.2 亿元，占总资产比例约 7%；"
         "货币资金：4.1 亿元。")

    section("三、现金流量情况")
    para("经营活动产生的现金流量净额：0.87 亿元；"
         "投资活动产生的现金流量净额：-2.4 亿元；"
         "筹资活动产生的现金流量净额：1.9 亿元。"
         "公司经营现金流净额连续两年低于净利润。")

    section("四、风险提示（节选）")
    para("1. 应收账款规模增长较快，若下游客户回款不及预期，可能产生坏账风险；"
         "2. 商誉账面价值较高，若被收购资产经营业绩不达预期，存在减值风险；"
         "3. 毛利率呈下降趋势，原材料价格波动可能进一步压缩利润空间；"
         "4. 经营活动现金流与净利润存在差异，需关注盈利质量。")

    c.save()
    print(f"已生成示例财报：{OUT}")


if __name__ == "__main__":
    main()
