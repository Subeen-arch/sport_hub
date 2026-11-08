from decimal import Decimal

from django.db import connection, transaction, IntegrityError
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError, PermissionDenied

from catalog.models import Product
from catalog.services import CatalogService
from commerce.models import Order, InventoryReservation
from support.models import ContactMessage
from .models import User
from .services import AccountService


class StaffAccountService(AccountService):
    def lock_staff(self):
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [73482002])
        if not User.objects.filter(pk=self.request.user.pk, is_staff=True, is_active=True).exists():
            raise PermissionDenied('Your staff account is no longer active.')

    @transaction.atomic
    def create_staff(self, data):
        self.lock_staff()
        user = User(username=data['username'], name=data['name'], email=data['email'], is_staff=True)
        self._validate_password(user, data['password'], data['password_confirm'], 'password')
        user.set_password(data['password'])
        try:
            with transaction.atomic():
                user.save()
        except IntegrityError as exc:
            self._identity_conflict(exc)
        return user

    @transaction.atomic
    def delete_user(self, pk, staff=False):
        CatalogService()._lock_catalog()
        self.lock_staff()
        user = get_object_or_404(User.objects.select_for_update(), pk=pk, is_staff=staff)
        if user.pk == self.request.user.pk:
            raise ValidationError({'detail': 'You cannot delete your own account.'})
        if staff and user.is_active and User.objects.filter(is_staff=True, is_active=True).count() <= 1:
            raise ValidationError({'detail': 'The last active staff account cannot be deleted.'})
        if InventoryReservation.objects.filter(payment__user=user, status='active').exists():
            raise ValidationError({'detail': 'This account has active payment reservations. Resolve them before deleting it.'})
        user.delete()


class DashboardService:
    def summary(self):
        pending = Order.objects.exclude(fulfillment_status='completed').aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        completed = Order.objects.filter(fulfillment_status='completed').aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        return dict(pending_total=format(pending, '.2f'), completed_total=format(completed, '.2f'), order_count=Order.objects.count(), product_count=Product.objects.count(), customer_count=User.objects.filter(is_staff=False).count(), admin_count=User.objects.filter(is_staff=True).count(), message_count=ContactMessage.objects.count(), featured_count=Product.objects.filter(featured=True).count())
