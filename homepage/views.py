import json
import threading
import base64
from django.core.files.base import ContentFile
from authentication.models import Profile
from datetime import datetime, timedelta
from django.utils import timezone as django_tz

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from boardinghouse.models import BoardingHouse, Room, BoardingHouseImage
from homepage.forms import FeedbackForms, NoticeForms, UserForm, UserChangePassword, ComplaintForm
from homepage.models import Feedback, Notice, Complaint
from payments.models import Payments, TransientPayment
from tenants.models import Tenant


# Create your views here.
@login_required(login_url='login')
def homepage(request):
    if request.user.is_superuser:
        if request.user.first_name == "" and request.user.last_name == "":
            return redirect('myaccount')
        else:
            return redirect('dashboard')
    elif request.user.is_staff:
        if request.user.first_name == "" and request.user.last_name == "":
            return redirect('myaccount')
        else:
            return redirect('dashboard_owner')
    elif hasattr(request.user, 'staff_profile'):
        if request.user.first_name == "" and request.user.last_name == "":
            return redirect('myaccount')
        else:
            return redirect('dashboard_staff')
    elif request.user.is_active:
        if request.user.first_name == "" and request.user.last_name == "":
            return redirect('myaccount')
        else:
            if hasattr(request.user, 'staff_profile'):
                return redirect('dashboard_staff')
            return redirect('dashboard_tenant')


@login_required(login_url='login')
def myaccount(request):
    form = UserForm(instance=request.user)
    change_password_form = UserChangePassword(request.user)


    # Change password form


    if request.method == "POST":
        form = UserForm(request.POST, request.FILES, instance=request.user)
        change_password_form = UserChangePassword(data=request.POST, user=request.user)
        
        # Profile Image Handling
        profile, created = Profile.objects.get_or_create(user=request.user)
        
        # Uploaded file
        if 'profile_image' in request.FILES:
            profile.image = request.FILES['profile_image']
            profile.save()
            
        # Webcam base64 data
        webcam_data = request.POST.get('webcam_image')
        if webcam_data and webcam_data.startswith('data:image'):
            try:
                format, imgstr = webcam_data.split(';base64,')
                ext = format.split('/')[-1]
                data = ContentFile(base64.b64decode(imgstr), name=f'webcam_{request.user.username}.{ext}')
                profile.image = data
                profile.save()
            except Exception as e:
                print(f"Webcam image save error: {e}")
        if request.POST.get("old_password") and request.POST.get("new_password1") and request.POST.get("new_password2"):

            if form.is_valid() and change_password_form.is_valid():
                user = form.save(commit=False)
                user.save()
                change_password_form.save()

                messages.success(request, 'Account Updated Successfully')
                return redirect('homepage')
            else:
                errors = str(form.errors) + str(change_password_form.errors)
                messages.error(request, 'Account Update Failed:' + errors)
                return redirect('myaccount')
        else:
            if form.is_valid():
                user = form.save(commit=False)
                user.save()
                messages.success(request, 'Account Updated Successfully')
                return redirect('myaccount')
            else:
                messages.error(request, 'Account Update Failed')
                return redirect('myaccount')


    return render(request, 'dashboard/myaccount.html',{
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
        'form':form,
        'change_password_form': change_password_form,
    })

@user_passes_test(lambda u: u.is_authenticated )
def dashboard(request):
    if request.user.is_superuser:
        tenants = Tenant.objects.all()
        tenants_count = User.objects.all().count()
        boardinghouses = BoardingHouse.objects.all()
        boardinghouses_count = boardinghouses.count()
        rooms = Room.objects.all()
        rooms_count = rooms.count()
        owner = User.objects.filter(is_superuser=False, is_staff=True).count()
        income = 0
        all_payments = Payments.objects.all()
        for p in all_payments:
            if p.note and any(kw in p.note for kw in ["Cash In", "Cash Out"]):
                continue
            income = float(income) + float(p.amount)
    else:
        return redirect('homepage')


    return render(request, 'dashboard/dashboard.html',{
        'tenants_count': tenants_count,
        'boardinghouses_count': boardinghouses_count,
        'rooms_count': rooms_count,
        'owner': owner,
        'income': income,
        'feedback_notif': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'complaint_notif': Complaint.objects.filter(complaint_to=request.user, is_resolved=False).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
    })

