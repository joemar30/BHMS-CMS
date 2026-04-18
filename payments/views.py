from datetime import datetime, timedelta
import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect

from boardinghouse.models import Room
from homepage.models import Feedback, Notice
from payments.forms import BillsForm, PaymentsForm, TransientPaymentForm
from payments.models import Bills, Payments, TransientPayment
from tenants.models import Tenant
from dateutil.relativedelta import relativedelta


# Create your views here.

@user_passes_test(lambda u: u.is_staff)
def utility_bill(request):
    if request.user.is_superuser:
        rooms = Room.objects.all()
        bills = Bills.objects.all()
        form_room = Room.objects.filter(is_archive=False)
    else:
        rooms = Room.objects.filter(boardinghouse__owner=request.user)
        bills = Bills.objects.filter(room__boardinghouse__owner=request.user)
        form_room = Room.objects.filter(boardinghouse__owner=request.user, is_archive=False)
    
    # Clear notifications for bills
    bills.update(is_viewed=True)

    if request.method == "POST":
        if "button" in request.POST:
            if request.POST.get("button") == "add_utility":
                form = BillsForm(request.POST)
                if form.is_valid():
                    form = form.save(commit=False)
                    form.room = Room.objects.get(id=request.POST.get('room'))
                    form.save()
                    messages.success(request, 'Utility bill added successfully')
                    return redirect('utility-bill')
                else:
                    messages.error(request, 'Error adding utility bill')
                    return redirect('utility-bill')
            elif request.POST.get("button") == "delete_utility":
                try:
                    bill = Bills.objects.get(id=request.POST.get('id_delete'))
                    bill.delete()
                    messages.success(request, 'Utility bill deleted successfully')
                    return redirect('utility-bill')
                except:
                    messages.error(request, 'Error deleting utility bill')
                    return redirect('utility-bill')
            elif request.POST.get("button") == "edit_utility":
                try:
                    print("request.POST.get('id_bills'", request.POST.get('id_bills'))
                    room = Room.objects.get(id=request.POST.get('edit_room'))
                    bill = Bills.objects.get(id=request.POST.get('edit_id'))
                    bill.room = room
                    bill.bills = request.POST.get('bills')
                    bill.rate = request.POST.get('edit_rate')
                    bill.save()
                    messages.success(request, 'Utility bill edited successfully')
                    return redirect('utility-bill')
                except Exception as e:
                    messages.error(request, 'Error editing utility bill')
                    print(e)
                    return redirect('utility-bill')
    else:
        form = BillsForm()

    return render(request, 'payments/utility-bill.html',{
        'rooms': rooms,
        'form': form,
        'bills': bills,
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
        'form_room': form_room,

    })


@login_required(login_url='login')
def payments(request):
    if request.user.is_superuser:
        return redirect('dashboard')
    tenant = None
    payments = Payments.objects.none()
    if request.user.is_staff:
        payments = Payments.objects.filter(room__boardinghouse__owner=request.user).order_by('-date')
    else:
        try:
            tenant = Tenant.objects.get(name=request.user)
            payments = Payments.objects.filter(tenant=tenant).order_by('-date')
        except Tenant.DoesNotExist:
            messages.warning(request, "Please connect your account to a Tenant profile to view payments.")
    
    # Clear notifications for payments
    if payments.exists():
        payments.update(is_viewed=True)
    
    form_tenant = Tenant.objects.filter(owner=request.user, is_archive=False) if request.user.is_staff else None
    form_room = Room.objects.filter(boardinghouse__owner=request.user, is_archive=False) if request.user.is_staff else None

    if request.method == "POST":
        if "button" in request.POST:
            if request.POST.get("button") == 'add_payment':
                form = PaymentsForm(request.POST)
                if form.is_valid():
                    form = form.save(commit=False)
                    form.tenant = Tenant.objects.get(id=request.POST.get('tenant'))
                    form.room = form.tenant.room
                    form.save()
                    messages.success(request, 'Payment added successfully')
                    return redirect('payments')
                else:
                    messages.error(request, 'Error adding payment')
                    return redirect('payments')
            elif request.POST.get("button") == 'delete_payment':
                try:
                    payment = Payments.objects.get(id=request.POST.get('id_delete'))
                    payment.delete()
                    messages.success(request, 'Payment deleted successfully')
                    return redirect('payments')
                except:
                    messages.error(request, 'Error deleting payment')
                    return redirect('payments')
    else:
        form = PaymentsForm()

    return render(request, 'payments/payments.html',{
        'payments': payments,
        'tenant': tenant,
        'form': form,
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
        'form_tenant': form_tenant,
        'form_room': form_room,
    })

