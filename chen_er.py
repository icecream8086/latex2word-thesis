"""
Chen-style ER Diagram Generator
================================
Pure SVG generation, no external dependencies beyond Python 3.
Produces clean SVGs (no foreignObject) that render correctly in Word.

Usage:
    from chen_er import Diagram, Entity, Relationship, Attr

    dia = Diagram("图例: 数据库ER图")
    student = dia.entity("学生", attrs=[
        Attr("学号", key=True), Attr("姓名"), Attr("性别"),
        Attr("年龄"), Attr("电话", multivalued=True),
    ])
    course = dia.entity("课程", attrs=[
        Attr("课程号", key=True), Attr("课程名"), Attr("学分"),
    ])
    enroll = dia.relationship("选修", student, course)
    enroll.set_card(student, "N")
    enroll.set_card(course, "M")
    enroll.attrs = [Attr("成绩")]

    dia.render("output.svg")
"""

import math
import os
from xml.sax.saxutils import escape as _escape
from dataclasses import dataclass, field


# ── Golden ratio ─────────────────────────────────────────────────────

PHI  = (1 + 5 ** 0.5) / 2   # 1.618
PHI2 = PHI * PHI            # 2.618


# ── Style (shared visual theme) ──────────────────────────────────────

@dataclass
class Style:
    """Visual theme for Chen ER diagrams.  All scripts share this.

    Override any field before passing to Diagram:
        my_style = Style(font=\"serif\", stroke_color=\"#b06\")
        dia = Diagram(title, style=my_style)
    """
    # typography
    font: str            = "sans-serif"
    font_size_entity: int = 15
    font_size_rel: int   = 14
    font_size_attr: int  = 12
    font_size_card: int  = 11
    font_size_title: int = 16

    # component sizing (minima — autosize grows from text)
    entity_w: int   = 120
    entity_h: int   = 56
    rel_size: int   = 48
    attr_rx: int    = 46
    attr_ry: int    = 22

    # spacing (all derived from φ relative to actual element sizes at layout-time)
    attr_dist: int  = 130   # entity-centre → attribute-centre
    padding: int    = 40
    group_gap: int  = 150

    # stroke & fill
    stroke_w: int     = 2
    stroke_color: str = "#333"
    fill_color: str   = "#fff"
    text_color: str   = "#222"
    line_color: str   = "#555"


# Default instance — other scripts can ``from chen_er import DEFAULT_STYLE``
DEFAULT_STYLE = Style()

# 概念图预设样式（紧凑，无属性，适合系统级 ER 图）
CONCEPTUAL_STYLE = Style(
    entity_w=100, entity_h=44, rel_size=40,
    font_size_entity=14, font_size_rel=13, font_size_card=10,
    group_gap=120, padding=40,
)


# ── Helper: estimate text pixel width ──────────────────────────────────

def _tw(text: str, size: int) -> int:
    """Rough pixel width of text at given font-size (px)."""
    w = 0
    for ch in text:
        if ord(ch) > 0x2e80:        # CJK
            w += size * 1.1
        elif ch in "iIl1.,;:!|' ":  # narrow
            w += size * 0.35
        elif ch in "mwWM@#$%&":     # wide
            w += size * 0.72
        else:
            w += size * 0.62
    return int(w) + 6


# ── Data classes ───────────────────────────────────────────────────────

@dataclass
class Attr:
    """An attribute (shown as ellipse in Chen notation)."""
    name: str
    key: bool = False
    multivalued: bool = False
    derived: bool = False
    x: float = 0
    y: float = 0
    angle: float = 0


@dataclass
class Entity:
    """An entity set (shown as rectangle)."""
    name: str
    attrs: list = field(default_factory=list)
    weak: bool = False
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0

    def __hash__(self):
        return id(self)

    def _text_width(self, fs: int) -> int:
        return _tw(self.name, fs) + 16

    def autosize(self, style: "Style"):
        self.w = max(style.entity_w, self._text_width(style.font_size_entity))
        self.h = style.entity_h


@dataclass
class Relationship:
    """A relationship set (shown as diamond)."""
    name: str
    entities: list = field(default_factory=list)
    cardinalities: dict = field(default_factory=dict)
    attrs: list = field(default_factory=list)
    weak: bool = False
    x: float = 0
    y: float = 0
    size: int = 0

    def __hash__(self):
        return id(self)

    @property
    def is_reflexive(self):
        """True if this is a self-loop (same entity on both sides)."""
        return len(self.entities) >= 2 and self.entities[0] is self.entities[-1]

    def set_card(self, entity, card: str):
        self.cardinalities[entity] = card

    def _text_width(self, fs: int) -> int:
        return _tw(self.name, fs) + 16

    def autosize(self, style: "Style"):
        tw = self._text_width(style.font_size_rel)
        self.size = max(style.rel_size, round(tw / 1.414 + 6))