@user_passes_test(lambda u: u.is_authenticated)
def dashboard_owner(request):
    # get all Payments in Payment
    if request.user.is_staff:
        income = 0
        payments = Payments.objects.filter(room__boardinghouse__owner=request.user)
        for p in payments:
            if p.note and any(kw in p.note for kw in ["Cash In", "Cash Out"]):
                continue
            income = float(income) + float(p.amount)
        # get all tenants in Tenant
        tenants = Tenant.objects.filter(room__boardinghouse__owner=request.user).count()
        # get all rooms in Room
        rooms = Room.objects.filter(boardinghouse__owner=request.user).count()
        # get all boardinghouses in BoardingHouse
        boardinghouses = BoardingHouse.objects.filter(owner=request.user).count()


        """
            [
                {
                    "month: "January",
                    "income": 10000
                },
                {
                    "month: "February",
                    "income": 10000
                },
                {
                    "month: "March",
                    "income": 10000
                },
                {
                    "month: "April",
                    "income": 10000
                },
                {
                    "month: "May",
                    "income": 10000
                },
                {
                    "month: "June",
                    "income": 10000
                },
                {
                    "month: "July",
                    "income": 10000
                },
                {
                    "month: "August",
                    "income": 10000
                },
                {
                    "month: "September",
                    "income": 10000
                },
                {
                    "month: "October",
                    "income": 10000
                },
                {
                    "month: "November",
                    "income": 10000
                },
                {
                    "month: "December",
                    "income": 10000
                },
            ]
        """
        # get all payments in Payments
        payments = Payments.objects.filter(room__boardinghouse__owner=request.user)
        transient_payments = TransientPayment.objects.filter(room__boardinghouse__owner=request.user)

        monthly_income = []
        for i in range(1, 13):
            monthly_income.append({
                "month": datetime(2021, i, 1).strftime("%B"),
                "income": 0,
            })

        for payment in payments:
            if payment.date:
                month_idx = payment.date.month - 1
                monthly_income[month_idx]["income"] += float(payment.amount)

        for transient_payment in transient_payments:
            if transient_payment.date:
                month_idx = transient_payment.date.month - 1
                monthly_income[month_idx]["income"] += float(transient_payment.amount)

        # Monthly Complaints for Owner
        monthly_complaints = []
        all_complaints = Complaint.objects.filter(complaint_to=request.user)
        current_year = datetime.now().year
        for i in range(1, 13):
            month_name = datetime(current_year, i, 1).strftime("%B")
            start_date = django_tz.make_aware(datetime(current_year, i, 1))
            if i == 12:
                end_date = django_tz.make_aware(datetime(current_year + 1, 1, 1))
            else:
                end_date = django_tz.make_aware(datetime(current_year, i + 1, 1))
            count = all_complaints.filter(date__gte=start_date, date__lt=end_date).count()
            monthly_complaints.append({
                "month": month_name,
                "count": count,
            })

        # Pending tenants where they registered via tenant registration but their is_active=False
        from django.db.models import Q
        pending_tenants = User.objects.filter(
            is_active=False, is_staff=False, is_superuser=False
        ).filter(
            Q(staff_profile__isnull=False, staff_profile__owner__isnull=True) | 
            Q(tenant__owner=request.user)
        ).distinct()


    else:
        return redirect('homepage')

    if request.method == "POST":
        if request.POST.get("button") == "activate":
            user_to_activate = User.objects.get(id=request.POST.get("user_id"))
            user_to_activate.is_active = True
            # Handle Staff Profile linkage
            if hasattr(user_to_activate, 'staff_profile'):
                user_to_activate.staff_profile.is_verified = True
                user_to_activate.staff_profile.owner = request.user
                user_to_activate.staff_profile.save()
                
            user_to_activate.save()
            messages.success(request, f'User {user_to_activate.username} activated successfully!')
            return redirect('dashboard_owner')

    return render(request, 'dashboard/dashboard.html',{
        'income': income,
        'tenants': tenants,
        'rooms': rooms,
        'boardinghouses': boardinghouses,
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
        'monthly_income': monthly_income,
        'monthly_complaints': monthly_complaints,
        'pending_tenants': pending_tenants,
    })

@csrf_exempt
@login_required
def update_complaint_status(request, complaint_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            new_status = data.get("status")
            complaint = get_object_or_404(Complaint, id=complaint_id)
            
            if new_status in ['Pending', 'In Progress', 'Resolved', 'Rejected']:
                complaint.status = new_status
                complaint.is_resolved = (new_status == 'Resolved')
                complaint.save()
                
                # Dynamic counts update for frontend
                owner = complaint.complaint_to
                all_c = Complaint.objects.filter(complaint_to=owner)
                counts = {
                    'total': all_c.count(),
                    'pending': all_c.filter(status='Pending').count(),
                    'progress': all_c.filter(status='In Progress').count(),
                    'resolved': all_c.filter(status='Resolved').count(),
                    'rejected': all_c.filter(status='Rejected').count(),
                }
                
                return JsonResponse({"success": True, "status": new_status, "counts": counts})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"success": False}, status=405)


