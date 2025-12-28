"""
Banking views for Stripe and Plaid integrations.
"""
import stripe
from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    StripeAccount, PaymentMethod, StripePayment,
    PlaidConnection, PlaidAccount, PlaidTransaction
)
from .serializers import (
    StripeAccountSerializer, PaymentMethodSerializer, StripePaymentSerializer,
    CreatePaymentIntentSerializer, PlaidConnectionSerializer,
    PlaidAccountSerializer, PlaidTransactionSerializer,
    CategorizeTransactionSerializer, PlaidLinkTokenSerializer,
    PlaidExchangeTokenSerializer
)
from apps.payments.models import RentPayment, PaymentRecord
from apps.transactions.models import Transaction, TransactionCategory

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Stripe Connect accounts."""

    serializer_class = StripeAccountSerializer

    def get_queryset(self):
        return StripeAccount.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def connect(self, request):
        """Start Stripe Connect onboarding."""
        # Check if user already has a Stripe account
        existing = StripeAccount.objects.filter(user=request.user).first()
        if existing and existing.details_submitted:
            return Response({
                'success': False,
                'error': {'code': 'ALREADY_CONNECTED', 'message': 'Stripe account already connected'}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create or retrieve Stripe account
            if existing:
                account = stripe.Account.retrieve(existing.stripe_account_id)
            else:
                account = stripe.Account.create(
                    type='express',
                    country='US',
                    email=request.user.email,
                    capabilities={
                        'card_payments': {'requested': True},
                        'transfers': {'requested': True},
                    },
                )
                StripeAccount.objects.create(
                    user=request.user,
                    stripe_account_id=account.id,
                    account_type='express'
                )

            # Create account link for onboarding
            account_link = stripe.AccountLink.create(
                account=account.id,
                refresh_url=f"{settings.FRONTEND_URL}/settings/payments?refresh=true",
                return_url=f"{settings.FRONTEND_URL}/settings/payments?success=true",
                type='account_onboarding',
            )

            return Response({
                'success': True,
                'data': {'onboarding_url': account_link.url}
            })

        except stripe.error.StripeError as e:
            return Response({
                'success': False,
                'error': {'code': 'STRIPE_ERROR', 'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get current Stripe Connect status."""
        try:
            stripe_account = StripeAccount.objects.get(user=request.user)
            account = stripe.Account.retrieve(stripe_account.stripe_account_id)

            # Update local record
            stripe_account.charges_enabled = account.charges_enabled
            stripe_account.payouts_enabled = account.payouts_enabled
            stripe_account.details_submitted = account.details_submitted
            if account.details_submitted and not stripe_account.onboarding_completed_at:
                stripe_account.onboarding_completed_at = timezone.now()
            stripe_account.save()

            return Response({
                'success': True,
                'data': StripeAccountSerializer(stripe_account).data
            })

        except StripeAccount.DoesNotExist:
            return Response({
                'success': True,
                'data': None
            })

    @action(detail=False, methods=['get'])
    def dashboard_link(self, request):
        """Get Stripe Express dashboard link."""
        try:
            stripe_account = StripeAccount.objects.get(user=request.user)
            login_link = stripe.Account.create_login_link(stripe_account.stripe_account_id)

            return Response({
                'success': True,
                'data': {'dashboard_url': login_link.url}
            })
        except StripeAccount.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_CONNECTED', 'message': 'Stripe account not connected'}
            }, status=status.HTTP_404_NOT_FOUND)


