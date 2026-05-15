"""
系统数据库 E-R 图（Chen 式记法）

定义系统核心实体与关系，渲染为 SVG 供论文使用。

用法:
  python convert_chen_er.py                        # 编译全部
  python convert_chen_er.py -f figures/chen_er/system_er.py  # 单文件
"""
import os, sys
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_script_dir))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from chen_er import Diagram, Attr

# 读取格式（由 convert_chen_er.py 传入）
fmt = os.environ.get("CHEN_ER_FORMAT", "svg")

# ── 构建 E-R 图 ──────────────────────────────────────────────────────

dia = Diagram()

# 实体
user = dia.entity("用户", attrs=[
    Attr("用户ID", key=True),
    Attr("用户名"), Attr("密码"),
    Attr("邮箱", multivalued=True),
    Attr("手机号"), Attr("注册时间"),
    Attr("最后登录", derived=True),
])
role = dia.entity("角色", attrs=[
    Attr("角色ID", key=True),
    Attr("角色名"), Attr("角色描述"),
])
permission = dia.entity("权限", attrs=[
    Attr("权限ID", key=True),
    Attr("权限标识"), Attr("权限名称"),
])
log = dia.entity("操作日志", attrs=[
    Attr("日志ID", key=True),
    Attr("操作类型"), Attr("操作详情"), Attr("操作时间"),
])
dept = dia.entity("部门", attrs=[
    Attr("部门ID", key=True),
    Attr("部门名称"), Attr("部门编码"),
])

# 关系
r1 = dia.relationship("分配", user, role)
r1.set_card(user, "N"); r1.set_card(role, "M")

r2 = dia.relationship("授权", role, permission)
r2.set_card(role, "N"); r2.set_card(permission, "M")

r3 = dia.relationship("隶属", user, dept)
r3.set_card(user, "N"); r3.set_card(dept, "1")

r4 = dia.relationship("记录", user, log)
r4.set_card(user, "1"); r4.set_card(log, "N")

# 用户自环：上级-下级管理关系
r5 = dia.relationship("管理", user, user)
r5.set_card(user, "N")   # N to N (用户可管理多个下级，也可有多个上级)

# ── 渲染 ──────────────────────────────────────────────────────────────

out_name = os.environ.get("CHEN_ER_OUTPUT", "system_er")
out_path = os.path.join(_script_dir, f"{out_name}.svg")
dia.render(out_path)
print(f"  SVG 已生成: {out_path}")
