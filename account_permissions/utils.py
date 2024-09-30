def has_permission(user, action, target_model):
    # Get all permission groups associated with the user
    permission_groups = user.permissions.all()

    # Check if any permission group grants the required action on the target model
    for group in permission_groups:
        if group.permissions.filter(action=action, target_model=target_model, can_execute=True).exists():
            return True
    return False