@dataclass
class Connection:
    """Links a relationship to one of its entities."""
    rel: Relationship
    ent: Entity


# ── Diagram ────────────────────────────────────────────────────────────

class Diagram:
    """Top-level container for a Chen ER diagram."""

    def __init__(self, title: str = "", *, style: Style = None):
        self.title = title
        self.style = style or DEFAULT_STYLE
        self.entities: list[Entity] = []
        self.relationships: list[Relationship] = []
        self.connections: list[Connection] = []
        self._svg_w = 800
        self._svg_h = 600

    # ── DSL builders ────────────────────────────────────────────────

    def entity(self, name: str, *, attrs: list = None, weak: bool = False) -> Entity:
        s = self.style
        e = Entity(name=name, attrs=attrs or [], weak=weak, w=s.entity_w, h=s.entity_h)
        e.autosize(s)
        self.entities.append(e)
        return e

    def relationship(self, name: str, *entities: Entity,
                     attrs: list = None, weak: bool = False) -> Relationship:
        r = Relationship(name=name, entities=list(entities),
                          attrs=attrs or [], weak=weak)
        for ent in entities:
            self.connections.append(Connection(r, ent))
        self.relationships.append(r)
        return r

    # ── Layout ──────────────────────────────────────────────────────

    # ── Main layout ────────────────────────────────────────────────

    def layout(self):
        """Auto-layout all elements with adaptive golden-ratio spacing."""
        # 1. size elements to content
        for e in self.entities:
            e.autosize(self.style)
        for r in self.relationships:
            r.autosize(self.style)
        # 2. layout
        if not self.relationships:
            self._layout_entities_only()
        else:
            self._layout_all_groups()
        # 3. place attributes
        for e in self.entities:
            self._layout_attrs(e)
        for r in self.relationships:
            self._layout_rel_attrs(r)
        self._centerize()
        bounds = self._calc_bounds()
        self._svg_w = max(int(bounds[2] + self.style.padding), 600)
        self._svg_h = max(int(bounds[3] + self.style.padding), 400)

    def _layout_entities_only(self):
        """No relationships – arrange entities horizontally."""
        n = len(self.entities)
        total_w = sum(e.w for e in self.entities) + (n - 1) * 80
        cx = self.style.padding + total_w / 2
        cy = self.style.padding + 120
        x0 = cx - total_w / 2
        for e in self.entities:
            e.x = x0 + e.w / 2
            e.y = cy
            x0 += e.w + 80

    def _autosize_all(self):
        for e in self.entities:
            e.autosize(self.style)
        for r in self.relationships:
            r.autosize(self.style)
        for e in self.entities:
            self._layout_attrs(e)
        for r in self.relationships:
            self._layout_rel_attrs(r)

    # ── Adaptive centre-to-centre (per group) ──────────────────────

    def _group_ctoc(self, ents, rels):
        """Compute adaptive CTOC for a connected group using φ."""
        halves = [e.w / 2 for e in ents] + [r.size for r in rels]
        mh = max(halves)
        return round((2 + PHI) * mh)  # = half + φ×half + half

    def _centerize(self):
        """Shift all elements so min x/y >= self.style.padding."""
        xs, ys = [], []
        for e in self.entities:
            xs.append(e.x - e.w / 2); xs.append(e.x + e.w / 2)
            ys.append(e.y - e.h / 2); ys.append(e.y + e.h / 2)
            for a in e.attrs:
                tw = _tw(a.name, self.style.font_size_attr) / 2 + 10
                xs.append(a.x - tw); xs.append(a.x + tw)
                ys.append(a.y - self.style.attr_ry); ys.append(a.y + self.style.attr_ry)
        for r in self.relationships:
            s = r.size
            xs.append(r.x - s); xs.append(r.x + s)
            ys.append(r.y - s); ys.append(r.y + s)
            for a in r.attrs:
                tw = _tw(a.name, self.style.font_size_attr) / 2 + 10
                xs.append(a.x - tw); xs.append(a.x + tw)
                ys.append(a.y - self.style.attr_ry); ys.append(a.y + self.style.attr_ry)
        if not xs:
            return
        dx = max(0, self.style.padding - min(xs))
        dy = max(0, self.style.padding - min(ys))
        if dx == 0 and dy == 0:
            return
        for e in self.entities:
            e.x += dx; e.y += dy
            for a in e.attrs:
                a.x += dx; a.y += dy
        for r in self.relationships:
            r.x += dx; r.y += dy
            for a in r.attrs:
                a.x += dx; a.y += dy

    # ── Component grouping ─────────────────────────────────────────

    def _layout_all_groups(self):
        """Layout each connected component independently, stacking vertically."""
        groups = self._find_groups()
        y_off = self.style.padding + 60
        for g in groups:
            rels, ents = g["rels"], g["ents"]
            C = self._group_ctoc(ents, rels)
            h = self._layout_group(rels, ents, y_off, C)
            y_off += h + round(self.style.group_gap)

    def _find_groups(self) -> list[dict]:
        """Partition relationships into connected-component groups via BFS."""
        visited = set()
        groups = []
        for r in self.relationships:
            if r in visited:
                continue
            stack = [r]
            comp_rels = set()
            comp_ents = set()
            while stack:
                cur = stack.pop()
                if cur in comp_rels:
                    continue
                comp_rels.add(cur)
                visited.add(cur)
                for ent in cur.entities:
                    comp_ents.add(ent)
                    for r2 in self.relationships:
                        if r2 not in comp_rels and ent in r2.entities:
                            stack.append(r2)
            groups.append({"rels": list(comp_rels), "ents": list(comp_ents)})
        return groups

    # ── Group layout dispatch ──────────────────────────────────────

    def _layout_group(self, rels, ents, y0, C):
        if len(rels) == 1:
            return self._layout_single_rel(rels[0], y0, C)
        return self._layout_tree(rels, ents, y0, C)

    # ── Single relationship ────────────────────────────────────────

    def _layout_single_rel(self, rel, y0, C):
        n = len(rel.entities)
        if n == 2:
            return self._layout_binary(rel, y0, C)
        return self._layout_radial(rel, y0, C)

    def _layout_binary(self, rel, y0, C):
        """Binary: entity L, diamond, entity R — φ spacing."""
        a, b = rel.entities
        cx = self.style.padding + 350
        cy = y0 + C * 2
        rel.x, rel.y = cx, cy
        a.x = cx - C - a.w / 2
        a.y = cy
        b.x = cx + C + b.w / 2
        b.y = cy
        return C * 3 + 80

    def _layout_radial(self, rel, y0, C):
        """N-ary: entities in a circle, relationship at centre."""
        n = len(rel.entities)
        radius = max(round(PHI * C), 90 + 30 * n)
        cx = self.style.padding + radius + 200
        cy = y0 + radius + 100
        rel.x, rel.y = cx, cy
        for i, ent in enumerate(rel.entities):
            a = -math.pi / 2 + i * (2 * math.pi / n)
            ent.x = cx + radius * math.cos(a)
            ent.y = cy + radius * math.sin(a)
        return 2 * (radius + 120)

    # ── Connected (multi-rel) group: tree layout ───────────────────

    def _layout_tree(self, rels, ents, y0, C):
        """
        Tree layout radiating from the hub entity.
        Spacing = C (adaptive φ-based CTOC for this group).
        Each branch takes a different direction → no crossing lines.
        """
        ent_rels = {e: [] for e in ents}
        rel_ents = {r: [] for r in rels}
        for cn in self.connections:
            if cn.ent in ent_rels and cn.rel in rel_ents:
                ent_rels[cn.ent].append(cn.rel)
                rel_ents[cn.rel].append(cn.ent)

        hub = max(ents, key=lambda e: len(ent_rels[e]))
        RX = self.style.padding + 400
        RY = y0 + 300
        hub.x, hub.y = RX, RY
        visited = {hub}
        dirs = [(-1, 0), (0, 1), (1, 0), (0, -1)]
        hub_rels = list(ent_rels.get(hub, []))

        def _place(to, fx, fy, dx, dy, dist):
            to.x = fx + dx * dist
            to.y = fy + dy * dist
            visited.add(to)

        # Zigzag counter for horizontal branches — ±C for ≈45° diagonal
        _zz = 0
        def _zigzag(dx):
            nonlocal _zz
            if dx != 0:
                _zz += 1
                return C if (_zz % 2 == 1) else -C
            return 0

        for i, rel in enumerate(hub_rels):
            # ── Reflexive (self-loop) ─────────────────────────────
            if rel.is_reflexive:
                rel.x = RX + C       # right of hub
                rel.y = RY - C       # above hub
                visited.add(rel)
                _zz += 1  # keep zigzag counter consistent
                continue

            dx, dy = dirs[i % len(dirs)]
            _place(rel, RX, RY, dx, dy, C)

            others = [e for e in rel.entities if e not in visited]
            for j, ent in enumerate(others):
                ndx, ndy = dx, dy
                if j > 0:
                    if dx == 0:
                        ndx = (j - (len(others) - 1) / 2) * 0.4
                    else:
                        ndy = (j - (len(others) - 1) / 2) * 0.4
                    norm = math.hypot(ndx, ndy) or 1
                    ndx, ndy = ndx / norm, ndy / norm
                _place(ent, rel.x, rel.y, ndx, ndy, C)
                ent.y += _zigzag(dx)

                # sub-relationships from this entity
                sub_rels = [r for r in ent_rels.get(ent, []) if r not in visited]
                for k, sr in enumerate(sub_rels):
                    sdx, sdy = ndx, ndy
                    if ndx == 0:
                        sdx = 0.3 * (k - (len(sub_rels) - 1) / 2)
                    else:
                        sdy = 0.3 * (k - (len(sub_rels) - 1) / 2)
                    sn = math.hypot(sdx, sdy) or 1
                    sdx, sdy = sdx / sn, sdy / sn
                    _place(sr, ent.x, ent.y, sdx, sdy, C)

                    for se in sr.entities:
                        if se in visited:
                            continue
                        _place(se, sr.x, sr.y, sdx, sdy, C)
                        se.y += _zigzag(sdx)

        # leftovers (should not happen for a tree)
        idx = 0
        for e in ents:
            if e not in visited:
                e.x, e.y = RX + 500, RY + (idx + 1) * C; idx += 1
        for r in rels:
            if r not in visited:
                r.x, r.y = RX - 500, RY + (idx + 1) * C; idx += 1

        ys = [n.y for n in list(rels) + list(ents)]
        return max(ys) - min(ys) + C * 2

    # ── Attribute placement ─────────────────────────────────────────

    def _layout_attrs(self, ent: Entity):
        """Place attributes around entity using angular fan."""
        attrs = ent.attrs
        n = len(attrs)
        if n == 0:
            return
        for i, attr in enumerate(attrs):
            a = i * (2 * math.pi / n) - math.pi / 2
            attr.angle = a
            attr.x = ent.x + self.style.attr_dist * math.cos(a)
            attr.y = ent.y + self.style.attr_dist * math.sin(a)

    def _layout_rel_attrs(self, rel: Relationship):
        """Place relationship attributes above the diamond (φ-spaced)."""
        n = len(rel.attrs)
        if n == 0:
            return
        for i, attr in enumerate(rel.attrs):
            angle = -math.pi / 2 + (i - (n - 1) / 2) * math.pi / (max(n, 2) * 1.5)
            attr.x = rel.x + self.style.attr_dist * math.cos(angle)
            attr.y = rel.y + self.style.attr_dist * math.sin(angle)

    def _calc_bounds(self):
        """Compute (min_x, min_y, max_x, max_y) covering all elements."""
        xs, ys = [], []
        for e in self.entities:
            xs.extend([e.x - e.w / 2, e.x + e.w / 2])
            ys.extend([e.y - e.h / 2, e.y + e.h / 2])
            for a in e.attrs:
                tw = _tw(a.name, self.style.font_size_attr) / 2 + 10
                xs.extend([a.x - tw, a.x + tw])
                ys.extend([a.y - self.style.attr_ry, a.y + self.style.attr_ry])
        for r in self.relationships:
            s = r.size
            xs.extend([r.x - s, r.x + s])
            ys.extend([r.y - s, r.y + s])
            for a in r.attrs:
                tw = _tw(a.name, self.style.font_size_attr) / 2 + 10
                xs.extend([a.x - tw, a.x + tw])
                ys.extend([a.y - self.style.attr_ry, a.y + self.style.attr_ry])
        if not xs:
            return 0, 0, 800, 600
        return min(xs), min(ys), max(xs), max(ys)

    # ── SVG rendering ───────────────────────────────────────────────

    def render(self, path: str):
        """Render diagram to SVG file."""
        self.layout()
        svg = self._generate_svg()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)

    # ── draw.io export ────────────────────────────────────────────

    def _dot_layout(self):
        """Use Graphviz dot for hierarchical layout (entities + relationship nodes)."""
        import subprocess, tempfile, re

        lines = ['digraph ER {', 'rankdir=LR;',
                 'node [shape=box,style=rounded,width=1.2,height=0.5,fixedsize=true];',
                 'edge [arrowhead=none];']
        ent_ids, rel_ids = {}, {}
        for i, e in enumerate(self.entities):
            vid = f"e{i}"
            ent_ids[id(e)] = vid
            lines.append(f'{vid} [label="{_escape(e.name)}"];')
        for i, r in enumerate(self.relationships):
            vid = f"r{i}"
            rel_ids[id(r)] = vid
            lines.append(f'{vid} [label="{_escape(r.name)}",shape=diamond,width=0.8,height=0.8];')
        done = set()
        for cn in self.connections:
            rid = rel_ids.get(id(cn.rel))
            eid = ent_ids.get(id(cn.ent))
            if not rid or not eid:
                continue
            chain = (rid, id(cn.rel), id(cn.ent))
            if chain in done:
                continue
            done.add(chain)
            rel_ents = [c.ent for c in self.connections if c.rel is cn.rel]
            if len(rel_ents) >= 2 and not cn.rel.is_reflexive:
                e0 = ent_ids.get(id(rel_ents[0]))
                e1 = ent_ids.get(id(rel_ents[1]))
                if e0 and e1:
                    lines.append(f'{e0} -> {rid};')
                    lines.append(f'{rid} -> {e1};')
            else:
                lines.append(f'{eid} -> {rid};')
        lines.append('}')

        try:
            r = subprocess.run(
                ["dot", "-Tplain"],
                input="\n".join(lines),
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode != 0:
                return False

            node_pos = {}
            for line in r.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[0] == "node":
                    name, x, y, w, h = parts[1], float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])
                    node_pos[name] = (x * 72, y * 72, w * 72, h * 72)

            max_y = 0
            for e in self.entities:
                nid = ent_ids.get(id(e))
                if nid and nid in node_pos:
                    nx, ny, nw, nh = node_pos[nid]
                    e.x = nx
                    e.y = ny
                    e.w = max(e.w, nw)
                    e.h = max(e.h, nh)
                    max_y = max(max_y, ny)
            for e in self.entities:
                nid = ent_ids.get(id(e))
                if nid and nid in node_pos:
                    e.y = max_y - e.y + 60
                    e.x += 80

            # Place rel diamonds at dot positions (same flip/offset as entities)
            for rel in self.relationships:
                nid = rel_ids.get(id(rel))
                if nid and nid in node_pos:
                    nx, ny, nw, nh = node_pos[nid]
                    rel.x = nx + 80
                    rel.y = (max_y - ny) + 60
                else:
                    # Fallback: midpoint between connected entities
                    xs, ys = [], []
                    for cn in self.connections:
                        if cn.rel is rel:
                            xs.append(cn.ent.x)
                            ys.append(cn.ent.y)
                    if xs:
                        rel.x = sum(xs) / len(xs)
                        rel.y = sum(ys) / len(ys) - 20

            return True
        except Exception:
            return False

    def render_drawio(self, path: str, do_layout=True):
        """Export diagram as draw.io XML (.drawio).

        Args:
            path: 输出路径.
            do_layout: True=内部自动布局, "dot"=Graphviz最优布局, False=用已有坐标.
        """
        if do_layout == "dot":
            ok = self._dot_layout()
            if not ok:
                print("  [提示] dot 布局失败，回退到内部布局")
                self.layout()
        elif do_layout:
            self.layout()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        _id = [0]
        def nid(): _id[0] += 1; return f"n{_id[0]}"

        cells = []
        id_map = {}  # python-object → drawio-id

        # ── vertices ───────────────────────────────────────────────
        for ent in self.entities:
            vid = nid()
            id_map[id(ent)] = vid
            x = ent.x - ent.w / 2
            y = ent.y - ent.h / 2
            style = "rounded=0;whiteSpace=wrap;html=1;"
            style += "dashed=1;" if ent.weak else ""
            cells.append(
                f'<mxCell id="{vid}" value="{_escape(ent.name)}" '
                f'style="{style}" vertex="1" parent="1">'
                f'<mxGeometry x="{x:.0f}" y="{y:.0f}" '
                f'width="{ent.w:.0f}" height="{ent.h:.0f}" as="geometry"/>'
                f'</mxCell>')

        for rel in self.relationships:
            rid = nid()
            id_map[id(rel)] = rid
            s = rel.size * 2
            x = rel.x - rel.size
            y = rel.y - rel.size
            style = "rhombus;whiteSpace=wrap;html=1;"
            style += "dashed=1;" if rel.weak else ""
            cells.append(
                f'<mxCell id="{rid}" value="{_escape(rel.name)}" '
                f'style="{style}" vertex="1" parent="1">'
                f'<mxGeometry x="{x:.0f}" y="{y:.0f}" '
                f'width="{s:.0f}" height="{s:.0f}" as="geometry"/>'
                f'</mxCell>')

        for ent in self.entities:
            for attr in ent.attrs:
                aid = nid()
                id_map[id(attr)] = aid
                tw = _tw(attr.name, self.style.font_size_attr)
                rx = max(self.style.attr_rx, tw / 2 + 10)
                ry = self.style.attr_ry
                x = attr.x - rx
                y = attr.y - ry
                style = "ellipse;whiteSpace=wrap;html=1;"
                style += "dashed=1;" if attr.derived else ""
                # 多值用 double 边框 (strokeWidth)
                if attr.multivalued:
                    style += "strokeWidth=3;"
                cells.append(
                    f'<mxCell id="{aid}" value="{_escape(attr.name)}" '
                    f'style="{style}" vertex="1" parent="1">'
                    f'<mxGeometry x="{x:.0f}" y="{y:.0f}" '
                    f'width="{rx*2:.0f}" height="{ry*2:.0f}" as="geometry"/>'
                    f'</mxCell>')

        # ── edges ──────────────────────────────────────────────────
        for conn in self.connections:
            src = id_map.get(id(conn.rel))
            tgt = id_map.get(id(conn.ent))
            if not src or not tgt:
                continue
            eid = nid()
            style = "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;"
            cells.append(
                f'<mxCell id="{eid}" style="{style}" edge="1" '
                f'parent="1" source="{src}" target="{tgt}">'
                f'<mxGeometry relative="1" as="geometry"/>'
                f'</mxCell>')

            # cardinality label on edge
            card = conn.rel.cardinalities.get(conn.ent, "")
            if card:
                ceid = nid()
                cells.append(
                    f'<mxCell id="{ceid}" value="{_escape(card)}" '
                    f'style="edgeLabel;html=1;align=center;'
                    f'verticalAlign=middle;resizable=0;points=[];" '
                    f'vertex="1" connectable="0" parent="{eid}">'
                    f'<mxGeometry x="0.5" y="0.5" relative="1" '
                    f'as="geometry"/>'
                    f'</mxCell>')

        # entity → attribute edges
        for ent in self.entities:
            for attr in ent.attrs:
                src = id_map.get(id(ent))
                tgt = id_map.get(id(attr))
                if not src or not tgt:
                    continue
                eid = nid()
                cells.append(
                    f'<mxCell id="{eid}" style="rounded=0;html=1;" '
                    f'edge="1" parent="1" source="{src}" target="{tgt}">'
                    f'<mxGeometry relative="1" as="geometry"/>'
                    f'</mxCell>')

        # rel → attribute edges
        for rel in self.relationships:
            for attr in rel.attrs:
                src = id_map.get(id(rel))
                tgt = id_map.get(id(attr))
                if not src or not tgt:
                    continue
                eid = nid()
                cells.append(
                    f'<mxCell id="{eid}" style="rounded=0;html=1;" '
                    f'edge="1" parent="1" source="{src}" target="{tgt}">'
                    f'<mxGeometry relative="1" as="geometry"/>'
                    f'</mxCell>')

        # ── assemble ───────────────────────────────────────────────
        w = max(self._svg_w, 800)
        h = max(self._svg_h, 600)
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<mxfile host="chen_er.py">',
            '<diagram name="Page-1">',
            f'<mxGraphModel dx="0" dy="0" grid="1" gridSize="10" '
            f'guides="1" tooltips="1" connect="1" arrows="1" '
            f'fold="1" page="1" pageScale="1" '
            f'pageWidth="{w}" pageHeight="{h}" math="0" shadow="0">',
            '<root>',
            '<mxCell id="0"/>',
            '<mxCell id="1" parent="0"/>',
            *cells,
            '</root>',
            '</mxGraphModel>',
            '</diagram>',
            '</mxfile>',
        ]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"  draw.io: {path}")

    def _generate_svg(self) -> str:
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self._svg_w}" height="{self._svg_h}" '
            f'viewBox="0 0 {self._svg_w} {self._svg_h}">',
        ]
        # Title
        if self.title:
            lines.append(self._text(self._svg_w / 2, 30, self.title,
                                    self.style.font_size_title, bold=True))

        # Collect all drawing elements
        elements = []

        # Attribute lines + shapes (draw first, behind entities/rels)
        for ent in self.entities:
            for attr in ent.attrs:
                elements.extend(self._attr_line(ent, attr))
                elements.append(self._attr_shape(attr))
        for rel in self.relationships:
            for attr in rel.attrs:
                elements.extend(self._attr_line(rel, attr))
                elements.append(self._attr_shape(attr, rel=True))

        # Relationship lines to entities (reflexive → double-line loop)
        drawn_reflexive = set()
        for conn in self.connections:
            rid = id(conn.rel)
            if conn.rel.is_reflexive and rid not in drawn_reflexive:
                drawn_reflexive.add(rid)
                elements.extend(self._reflexive_lines(conn.rel, conn.ent))
            elif not conn.rel.is_reflexive:
                elements.extend(self._rel_line(conn.rel, conn.ent))

        # Entity shapes
        for ent in self.entities:
            elements.append(self._entity_shape(ent))

        # Relationship shapes
        for rel in self.relationships:
            elements.append(self._rel_shape(rel))

        lines.extend(elements)
        lines.append("</svg>")
        return "\n".join(lines)

    # ── SVG element helpers ─────────────────────────────────────────

    def _text(self, x: float, y: float, content: str, size: int,
              bold: bool = False, italic: bool = False,
              color: str = None, anchor: str = "middle") -> str:
        color = color or self.style.text_color
        weight = "bold" if bold else "normal"
        style = f"italic" if italic else "normal"
        return (f'<text x="{x:.1f}" y="{y:.1f}" '
                f'font-family="{self.style.font}" font-size="{size}px" '
                f'font-weight="{weight}" font-style="{style}" '
                f'fill="{color}" text-anchor="{anchor}" '
                f'dominant-baseline="central">{_escape(content)}</text>')

    def _rect(self, cx: float, cy: float, w: float, h: float,
              stroke: str = None, fill: str = None,
              dashed: bool = False, double: bool = False) -> list:
        stroke = stroke or self.style.stroke_color
        fill = fill or self.style.fill_color
        r = []
        dash = 'stroke-dasharray="6,4"' if dashed else ""
        r.append(f'<rect x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" '
                 f'width="{w:.1f}" height="{h:.1f}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{self.style.stroke_w}" '
                 f'{dash} />')
        if double:
            pad = 5
            r.append(f'<rect x="{cx - w / 2 + pad:.1f}" '
                     f'y="{cy - h / 2 + pad:.1f}" '
                     f'width="{w - 2 * pad:.1f}" '
                     f'height="{h - 2 * pad:.1f}" '
                     f'fill="none" stroke="{stroke}" stroke-width="{self.style.stroke_w}" '
                     f'{dash} />')
        return r

    def _diamond(self, cx: float, cy: float, size: float,
                 stroke: str = None, fill: str = None,
                 dashed: bool = False, double: bool = False) -> list:
        stroke = stroke or self.style.stroke_color
        fill = fill or self.style.fill_color
        pts = f"{cx},{cy - size} {cx + size},{cy} {cx},{cy + size} {cx - size},{cy}"
        dash = 'stroke-dasharray="6,4"' if dashed else ""
        r = [f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" '
             f'stroke-width="{self.style.stroke_w}" {dash} />']
        if double:
            s = size - 6
            pts2 = f"{cx},{cy - s} {cx + s},{cy} {cx},{cy + s} {cx - s},{cy}"
            r.append(f'<polygon points="{pts2}" fill="none" '
                     f'stroke="{stroke}" stroke-width="{self.style.stroke_w}" {dash} />')
        return r

    def _ellipse(self, cx: float, cy: float, rx: float, ry: float,
                 stroke: str = None, fill: str = None,
                 dashed: bool = False, double: bool = False) -> list:
        stroke = stroke or self.style.stroke_color
        fill = fill or self.style.fill_color
        dash = 'stroke-dasharray="6,4"' if dashed else ""
        r = [f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" '
             f'ry="{ry:.1f}" fill="{fill}" stroke="{stroke}" '
             f'stroke-width="{self.style.stroke_w}" {dash} />']
        if double:
            r.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" '
                     f'rx="{rx + 4:.1f}" ry="{ry + 4:.1f}" '
                     f'fill="none" stroke="{stroke}" '
                     f'stroke-width="{self.style.stroke_w}" {dash} />')
        return r

    def _line(self, x1: float, y1: float, x2: float, y2: float,
              color: str = None, double: bool = False) -> list:
        color = color or self.style.line_color
        r = [f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
             f'x2="{x2:.1f}" y2="{y2:.1f}" '
             f'stroke="{color}" stroke-width="{self.style.stroke_w}" />']
        if double:
            # offset second line
            dx = x2 - x1
            dy = y2 - y1
            length = math.hypot(dx, dy) or 1
            nx = -dy / length * 4
            ny = dx / length * 4
            r.append(f'<line x1="{x1 + nx:.1f}" y1="{y1 + ny:.1f}" '
                     f'x2="{x2 + nx:.1f}" y2="{y2 + ny:.1f}" '
                     f'stroke="{color}" stroke-width="{self.style.stroke_w}" />')
        return r

    # ── Shape generators ────────────────────────────────────────────

    def _entity_shape(self, ent: Entity) -> str:
        parts = self._rect(ent.x, ent.y, ent.w, ent.h,
                           double=ent.weak)
        parts.append(self._text(ent.x, ent.y, ent.name,
                                self.style.font_size_entity, bold=True))
        return "\n".join(parts)

    def _rel_shape(self, rel: Relationship) -> str:
        parts = self._diamond(rel.x, rel.y, rel.size, double=rel.weak)
        parts.append(self._text(rel.x, rel.y, rel.name, self.style.font_size_rel, bold=True))
        return "\n".join(parts)

    def _attr_shape(self, attr: Attr, rel: bool = False) -> str:
        rx = max(self.style.attr_rx, _tw(attr.name, self.style.font_size_attr) / 2 + 10)
        # Adjust rx for key underline width
        if attr.key:
            rx = max(rx, _tw(attr.name, self.style.font_size_attr) / 2 + 16)
        ry = self.style.attr_ry
        parts = self._ellipse(attr.x, attr.y, rx, ry,
                              dashed=attr.derived, double=attr.multivalued)
        # Attribute text
        text_el = self._text(attr.x, attr.y, attr.name, self.style.font_size_attr,
                             italic=attr.derived)
        parts.append(text_el)
        # Underline for key attribute
        if attr.key:
            tw = _tw(attr.name, self.style.font_size_attr)
            line_x1 = attr.x - tw / 2
            line_x2 = attr.x + tw / 2
            line_y = attr.y + rx * 0.05 + 2
            parts.append(f'<line x1="{line_x1:.1f}" y1="{line_y:.1f}" '
                         f'x2="{line_x2:.1f}" y2="{line_y:.1f}" '
                         f'stroke="{self.style.text_color}" stroke-width="1.5" />')
        return "\n".join(parts)

    def _rel_line(self, rel: Relationship, ent: Entity) -> list:
        """Line from relationship diamond edge to entity box edge, with cardinality label."""
        dx = ent.x - rel.x
        dy = ent.y - rel.y
        dist = math.hypot(dx, dy) or 1
        ux = dx / dist
        uy = dy / dist
        sz = rel.size

        # Intersection with diamond
        sx = rel.x + ux * sz
        sy = rel.y + uy * sz

        # Intersection with entity rect
        ex, ey = self._rect_intersect(ent, ux, uy)

        double = False
        # Check if there's total participation: search connection for this pair
        for c in self.connections:
            if c.rel is rel and c.ent is ent:
                pass
        # We'll let user specify total participation implicitly

        parts = self._line(sx, sy, ex, ey, double=double)

        # Cardinality label
        card = rel.cardinalities.get(ent, "")
        if card:
            mx = (sx + ex) / 2 + uy * 12
            my = (sy + ey) / 2 - ux * 12
            parts.append(self._text(mx, my, card, self.style.font_size_card, bold=True,
                                    italic=True, color="#666"))

        return parts

    def _reflexive_lines(self, rel: Relationship, ent: Entity) -> list:
        """Two separate lines forming a self-loop (reflexive relationship)."""
        sz  = rel.size
        hw = ent.w / 2
        hh = ent.h / 2
        # Line 1: entity right-top → diamond left-bottom
        # Line 2: entity left-top  → diamond right-bottom
        off = min(hw * 0.35, 30)
        p1 = self._line(ent.x + off, ent.y - hh,
                        rel.x - sz * 0.6, rel.y + sz * 0.6)
        p2 = self._line(ent.x - off, ent.y - hh,
                        rel.x + sz * 0.6, rel.y + sz * 0.6)
        # Cardinality labels (if any)
        card = rel.cardinalities.get(ent, "")
        if card:
            s = self.style
            p1.append(self._text(ent.x + off, ent.y - hh - 12,
                                 card, s.font_size_card, bold=True, italic=True, color="#666"))
        return p1 + p2

    def _attr_line(self, parent, attr: Attr) -> list:
        """Line from entity/relationship to attribute."""
        dx = attr.x - parent.x
        dy = attr.y - parent.y
        dist = math.hypot(dx, dy) or 1
        ux = dx / dist
        uy = dy / dist

        if isinstance(parent, Entity):
            sx, sy = self._rect_intersect(parent, ux, uy)
        else:  # Relationship
            sx = parent.x + ux * parent.size
            sy = parent.y + uy * parent.size

        ex = attr.x - ux * self.style.attr_ry
        ey = attr.y - uy * self.style.attr_ry
        return self._line(sx, sy, ex, ey)

    def _rect_intersect(self, ent: Entity, ux: float, uy: float) -> tuple:
        """Intersection point of ray from entity center to its rect edge."""
        hw = ent.w / 2
        hh = ent.h / 2
        if ux == 0 and uy == 0:
            return ent.x + hw, ent.y
        tx = hw / abs(ux) if ux != 0 else float("inf")
        ty = hh / abs(uy) if uy != 0 else float("inf")
        t = min(tx, ty)
        return ent.x - ux * t, ent.y - uy * t
