from django.contrib import admin
from authentication.models import Cellphone_number, Profile, StaffProfile

@admin.register(Cellphone_number)
class CellphoneAdmin(admin.ModelAdmin):
    list_display = ('user', 'cellphone_number')
    search_fields = ('user__username', 'cellphone_number')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'owner', 'is_verified')
    list_filter = ('is_verified', 'owner')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'owner__username')
    actions = ['verify_staff']

    def verify_staff(self, request, queryset):
        queryset.update(is_verified=True)
    verify_staff.short_description = "Mark selected staff as verified"