"""
柱状图示例：不同方法的性能对比
"""
import sciplot as sp

# 单组柱状图
sp.bar(
    categories=["方法A", "方法B", "方法C", "方法D", "方法E"],
    values=[78.5, 85.3, 62.1, 91.7, 74.8],
    title="不同方法在测试集上的准确率对比",
    xlabel="方法",
    ylabel="准确率 (%)",
    show_values=True,
    value_format="{:.1f}",
)
sp.savefig("bar_accuracy")

# 多组柱状图
sp.bar(
    categories=["数据集1", "数据集2", "数据集3"],
    values=[[88.5, 82.3, 90.1], [76.2, 71.8, 79.5]],
    labels=["本方案", "基线方案"],
    title="不同数据集上的性能对比",
    xlabel="数据集",
    ylabel="F1 Score (%)",
    show_values=True,
    value_format="{:.1f}",
)
sp.savefig("bar_grouped")
