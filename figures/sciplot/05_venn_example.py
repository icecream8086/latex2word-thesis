"""
维恩图示例：概念对比与重叠分析
"""
import sciplot as sp

# 两集合维恩图
sp.venn(
    sets=[{"CNN", "RNN", "Transformer", "GNN"}, {"Transformer", "GNN", "GCN", "GAT"}],
    labels=["学术界常用模型", "工业界常用模型"],
    title="学术界与工业界模型重叠情况",
)
sp.savefig("venn_2sets")

# 三集合维恩图
sp.venn(
    sets=[
        {"CNN", "ResNet", "DenseNet", "VGG"},
        {"LSTM", "GRU", "Transformer", "ResNet"},
        {"GCN", "GAT", "GIN", "Transformer"},
    ],
    labels=["计算机视觉", "自然语言处理", "图神经网络"],
    title="三大领域模型需求分析",
)
sp.savefig("venn_3sets")