@login_required(login_url='login')
def online_payment(request):
    if request.user.is_superuser:
        return redirect('dashboard')
    if request.method == "POST":
        try:
            # Safer fetch
            tenant = Tenant.objects.filter(name=request.user).first()
            if not tenant:
                messages.error(request, 'No linked tenant profile found.')
                return redirect('payments')
            
            if not tenant.room:
                messages.error(request, 'You cannot transact until a room is assigned to you.')
                return redirect('payments')

            amount = request.POST.get('amount')
            mode = request.POST.get('payment_method', 'GCash')
            action_type = request.POST.get('action_type', 'pay_rent')
            category = request.POST.get('bill_category', 'Rent')
            
            from decimal import Decimal
            numeric_amount = Decimal(amount)
            
            if action_type == 'cash_out':
                if tenant.wallet_balance < numeric_amount:
                    messages.error(request, 'Insufficient wallet balance to cash out.')
                    return redirect('payments')
                amount = str(-numeric_amount)
                note = "Cash Out"
                tenant.wallet_balance -= numeric_amount
                tenant.save()
            elif action_type == 'cash_in':
                note = "Cash In"
                tenant.wallet_balance += numeric_amount
                tenant.save()
            else:
                if tenant.wallet_balance < numeric_amount:
                    messages.error(request, 'Insufficient wallet balance. Please Cash In first.')
                    return redirect('payments')
                note = category
                tenant.wallet_balance -= numeric_amount
                tenant.save()
            
            # Record the payment
            payment_obj = Payments.objects.create(
                room=tenant.room,
                tenant=tenant,
                amount=amount,
                mode=mode,
                note=note
            )
            
            # Get Boarding House Name
            house_name = tenant.room.boardinghouse.name if tenant.room and tenant.room.boardinghouse else "Boarding House"
            
            # Generate a Mock Reference Number (GCash format: 2012 120 513868)
            import random
            ref_no = f"20{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100000, 999999)}"
            
            # Store data for Receipt Popup
            request.session['receipt_data'] = {
                'amount': f"{abs(float(amount)):,.2f}",
                'ref_no': ref_no,
                'date': payment_obj.date.strftime('%b %d, %Y %I:%M %p'),
                'mode': mode,
                'note': note,
                'category': category if action_type == 'pay_rent' else note,
                'house_name': house_name
            }
            
            # Email Notification Logic
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                
                subject = f"Transaction Alert: ₱{abs(float(amount)):.2f} via {mode}"
                message = f"""Hello {tenant.name.get_full_name()}!

We successfully processed your transaction.

Transaction Details:
- Action: {note}
- Amount: ₱{abs(float(amount)):.2f}
- Method: {mode}
- Date: {payment_obj.date.strftime('%B %d, %Y %I:%M %p')}

This transaction has been forwarded and recorded to your boarding house owner.

Thank you!
Boarding House Management System"""
                
                recipient_list = []
                if tenant.name.email:
                    recipient_list.append(tenant.name.email)
                if getattr(tenant, 'owner', None) and tenant.owner.email:
                    recipient_list.append(tenant.owner.email)
                    
                if recipient_list:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        recipient_list,
                        fail_silently=True
                    )
            except Exception as e:
                print(f"Failed to send email notification: {e}")
            
            messages.success(request, f'Success! {note} of ₱{abs(float(amount)):.2f} processed.')
            return redirect('payments')
        except Exception as e:
            messages.error(request, f'Processing error: {str(e)}')
            return redirect('payments')
    return redirect('payments')



@login_required(login_url='login')
def payments_info(request, id):
    if request.user.is_superuser:
        return redirect('dashboard')
    payment = Payments.objects.get(id=id)

    form = PaymentsForm(instance=payment)

    if request.method == "POST":
        form = PaymentsForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment edited successfully')
            return redirect('payments')
        else:
            messages.error(request, 'Error editing payment')
            return redirect('payments')



    return render(request, 'payments/payments-info.html',{
        'payment': payment,
        'form': form,
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),

    })

