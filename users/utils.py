# mappings
from users.maps import role_specific_maps

def get_account_and_its_school(user, role):
    Model = role_specific_maps.account_access_control_mapping.get(role)
    return Model.objects.select_related('school').only('school').get(account_id=user)