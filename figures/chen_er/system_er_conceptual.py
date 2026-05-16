"""
系统概念级 Chen 式 ER 图（无属性版）
网格布局，按业务域分组，实体间距充足。
"""
import os, sys
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_script_dir))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from chen_er import Diagram, CONCEPTUAL_STYLE

dia = Diagram(style=CONCEPTUAL_STYLE)

# ═══════════════════════════════════════════════
# 实体网格 (行, 列)
#  列0       列1       列2       列3       列4
# ═══════════════════════════════════════════════
EW, EH = 100, 44
GX, GY = 260, 240   # 间距防粘连
OX, OY = 100, 80

def gp(r, c):
    return OX + c*GX + EW//2, OY + r*GY + EH//2

# 实体
cust  = dia.entity("客户");  cust.x, cust.y  = gp(0, 0)
pet   = dia.entity("宠物");  pet.x, pet.y   = gp(0, 1)
ptype = dia.entity("宠物类型"); ptype.x, ptype.y = gp(0, 2)
appt  = dia.entity("预约");  appt.x, appt.y  = gp(1, 0)
doc   = dia.entity("医生");  doc.x, doc.y    = gp(1, 1)
sched = dia.entity("排班");  sched.x, sched.y = gp(1, 2)
user  = dia.entity("用户");  user.x, user.y   = gp(1, 3)
case  = dia.entity("病例");  case.x, case.y   = gp(2, 0)
med   = dia.entity("药品");  med.x, med.y     = gp(2, 1)
medcat= dia.entity("药品分类"); medcat.x, medcat.y = gp(2, 2)
equip = dia.entity("器械");  equip.x, equip.y = gp(2, 3)
eqpcat= dia.entity("器械分类"); eqpcat.x, eqpcat.y = gp(2, 4)
inv   = dia.entity("库存");  inv.x, inv.y     = gp(3, 1)

# 保存尺寸
for e in dia.entities:
    e.w, e.h = EW, EH

# ═══════════════════════════════════════════════
# 关系 (置于两实体之间)
# ═══════════════════════════════════════════════
RS = 40

def pos(r, c):
    """网格行列 → 中心坐标"""
    return gp(r, c)

# 关系: 名称, 实体1, 实体2, card1, card2, (行, 列)
for name, e1, e2, c1, c2, (r, c) in [
    ("拥有", cust, pet, "1", "N", (0, 0.5)),
    ("属于", pet, ptype, "N", "1", (0, 1.5)),
    ("发起", cust, appt, "1", "N", (0.5, 0)),
    ("关联", pet, appt, "1", "N", (0.5, 1)),
    ("接诊", doc, appt, "1", "N", (0.5, 0.5)),
    ("排班", doc, sched, "1", "N", (1, 1.5)),
    ("管理", user, doc, "1", "N", (1, 2)),
    ("就诊", pet, case, "1", "N", (1, 0.5)),
    ("主治", doc, case, "1", "N", (1.5, 0.5)),
    ("生成", appt, case, "1", "1", (1.5, 0)),
    ("分类", med, medcat, "N", "1", (2, 1.5)),
    ("分类", equip, eqpcat, "N", "1", (2, 3.5)),
    ("记录", inv, med, "1", "1", (2.5, 1)),
    ("记录", inv, equip, "1", "1", (2.5, 2)),
    ("使用", case, med, "N", "M", (2, 0.5)),
    # case(0,2) ↔ equip(2,3), 菱形放在列2.5避开与"分类"重叠
    ("使用", case, equip, "N", "M", (2.1, 2.5)),
]:
    x, y = pos(r, c)
    rel = dia.relationship(name, e1, e2)
    rel.x, rel.y = x, y
    rel.size = RS
    rel.set_card(e1, c1)
    rel.set_card(e2, c2)

# 病例自引用(链表) — 放在病例右上方
r_self = dia.relationship("追溯", case, case)
r_self.x = case.x + 140
r_self.y = case.y - 90
r_self.size = RS
r_self.set_card(case, "N")

# ═══════════════════════════════════════════════
# 手动渲染
# ═══════════════════════════════════════════════
def manual_render(dia, path):
    xs, ys = [], []
    for e in dia.entities:
        xs.extend([e.x - e.w/2, e.x + e.w/2])
        ys.extend([e.y - e.h/2, e.y + e.h/2])
    for r in dia.relationships:
        xs.extend([r.x - r.size, r.x + r.size])
        ys.extend([r.y - r.size, r.y + r.size])
    pad = dia.style.padding
    dia._svg_w = max(int(max(xs) - min(xs) + pad*2), 600)
    dia._svg_h = max(int(max(ys) - min(ys) + pad*2), 400)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{dia._svg_w}" height="{dia._svg_h}" '
        f'viewBox="0 0 {dia._svg_w} {dia._svg_h}">',
    ]
    drawn_reflexive = set()
    for conn in dia.connections:
        rid = id(conn.rel)
        if conn.rel.is_reflexive and rid not in drawn_reflexive:
            drawn_reflexive.add(rid)
            lines.extend(dia._reflexive_lines(conn.rel, conn.ent))
        elif not conn.rel.is_reflexive:
            lines.extend(dia._rel_line(conn.rel, conn.ent))
    for e in dia.entities:
        lines.append(dia._entity_shape(e))
    for r in dia.relationships:
        lines.append(dia._rel_shape(r))
    lines.append("</svg>")
    svg = "\n".join(lines)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"  SVG: {path}")

manual_render(dia, os.path.join(_script_dir, "system_er_conceptual.svg"))
dia.render_drawio(os.path.join(_script_dir, "system_er_conceptual.drawio"), do_layout="dot")
