from homepage.models import Feedback, Notice, Complaint
from tenants.models import Tenant
from boardinghouse.models import BoardingHouse, Room
from payments.models import Bills, Payments, TransientPayment
from django.db.models import Sum

def notifications(request):
    ctx = {}
    if request.user.is_authenticated:
        feedback_notif = Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count()
        complaint_notif = Complaint.objects.filter(complaint_to=request.user, is_resolved=False).count()
        notice_notif = Notice.objects.filter(is_viewed=False).count()
        
        ctx.update({
            'feedback_notif': feedback_notif,
            'complaint_notif': complaint_notif,
            'notice': notice_notif,
        })
        
        if request.user.is_staff or request.user.is_superuser:
            from django.db.models import Q
            ctx['bhouse_count'] = BoardingHouse.objects.filter(owner=request.user, is_archive=False).count() if not request.user.is_superuser else BoardingHouse.objects.filter(is_archive=False).count()
            ctx['tenant_count'] = Tenant.objects.filter(Q(room__boardinghouse__owner=request.user) | Q(owner=request.user), is_archive=False).distinct().count() if not request.user.is_superuser else Tenant.objects.filter(is_archive=False).count()
            ctx['room_count'] = Room.objects.filter(boardinghouse__owner=request.user, is_archive=False).count() if not request.user.is_superuser else Room.objects.filter(is_archive=False).count()
            ctx['manage_room_count'] = Tenant.objects.filter(room__isnull=True).count() if not request.user.is_superuser else Tenant.objects.filter(room__isnull=True).count()
            ctx['utility_count'] = Bills.objects.filter(room__boardinghouse__owner=request.user).count() if not request.user.is_superuser else Bills.objects.all().count()
            ctx['collectibles_count'] = Tenant.objects.filter(room__boardinghouse__owner=request.user, room__isnull=False).count() if not request.user.is_superuser else Tenant.objects.filter(room__isnull=False).count()
            ctx['payment_count'] = Payments.objects.filter(room__boardinghouse__owner=request.user).count() if not request.user.is_superuser else Payments.objects.all().count()
            ctx['transient_count'] = TransientPayment.objects.filter(room__boardinghouse__owner=request.user).count() if not request.user.is_superuser else TransientPayment.objects.all().count()
    return ctx
