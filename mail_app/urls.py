from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),
    path('messages/', views.messages, name='messages_list'),
    path('logout/', views.logout, name='logout'),
]