@login_required(login_url='login')
def dashboard_staff(request):
    if not hasattr(request.user, 'staff_profile') or not request.user.staff_profile.is_verified:
        return redirect('homepage')
        
    owner = request.user.staff_profile.owner
    all_complaints = Complaint.objects.filter(complaint_to=owner).order_by('-date')
    
    # Dynamic Counts
    pending_count = all_complaints.filter(status='Pending').count()
    progress_count = all_complaints.filter(status='In Progress').count()
    resolved_count = all_complaints.filter(status='Resolved').count()
    rejected_count = all_complaints.filter(status='Rejected').count()
    total_count = all_complaints.count()

    # Monthly Revenue for the chart
    # NOTE: Using date range filters instead of date__month/date__year
    # because those use Django's custom SQLite functions which crash
    # with USE_TZ=True + Asia/Manila timezone on Python 3.12
    monthly_income = []
    current_year = datetime.now().year
    for i in range(1, 13):
        month_name = datetime(current_year, i, 1).strftime("%B")
        start_date = django_tz.make_aware(datetime(current_year, i, 1))
        if i == 12:
            end_date = django_tz.make_aware(datetime(current_year + 1, 1, 1))
        else:
            end_date = django_tz.make_aware(datetime(current_year, i + 1, 1))
        monthly_sum = Payments.objects.filter(
            room__boardinghouse__owner=owner,
            date__gte=start_date,
            date__lt=end_date
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        monthly_income.append({
            "month": month_name,
            "income": float(monthly_sum),
        })

    # Prepare complaints with room data
    for c in all_complaints:
        tenant_room = Room.objects.filter(tenant__name_id=c.user.id).first()
        c.room_no = tenant_room.name if tenant_room else "N/A"

    return render(request, 'dashboard/dashboard.html',{
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
        'all_complaints': all_complaints,
        'pending_count': pending_count,
        'progress_count': progress_count,
        'resolved_count': resolved_count,
        'rejected_count': rejected_count,
        'total_count': total_count,
        'monthly_income': monthly_income,
        'income': float(Payments.objects.filter(room__boardinghouse__owner=owner).aggregate(Sum('amount'))['amount__sum'] or 0),
        'tenants': Tenant.objects.filter(room__boardinghouse__owner=owner, is_archive=False).count(),
        'boardinghouses': BoardingHouse.objects.filter(owner=owner, is_archive=False).count(),
        'rooms': Room.objects.filter(boardinghouse__owner=owner, is_archive=False).count(),
    })

@user_passes_test(lambda u: u.is_authenticated)
def dashboard_tenant(request):
    if not request.user.is_superuser and not request.user.is_staff:
        try:
            tenant = Tenant.objects.get(name__id=request.user.id)
            room = tenant.room
        except Tenant.DoesNotExist:
            tenant = None
            room = None
    else:
        return redirect('homepage')
    notices = []
    if tenant:
        # Determine the owner to show notices from
        target_owner = None
        if tenant.room and tenant.room.boardinghouse:
            target_owner = tenant.room.boardinghouse.owner
        elif tenant.owner:
            target_owner = tenant.owner
            
        if target_owner:
            # Sync: Show all notices from the owner
            notices = Notice.objects.filter(boardinghouse__owner=target_owner, is_archived=False).order_by('-date')

    return render(request, 'dashboard/dashboard.html',{
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice_count': len([n for n in notices if not n.is_viewed]),
        'notice_notif': len([n for n in notices if not n.is_viewed]),
        'notices': notices[:5], # Show latest 5 on dashboard
        'tenant': tenant,
        'room': room,
    })

@user_passes_test(lambda u: u.is_authenticated)
def notice(request):
    if request.user.is_superuser:
        notices = Notice.objects.filter(is_archived=False)
    elif request.user.is_staff:
        notices = Notice.objects.filter(boardinghouse__owner=request.user, is_archived=False)

    else:
        user = User.objects.get(id=request.user.id)
        try:
            tenant_instance = Tenant.objects.get(name__id=user.id)
            if tenant_instance.room and tenant_instance.room.boardinghouse:
                owner = tenant_instance.room.boardinghouse.owner
                # Show all notices from the owner of this boarding house
                notices = Notice.objects.filter(boardinghouse__owner=owner, is_archived=False)
                # Removed auto-marking as viewed here so other tenants still see the notification
            else:
                notices = Notice.objects.none()
                messages.info(request, "You are not yet assigned to a room. Once assigned, you will see notices from your Boarding House.")
        except Tenant.DoesNotExist:
            notices = Notice.objects.none()
            messages.warning(request, "Please connect your account to a Tenant profile to view notices.")
    if request.user.is_superuser:
        bhouses = BoardingHouse.objects.filter(is_archive=False)
    else:
        bhouses = BoardingHouse.objects.filter(owner=request.user, is_archive=False)

    if request.method == "POST":
        form = NoticeForms(request.POST)
        if "button" in request.POST:
            if request.POST.get("button") == "add_notice":

                if form.is_valid():
                    target_bhouse_id = request.POST.get("boardinghouse")
                    if target_bhouse_id == "all":
                        # Post to all owner's boarding houses
                        my_bhouses = BoardingHouse.objects.filter(owner=request.user, is_archive=False)
                        for bh in my_bhouses:
                            new_notice = Notice(
                                title=form.cleaned_data['title'],
                                notice=form.cleaned_data['notice'],
                                boardinghouse=bh
                            )
                            new_notice.save()
                        messages.success(request, f'Notice broadcasted to {my_bhouses.count()} boarding houses.')
                    else:
                        notice = form.save(commit=False)
                        notice.boardinghouse = BoardingHouse.objects.get(id=target_bhouse_id)
                        notice.save()
                        messages.success(request, 'Notice Submitted Successfully')
                    return redirect('notice')
                else:
                    messages.error(request, 'Notice Submission Failed')
                    return redirect('notice')
            elif request.POST.get("button") == "delete_notice":
                try:
                    notice = Notice.objects.get(id=request.POST.get("delete_id"))
                    notice.is_archived = True
                    notice.is_viewed = True
                    notice.save()
                    messages.success(request, 'Notice Archived Successfully')
                    return redirect('notice')
                except Exception as e:
                    messages.error(request, 'Notice Archived Failed')
                    print(e)
                    return redirect('notice')
    else:
        form = NoticeForms()

    return render(request, 'dashboard/notice.html',{
        'notices': notices,
        'form': form,
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
        'bhouses': bhouses,

    })

@user_passes_test(lambda u: u.is_superuser)
def notice_archive(request):
    if request.user.is_superuser:
        notices = Notice.objects.filter(is_archived=True)
    else:
        notices = Notice.objects.filter(boardinghouse__owner=request.user, is_archived=True)


    if request.method == "POST":
        if request.POST.get("button") == "recover":
            try:
                notice = Notice.objects.get(id=request.POST.get("recover_id"))
                notice.is_archived = False
                notice.is_viewed = False
                notice.save()
                messages.success(request, 'Notice Recovered Successfully')
                return redirect('notice_archive')
            except Exception as e:
                messages.error(request, 'Notice Recovery Failed')
                print(e)
                return redirect('notice_archive')
        elif request.POST.get("button") == "delete":
            try:
                notice = Notice.objects.get(id=request.POST.get("delete_id"))
                notice.delete()
                messages.success(request, 'Notice Deleted Successfully')
                return redirect('notice_archive')
            except Exception as e:
                messages.error(request, 'Notice Deletion Failed')
                print(e)
                return redirect('notice_archive')



    return render(request, 'dashboard/notice_archive.html',{
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
        'notices': notices,

    })


@user_passes_test(lambda u: u.is_authenticated)
def notice_detail(request, id):
    notice = Notice.objects.get(id=id)

    form = NoticeForms(instance=notice)

    if request.method == "POST":
        if request.user.is_superuser or request.user.is_staff:
            form = NoticeForms(request.POST, instance=notice)
            if form.is_valid():
                notice = form.save(commit=False)
                notice.save()
                messages.success(request, 'Notice Updated Successfully')
                return redirect('notice')
            else:
                messages.error(request, 'Notice Update Failed')
                return redirect('notice')
        else:
            messages.error(request, 'You do not have permission to edit notices.')
            return redirect('notice')

    return render(request, 'dashboard/notice_detail.html',{
        'notice': notice,
        'form': form,
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),

    })

