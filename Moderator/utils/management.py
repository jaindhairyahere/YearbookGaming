from utils.choices import GroupPermissions

def add_permissions_to_group(app_config, apps, **kwargs):
    Permission = apps.get_model('app_admin', 'Permission')
    Group = apps.get_model('auth', 'Group')
    
    groups = list(Group.objects.all())
    for group in groups:
        group_perms = getattr(GroupPermissions, group.name)
        for group_perm in group_perms:
            perms = Permission.get_permission_objects(*group_perms)
            for perm in perms:
                group.permissions.add(perm)
        group.save()
            
def create_permissions(app_config, apps, **kwargs):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('app_admin', 'Permission')
    ctypes = set()
    searched_perms = []
    
    for model_name in getattr(app_config, "permission_models", []):
        model = app_config.get_model(model_name, require_ready=False)
        ctype = ContentType.objects.get_for_model(model, for_concrete_model=False)
        ctypes.add(ctype)
        for field_name in getattr(model, "permission_fields", []):
            for action in app_config.actions:
                codename = f"{model_name}|{action}|{field_name}"
                name = f"{action.capitalize()} {app_config.name}.{model_name}.{field_name}"
                perm = (codename, name)
                searched_perms.append((ctype, perm))
                    
    # Find all the Permissions that have a content_type for a model we're
    # looking for.  We don't need to check for codenames since we already have
    # a list of the ones we're going to create.
    all_perms = set(Permission.objects.filter(
        content_type__in=ctypes,
    ).values_list(
        "content_type", "codename"
    ))

    perms = [
        Permission(codename=codename, name=name, content_type=ct)
        for ct, (codename, name) in searched_perms
        if (ct.pk, codename) not in all_perms
    ]
    Permission.objects.bulk_create(perms)