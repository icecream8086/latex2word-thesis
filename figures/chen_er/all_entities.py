#!/usr/bin/env python3
"""
生成所有数据表实体的 Chen 式 ER 图（单实体 + 属性）。
每个图仅展示单个实体及其属性，用于论文逻辑结构设计小节。

用法:
  python figures/chen_er/all_entities.py            # 直接运行
  python convert_chen_er.py -f figures/chen_er/all_entities.py  # 通过编译工具
"""
import os, sys, math
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_script_dir))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from chen_er import Diagram, Attr, Style


def render_entity(dia: Diagram, name: str, attrs: list, out_name: str):
    """渲染单个实体 ER 图并保存为 SVG."""
    ent = dia.entity(name, attrs=attrs)
    ent.autosize(dia.style)
    dia._layout_attrs(ent)
    dia._centerize()
    bounds = dia._calc_bounds()
    dia._svg_w = max(int(bounds[2] + dia.style.padding), 500)
    dia._svg_h = max(int(bounds[3] + dia.style.padding), 350)
    out_path = os.path.join(_script_dir, f"{out_name}.svg")
    svg = dia._generate_svg()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"  SVG 已生成: {out_path}")
    dia.render_drawio(os.path.join(_script_dir, f"{out_name}.drawio"), do_layout=False)


# ── 1. 用户 ──────────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "用户", [
    Attr("用户ID", key=True),
    Attr("用户名"),
    Attr("密码哈希"),
    Attr("用户全名"),
    Attr("邮箱"),
    Attr("手机号"),
    Attr("是否总管理员"),
    Attr("是否仓储管理员"),
    Attr("是否医生管理员"),
    Attr("是否客户管理员"),
    Attr("最后登录时间", derived=True),
    Attr("登录尝试次数"),
    Attr("账户锁定截止时间"),
    Attr("创建时间"),
    Attr("更新时间"),
], "entity_user")

# ── 2. 客户 ──────────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "客户", [
    Attr("客户ID", key=True),
    Attr("客户姓名"),
    Attr("联系电话"),
    Attr("邮箱"),
    Attr("密码哈希"),
    Attr("邮箱已验证"),
    Attr("验证令牌"),
    Attr("重置令牌"),
    Attr("重置令牌过期时间"),
    Attr("最后登录时间", derived=True),
    Attr("登录尝试次数"),
    Attr("账户锁定截止时间"),
    Attr("是否激活"),
    Attr("创建时间"),
    Attr("更新时间"),
], "entity_customer")

# ── 3. 宠物 ──────────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "宠物", [
    Attr("宠物ID", key=True),
    Attr("客户ID"),
    Attr("宠物类型ID"),
    Attr("宠物名称"),
    Attr("品种"),
    Attr("出生日期"),
    Attr("性别"),
    Attr("颜色"),
    Attr("体重"),
    Attr("头像URL"),
    Attr("备注"),
    Attr("创建时间"),
    Attr("更新时间"),
], "entity_pet")

# ── 4. 宠物类型 ──────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "宠物类型", [
    Attr("类型ID", key=True),
    Attr("类型名称"),
    Attr("描述"),
], "entity_pet_type")

# ── 5. 医生 ──────────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "医生", [
    Attr("医生ID", key=True),
    Attr("关联用户ID"),
    Attr("医生姓名"),
    Attr("专业领域"),
    Attr("执业证书编号"),
    Attr("联系电话"),
    Attr("邮箱"),
    Attr("头像URL"),
    Attr("是否在职"),
    Attr("备注"),
    Attr("创建时间"),
    Attr("更新时间"),
], "entity_doctor")

# ── 6. 预约 ──────────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "预约", [
    Attr("预约ID", key=True),
    Attr("客户ID"),
    Attr("宠物ID"),
    Attr("医生ID"),
    Attr("预约日期"),
    Attr("开始时间"),
    Attr("结束时间"),
    Attr("状态"),
    Attr("服务类型"),
    Attr("关联病例ID"),
    Attr("备注"),
    Attr("创建时间"),
    Attr("更新时间"),
], "entity_appointment")

# ── 7. 病例 ──────────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "病例", [
    Attr("病例ID", key=True),
    Attr("宠物ID"),
    Attr("医生ID"),
    Attr("就诊日期"),
    Attr("就诊时间"),
    Attr("症状描述"),
    Attr("诊断结果"),
    Attr("治疗方案"),
    Attr("状态"),
    Attr("总金额"),
    Attr("下一病例ID"),
    Attr("创建时间"),
    Attr("更新时间"),
], "entity_medical_case")

# ── 8. 药品 ──────────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "药品", [
    Attr("药品ID", key=True),
    Attr("分类ID"),
    Attr("药品名称"),
    Attr("SKU编码"),
    Attr("规格"),
    Attr("厂家"),
    Attr("单价"),
    Attr("描述"),
    Attr("创建时间"),
    Attr("更新时间"),
], "entity_medicine")