@user_passes_test(lambda u: u.is_authenticated)
def feedbacks(request):

    if request.user.is_superuser:
        my_feedbacks = None
        received_feedbacks = Feedback.objects.filter(feedback_to=request.user, is_archived=False).order_by('date')
        for feeds in received_feedbacks:
            feeds.is_viewed = True
            feeds.save()
    elif request.user.is_staff:
        my_feedbacks = Feedback.objects.filter(user=request.user, is_archived=False).order_by('date')
        received_feedbacks = Feedback.objects.filter(feedback_to=request.user, is_archived=False).order_by('date')
        for feeds in received_feedbacks:
            feeds.is_viewed = True
            feeds.save()
    else:
        my_feedbacks = Feedback.objects.filter(user=request.user, is_archived=False).order_by('date')
        received_feedbacks = None

    # For admin/owner, get list of users who sent them feedback
    conversations = []
    if request.user.is_superuser or request.user.is_staff:
        senders = Feedback.objects.filter(feedback_to=request.user, is_archived=False).values_list('user', flat=True).distinct()
        conversations = User.objects.filter(id__in=senders)

    form = FeedbackForms()
    room = Room.objects.filter(tenant__name__id=request.user.id)

    if request.method == "POST":
        if request.POST.get("button") == "add":
            form = FeedbackForms(request.POST)
            if form.is_valid():
                save = form.save(commit=False)
                save.user = request.user
                recipient = request.POST.get("feedback_to")
                if recipient == "admin":
                    save.feedback_to = User.objects.filter(is_superuser=True)[0]
                elif recipient == "owner":
                    save.feedback_to = User.objects.get(id=room[0].boardinghouse.owner.id)
                save.save()
                messages.success(request, 'Feedback Submitted Successfully')
                return redirect(f'/feedbacks/?to={recipient}')
        elif request.POST.get("button") == "edit":
            try:
                feedback = Feedback.objects.get(id=request.POST.get("edit_id"))
                feedback.feedback = request.POST.get("edit_feedback")
                recipient = request.POST.get("edit_feedback_to")
                if recipient == "admin":
                    feedback.feedback_to = User.objects.filter(is_superuser=True)[0]
                elif recipient == "owner":
                    feedback.feedback_to = User.objects.get(id=room[0].boardinghouse.owner.id)
                feedback.date = datetime.now()
                feedback.save()
                messages.success(request, 'Feedback Updated Successfully')
                return redirect(f'/feedbacks/?to={recipient}')
            except Exception as e:
                messages.error(request, 'Feedback Update Failed')
                print(e)
                return redirect('feedbacks')
        elif request.POST.get("button") == "delete":
            try:
                feedback = Feedback.objects.get(id=request.POST.get("delete_id"))
                feedback.is_archived = True
                feedback.is_viewed = True
                feedback.save()
                messages.success(request, 'Feedback Archived Successfully')
                return redirect('feedbacks')
            except Exception as e:
                messages.error(request, 'Feedback Archived Failed')
                print(e)
                return redirect('feedbacks')

    return render(request, 'dashboard/feedbacks.html',{
        'feedback_notif': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'complaint_notif': Complaint.objects.filter(complaint_to=request.user, is_resolved=False).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
        'my_feedbacks': my_feedbacks,
        'form': form,
        'room': room,
        'received_feedbacks': received_feedbacks,
        'conversations': conversations,
    })

