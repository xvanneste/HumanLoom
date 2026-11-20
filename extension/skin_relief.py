"""Attach original age-driven geometric skin detail to the indexed base."""
NAME='Human Modeling · Relief de peau'
GROUP='HM · Relief visage'


def attach(body, source):
    if body.modifiers.get(NAME):return False
    original=source.modifiers.get(NAME)
    if original is None:return False
    if body.vertex_groups.get(GROUP):
        raise ValueError('Un groupe du même nom existe déjà sur ce personnage.')
    group=body.vertex_groups.new(name=GROUP)
    modifier=None
    try:
        index=source.vertex_groups[GROUP].index
        for vertex in source.data.vertices:
            weight=next((g.weight for g in vertex.groups if g.group==index),0.)
            if weight:group.add([vertex.index],weight,'REPLACE')
        modifier=body.modifiers.new(NAME,'DISPLACE')
        for attribute in ('texture','texture_coords','uv_layer','mid_level','vertex_group'):
            setattr(modifier,attribute,getattr(original,attribute))
        driver=modifier.driver_add('strength').driver
        driver.type='SCRIPTED'
        for name,path in (('stage','["human_modeling_age"]'),('amount','["hm_skin_relief"]')):
            variable=driver.variables.new();variable.name=name;variable.type='SINGLE_PROP'
            variable.targets[0].id_type='KEY';variable.targets[0].id=body.data.shape_keys;variable.targets[0].data_path=path
        driver.expression='max(0,stage-2)*.002*(1+amount)'
        return True
    except Exception:
        if modifier:body.modifiers.remove(modifier)
        body.vertex_groups.remove(group)
        raise
