from django.http import JsonResponse
from django.shortcuts import render


def landing(request):
    return render(request, "core/landing.html")


def health_check(request):
    return JsonResponse({"status": "ok", "service": "CampusFix"})


def custom_404(request, exception):
    return render(request, "404.html", status=404)


def custom_403(request, exception=None):
    return render(request, "403.html", status=403)
