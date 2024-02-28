from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

# Create your views here.
def homepage(reguest):
    return JsonResponse('hello', safe=False)