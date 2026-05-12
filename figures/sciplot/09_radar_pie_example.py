"""
雷达图 + 饼图示例：多维对比
"""
import sciplot as sp

# 雷达图：多维能力对比
categories = ["准确率", "召回率", "F1分数", "推理速度", "内存占用", "可扩展性"]
sp.radar(
    categories=categories,
    values=[
        [90, 75, 85, 70, 60, 80],
        [85, 70, 80, 90, 85, 65],
        [70, 85, 75, 60, 50, 75],
    ],
    labels=["本方案", "对比方案A", "对比方案B"],
    title="多维度性能对比雷达图",
)
sp.savefig("radar_comparison")

# 饼图：数据集构成
sp.pie(
    values=[45, 25, 15, 10, 5],
    labels=["训练集", "验证集", "测试集A", "测试集B", "测试集C"],
    title="数据集划分比例",
    autopct="{:.1f}%",
)
sp.savefig("pie_dataset")
