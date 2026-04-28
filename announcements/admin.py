from django.contrib import admin
from .models import Announcement

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display  = ('title', 'visibility', 'is_pinned', 'created_by', 'created_at')
    list_filter   = ('visibility', 'is_pinned')
    search_fields = ('title', 'body')