"""
PayMongo integration — hosted checkout (v2) with GCash support.

Handles:
  - Creating checkout sessions for a Transaction
  - Verifying webhook signatures (HMAC-SHA256)
  - Fulfilling orders on checkout_session.payment.paid / payment.paid

Uses the REST API directly via `requests` (no SDK required).
"""
import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone as dt_timezone

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Transaction


def payments_enabled():
    """Online payments are only offered when a PayMongo key is configured."""
    return bool(settings.PAYMENTS_ENABLED)


def _api_headers():
    token = base64.b64encode(
        f'{settings.PAYMONGO_SECRET_KEY}:'.encode()
    ).decode()
    return {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json',
    }


def _line_item_name(transaction):
    """Short human-readable line item name for the checkout page."""
    label = transaction.get_tx_type_display()
    if transaction.booking:
        b = transaction.booking
        return f'{label} – {b.court} {b.date:%b %d} {b.start_time:%I:%M %p}'
    if transaction.openplay:
        p = transaction.openplay
        return f'{label} – {p.session.title}'
    return label


def _redirect_url(base_url, path):
    return f'{base_url.rstrip("/")}{path}'


def create_checkout(transaction, base_url=None):
    """
    Create (or reuse) a PayMongo hosted checkout session for a transaction.

    Returns the checkout_url. Raises ValidationError if payments are
    disabled, the transaction is not payable, or the API call fails.
    """
    if not payments_enabled():
        raise ValidationError('Online payments are not enabled.')

    if transaction.payment_status in (
        Transaction.PaymentStatus.PAID,
        Transaction.PaymentStatus.REFUNDED,
        Transaction.PaymentStatus.WAIVED,
    ):
        raise ValidationError('This transaction is not payable.')

    if transaction.amount <= 0:
        raise ValidationError('This transaction has no amount due.')

    # Reuse an in-flight checkout session if we already created one.
    if transaction.provider_checkout_id:
        try:
            resp = requests.get(
                f'{settings.PAYMONGO_API_BASE}/v1/checkout_sessions/'
                f'{transaction.provider_checkout_id}',
                headers=_api_headers(),
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()['data']['attributes']['checkout_url']
        except (requests.RequestException, KeyError, ValueError):
            pass  # stale/expired session — create a fresh one

    if not base_url:
        base_url = settings.SITE_URL
    if not base_url:
        raise ValidationError('Payment redirect URL is not configured.')

    payload = {
        'data': {
            'attributes': {
                'line_items': [{
                    'name': _line_item_name(transaction),
                    'amount': int(transaction.amount * 100),  # centavos
                    'currency': 'PHP',
                    'quantity': 1,
                }],
                'payment_method_types': ['gcash', 'card'],
                'success_url': _redirect_url(base_url, f'/transactions/{transaction.pk}/result/success/'),
                'cancel_url': _redirect_url(base_url, f'/transactions/{transaction.pk}/result/cancelled/'),
                'reference_number': str(transaction.pk),
                'metadata': {
                    'tx_id': str(transaction.pk),
                    'tx_type': transaction.tx_type,
                },
                'send_email_receipt': False,
            }
        }
    }

    try:
        resp = requests.post(
            f'{settings.PAYMONGO_API_BASE}/v2/checkout_sessions',
            headers=_api_headers(),
            data=json.dumps(payload),
            timeout=15,
        )
    except requests.RequestException as e:
        raise ValidationError(f'Could not reach payment provider: {e}')

    if resp.status_code >= 400:
        raise ValidationError(
            f'Payment provider error ({resp.status_code}). '
            f'Please try again later.'
        )

    data = resp.json()['data']
    transaction.provider = Transaction.Provider.PAYMONGO
    transaction.provider_checkout_id = data['id']
    transaction.save(update_fields=['provider', 'provider_checkout_id'])

    return data['attributes']['checkout_url']


# ── Webhooks ──────────────────────────────────────────────────────────────────

def verify_webhook_signature(payload, signature_header, secret=None):
    """
    Verify the PayMongo webhook signature.

    Header format: t=<timestamp>,te=<test sig>,li=<live sig>
    Expected HMAC: sha256(secret, "{timestamp}.{payload}") hexdigest.
    """
    if not signature_header:
        return False
    secret = secret or settings.PAYMONGO_WEBHOOK_SECRET
    if not secret:
        return False

    parts = {}
    for segment in signature_header.split(','):
        segment = segment.strip()
        if '=' in segment:
            key, _, value = segment.partition('=')
            parts[key.strip()] = value.strip()

    timestamp = parts.get('t', '')
    if not timestamp:
        return False

    # Reject replay attempts (allow ~5 min skew)
    try:
        ts_epoch = int(timestamp)
    except ValueError:
        return False
    if abs(datetime.now(dt_timezone.utc).timestamp() - ts_epoch) > 300:
        return False

    # Test-mode keys sign with `te`, live-mode keys with `li`.
    is_test = settings.PAYMONGO_SECRET_KEY.startswith('sk_test')
    signature = parts.get('te') if is_test else (parts.get('li') or parts.get('te'))
    if not signature:
        return False

    expected = hmac.new(
        secret.encode(),
        f'{timestamp}.{payload}'.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _parse_event(payload):
    """
    Normalize both webhook payload shapes into (event_type, data_dict).

    v2 hosted checkout:
        data.type = checkout_session.payment.paid
        data.data.attributes = checkout session attributes
    v1 payments:
        data.type = event
        data.attributes.type = payment.paid / payment.failed
        data.attributes.data = payment object
    """
    data = (payload or {}).get('data') or {}
    event_type = data.get('type', '')
    attributes = data.get('attributes') or {}

    if event_type == 'event':
        return attributes.get('type', ''), attributes.get('data') or {}

    if event_type in ('checkout_session.payment.paid', 'checkout_session.payment.failed'):
        return event_type, (data.get('data') or {}).get('attributes') or {}

    return event_type, {}


def handle_webhook_payload(payload):
    """
    Handle a verified webhook payload. Returns the updated Transaction
    when a payment was fulfilled, otherwise None.
    """
    event_type, data = _parse_event(payload)
    if not event_type:
        return None

    if event_type in ('checkout_session.payment.paid', 'payment.paid'):
        return _fulfill_paid(data, pay_id=payload.get('data', {}).get('id') or '')

    if event_type in ('checkout_session.payment.failed', 'payment.failed'):
        return _handle_failed(data)

    return None


def _amount_centavos(data):
    """Best-effort extraction of the paid amount (in centavos)."""
    payments = data.get('payments') or []
    if payments:
        attrs = payments[-1].get('attributes') or {}
        if attrs.get('amount') is not None:
            return int(attrs['amount'])
    if data.get('amount') is not None:
        return int(data['amount'])
    return None


def _payment_method(data):
    payments = data.get('payments') or []
    if payments:
        source = (payments[-1].get('attributes') or {}).get('source') or {}
        return source.get('type') or ''
    source = data.get('source') or {}
    return source.get('type') or ''


def _fulfill_paid(data, pay_id=''):
    """
    Mark a transaction paid and fulfill its linked order.
    Idempotent: re-delivered webhooks are no-ops.
    """
    from django.db import transaction as db_transaction

    reference_number = str(data.get('reference_number') or '')
    payments = data.get('payments') or []
    if payments:
        pay_id = pay_id or (payments[-1].get('id') or '')

    with db_transaction.atomic():
        # Idempotency #1: already recorded under this payment id?
        if pay_id:
            existing = Transaction.objects.filter(
                provider_payment_id=pay_id
            ).first()
            if existing:
                return existing

        tx = None
        if reference_number.isdigit():
            tx = Transaction.objects.filter(pk=int(reference_number)).first()
        if tx is None and pay_id:
            tx = Transaction.objects.filter(provider_checkout_id=pay_id).first()

        if tx is None:
            return None

        # Money check: never fulfill for a mismatched amount.
        paid_amount = _amount_centavos(data)
        if paid_amount is not None and paid_amount != int(tx.amount * 100):
            return None

        tx.payment_status = Transaction.PaymentStatus.PAID
        tx.provider = Transaction.Provider.PAYMONGO
        tx.payment_method = _payment_method(data) or tx.payment_method
        tx.paid_at = timezone.now()
        if pay_id:
            tx.provider_payment_id = pay_id
        tx.save()

        _fulfill_order(tx)
        return tx


def _fulfill_order(tx):
    """Apply order-level effects of a successful payment."""
    # Booking: payment confirms the booking (auto-confirm).
    if tx.booking and tx.booking.status == 'pending':
        tx.booking.status = 'confirmed'
        tx.booking.save(update_fields=['status'])

    # Open Play: payment approves the participant (pay-to-join).
    if tx.openplay and tx.openplay.status == 'pending':
        from openplay.services import approve_participant
        try:
            approve_participant(tx.openplay)
        except ValidationError:
            # Session became full before payment landed — refund and flag.
            tx.payment_status = Transaction.PaymentStatus.REFUNDED
            tx.notes = (tx.notes + '\n' if tx.notes else '') + (
                'Auto-refund: session full when payment arrived.'
            )
            tx.save()


def _handle_failed(data):
    """Failed payments leave the transaction pending so the user can retry."""
    return None
