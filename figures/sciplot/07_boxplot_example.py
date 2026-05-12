"""
箱线图 + 直方图示例：数据分布分析
"""
import numpy as np
import sciplot as sp

# 多组箱线图
np.random.seed(42)
data = [
    np.random.normal(75, 10, 100),
    np.random.normal(82, 12, 100),
    np.random.normal(68, 8, 100),
    np.random.normal(90, 15, 100),
]

sp.boxplot(
    data,
    labels=["方法A", "方法B", "方法C", "方法D"],
    title="各方法得分分布",
    ylabel="得分",
)
sp.savefig("boxplot_scores")

# 直方图
sp.histogram(
    data[0],
    bins=15,
    title="方法A 得分分布直方图",
    xlabel="得分",
    ylabel="频数",
)
sp.savefig("histogram_single")

# 多组重叠直方图
sp.histogram(
    data[:3],
    labels=["方法A", "方法B", "方法C"],
    bins=12,
    alpha=0.5,
    title="多方法得分分布对比",
    xlabel="得分",
    ylabel="频数",
)
sp.savefig("histogram_multi")
