from django.contrib.auth.models import User
from homepage.models import Feedback, Notice, Complaint, Inquiry
from tenants.models import Tenant, TenantDocument
from boardinghouse.models import BoardingHouse, Room
from payments.models import Bills, Payments, TransientPayment
from django.db.models import Sum, Q

def notifications(request):
    ctx = {}
    if request.user.is_authenticated:
        feedback_notif = Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count()
        complaint_notif = Complaint.objects.filter(Q(complaint_to=request.user) | Q(assigned_staff=request.user), is_viewed=False).count()
        
        # Correctly filter notices for the specific user
        if request.user.is_superuser:
            notice_notif = Notice.objects.filter(is_viewed=False, is_archived=False).count()
        elif request.user.is_staff:
            notice_notif = Notice.objects.filter(boardinghouse__owner=request.user, is_viewed=False, is_archived=False).count()
        else:
            # For tenants
            try:
                tenant_instance = Tenant.objects.get(name__id=request.user.id)
                if tenant_instance.room and tenant_instance.room.boardinghouse:
                    owner = tenant_instance.room.boardinghouse.owner
                    notice_notif = Notice.objects.filter(boardinghouse__owner=owner, is_viewed=False, is_archived=False).count()
                elif tenant_instance.owner:
                    owner = tenant_instance.owner
                    notice_notif = Notice.objects.filter(boardinghouse__owner=owner, is_viewed=False, is_archived=False).count()
                else:
                    notice_notif = 0
            except Tenant.DoesNotExist:
                notice_notif = 0
        
        inquiry_notif = 0
        if request.user.is_staff and not request.user.is_superuser:
            inquiry_notif = Inquiry.objects.filter(is_viewed=False, is_archived=False).count()
        
        ctx.update({
            'feedback_notif': feedback_notif,
            'complaint_notif': complaint_notif,
            'notice_notif': notice_notif,
            'inquiry_notif': inquiry_notif,
        })
        
        if request.user.is_staff or request.user.is_superuser:
            # Notifications for other sections
            ctx['bhouse_count'] = BoardingHouse.objects.filter(owner=request.user, is_archive=False, is_viewed=False).count() if not request.user.is_superuser else BoardingHouse.objects.filter(is_archive=False, is_viewed=False).count()
            ctx['tenant_count'] = Tenant.objects.filter(Q(room__boardinghouse__owner=request.user) | Q(owner=request.user), is_archive=False, is_viewed=False).distinct().count() if not request.user.is_superuser else Tenant.objects.filter(is_archive=False, is_viewed=False).count()
            ctx['room_count'] = Room.objects.filter(boardinghouse__owner=request.user, is_archive=False, is_viewed=False).count() if not request.user.is_superuser else Room.objects.filter(is_archive=False, is_viewed=False).count()
            ctx['manage_room_count'] = Tenant.objects.filter(room__isnull=True, is_viewed=False).count() if not request.user.is_superuser else Tenant.objects.filter(room__isnull=True, is_viewed=False).count()
            ctx['utility_count'] = Bills.objects.filter(room__boardinghouse__owner=request.user, is_viewed=False).count() if not request.user.is_superuser else Bills.objects.filter(is_viewed=False).count()
            ctx['collectibles_count'] = Tenant.objects.filter(room__boardinghouse__owner=request.user, room__isnull=False, is_viewed=False).count() if not request.user.is_superuser else Tenant.objects.filter(room__isnull=False, is_viewed=False).count()
            ctx['payment_count'] = Payments.objects.filter(room__boardinghouse__owner=request.user, is_viewed=False).count() if not request.user.is_superuser else Payments.objects.filter(is_viewed=False).count()
            ctx['transient_count'] = TransientPayment.objects.filter(room__boardinghouse__owner=request.user, is_viewed=False).count() if not request.user.is_superuser else TransientPayment.objects.filter(is_viewed=False).count()
            
            if request.user.is_superuser:
                ctx['document_notif'] = TenantDocument.objects.filter(is_verified=False).count()
                ctx['pending_user_count'] = User.objects.filter(is_active=False, is_staff=False, is_superuser=False).count()
            else:
                ctx['document_notif'] = TenantDocument.objects.filter(Q(tenant__room__boardinghouse__owner=request.user) | Q(tenant__owner=request.user), is_verified=False).distinct().count()
                ctx['pending_user_count'] = User.objects.filter(is_active=False, is_staff=False, is_superuser=False).filter(Q(staff_profile__isnull=False, staff_profile__owner=request.user) | Q(tenant__owner=request.user)).distinct().count()
    return ctx
