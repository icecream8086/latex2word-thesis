"""
简单二元关系 E-R 图示例（Chen 式记法）
"""
import os, sys
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_script_dir))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from chen_er import Diagram, Attr

dia = Diagram()

student = dia.entity("学生", attrs=[
    Attr("学号", key=True), Attr("姓名"),
    Attr("年龄"), Attr("性别"),
])
course = dia.entity("课程", attrs=[
    Attr("课程号", key=True), Attr("课程名"), Attr("学分"),
])
rel = dia.relationship("选修", student, course)
rel.set_card(student, "N"); rel.set_card(course, "M")

out_path = os.path.join(_script_dir, "simple_test.svg")
dia.render(out_path)
print(f"  SVG 已生成: {out_path}")

# 导出 draw.io 格式
drawio_path = os.path.join(_script_dir, "simple_test.drawio")
dia.render_drawio(drawio_path)
