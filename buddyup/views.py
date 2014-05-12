from django.shortcuts import render


def index(request):

    return render(request, 'index.html')

def about(request):

    return render(request, 'about.html')

def tos(request):

    return render(request, 'tos.html')

def privacyPolicy(request):

    return render(request, 'privacy_policy.html')

