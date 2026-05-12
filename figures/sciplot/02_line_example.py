"""
折线图示例：训练曲线 / 收敛过程
"""
import numpy as np
import sciplot as sp

epochs = np.arange(1, 51)

# 模拟训练损失曲线
train_loss = 2.0 / (1 + 0.08 * epochs) + 0.1 * np.random.randn(50)
val_loss = 1.8 / (1 + 0.07 * epochs) + 0.12 * np.random.randn(50)

sp.line(
    x=epochs,
    y=[train_loss, val_loss],
    labels=["训练损失", "验证损失"],
    title="模型训练收敛曲线",
    xlabel="Epoch",
    ylabel="Loss",
    markers=False,
    legend_loc="upper right",
)
sp.savefig("line_training_curve")

# 多方法对比
x = np.arange(1, 11)
sp.line(
    x=x,
    y=[
        0.92 * (1 - 0.6**x) + 0.03 * (np.random.randn(10) * 0.5**x),
        0.85 * (1 - 0.4**x) + 0.02 * (np.random.randn(10) * 0.5**x),
        0.78 * (1 - 0.3**x) + 0.02 * (np.random.randn(10) * 0.5**x),
    ],
    labels=["本方案", "对比方法A", "对比方法B"],
    title="各方法准确率随训练数据量变化",
    xlabel="训练数据量 (千条)",
    ylabel="准确率",
    markers=True,
    marker_interval=2,
)
sp.savefig("line_comparison")
