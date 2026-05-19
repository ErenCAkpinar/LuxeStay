from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import LoginForm, SignupForm


def account_context(request):
    if not request.user.is_authenticated:
        return {}

    full_name = request.user.get_full_name().strip()
    account_name = full_name or request.user.email or request.user.username
    initials_source = full_name or request.user.email or request.user.username
    initials = "".join(part[0] for part in initials_source.split()[:2]).upper()
    if not initials:
        initials = request.user.username[:2].upper()

    return {
        "account_name": account_name,
        "account_first_name": request.user.first_name or account_name.split()[0],
        "account_initials": initials,
    }


def page(template_name, require_login=False):
    def view(request):
        return render(request, template_name, account_context(request))

    if require_login:
        return login_required(view)
    return view


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard")

    return render(request, "auth/html/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        if not form.cleaned_data.get("remember"):
            request.session.set_expiry(0)
        next_url = request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
        ):
            return redirect(next_url)
        return redirect(reverse("dashboard"))

    return render(request, "auth/html/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")
