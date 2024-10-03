def has_permission(account, action, target_model):
    print('çhecking permissions..')
    try:
        # Check if any permission group grants the required action on the target model
        if account.permissions.filter(permissions__action=action, permissions__target_model=target_model, permissions__can_execute=True).exists():
            return True
        return False
    
    except Exception as e:
        return {'error': str(e)}


