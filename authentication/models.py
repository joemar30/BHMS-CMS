from django.contrib.auth.models import AbstractUser, User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.

class Cellphone_number (models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cellphone_number = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.cellphone_number

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    image = models.ImageField(upload_to='profiles/', default='profiles/default.png', null=True, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'

# Signals to create profile automatically
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)
    instance.profile.save()

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_staff', null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.get_full_name()