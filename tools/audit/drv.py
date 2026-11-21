import bpy, re, collections, json
bpy.ops.human_modeling.create(); b = bpy.context.object; k = b.data.shape_keys
exprs = collections.Counter(); vars_n = collections.Counter(); targets = collections.Counter(); ex_by = {}
for d in k.animation_data.drivers:
    dr = d.driver; e = dr.expression
    tmpl = re.sub(r"\b[a-z_]+\b", lambda m: m.group(0) if m.group(0) in ("max","min","abs","amount","fat","bulk","stage","sex") else "v", e)
    exprs[e] += 1; vars_n[len(dr.variables)] += 1
    for v in dr.variables: targets[(v.targets[0].id_type, v.targets[0].data_path.split('"')[1] if '"' in v.targets[0].data_path else v.targets[0].data_path)] += 1
    ex_by.setdefault(e, d.data_path)
print("DRV total", len(k.animation_data.drivers), "unique expressions", len(exprs))
for e, n in exprs.most_common(14): print("DRV expr x%d: %s" % (n, e[:170]))
print("DRV variables-per-driver", dict(vars_n))
print("DRV distinct target props", len(targets), "id types", set(t[0] for t in targets))
print("DRV top targets", [(t, n) for t, n in targets.most_common(8)])
# example age driver
for d in k.animation_data.drivers:
    if "Age · Enfant · HM · waist\"]" in d.data_path or "Enfant · HM · waist" in d.data_path:
        print("DRV example", d.data_path, "|", d.driver.expression[:200], "|", [(v.name, v.targets[0].data_path) for v in d.driver.variables]); break
