from django.urls import path
from . import views
from . import payment_views as payments

urlpatterns = [
    path('payments/config/', payments.PaymentConfigView.as_view()),
    path('payments/khalti/initiate/', payments.InitiatePaymentView.as_view()),
    path('payments/khalti/verify/', payments.VerifyPaymentView.as_view()),
    path('payments/', payments.PaymentListView.as_view()),
    path('payments/<uuid:attempt>/', payments.PaymentDetailView.as_view()),
    path('cart/', views.CartView.as_view()),
    path('cart/clear/', views.CartClearView.as_view()),
    path('cart/<int:pk>/', views.CartDetailView.as_view()),
    path('wishlist/', views.WishlistView.as_view()),
    path('wishlist/clear/', views.WishlistClearView.as_view()),
    path('wishlist/<int:pk>/', views.WishlistDetailView.as_view()),
    path('orders/checkout/', views.CheckoutView.as_view()),
    path('orders/', views.OrderListView.as_view()),
    path('orders/<int:pk>/', views.OrderDetailView.as_view()),
    path('admin/orders/', views.AdminOrderListView.as_view()),
    path('admin/orders/<int:pk>/', views.AdminOrderDetailView.as_view()),
]
