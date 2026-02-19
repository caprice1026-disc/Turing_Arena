from django.shortcuts import render


def home_view(request):
    return render(request, "pages/home.html")


def transparency_view(request):
    return render(request, "pages/transparency.html")

# Create your views here.
