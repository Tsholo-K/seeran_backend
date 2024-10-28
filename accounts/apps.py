from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    """
        users.signals is imported in the ready method of MyAppConfig. 
        The ready method is called when Django starts and after all models have been loaded, 
        so it`s a good place to import your signal receivers
    """
    # def ready(self):
    #     import accounts.signals