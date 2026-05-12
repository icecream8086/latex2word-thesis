"""
散点图示例：数据分布与回归趋势
"""
import numpy as np
import sciplot as sp

# 带趋势线的散点图
np.random.seed(42)
x = np.random.rand(50) * 10
y = 2.5 * x + 3 + np.random.randn(50) * 3

sp.scatter(
    x, y,
    title="数据分布与线性拟合",
    xlabel="特征值 X",
    ylabel="目标值 Y",
    fit_line=True,
    fit_label="线性拟合: y = 2.5x + 3",
    alpha=0.6,
)
sp.savefig("scatter_fit")

# 分类散点图
clusters = []
centers = [(3, 3), (7, 7), (3, 7)]
labels_list = ["Cluster A", "Cluster B", "Cluster C"]
all_x, all_y, all_c = [], [], []
for i, (cx, cy) in enumerate(centers):
    pts = 30
    all_x.extend(np.random.randn(pts) * 0.8 + cx)
    all_y.extend(np.random.randn(pts) * 0.8 + cy)
    all_c.extend([i] * pts)

fig, ax = sp.scatter(
    all_x, all_y,
    c=all_c,
    title="聚类结果可视化",
    xlabel="PC1",
    ylabel="PC2",
    alpha=0.7,
    colorbar=False,
)
sp.savefig("scatter_clusters")
