from django.db import models
from django.conf import settings


class Announcement(models.Model):

    class Visibility(models.TextChoices):
        ALL      = 'all',      'Everyone'
        MEMBERS  = 'members',  'Members Only'

    title      = models.CharField(max_length=200)
    body       = models.TextField()
    image      = models.ImageField(upload_to='announcements/', blank=True, null=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.ALL
    )
    is_pinned  = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='announcements'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes  = [models.Index(fields=['-is_pinned', '-created_at'])]

    def __str__(self):
        return self.title