from django.apps import AppConfig


class SchoolsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'schools'

    """
        schools.signals is imported in the ready method of MyAppConfig. 
        The ready method is called when Django starts and after all models have been loaded, 
        so it`s a good place to import your signal receivers
    """
    # def ready(self):
    #     import schools.signals