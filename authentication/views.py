# import this to require login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

# import this for sending email to user
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from authentication.forms import UserRegistrationForm


# Create your views here.



from django.contrib.auth import logout as auth_logout
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def user_logout(request):
    # Log out the user and redirect to landing page
    auth_logout(request)
    return redirect('landing_page')

def register(request):
    form = UserRegistrationForm()

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)

            role = request.POST.get('role')
            if role == 'Owner':
                user.is_staff = True
                user.is_superuser = False
                user.is_active = True
                user.save()
            elif role == 'Staff':
                from authentication.models import StaffProfile
                user.is_staff = False
                user.is_superuser = False
                user.is_active = False # Require verification
                user.save()
                StaffProfile.objects.create(user=user, is_verified=False)
            else: # Tenant
                from tenants.models import Tenant
                from boardinghouse.models import Room
                from datetime import datetime
                from dateutil.relativedelta import relativedelta

                user.is_active = True
                user.save()

                tenant = Tenant.objects.create(name=user)
                room_id = request.POST.get('room')
                if room_id:
                    try:
                        selected_room = Room.objects.get(id=room_id)
                        tenant.room = selected_room
                        tenant.owner = selected_room.boardinghouse.owner
                        tenant.date_start = datetime.now().date()
                        tenant.add_month = datetime.now().date() + relativedelta(months=1)
                        tenant.save()
                    except Room.DoesNotExist:
                        pass


            messages.success(request, 'Account created successfully! You may now log in.')
            return redirect('login')
        else:
            messages.error(request, 'Account creation failed. Please try again.')


    from boardinghouse.models import Room
    vacant_rooms = Room.objects.filter(vacant=True, is_archive=False)

    return render(request, 'authentication/register.html',{
        'form': form,
        'vacant_rooms': vacant_rooms
    })

# to activate user from email
def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'authentication/email_activation/activation_successful.html')
    else:
        return render(request, 'authentication/email_activation/activation_unsuccessful.html')

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'authentication/email_activation/activation_successful.html')
    else:
        return render(request, 'authentication/email_activation/activation_unsuccessful.html')