@user_passes_test(lambda u: u.is_staff)
def income(request):
    if request.user.is_superuser:
        payments = Payments.objects.all().order_by('-date')
        transient_payments = TransientPayment.objects.all().order_by('-date')
    else:
        payments = Payments.objects.filter(room__boardinghouse__owner=request.user).order_by('-date')
        transient_payments = TransientPayment.objects.filter(room__boardinghouse__owner=request.user).order_by('-date')
    
    months = []
    # Combine all payments for a detailed master list
    all_transactions = []
    total_income = 0

    for p in payments:
        # Exclude wallet loadings/withdrawals from Income Report
        if p.note and any(kw in p.note for kw in ["Cash In", "Cash Out"]):
            continue
            
        all_transactions.append({
            'date': p.date,
            'type': 'Tenant Payment',
            'room': p.room.name,
            'bhouse': p.room.boardinghouse.name,
            'payer': p.tenant.name.get_full_name(),
            'amount': float(p.amount),
            'mode': p.mode or 'N/A'
        })
        total_income += float(p.amount)

    for tp in transient_payments:
        all_transactions.append({
            'date': tp.date,
            'type': 'Transient',
            'room': tp.room.name,
            'bhouse': tp.room.boardinghouse.name,
            'payer': tp.transient,
            'amount': float(tp.amount),
            'mode': tp.mode or 'N/A'
        })
        total_income += float(tp.amount)

    # Sort combined transactions by the full datetime
    all_transactions.sort(key=lambda x: x['date'], reverse=True)

    # Re-calculate monthly summary
    monthly_data = {}
    for trans in all_transactions:
        month_name = trans['date'].strftime('%B')
        if month_name not in monthly_data:
            monthly_data[month_name] = 0
        monthly_data[month_name] += trans['amount']

    months_list = [{'month': m, 'income': i} for m, i in monthly_data.items()]

    return render(request, 'payments/income.html', {
        'months': months_list,
        'all_transactions': all_transactions,
        'total_income': total_income,
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice_count': Notice.objects.filter(is_viewed=False).count(),
    })


@user_passes_test(lambda u: u.is_staff)
def collectibles(request):
    #########################
    tenants = Tenant.objects.filter(owner=request.user)
    print("tenants", tenants)
    for tenant in tenants:
        if tenant.add_month is not None:
            if tenant.add_month < datetime.now().date():
                print("add month is less than now")
                print("late")
                tenant.previous_balance += tenant.current_balance
                tenant.current_balance = 0

                tenant.add_month = tenant.add_month + timedelta(days=30)

                tenant.save()
            else:
                print("add month is greater than now")
                print("not late")
                # get all payments
                payments = Payments.objects.filter(tenant=tenant)
                print(payments)
                total = 0
                print(total)
                for payment in payments:
                    total += float(payment.amount)
                tenant.amount_paid = total
                tenant.save()


    #########################
    if request.user.is_superuser:
        tenants = Tenant.objects.filter(room__isnull=False)
    else:
        tenants = Tenant.objects.filter(room__boardinghouse__owner=request.user, room__isnull=False)

    # Clear notifications for collectibles (Tenant unviewed status)
    tenants.update(is_viewed=True)

    collectibles_lists = []

    for tenant in tenants:
        bills = Bills.objects.filter(room=tenant.room)
        total_bills = 0
        if bills:
            for bill in bills:
                total_bills += float(bill.rate)

        total_due = 0
        try:
            total_due = float(tenant.previous_balance) + float(total_bills)
        except:
            pass

        amount_paid = 0
        try:
            for payment in Payments.objects.filter(tenant=tenant):
                amount_paid += float(payment.amount)
        except:
            pass

        current_balance = 0
        try:
            current_balance = float(total_due) - float(tenant.amount_paid)
            tenant.current_balance = current_balance
            tenant.save()
        except Exception as e:
            print("error")
            print(e)




        collectibles_lists.append({
            'tenant': tenant,
            'room': tenant.room.name,
            'monthly_due': total_bills,
            'previous_balance': tenant.previous_balance,
            'total_due': total_due,
            'amount_paid': tenant.amount_paid,
            'current_balance': current_balance,
        })




    return render(request, 'payments/collectibles.html',{
        'tenants': tenants,
        'collectibles_lists': collectibles_lists,
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),

    })


