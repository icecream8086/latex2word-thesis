"""
函数曲线图示例：数学公式可视化
"""
import numpy as np
import sciplot as sp

# 基本函数 y = sin(x) / x
sp.curve(
    lambda x: np.sin(x) / (x + 1e-10),
    x_range=(-10, 10),
    label=r"$y = \frac{\sin(x)}{x}$",
    title="Sinc 函数",
    xlabel="x",
    ylabel="y",
    fill_area=(-2, 2),
)
sp.savefig("curve_sinc")

# 多条函数对比
sp.curve(
    lambda x: x**2,
    x_range=(-3, 3),
    label=r"$y = x^2$",
    title="常见激活函数对比",
    xlabel="x",
    ylabel="y",
    secondary_funcs=[
        (lambda x: x**3, r"$y = x^3$", "#DD8452", "-"),
        (lambda x: np.sin(x), r"$y = \sin(x)$", "#55A868", "--"),
        (lambda x: 1 / (1 + np.exp(-x)), r"$y = \sigma(x)$", "#C44E52", "-."),
    ],
    ylim=(-3, 5),
)
sp.savefig("curve_functions")

# 带参数的函数
def gaussian(x, mu=0, sigma=1, amp=1):
    return amp * np.exp(-((x - mu)**2) / (2 * sigma**2))

sp.curve(
    gaussian,
    x_range=(-5, 5),
    params={"mu": 0, "sigma": 1.0, "amp": 1},
    label=r"$\mu=0,\ \sigma=1$",
    title="高斯分布曲线",
    xlabel="x",
    ylabel="密度",
    secondary_funcs=[
        (lambda x: gaussian(x, 0, 2, 1), r"$\mu=0,\ \sigma=2$", "#DD8452", "--"),
        (lambda x: gaussian(x, 0, 0.5, 1), r"$\mu=0,\ \sigma=0.5$", "#55A868", "-."),
    ],
)
sp.savefig("curve_gaussian")