@user_passes_test(lambda u: u.is_superuser)
def feedbacks_archive(request):
    feedbacks = Feedback.objects.filter(user=request.user, is_archived=True)

    if request.method == "POST":
        if request.POST.get("button") == "restore":
            try:
                feedback = Feedback.objects.get(id=request.POST.get("restore_id"))
                feedback.is_archived = False
                feedback.is_viewed = False
                feedback.save()
                messages.success(request, 'Feedback Restored Successfully')
                return redirect('feedbacks_archive')
            except Exception as e:
                messages.error(request, 'Feedback Restoration Failed')
                print(e)
                return redirect('feedbacks_archive')
        elif request.POST.get("button") == "delete":
            try:
                feedback = Feedback.objects.get(id=request.POST.get("delete_id"))
                feedback.delete()
                messages.success(request, 'Feedback Deleted Successfully')
                return redirect('feedbacks_archive')
            except Exception as e:
                messages.error(request, 'Feedback Deletion Failed')
                print(e)
                return redirect('feedbacks_archive')



    return render(request, 'dashboard/feedbacks_archive.html',{
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
        'feedbacks': feedbacks,
    })

@user_passes_test(lambda u: u.is_superuser)
def users(request):
    users = User.objects.filter(is_active=True)

    form = UserForm()

    if request.method == "POST":
        if "button" in request.POST:
            if request.POST.get("button") == "add":
                form = UserForm(request.POST)
                if form.is_valid():
                    user = form.save(commit=False)
                    user.set_password("@default123")

                    role = request.POST.get("role")
                    if role == "admin":
                        user.is_superuser = True
                        user.is_staff = True
                    elif role == "owner":
                        user.is_superuser = False
                        user.is_staff = True
                    elif role == "tenant":
                        user.is_superuser = False
                        user.is_staff = False
                    user.save()
                    messages.success(request, 'User Added Successfully')
                    return redirect('users')
                else:
                    messages.error(request, 'User Addition Failed')
                    print(form.errors)
                    return redirect('users')
            elif request.POST.get("button") == "delete":
                try:
                    user = User.objects.get(id=request.POST.get("delete_id"))
                    user.is_active = False
                    user.save()
                    messages.success(request, 'User Deleted Successfully')
                    return redirect('users')
                except Exception as e:
                    messages.error(request, 'User Deletion Failed')
                    print(e)
                    return redirect('users')
            elif request.POST.get("button") == "edit":
                try:
                    user = User.objects.get(id=request.POST.get("edit_id"))
                    user.first_name = request.POST.get("edit_first_name")
                    user.last_name = request.POST.get("edit_last_name")
                    user.email = request.POST.get("edit_email")
                    user.username = request.POST.get("edit_username")
                    role = request.POST.get("edit_role")
                    if role == "admin":
                        user.is_superuser = True
                        user.is_staff = True
                    elif role == "owner":
                        user.is_superuser = False
                        user.is_staff = True
                    elif role == "tenant":
                        user.is_superuser = False
                        user.is_staff = False

                    user.save()
                    messages.success(request, 'User Updated Successfully')
                    return redirect('users')
                except Exception as e:
                    messages.error(request, 'User Update Failed')
                    print(e)
                    return redirect('users')

    return render(request,'dashboard/users.html', {
        'users': users,
        'form': form,
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),

    })