# ── 9. 器械 ──────────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "器械", [
    Attr("器械ID", key=True),
    Attr("分类ID"),
    Attr("器械名称"),
    Attr("SKU编码"),
    Attr("规格"),
    Attr("厂家"),
    Attr("单价"),
    Attr("描述"),
    Attr("创建时间"),
    Attr("更新时间"),
], "entity_equipment")

# ── 10. 药品分类 ─────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "药品分类", [
    Attr("分类ID", key=True),
    Attr("分类名称"),
    Attr("父分类ID"),
    Attr("描述"),
], "entity_medicine_category")

# ── 11. 器械分类 ────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "器械分类", [
    Attr("分类ID", key=True),
    Attr("分类名称"),
    Attr("父分类ID"),
    Attr("描述"),
], "entity_equipment_category")

# ── 12. 库存 ────────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "库存", [
    Attr("库存ID", key=True),
    Attr("物品ID"),
    Attr("物品类型"),
    Attr("当前数量"),
    Attr("预警阈值"),
    Attr("创建时间"),
    Attr("更新时间"),
], "entity_inventory")

# ── 13. 库存交易 ────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "库存交易", [
    Attr("交易ID", key=True),
    Attr("库存ID"),
    Attr("交易类型"),
    Attr("数量变化"),
    Attr("关联病例ID"),
    Attr("备注"),
    Attr("创建时间"),
], "entity_inventory_transaction")

# ── 14. 排班 ────────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "排班", [
    Attr("排班ID", key=True),
    Attr("医生ID"),
    Attr("排班日期"),
    Attr("开始时间"),
    Attr("结束时间"),
    Attr("是否可用"),
    Attr("创建时间"),
    Attr("更新时间"),
], "entity_schedule")

# ── 15. 排班模板 ────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "排班模板", [
    Attr("模板ID", key=True),
    Attr("模板名称"),
    Attr("星期几"),
    Attr("开始时间"),
    Attr("结束时间"),
    Attr("创建时间"),
], "entity_schedule_template")

# ── 16. 实体图片 ────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "实体图片", [
    Attr("图片ID", key=True),
    Attr("实体类型"),
    Attr("实体ID"),
    Attr("文件路径"),
    Attr("是否主图"),
    Attr("文件名"),
    Attr("文件大小"),
    Attr("MIME类型"),
    Attr("创建时间"),
], "entity_image")

# ── 17. 存储配置 ────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "存储配置", [
    Attr("配置ID", key=True),
    Attr("配置名称"),
    Attr("存储类型"),
    Attr("访问密钥"),
    Attr("密钥密码"),
    Attr("端点URL"),
    Attr("存储路径"),
    Attr("是否启用"),
], "entity_storage_config")

# ── 18. 角色 ────────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "角色", [
    Attr("角色ID", key=True),
    Attr("角色名"),
    Attr("角色描述"),
], "entity_role")

# ── 19. 权限 ────────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "权限", [
    Attr("权限ID", key=True),
    Attr("权限标识"),
    Attr("权限名称"),
], "entity_permission")

# ── 20. 操作日志 ────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "操作日志", [
    Attr("日志ID", key=True),
    Attr("操作类型"),
    Attr("操作详情"),
    Attr("操作时间"),
], "entity_operation_log")

# ── 21. 医生请假 ────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "医生请假", [
    Attr("请假ID", key=True),
    Attr("医生ID"),
    Attr("开始日期"),
    Attr("结束日期"),
    Attr("请假原因"),
    Attr("审核状态"),
    Attr("创建时间"),
    Attr("更新时间"),
], "entity_doctor_leave")

# ── 22. 医生证书 ────────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "医生证书", [
    Attr("证书ID", key=True),
    Attr("医生ID"),
    Attr("证书名称"),
    Attr("文件路径"),
    Attr("是否可见"),
    Attr("创建时间"),
], "entity_doctor_certificate")

# ── 23. 病例药品明细 ────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "病例药品明细", [
    Attr("明细ID", key=True),
    Attr("病例ID"),
    Attr("药品ID"),
    Attr("数量"),
    Attr("单价"),
    Attr("备注"),
], "entity_case_medicine")

# ── 24. 病例器械明细 ────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "病例器械明细", [
    Attr("明细ID", key=True),
    Attr("病例ID"),
    Attr("器械ID"),
    Attr("数量"),
    Attr("单价"),
    Attr("备注"),
], "entity_case_equipment")

# ── 25. 病例服务明细 ────────────────────────────────────────────
dia = Diagram()
render_entity(dia, "病例服务明细", [
    Attr("明细ID", key=True),
    Attr("病例ID"),
    Attr("服务名称"),
    Attr("数量"),
    Attr("单价"),
    Attr("备注"),
], "entity_case_service")

print("所有实体 ER 图已生成完毕。")
