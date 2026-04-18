from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from tenants.models import Tenant


class Bills(models.Model):
    room = models.ForeignKey('boardinghouse.Room', on_delete = models.CASCADE)
    bills = models.CharField(max_length=100)
    rate = models.CharField(max_length=100)
    is_viewed = models.BooleanField(default=False)

    def __str__(self):
        return self.bills


class Payments(models.Model):
    room = models.ForeignKey('boardinghouse.Room', on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    amount = models.CharField(max_length=100)
    date = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=100, blank=True, null=True)
    mode = models.CharField(max_length=100, blank=True, null=True)
    is_viewed = models.BooleanField(default=False)


    def __str__(self):
        return self.amount

    def save(self, *args, **kwargs):
        is_wallet_tx = self.note in ["Cash In", "Cash Out"]
        if self.pk:
            # If editing existing payment, calculate the difference
            old_payment = Payments.objects.get(pk=self.pk)
            diff = float(self.amount) - float(old_payment.amount)
            if not is_wallet_tx:
                self.tenant.amount_paid = float(self.tenant.amount_paid) + diff
                self.tenant.current_balance = float(self.tenant.current_balance) - diff
                self.tenant.save()
        else:
            # New payment
            if not is_wallet_tx:
                self.tenant.amount_paid = float(self.tenant.amount_paid) + float(self.amount)
                self.tenant.current_balance = float(self.tenant.current_balance) - float(self.amount)
                self.tenant.save()
        super(Payments, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        is_wallet_tx = self.note in ["Cash In", "Cash Out"]
        # Subtract amount from tenant's total when a payment is deleted
        if not is_wallet_tx:
            self.tenant.amount_paid = float(self.tenant.amount_paid) - float(self.amount)
            self.tenant.current_balance = float(self.tenant.current_balance) + float(self.amount)
            self.tenant.save()
        super(Payments, self).delete(*args, **kwargs)


class TransientPayment(models.Model):
    room = models.ForeignKey('boardinghouse.Room', on_delete=models.CASCADE)
    transient = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    contact = models.CharField(max_length=100)
    days = models.IntegerField(default=0)
    amount = models.CharField(max_length=100)
    note = models.CharField(max_length=100, blank=True, null=True)
    mode = models.CharField(max_length=100, blank=True, null=True)
    is_viewed = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)