@user_passes_test(lambda u: u.is_superuser)
def users_archive(request):
    users = User.objects.filter(is_active=False)

    if request.method == "POST":
        if request.POST.get("button") == "restore":
            try:
                user = User.objects.get(id=request.POST.get("restore_id"))
                user.is_active = True
                user.save()
                messages.success(request, 'User Restored Successfully')
                return redirect('users_archive')
            except Exception as e:
                messages.error(request, 'User Restoration Failed')
                print(e)
                return redirect('users_archive')
        elif request.POST.get("button") == "delete":
            try:
                user = User.objects.get(id=request.POST.get("delete_id"))
                user.delete()
                messages.success(request, 'User Deleted Successfully')
                return redirect('users_archive')
            except Exception as e:
                messages.error(request, 'User Deletion Failed')
                print(e)
                return redirect('users_archive')

    return render(request, 'dashboard/users_archive.html',{
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
        'users': users,
    })




from homepage.forms import FeedbackForms, NoticeForms, UserForm, UserChangePassword, ComplaintForm, InquiryForm
from homepage.models import Feedback, Notice, Complaint, Inquiry


def landing_page(request):
    boardinghouses = BoardingHouse.objects.filter(is_archive=False)
    rooms = Room.objects.filter(is_archive=False)
    inquiry_form = InquiryForm()

    if request.method == "POST":
        inquiry_form = InquiryForm(request.POST)
        if inquiry_form.is_valid():
            inquiry = inquiry_form.save()
            
            # Notify Owner via Email in background to keep it fast
            def send_inquiry_email(inquiry_data):
                try:
                    subject = f"New User Inquiry from {inquiry_data.full_name}"
                    message = f"You have received a new inquiry on the Boarding House Management System.\n\n" \
                              f"Name: {inquiry_data.full_name}\n" \
                              f"Email: {inquiry_data.email}\n" \
                              f"Contact: {inquiry_data.contact_number}\n" \
                              f"Message:\n{inquiry_data.message}\n\n" \
                              f"You can reply to this inquiry by logging into your Owner Portal: {request.build_absolute_uri('/inquiries/')}"
                    
                    send_mail(
                        subject,
                        message,
                        settings.EMAIL_HOST_USER,
                        [settings.EMAIL_HOST_USER],
                        fail_silently=True
                    )
                except Exception as e:
                    print(f"Notification email failed: {e}")

            email_thread = threading.Thread(target=send_inquiry_email, args=(inquiry,))
            email_thread.start()

            messages.success(request, 'Your inquiry has been sent to the Administrator!')
            return redirect('landing_page')

    return render(request, 'landing_page/landing_page.html', {
        'boardinghouses': boardinghouses,
        'rooms': rooms,
        'inquiry_form': inquiry_form,
    })


def bhouse_listings(request):
    boardinghouses = BoardingHouse.objects.all()

    return render(request, 'landing_page/bhouse_listings.html',{
        'boardinghouses': boardinghouses,
    })


def bhouse_listings_detail(request, id):
    bhouse = get_object_or_404(BoardingHouse, id=id)
    bhouse_images = BoardingHouseImage.objects.filter(boardinghouse=bhouse)
    rooms = Room.objects.filter(boardinghouse=bhouse)


    return render(request, 'landing_page/bhouse_listings_detail.html',{
        'bhouse': bhouse,
        'rooms': rooms,
        'bhouse_images': bhouse_images,
    })


def feedback_reply(request, id):
    feedback = get_object_or_404(Feedback, id=id)
    if request.method == "POST":
        feedback.reply = request.POST.get('reply')
        feedback.reply_date = datetime.now()
        feedback.save()
        messages.success(request, 'Reply sent successfully')
        return redirect(f'/feedbacks/?user_id={feedback.user.id}')
    return redirect('feedbacks')


