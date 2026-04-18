from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

from homepage.models import Feedback
from .models import Tenant

# Create your views here.


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def tenants_profile(request):
    users = User.objects.filter(tenant__isnull=True).exclude(is_superuser=True).exclude(is_staff=True)
    if request.user.is_superuser:
        tenants = Tenant.objects.filter(is_archive=False)
    else:
        # Fetch tenants in owner's boarding houses or created by owner directly
        from django.db.models import Q
        tenants = Tenant.objects.filter(Q(room__boardinghouse__owner=request.user) | Q(owner=request.user), is_archive=False).distinct()
    
    # Clear notifications for currently listed tenants
    tenants.update(is_viewed=True)
    
    if request.method == "POST":
        if request.POST.get("button") == "add":
            try:
                name = request.POST.get('user')
                user_instance = User.objects.get(id=name)
                # create tenant object
                tenant = Tenant(name=user_instance)
                tenant.owner = request.user
                tenant.address = request.POST.get('address')
                tenant.contact_number = request.POST.get('number')
                if 'image' in request.FILES:
                    tenant.image = request.FILES['image']
                tenant.save()
                messages.success(request, 'Tenant added successfully!')
                return redirect('tenants_profile')
            except Exception as e:
                print(e)
                messages.error(request, e)
                return redirect('tenants_profile')
        elif request.POST.get("button") == "edit":
            try:
                tenant = Tenant.objects.get(id=request.POST.get('edit_id'))
                tenant.contact_number = request.POST.get('number')
                tenant.address = request.POST.get('address')
                if 'image' in request.FILES:
                    tenant.image = request.FILES['image']
                tenant.save()
                
                # Update associated User info
                user = tenant.name
                user.first_name = request.POST.get('first_name', user.first_name)
                user.last_name = request.POST.get('last_name', user.last_name)
                user.email = request.POST.get('email', user.email)
                
                # Password Change
                new_password = request.POST.get('password')
                if new_password:
                    user.set_password(new_password)
                user.save()
                
                messages.success(request, 'Tenant updated successfully!')
                return redirect('tenants_profile')
            except Exception as e:
                messages.error(request, f"Update failed: {e}")
                return redirect('tenants_profile')
        elif request.POST.get("button") == "archive":
            try:
                tenant = Tenant.objects.get(id=request.POST.get('delete_id'))
                tenant.is_archive = True
                tenant.save()
                messages.success(request, 'Tenant archived successfully!')
                return redirect('tenants_profile')
            except Exception as e:
                messages.error(request, e)
                return redirect('tenants_profile')





    return render(request, 'tenants/tenants_profile.html',{
        'users': users,
        'tenants': tenants,
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),

    })

@user_passes_test(lambda u: u.is_superuser)
def tenant_archive(request):
    tenants = Tenant.objects.filter(is_archive=True)

    if request.method == "POST":
        if request.POST.get("button") == "restore":
            try:
                tenant = Tenant.objects.get(id=request.POST.get('restore_id'))
                tenant.is_archive = False
                tenant.save()
                messages.success(request, 'Tenant restored successfully!')
                return redirect('tenants_profile')
            except Exception as e:
                print(e)
                messages.error(request, e)
                return redirect('tenants_profile')
        elif request.POST.get("button") == "delete":
            try:
                tenant = Tenant.objects.get(id=request.POST.get('delete_id'))
                tenant.delete()
                messages.success(request, 'Tenant deleted successfully!')
                return redirect('tenants_profile')
            except Exception as e:
                print(e)
                messages.error(request, e)
                return redirect('tenants_profile')

    return render(request, 'tenants/tenant_archive.html',{
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'tenants': tenants,
    })

from .forms import TenantDocumentForm
from .models import TenantDocument
from homepage.models import Notice

@user_passes_test(lambda u: u.is_authenticated)
def tenant_documents(request):
    is_tenant = not request.user.is_superuser and not request.user.is_staff
    
    if is_tenant:
        try:
            tenant = Tenant.objects.get(name=request.user)
            documents = TenantDocument.objects.filter(tenant=tenant)
        except Tenant.DoesNotExist:
            tenant = None
            documents = []
    else:
        # For Owners/Admin, show documents related to their tenants
        if request.user.is_superuser:
            documents = TenantDocument.objects.all()
        else:
            documents = TenantDocument.objects.filter(tenant__room__boardinghouse__owner=request.user)

    if request.method == "POST":
        if "upload_btn" in request.POST and is_tenant and tenant:
            form = TenantDocumentForm(request.POST, request.FILES)
            if form.is_valid():
                doc = form.save(commit=False)
                doc.tenant = tenant
                doc.save()
                messages.success(request, "Document uploaded successfully! Owner will review it soon.")
                return redirect('tenant_documents')
            else:
                messages.error(request, "Upload failed. Please check the file.")
        
        elif "verify_btn" in request.POST and not is_tenant:
            doc_id = request.POST.get("doc_id")
            doc = TenantDocument.objects.get(id=doc_id)
            doc.is_verified = True
            doc.is_rejected = False
            doc.save()
            messages.success(request, f"Document for {doc.tenant.name.get_full_name()} approved.")
            return redirect('tenant_documents')

        elif "reject_btn" in request.POST and not is_tenant:
            doc_id = request.POST.get("doc_id")
            doc = TenantDocument.objects.get(id=doc_id)
            doc.is_verified = False
            doc.is_rejected = True
            doc.save()
            messages.error(request, f"Document for {doc.tenant.name.get_full_name()} rejected.")
            return redirect('tenant_documents')

        elif "delete_btn" in request.POST:
            doc_id = request.POST.get("doc_id")
            doc = TenantDocument.objects.get(id=doc_id)
            # Security check: tenants can only delete their own
            if is_tenant and doc.tenant != tenant:
                messages.error(request, "Unauthorized.")
            else:
                doc.delete()
                messages.success(request, "Document deleted.")
            return redirect('tenant_documents')

    form = TenantDocumentForm() if is_tenant else None
    
    return render(request, 'tenants/documents.html', {
        'documents': documents,
        'form': form,
        'is_tenant': is_tenant,
        'feedback': Feedback.objects.filter(is_viewed=False, feedback_to=request.user).count(),
        'notice': Notice.objects.filter(is_viewed=False).count(),
    })

