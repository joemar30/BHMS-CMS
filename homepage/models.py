from django.db import models

# Create your models here.

class Feedback(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    feedback = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    is_viewed = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    feedback_to = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='feedback_to')
    reply = models.TextField(null=True, blank=True)
    reply_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.user.get_full_name()


class Inquiry(models.Model):
    full_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)
    message = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    is_viewed = models.BooleanField(default=False)
    reply = models.TextField(null=True, blank=True)
    reply_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='Pending') # Pending, Approved, Rejected
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name


class Notice(models.Model):
    title = models.CharField(max_length=100)
    notice = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    boardinghouse = models.ForeignKey('boardinghouse.BoardingHouse', on_delete=models.CASCADE)
    is_viewed = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Complaint(models.Model):
    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Mid', 'Mid'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    )
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    complaint_to = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='complaint_to')
    assigned_staff = models.ForeignKey('auth.User', on_delete=models.SET_NULL, related_name='assigned_complaints', null=True, blank=True)
    issue = models.TextField()
    priority_level = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Low')
    date = models.DateTimeField(auto_now_add=True)
    reply = models.TextField(null=True, blank=True)
    reply_date = models.DateTimeField(null=True, blank=True)
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
        ('Rejected', 'Rejected'),
    )
    is_resolved = models.BooleanField(default=False)
    is_viewed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_full_name()