@login_required
def complaints(request):
    my_complaints = Complaint.objects.none()
    received_complaints = Complaint.objects.none()

    # Handle Status Filtering from Dashboard
    status_filter = request.GET.get('status')
    if status_filter in ['Pending', 'In Progress', 'Resolved', 'Rejected']:
        if request.user.is_superuser:
            received_complaints = Complaint.objects.filter(complaint_to__is_superuser=True, status=status_filter)
        elif request.user.is_staff:
            if hasattr(request.user, 'staff_profile'):
                my_complaints = Complaint.objects.filter(user=request.user, status=status_filter).order_by('date')
                received_complaints = Complaint.objects.filter(complaint_to=request.user, status=status_filter).order_by('date')
            else:
                my_complaints = Complaint.objects.filter(user=request.user, status=status_filter).order_by('date')
                received_complaints = Complaint.objects.filter(complaint_to=request.user, status=status_filter).order_by('date')
        else:
            my_complaints = Complaint.objects.filter(user=request.user, status=status_filter).order_by('date')
        
        assigned_complaints = Complaint.objects.filter(assigned_staff=request.user, status=status_filter)
    else:
        if request.user.is_superuser:
            received_complaints = Complaint.objects.filter(complaint_to__is_superuser=True, is_resolved=False).order_by('date')
        elif request.user.is_staff:
            received_complaints = Complaint.objects.filter(models.Q(complaint_to=request.user) | models.Q(assigned_staff=request.user), is_resolved=False).order_by('date')
            my_complaints = Complaint.objects.filter(user=request.user).order_by('date')
        else:
            my_complaints = Complaint.objects.filter(user=request.user).order_by('date')

    # Clear notifications by marking complaints as viewed
    received_complaints.filter(is_viewed=False).update(is_viewed=True)

    form = ComplaintForm()
    room = Room.objects.filter(tenant__name_id=request.user.id)

    if request.method == "POST":
        if request.POST.get("button") == "add_complaint":
            form = ComplaintForm(request.POST)
            if form.is_valid():
                complaint = form.save(commit=False)
                complaint.user = request.user
                
                # Determine recipient
                recipient = request.POST.get("complaint_to")
                if recipient == "admin":
                    complaint.complaint_to = User.objects.filter(is_superuser=True).first()
                elif (recipient == "owner" or recipient == "staff") and room.exists():
                    owner = room.first().boardinghouse.owner
                    complaint.complaint_to = owner
                    
                    if recipient == "staff":
                        # Find a staff member belonging to this owner
                        staff_member = User.objects.filter(staff_profile__owner=owner, staff_profile__is_verified=True).first()
                        if staff_member:
                            complaint.assigned_staff = staff_member
                            complaint.status = 'Accepted' # Automatically accepted if sent to staff
                
                complaint.save()
                messages.success(request, 'Complaint Submitted Successfully')
                return redirect('complaints')
        
        elif request.POST.get("button") == "update_status":
            complaint = get_object_or_404(Complaint, id=request.POST.get("complaint_id"))
            new_status = request.POST.get("new_status")
            if new_status in ['Pending', 'Accepted', 'Resolved', 'Rejected']:
                complaint.status = new_status
                if new_status == 'Resolved':
                    complaint.is_resolved = True
                else:
                    complaint.is_resolved = False
                complaint.save()
                messages.success(request, f'Complaint status updated to {new_status}')
            return redirect('complaints')
        
        elif request.POST.get("button") == "resolve":
            complaint = get_object_or_404(Complaint, id=request.POST.get("complaint_id"))
            complaint.is_resolved = True
            complaint.save()
            messages.success(request, 'Complaint marked as resolved')
            return redirect('complaints')
        
        elif request.POST.get("button") == "assign_staff":
            complaint = get_object_or_404(Complaint, id=request.POST.get("complaint_id"))
            staff_id = request.POST.get("staff_id")
            if staff_id:
                complaint.assigned_staff_id = staff_id
                complaint.save()
                messages.success(request, 'Staff assigned successfully')
            return redirect('complaints')

    if request.user.is_superuser:
        staff_members = User.objects.filter(is_staff=True)
    elif request.user.is_staff and not hasattr(request.user, 'staff_profile'):
        # Owner: see staff they manage, or all verified staff if none assigned yet
        staff_members = User.objects.filter(staff_profile__owner=request.user, staff_profile__is_verified=True)
        if not staff_members.exists():
            staff_members = User.objects.filter(staff_profile__is_verified=True)
    else:
        staff_members = User.objects.none()

    context = {
        'my_complaints': my_complaints,
        'received_complaints': received_complaints,
        'staff_members': staff_members,
        'form': form,
        'room': room,
        'feedback_notif': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'complaint_notif': Complaint.objects.filter(models.Q(complaint_to=request.user) | models.Q(assigned_staff=request.user), is_resolved=False).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
    }
    return render(request, 'dashboard/complaints.html', context)


def complaint_detail(request, id):
    complaint = get_object_or_404(Complaint, id=id)
    if request.method == "POST":
        complaint.reply = request.POST.get('reply')
        complaint.reply_date = datetime.now()
        complaint.save()
        messages.success(request, 'Response sent')
    return redirect('complaints')


