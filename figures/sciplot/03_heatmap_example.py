"""
热力图 / 混淆矩阵示例
"""
import numpy as np
import sciplot as sp

# 混淆矩阵
cm = np.array([[85, 3, 2],
               [5, 78, 7],
               [2, 4, 94]])

class_names = ["类别A", "类别B", "类别C"]
sp.confusion_matrix(cm, class_names, title="分类混淆矩阵")
sp.savefig("heatmap_confusion")

# 归一化混淆矩阵
sp.confusion_matrix(cm, class_names,
                    title="归一化混淆矩阵", normalize=True)
sp.savefig("heatmap_confusion_norm")

# 相关性热力图 (上三角掩码)
np.random.seed(42)
n_vars = 6
corr = np.zeros((n_vars, n_vars))
for i in range(n_vars):
    for j in range(n_vars):
        corr[i, j] = np.tanh((np.random.randn() * 0.3) + 0.5 * (i == j))

var_labels = ["特征1", "特征2", "特征3", "特征4", "特征5", "特征6"]
sp.heatmap(
    corr,
    xticklabels=var_labels,
    yticklabels=var_labels,
    title="特征相关性热力图",
    cmap="RdBu_r",
    vmin=-1, vmax=1,
    mask_upper=True,
)
sp.savefig("heatmap_correlation")
