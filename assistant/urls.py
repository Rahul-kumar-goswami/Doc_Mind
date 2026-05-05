from django.urls import path
from . import views

app_name = 'assistant'

urlpatterns = [
    path('', views.index, name='index'),
    path('ask/', views.ask, name='ask'),
    path('reset/', views.reset, name='reset'),
    path('delete-session/', views.delete_session, name='delete_session'),

    # Auth URLs
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('otp/', views.otp_verify, name='otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-otp/', views.reset_otp_verify, name='reset_otp'),
    path('refresh-captcha/', views.refresh_captcha, name='refresh_captcha'),
    path('logout/', views.logout_view, name='logout'),
]

