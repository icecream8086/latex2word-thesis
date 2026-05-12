"""
流程图示例：带数学标注的实验流程
Mermaid 画不了带数学公式的流程图节点
"""
import sciplot as sp
from sciplot._config import COLORS

sp.flow(
    blocks=[
        {"text": "原始数据",           "xy": (0, 3), "w": 2.5, "h": 0.8, "color": COLORS["blue"]},
        {"text": "预处理",             "xy": (0, 2), "w": 2.5, "h": 0.8, "color": COLORS["teal"]},
        {"text": "特征提取\n(PCA)",    "xy": (0, 1), "w": 2.5, "h": 0.8, "color": COLORS["purple"]},
        {"text": "模型训练\nL = -Σ y log ŷ", "xy": (0, 0), "w": 2.5, "h": 0.8, "color": COLORS["orange"]},
        {"text": "评估\nAcc / F1",     "xy": (0, -1), "w": 2.5, "h": 0.8, "color": COLORS["red"]},
    ],
    connections=[(0, 1), (1, 2), (2, 3), (3, 4)],
    title="实验数据处理流程",
)
sp.savefig("flow_pipeline")

# 分支流程图
sp.flow(
    blocks=[
        {"text": "输入数据",         "xy": (1, 3), "w": 2.0, "h": 0.8, "color": COLORS["blue"]},
        {"text": "条件判断",         "xy": (1, 2), "w": 2.0, "h": 0.8, "color": COLORS["purple"], "shape": "diamond"},
        {"text": "分支A\n处理",      "xy": (0, 0.8), "w": 2.0, "h": 0.8, "color": COLORS["green"]},
        {"text": "分支B\n处理",      "xy": (2, 0.8), "w": 2.0, "h": 0.8, "color": COLORS["orange"]},
        {"text": "合并输出",         "xy": (1, -0.5), "w": 2.0, "h": 0.8, "color": COLORS["red"]},
    ],
    connections=[(0, 1), (1, 2), (1, 3), (2, 4), (3, 4)],
    title="分支决策流程",
)
sp.savefig("flow_branch")
