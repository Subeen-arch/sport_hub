"""Khalti HTTP boundary: no automatic initiation retry and no redirect following."""
from urllib.parse import urlsplit, parse_qs

import requests
from django.conf import settings
from rest_framework.exceptions import APIException


class PaymentUnavailable(APIException):
    status_code = 503
    default_detail = 'Khalti is currently unavailable. Please use cash on delivery or try again later.'


class GatewayError(Exception):
    def __init__(self, code, definitive=False):
        self.code = code
        self.definitive = definitive
        super().__init__(code)


def frontend_url():
    value = settings.FRONTEND_URL
    parsed = urlsplit(value)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise PaymentUnavailable()
    if parsed.scheme != 'https' and not (settings.KHALTI_ENV == 'sandbox' and parsed.scheme == 'http' and parsed.hostname in {'localhost', '127.0.0.1'}):
        raise PaymentUnavailable()
    return value.rstrip('/')


def configured():
    if not settings.KHALTI_SECRET_KEY.strip():
        return False
    try:
        frontend_url()
    except PaymentUnavailable:
        return False
    return True


def valid_payment_url(value, pidx, environment):
    if not isinstance(value, str) or len(value) > 1000:
        return False
    try:
        url = urlsplit(value)
        expected = 'test-pay.khalti.com' if environment == 'sandbox' else 'pay.khalti.com'
        return (url.scheme == 'https' and url.hostname == expected and url.port in {None, 443}
                and not url.username and not url.password and not url.fragment
                and '\\' not in value and not any(ord(c) < 32 for c in value)
                and parse_qs(url.query).get('pidx') == [pidx])
    except ValueError:
        return False


class KhaltiClient:
    def __init__(self, environment=None):
        self.environment = environment or settings.KHALTI_ENV
        if not configured() or self.environment != settings.KHALTI_ENV:
            raise PaymentUnavailable()
        self.base_url = 'https://dev.khalti.com/api/v2' if self.environment == 'sandbox' else 'https://khalti.com/api/v2'

    def _post(self, endpoint, payload):
        try:
            response = requests.post(f'{self.base_url}/epayment/{endpoint}/', json=payload,
                                     headers={'Authorization': f'Key {settings.KHALTI_SECRET_KEY}', 'Accept': 'application/json'},
                                     timeout=(5, 15), allow_redirects=False)
        except requests.RequestException as exc:
            raise GatewayError('connection_error') from exc
        try:
            body = response.json()
        except ValueError as exc:
            raise GatewayError('invalid_response') from exc
        if not isinstance(body, dict):
            raise GatewayError('invalid_response')
        # Khalti documents HTTP 400 for Expired/User canceled lookups. These are
        # status responses, but every identity/amount is still checked by the service.
        lookup_status = endpoint == 'lookup' and response.status_code == 400 and body.get('status') in {'Expired', 'User canceled', 'Failed'}
        if response.status_code != 200 and not lookup_status:
            definitive = endpoint == 'initiate' and response.status_code in {400, 401, 403, 422, 429}
            raise GatewayError('initiation_rejected' if definitive else 'gateway_error', definitive=definitive)
        return body

    def initiate(self, payment):
        delivery = payment.checkout_snapshot['delivery']
        origin = frontend_url()
        return self._post('initiate', {
            'return_url': f'{origin}/payment/return?attempt={payment.purchase_order_id}',
            'website_url': origin,
            'amount': payment.amount_paisa,
            'purchase_order_id': str(payment.purchase_order_id),
            'purchase_order_name': f'SportHub {payment.purchase_order_id}',
            'customer_info': {key: delivery[key] for key in ('name', 'email', 'phone')},
        })

    def lookup(self, pidx):
        return self._post('lookup', {'pidx': pidx})
