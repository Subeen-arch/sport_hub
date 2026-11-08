from django.urls import path
from . import views

urlpatterns = [
    path('outlets/', views.PublicShops.as_view()),
    path('outlets/graph/', views.PublicGraph.as_view()),
    path('admin/outlets/', views.StaffShops.as_view()),
    path('admin/outlets/<int:pk>/', views.StaffShop.as_view()),
    path('admin/map-nodes/', views.StaffNodes.as_view()),
    path('admin/map-nodes/<int:pk>/', views.StaffNode.as_view()),
    path('admin/map-edges/', views.StaffEdges.as_view()),
    path('admin/map-edges/<int:pk>/', views.StaffEdge.as_view()),
]
