from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from rest_framework.exceptions import APIException

from commerce.models import Payment
from commerce.payment_services import PaymentService


class Command(BaseCommand):
    help = 'Look up unresolved Khalti payments; release stock only after provider-confirmed terminal status.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)
        parser.add_argument('--include-settled', action='store_true', help='Also check settled payments for refunds.')

    def handle(self, *args, **options):
        if not 1 <= options['limit'] <= 1000:
            raise CommandError('--limit must be between 1 and 1000.')
        payments = Payment.objects.all()
        if not options['include_settled']:
            payments = payments.filter(Q(status__in=['Initiated', 'Pending', 'Partially refunded']) | Q(needs_review=True))
        for payment in payments.order_by('updated_at')[:options['limit']]:
            if not payment.pidx:
                self.stdout.write(f'{payment.purchase_order_id}: missing provider identifier; merchant investigation required')
                continue
            try:
                result = PaymentService().reconcile(payment)
            except APIException:
                self.stderr.write(f'{payment.purchase_order_id}: lookup unavailable; reservation retained')
                continue
            self.stdout.write(f'{result.purchase_order_id}: {result.status}; review={result.needs_review}; order={result.order_id or "none"}')
