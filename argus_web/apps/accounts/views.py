from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import redirect, render


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("programs:list")
    else:
        form = UserCreationForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def me(request):
    return JsonResponse({
        "username": request.user.username,
        "email": request.user.email,
        "is_staff": request.user.is_staff,
        "programs_count": request.user.programs.count(),
    })
