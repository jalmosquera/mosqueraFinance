from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.csrf, name="auth-csrf"),
    path("auth/login/", views.login_view, name="auth-login"),
    path("auth/me/", views.current_user, name="auth-me"),
    path("auth/logout/", views.logout_view, name="auth-logout"),
]
