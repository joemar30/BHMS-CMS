from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from payments.models import Bills


# Create your models here.

class BoardingHouse(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()
    address = models.CharField(max_length=100)
    num_beds = models.IntegerField()
    num_baths = models.IntegerField()
    latitude = models.DecimalField(max_digits=25, decimal_places=20)
    longitude = models.DecimalField(max_digits=25, decimal_places=20)
    image = models.ImageField(upload_to='boardinghouse', blank=True)
    owner = models.ForeignKey('auth.User', related_name='boardinghouses', on_delete=models.CASCADE)
    is_archive = models.BooleanField(default=False)
    is_viewed = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class BoardingHouseImage(models.Model):
    boardinghouse = models.ForeignKey(BoardingHouse, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='boardinghouse', blank=True)

    def __str__(self):
        return self.boardinghouse.name



class Room(models.Model):
    boardinghouse = models.ForeignKey(BoardingHouse, related_name='rooms', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    num_bed = models.IntegerField()

    male_female_choices = (
        ("For Male Only", "For Male Only"),
        ("For Female Only", "For Female Only"),
        ("For Both Male and Female", "For Both Male and Female")
    )
    male_female = models.CharField(choices=male_female_choices, max_length=50)
    vacant = models.BooleanField(default=True)
    image = models.ImageField(upload_to='room', blank=True)
    owner = models.ForeignKey('auth.User', related_name='rooms', on_delete=models.CASCADE)
    is_archive = models.BooleanField(default=False)
    is_viewed = models.BooleanField(default=False)


    def __str__(self):
        return self.name

    @property
    def active_tenants_count(self):
        return self.tenant_set.filter(is_archive=False).count()

    @property
    def is_full(self):
        return self.active_tenants_count >= self.num_bed

    @property
    def space_left(self):
        return max(0, self.num_bed - self.active_tenants_count)





@receiver(post_save, sender=Room)
def update_bills(sender, instance, created, **kwargs):
    # check if room is in Bills
    bills = Bills.objects.filter(room=instance)
    if bills:
        for bill in bills:
            bill.rate = instance.price
            bill.save()
    else:
        Bills.objects.create(
            room=instance,
            bills="Rent",
            rate=instance.price
        )
