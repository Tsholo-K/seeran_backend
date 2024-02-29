from django.http import JsonResponse
from django.shortcuts import render
import json


# Create your views here.
def login(request):
    if request.method == 'POST':
        user_data = json.loads(request.body)
        if user_data.get('email') == 'lethabo.mochaki1076@icloud.com' & user_data.get('email') == 'lethabo.mochaki1076@icloud.com':
            return JsonResponse('authenticated')
        else:
            return JsonResponse('invalid user')