class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for saved payment methods."""

    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        # Get payment methods for tenants associated with user's leases
        return PaymentMethod.objects.filter(
            tenant__leases__owner=self.request.user
        ).distinct()

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set a payment method as default."""
        payment_method = self.get_object()

        # Unset other defaults for this tenant
        PaymentMethod.objects.filter(
            tenant=payment_method.tenant,
            is_default=True
        ).update(is_default=False)

        payment_method.is_default = True
        payment_method.save()

        return Response({
            'success': True,
            'data': PaymentMethodSerializer(payment_method).data
        })

    @action(detail=True, methods=['delete'])
    def remove(self, request, pk=None):
        """Remove a payment method."""
        payment_method = self.get_object()

        try:
            # Detach from Stripe
            stripe.PaymentMethod.detach(payment_method.stripe_payment_method_id)
            payment_method.delete()

            return Response({
                'success': True,
                'message': 'Payment method removed'
            })
        except stripe.error.StripeError as e:
            return Response({
                'success': False,
                'error': {'code': 'STRIPE_ERROR', 'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)


class PaymentIntentView(APIView):
    """Create payment intents for rent payments."""

    def post(self, request):
        """Create a payment intent."""
        serializer = CreatePaymentIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            rent_payment = RentPayment.objects.get(
                id=data['rent_payment_id'],
                lease__owner=request.user
            )
        except RentPayment.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Rent payment not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        # Get landlord's Stripe account
        try:
            stripe_account = StripeAccount.objects.get(user=request.user)
            if not stripe_account.charges_enabled:
                return Response({
                    'success': False,
                    'error': {'code': 'PAYMENTS_NOT_ENABLED', 'message': 'Payment account not fully set up'}
                }, status=status.HTTP_400_BAD_REQUEST)
        except StripeAccount.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NO_STRIPE_ACCOUNT', 'message': 'Payment account not connected'}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Calculate amount in cents
            amount_cents = int(rent_payment.balance_due * 100)

            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                payment_method_types=['card', 'us_bank_account'],
                metadata={
                    'rent_payment_id': str(rent_payment.id),
                    'lease_id': str(rent_payment.lease.id),
                },
                transfer_data={
                    'destination': stripe_account.stripe_account_id,
                },
            )

            # Store payment record
            StripePayment.objects.create(
                rent_payment=rent_payment,
                stripe_payment_intent_id=intent.id,
                amount=rent_payment.balance_due,
                status='pending'
            )

            return Response({
                'success': True,
                'data': {
                    'client_secret': intent.client_secret,
                    'payment_intent_id': intent.id,
                    'amount': float(rent_payment.balance_due),
                }
            })

        except stripe.error.StripeError as e:
            return Response({
                'success': False,
                'error': {'code': 'STRIPE_ERROR', 'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)


class StripeWebhookView(APIView):
    """Handle Stripe webhooks."""

    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            self._handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'payment_intent.payment_failed':
            self._handle_payment_failed(event['data']['object'])
        elif event['type'] == 'account.updated':
            self._handle_account_updated(event['data']['object'])

        return Response(status=status.HTTP_200_OK)

    def _handle_payment_succeeded(self, payment_intent):
        """Handle successful payment."""
        try:
            stripe_payment = StripePayment.objects.get(
                stripe_payment_intent_id=payment_intent['id']
            )
            stripe_payment.status = 'succeeded'
            stripe_payment.stripe_charge_id = payment_intent.get('latest_charge', '')
            stripe_payment.save()

            # Record the payment
            rent_payment = stripe_payment.rent_payment
            PaymentRecord.objects.create(
                rent_payment=rent_payment,
                amount=stripe_payment.amount,
                payment_date=timezone.now().date(),
                payment_method='online',
                reference_number=payment_intent['id'],
                notes='Paid online via Stripe'
            )

            # Create income transaction
            rent_category = TransactionCategory.objects.filter(
                name__icontains='rent',
                type='income',
                is_system=True
            ).first()

            Transaction.objects.create(
                owner=rent_payment.lease.owner,
                type='income',
                category=rent_category,
                property=rent_payment.lease.rental_property,
                unit=rent_payment.lease.unit,
                tenant=rent_payment.lease.tenant,
                lease=rent_payment.lease,
                amount=stripe_payment.amount,
                date=timezone.now().date(),
                description=f"Online rent payment for {rent_payment.due_date.strftime('%B %Y')}",
                payment_method='online',
                reference_number=payment_intent['id'],
            )

        except StripePayment.DoesNotExist:
            pass

    def _handle_payment_failed(self, payment_intent):
        """Handle failed payment."""
        try:
            stripe_payment = StripePayment.objects.get(
                stripe_payment_intent_id=payment_intent['id']
            )
            stripe_payment.status = 'failed'
            stripe_payment.failure_code = payment_intent.get('last_payment_error', {}).get('code', '')
            stripe_payment.failure_message = payment_intent.get('last_payment_error', {}).get('message', '')
            stripe_payment.save()
        except StripePayment.DoesNotExist:
            pass

    def _handle_account_updated(self, account):
        """Handle Stripe Connect account updates."""
        try:
            stripe_account = StripeAccount.objects.get(stripe_account_id=account['id'])
            stripe_account.charges_enabled = account['charges_enabled']
            stripe_account.payouts_enabled = account['payouts_enabled']
            stripe_account.details_submitted = account['details_submitted']
            if account['details_submitted'] and not stripe_account.onboarding_completed_at:
                stripe_account.onboarding_completed_at = timezone.now()
            stripe_account.save()
        except StripeAccount.DoesNotExist:
            pass


class PlaidConnectionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Plaid connections."""

    serializer_class = PlaidConnectionSerializer

    def get_queryset(self):
        return PlaidConnection.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def link_token(self, request):
        """Create a Plaid Link token."""
        try:
            from plaid.api import plaid_api
            from plaid.model.link_token_create_request import LinkTokenCreateRequest
            from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
            from plaid.model.products import Products
            from plaid.model.country_code import CountryCode
            from plaid import Configuration, ApiClient

            configuration = Configuration(
                host=self._get_plaid_host(),
                api_key={
                    'clientId': settings.PLAID_CLIENT_ID,
                    'secret': settings.PLAID_SECRET,
                }
            )
            api_client = ApiClient(configuration)
            client = plaid_api.PlaidApi(api_client)

            link_request = LinkTokenCreateRequest(
                products=[Products('transactions')],
                client_name='LeaseLog',
                country_codes=[CountryCode('US')],
                language='en',
                user=LinkTokenCreateRequestUser(
                    client_user_id=str(request.user.id)
                )
            )

            response = client.link_token_create(link_request)

            return Response({
                'success': True,
                'data': {
                    'link_token': response['link_token'],
                    'expiration': response['expiration'],
                }
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': {'code': 'PLAID_ERROR', 'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def exchange_token(self, request):
        """Exchange public token for access token."""
        serializer = PlaidExchangeTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            from plaid.api import plaid_api
            from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
            from plaid import Configuration, ApiClient

            configuration = Configuration(
                host=self._get_plaid_host(),
                api_key={
                    'clientId': settings.PLAID_CLIENT_ID,
                    'secret': settings.PLAID_SECRET,
                }
            )
            api_client = ApiClient(configuration)
            client = plaid_api.PlaidApi(api_client)

            exchange_request = ItemPublicTokenExchangeRequest(
                public_token=serializer.validated_data['public_token']
            )
            response = client.item_public_token_exchange(exchange_request)

            # Get institution info
            from plaid.model.item_get_request import ItemGetRequest
            item_request = ItemGetRequest(access_token=response['access_token'])
            item_response = client.item_get(item_request)

            from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
            inst_request = InstitutionsGetByIdRequest(
                institution_id=item_response['item']['institution_id'],
                country_codes=[CountryCode('US')]
            )
            inst_response = client.institutions_get_by_id(inst_request)
            institution = inst_response['institution']

            # Create connection
            connection = PlaidConnection.objects.create(
                user=request.user,
                plaid_item_id=response['item_id'],
                plaid_access_token=response['access_token'],
                institution_id=institution['institution_id'],
                institution_name=institution['name'],
                institution_logo=institution.get('logo', ''),
            )

            # Fetch accounts
            from plaid.model.accounts_get_request import AccountsGetRequest
            accounts_request = AccountsGetRequest(access_token=response['access_token'])
            accounts_response = client.accounts_get(accounts_request)

            for account in accounts_response['accounts']:
                PlaidAccount.objects.create(
                    connection=connection,
                    plaid_account_id=account['account_id'],
                    name=account['name'],
                    official_name=account.get('official_name', ''),
                    mask=account['mask'],
                    type=account['type'],
                    subtype=account.get('subtype', 'other'),
                    current_balance=account['balances'].get('current'),
                    available_balance=account['balances'].get('available'),
                )

            return Response({
                'success': True,
                'data': PlaidConnectionSerializer(connection).data
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': {'code': 'PLAID_ERROR', 'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Sync transactions for a connection."""
        connection = self.get_object()

        try:
            from plaid.api import plaid_api
            from plaid.model.transactions_sync_request import TransactionsSyncRequest
            from plaid import Configuration, ApiClient

            configuration = Configuration(
                host=self._get_plaid_host(),
                api_key={
                    'clientId': settings.PLAID_CLIENT_ID,
                    'secret': settings.PLAID_SECRET,
                }
            )
            api_client = ApiClient(configuration)
            client = plaid_api.PlaidApi(api_client)

            has_more = True
            cursor = connection.cursor

            while has_more:
                sync_request = TransactionsSyncRequest(
                    access_token=connection.plaid_access_token,
                    cursor=cursor if cursor else None,
                )
                response = client.transactions_sync(sync_request)

                # Process added transactions
                for txn in response['added']:
                    account = PlaidAccount.objects.filter(
                        plaid_account_id=txn['account_id']
                    ).first()

                    if account and account.sync_transactions:
                        PlaidTransaction.objects.update_or_create(
                            plaid_transaction_id=txn['transaction_id'],
                            defaults={
                                'account': account,
                                'date': txn['date'],
                                'name': txn['name'],
                                'merchant_name': txn.get('merchant_name', ''),
                                'amount': txn['amount'],
                                'plaid_category': txn.get('category', []),
                                'plaid_category_id': txn.get('category_id', ''),
                                'pending': txn['pending'],
                            }
                        )

                cursor = response['next_cursor']
                has_more = response['has_more']

            connection.cursor = cursor
            connection.last_synced_at = timezone.now()
            connection.save()

            return Response({
                'success': True,
                'message': 'Transactions synced successfully'
            })

        except Exception as e:
            connection.status = 'error'
            connection.error_message = str(e)
            connection.save()

            return Response({
                'success': False,
                'error': {'code': 'PLAID_ERROR', 'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def disconnect(self, request, pk=None):
        """Disconnect a Plaid connection."""
        connection = self.get_object()

        try:
            from plaid.api import plaid_api
            from plaid.model.item_remove_request import ItemRemoveRequest
            from plaid import Configuration, ApiClient

            configuration = Configuration(
                host=self._get_plaid_host(),
                api_key={
                    'clientId': settings.PLAID_CLIENT_ID,
                    'secret': settings.PLAID_SECRET,
                }
            )
            api_client = ApiClient(configuration)
            client = plaid_api.PlaidApi(api_client)

            remove_request = ItemRemoveRequest(access_token=connection.plaid_access_token)
            client.item_remove(remove_request)

        except Exception:
            pass  # Continue with deletion even if Plaid removal fails

        connection.delete()

        return Response({
            'success': True,
            'message': 'Connection removed'
        })

    def _get_plaid_host(self):
        from plaid import Environment
        env_map = {
            'sandbox': Environment.Sandbox,
            'development': Environment.Development,
            'production': Environment.Production,
        }
        return env_map.get(settings.PLAID_ENV, Environment.Sandbox)


class PlaidAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for Plaid accounts."""

    serializer_class = PlaidAccountSerializer

    def get_queryset(self):
        return PlaidAccount.objects.filter(
            connection__user=self.request.user
        )


class PlaidTransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for Plaid transactions."""

    serializer_class = PlaidTransactionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['account', 'status']

    def get_queryset(self):
        queryset = PlaidTransaction.objects.filter(
            account__connection__user=self.request.user
        )

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        return queryset

    @action(detail=True, methods=['post'])
    def categorize(self, request, pk=None):
        """Categorize a Plaid transaction."""
        plaid_txn = self.get_object()
        serializer = CategorizeTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            category = TransactionCategory.objects.get(id=data['category_id'])
        except TransactionCategory.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Category not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        # Determine transaction type based on amount
        txn_type = 'expense' if plaid_txn.amount > 0 else 'income'

        # Create LeaseLog transaction
        transaction = Transaction.objects.create(
            owner=request.user,
            type=txn_type,
            category=category,
            property_id=data.get('property_id'),
            amount=abs(plaid_txn.amount),
            date=plaid_txn.date,
            description=data.get('description', plaid_txn.name),
            payment_method='bank_transfer',
        )

        plaid_txn.matched_transaction = transaction
        plaid_txn.status = 'categorized'
        plaid_txn.save()

        return Response({
            'success': True,
            'data': PlaidTransactionSerializer(plaid_txn).data
        })

    @action(detail=True, methods=['post'])
    def ignore(self, request, pk=None):
        """Ignore a Plaid transaction."""
        plaid_txn = self.get_object()
        plaid_txn.status = 'ignored'
        plaid_txn.save()

        return Response({
            'success': True,
            'data': PlaidTransactionSerializer(plaid_txn).data
        })