def transient(request):
    if request.user.is_superuser or request.user.is_staff:
        if request.user.is_superuser:
            payments = TransientPayment.objects.all()
        else:
            payments = TransientPayment.objects.filter(room__boardinghouse__owner=request.user)
    else:
        try:
            tenant = Tenant.objects.get(name__id=request.user.id)
            payments = TransientPayment.objects.filter(tenant=tenant)
        except:
            tenant = None
            payments = None
    form_tenant = Tenant.objects.filter(owner=request.user, is_archive=False)
    form_room = Room.objects.filter(owner=request.user, is_archive=False)

    # Clear notifications for transient payments
    if payments and payments.exists():
        payments.update(is_viewed=True)

    if request.method == "POST":
        if "button" in request.POST:
            if request.POST.get("button") == 'add_payment':

                form = TransientPaymentForm(request.POST)
                if form.is_valid():
                    form = form.save(commit=False)
                    form.save()
                    messages.success(request, 'Payment added successfully')
                    return redirect('transient')
                else:
                    messages.error(request, 'Error adding payment')
                    return redirect('transient')
            elif request.POST.get("button") == 'delete_payment':
                try:
                    payment = TransientPayment.objects.get(id=request.POST.get('id_delete'))
                    payment.delete()
                    messages.success(request, 'Payment deleted successfully')
                    return redirect('transient')
                except:
                    messages.error(request, 'Error deleting payment')
                    return redirect('transient')
    else:
        form = TransientPaymentForm()

    return render (request, 'payments/transient.html',{
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
        'payments': payments,
        'form': form,
        'form_tenant': form_tenant,
        'form_room': form_room,


    })


def transient_info(request, id):
    payment = TransientPayment.objects.get(id=id)

    form = TransientPaymentForm(instance=payment)

    if request.method == "POST":
        form = TransientPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment edited successfully')
            return redirect('transient')
        else:
            messages.error(request, 'Error editing payment')
            return redirect('transient')


    return render(request, 'payments/transient-info.html',{
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
        'payment': payment,
        'form': form,
    })

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def create_stripe_checkout_session(request):
    if request.method == 'POST':
        try:
            amount = request.POST.get('amount')
            action_type = request.POST.get('action_type', 'pay_rent')
            
            # Convert to cents for Stripe
            amount_in_cents = int(float(amount) * 100)
            
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'php',
                        'product_data': {
                            'name': f'Boarding House Payment: {action_type.replace("_", " ").title()}',
                        },
                        'unit_amount': amount_in_cents,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=settings.STRIPE_SUCCESS_URL + f'?session_id={{CHECKOUT_SESSION_ID}}&amount={amount}&type={action_type}',
                cancel_url=settings.STRIPE_CANCEL_URL,
            )
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            messages.error(request, str(e))
            return redirect('payments')
    return redirect('payments')

def stripe_success(request):
    session_id = request.GET.get('session_id')
    amount = request.GET.get('amount')
    action_type = request.GET.get('type')
    
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == 'paid':
                tenant = Tenant.objects.get(name=request.user)
                from decimal import Decimal
                numeric_amount = Decimal(amount)
                
                if action_type == 'cash_in':
                    note = "Stripe Cash In (Card)"
                    tenant.wallet_balance += numeric_amount
                else:
                    note = f"Stripe Rent Payment (Card)"
                    # If it's rent payment directly, we might subtract it from balance but here we use wallet logic
                    # Usually Cash In first then pay, but here we do it directly
                    # For simplicity, let's treat it as Cash In then immediate record
                
                tenant.save()
                
                # Record Payment
                Payments.objects.create(
                    room=tenant.room,
                    tenant=tenant,
                    amount=numeric_amount,
                    mode="Stripe/Card",
                    note=note
                )
                
                messages.success(request, f'Payment of ₱{amount} successful via Stripe!')
            else:
                messages.error(request, 'Payment not verified.')
        except Exception as e:
            messages.error(request, f'Error processing Stripe success: {str(e)}')
            
    return redirect('payments')

def stripe_cancel(request):
    messages.warning(request, 'Payment cancelled.')
    return redirect('payments')