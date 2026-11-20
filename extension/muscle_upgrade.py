"""Refresh managed legacy muscle drivers when appending the regional revision."""

PREFIXES=('HM · muscles_', 'HM · whole_body ·', 'HM · anatomical_')

def snapshot(driver):
    variables=[]
    for var in driver.variables:
        if var.type!='SINGLE_PROP':
            raise ValueError('Un driver musculaire utilise une variable personnalisée incompatible avec cette mise à jour.')
        target=var.targets[0]
        variables.append((var.name,target.id_type,target.id,target.data_path))
    return driver.type,driver.expression,driver.use_self,variables

def apply(driver,state,source_owner=None,target_owner=None):
    kind,expression,use_self,variables=state
    for var in tuple(driver.variables):driver.variables.remove(var)
    driver.type=kind;driver.use_self=use_self
    for name,id_type,owner,path in variables:
        var=driver.variables.new();var.name=name;var.type='SINGLE_PROP'
        var.targets[0].id_type=id_type
        var.targets[0].id=target_owner if source_owner is not None and owner==source_owner else owner
        var.targets[0].data_path=path
    driver.expression=expression

def refresh(body,source,existing_names):
    owner=body.data.shape_keys;original=source.data.shape_keys;plan=[]
    curves={curve.data_path:curve for curve in owner.animation_data.drivers} if owner.animation_data else {}
    for curve in original.animation_data.drivers:
        key=next((key for key in original.key_blocks if key.path_from_id('value')==curve.data_path),None)
        if key is None or key.name not in existing_names or not key.name.startswith(PREFIXES):continue
        current=curves.get(curve.data_path)
        plan.append((key.name,snapshot(current.driver) if current else None,snapshot(curve.driver)))
    backups=[]
    try:
        for name,previous,replacement in plan:
            backups.append((name,previous))
            apply(owner.key_blocks[name].driver_add('value').driver,replacement,original,owner)
    except Exception:
        rollback(body,backups)
        raise
    return backups

def rollback(body,backups):
    for name,state in reversed(backups):
        key=body.data.shape_keys.key_blocks.get(name)
        if key is None:continue
        if state is None:key.driver_remove('value')
        else:apply(key.driver_add('value').driver,state)
