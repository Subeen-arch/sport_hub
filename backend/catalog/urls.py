from django.urls import path
from . import views

urlpatterns = [
    path("categories/", views.CategoryListView.as_view()),
    path("products/", views.ProductListView.as_view()),
    path("products/<int:pk>/", views.ProductDetailView.as_view()),
    path("catalog/options/", views.CatalogOptionsView.as_view()),
    path("admin/products/", views.AdminProductListView.as_view()),
    path("admin/products/<int:pk>/", views.AdminProductDetailView.as_view()),
    path("admin/categories/", views.AdminCategoryListView.as_view()),
    path("admin/categories/<int:pk>/", views.AdminCategoryDetailView.as_view()),
]