def complaints_archive(request):
    complaints = Complaint.objects.filter(is_resolved=True)
    if not request.user.is_superuser:
        complaints = complaints.filter(models.Q(user=request.user) | models.Q(complaint_to=request.user))
    
    return render(request, 'dashboard/complaints_archive.html', {
        'complaints': complaints,
    })


def room_listings(request):
    rooms = Room.objects.all()

    return render(request, 'landing_page/room_listings.html', {
        'rooms': rooms,
    })


def room_listings_detail(request, id):
    room = get_object_or_404(Room, id=id)
    bhouse = BoardingHouse.objects.get(id=room.boardinghouse.id)
    return render(request, 'landing_page/room_listings_detail.html', {
        'room': room,
        'bhouse': bhouse,
    })


@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def inquiries(request):
    inquiries_list = Inquiry.objects.filter(is_archived=False).order_by('-date')
    
    # Mark all as viewed when visiting the page
    for i in inquiries_list:
        if not i.is_viewed:
            i.is_viewed = True
            i.save()
        
    if request.method == "POST":
        if request.POST.get("button") == "reply":
            inquiry = get_object_or_404(Inquiry, id=request.POST.get("inquiry_id"))
            inquiry.reply = request.POST.get("reply")
            inquiry.reply_date = datetime.now()
            inquiry.save()
            
            # Send Email Notification in background
            if inquiry.email:
                subject = f"Reply to your inquiry - {inquiry.full_name}"
                message = f"Hello {inquiry.full_name},\n\nThank you for your inquiry. Here is our response:\n\n{inquiry.reply}\n\nBest regards,\nBoarding House Management"
                email_from = settings.EMAIL_HOST_USER
                recipient_list = [inquiry.email]
                
                def send_reply_email():
                    try:
                        send_mail(subject, message, email_from, recipient_list, fail_silently=False)
                    except Exception as e:
                        print(f"Failed to send reply email: {e}")

                threading.Thread(target=send_reply_email).start()
                messages.success(request, 'Reply saved successfully. Email is being sent in the background.')
            else:
                messages.success(request, 'Reply saved successfully (no email provided by user)')
                
            return redirect('inquiries')
        elif request.POST.get("button") == "approve":
            inquiry = get_object_or_404(Inquiry, id=request.POST.get("inquiry_id"))
            inquiry.status = "Approved"
            inquiry.save()
            messages.success(request, 'Inquiry approved')
            return redirect('inquiries')
        elif request.POST.get("button") == "reject":
            inquiry = get_object_or_404(Inquiry, id=request.POST.get("inquiry_id"))
            inquiry.status = "Rejected"
            inquiry.save()
            messages.success(request, 'Inquiry rejected')
            return redirect('inquiries')
        elif request.POST.get("button") == "send_gmail":
            inquiry = get_object_or_404(Inquiry, id=request.POST.get("inquiry_id"))
            subject = request.POST.get("subject")
            body = request.POST.get("gmail_body")
            recipient = request.POST.get("to_email")
            
            def send_form_email():
                try:
                    send_mail(subject, body, settings.EMAIL_HOST_USER, [recipient], fail_silently=False)
                except Exception as e:
                    print(f"Failed to send form email: {e}")

            threading.Thread(target=send_form_email).start()
            messages.success(request, f'Room Inquiry Form is being sent to {inquiry.full_name} in the background.')
            return redirect('inquiries')
        elif request.POST.get("button") == "archive":
            inquiry = get_object_or_404(Inquiry, id=request.POST.get("inquiry_id"))
            inquiry.is_archived = True
            inquiry.save()
            messages.success(request, 'Inquiry archived')
            return redirect('inquiries')

    # Clear notifications by marking inquiries as viewed
    if inquiries_list.exists():
        inquiries_list.update(is_viewed=True)
        
    return render(request, 'dashboard/inquiries.html', {
        'inquiries': inquiries_list,
    })

@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def inquiries_archive(request):
    inquiries_list = Inquiry.objects.filter(is_archived=True).order_by('-date')
    
    if request.method == "POST":
        if request.POST.get("button") == "restore":
            inquiry = get_object_or_404(Inquiry, id=request.POST.get("inquiry_id"))
            inquiry.is_archived = False
            inquiry.save()
            messages.success(request, 'Inquiry restored')
            return redirect('inquiries_archive')
        elif request.POST.get("button") == "delete":
            inquiry = get_object_or_404(Inquiry, id=request.POST.get("inquiry_id"))
            inquiry.delete()
            messages.success(request, 'Inquiry deleted permanently')
            return redirect('inquiries_archive')
            
    return render(request, 'dashboard/inquiries_archive.html', {
        'inquiries': inquiries_list,
    })
