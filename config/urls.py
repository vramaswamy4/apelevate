"""APElevate URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from APE.views import home_page, log_in, create_a_class, create_a_class2, create_a_class3, sign_up, logout_page, forgot_password, std_dashboard, men_dashboard, enrol_page, class_info, joined_classes, my_classes, mentor_application, applications, purchase_tokens, payment_portal, payment_complete, enrol_page_filtered, accept, reject

from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_page, name='home'),
    path('login/', log_in, name='login'),
    path('logout/', logout_page, name='logout'),
    path('signup/', sign_up, name='signup'),
    path('create-a-class/', create_a_class, name='create_a_class'),
    path('create-a-class2/', create_a_class2, name='create_a_class2'),
    path('create-a-class3/', create_a_class3, name='create_a_class3'),
    path('forgot/', forgot_password, name='forgot'),
    path('student-dashboard/', std_dashboard, name='std_dashboard'),
    path('mentor-dashboard/', men_dashboard, name='men_dashboard'),
    path('classes/', enrol_page, name='enrol'),
    path('classes-filtered/', enrol_page_filtered, name='enrol-filtered'),
    path('purchase-tokens/', purchase_tokens, name='purchase'),
    path('purchase-tokens/payment_portal/<int:cost>', payment_portal, name='payment_portal'),
    path('payment-complete/<int:cost>', payment_complete, name='payment-complete'),
    path('classes/class-info/<int:id>', class_info, name='class-info'),
    path('joined-classes/', joined_classes, name='joined'),
    path('my-classes/', my_classes, name='my_classes'),
    path('mentor-applications/', mentor_application, name='mentor_apps'),
    path('applications/', applications, name='applications'),
    path('applications/accept/<int:id>', accept, name='accept'),
    path('applications/reject/<int:id>', reject, name='reject'),

    path("reset_password/", auth_views.PasswordResetView.as_view(template_name = "password_reset.html"), name = 'reset_password'),
    path("reset_password_sent/", auth_views.PasswordResetDoneView.as_view(template_name = "password_reset_sent.html"), name='password_reset_done'),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name = "password_reset_confirm.html"), name='password_reset_confirm'),
    path("reset_password_complete/", auth_views.PasswordResetCompleteView.as_view(template_name = "password_reset_complete.html"), name='password_reset_complete'),
]
