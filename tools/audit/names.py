import bpy, re, collections
bpy.ops.human_modeling.create(); k = bpy.context.object.data.shape_keys
ns = [x.name for x in k.key_blocks]
age = [n for n in ns if n.startswith("Age ·")]
print("NM age sample", age[:6], age[100:103], age[-3:])
pat = collections.Counter(re.sub(r"[a-z_0-9]+", "x", n.split(" · ")[1]) if len(n.split(" · "))>1 else "" for n in age)
print("NM age stage tokens", collections.Counter(n.split(" · ")[1] for n in age if len(n.split(" · "))>1))
print("NM hm sample", [n for n in ns if n.startswith("HM ·")][:8], [n for n in ns if n.startswith("HM ·") and "correction" in n][:3], sum("correction" in n for n in ns))
print("NM rel", collections.Counter(x.relative_key.name.split(" · ")[0] for x in k.key_blocks).most_common(4))
