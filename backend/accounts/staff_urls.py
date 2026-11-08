from django.urls import path
from . import staff_views as views

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view()),
    path('users/', views.UserListView.as_view()),
    path('users/<int:pk>/', views.UserDeleteView.as_view()),
    path('accounts/', views.StaffListView.as_view()),
    path('accounts/<int:pk>/', views.StaffDeleteView.as_view()),
    path('messages/', views.MessageListView.as_view()),
    path('messages/<int:pk>/', views.MessageDeleteView.as_view()),
]
