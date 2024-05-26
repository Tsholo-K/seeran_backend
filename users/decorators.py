# django
from django.http import JsonResponse

# utility functions 


def founder_only(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.user.role == "FOUNDER":
            return JsonResponse({'error': 'permission denied'})

        response = view_func(request, *args, **kwargs)
        
        return response
    return _wrapped_view_func


def admins_only(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if request.user.role != "ADMIN" or request.user.role != "PRINCIPAL" :
            return JsonResponse({'error': 'permission denied'})

        response = view_func(request, *args, **kwargs)
        
        return response
    return _wrapped_view_func