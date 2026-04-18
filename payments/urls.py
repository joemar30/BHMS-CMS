from django.urls import path

from payments import views

urlpatterns = [
    path('utility-bill/', views.utility_bill, name='utility-bill'),
    path('payments/', views.payments, name='payments'),
    path('payments/<int:id>/', views.payments_info, name='payments-info'),
    path('payments/transient/', views.transient, name='transient'),
    path('payments/transient/<int:id>/', views.transient_info, name='transient-info'),
    path('income/', views.income, name='income'),
    path('collectibles/', views.collectibles, name='collectibles'),
    path('online-payment/', views.online_payment, name='online-payment'),
    path('payments/stripe/create-checkout-session/', views.create_stripe_checkout_session, name='stripe-create-checkout-session'),
    path('payments/stripe/success/', views.stripe_success, name='stripe-success'),
    path('payments/stripe/cancel/', views.stripe_cancel, name='stripe-cancel'),
    ]
