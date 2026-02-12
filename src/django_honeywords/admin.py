from django.contrib import admin
from django.utils import timezone

from .models import AmnesiaCredential, AmnesiaSet, HoneywordEvent, HoneywordUserState


# ── Inline: credentials shown inside AmnesiaSet ─────────────────────


class AmnesiaCredentialInline(admin.TabularInline):
    model = AmnesiaCredential
    fields = ("index", "marked", "password_hash")
    readonly_fields = ("index", "password_hash")
    ordering = ("index",)
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ── AmnesiaSet ───────────────────────────────────────────────────────


@admin.register(AmnesiaSet)
class AmnesiaSetAdmin(admin.ModelAdmin):
    list_display = ("user", "k", "p_mark", "p_remark", "algorithm_version", "created_at")
    list_filter = ("algorithm_version", "k")
    search_fields = ("user__username",)
    readonly_fields = ("user", "k", "p_mark", "p_remark", "algorithm_version", "created_at")
    inlines = [AmnesiaCredentialInline]

    def has_add_permission(self, request):
        # Sets should only be created via amnesia_initialize()
        return False


# ── HoneywordEvent ───────────────────────────────────────────────────


@admin.register(HoneywordEvent)
class HoneywordEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "username", "outcome", "ip_address", "short_ua")
    list_filter = ("outcome", "created_at")
    search_fields = ("username", "ip_address")
    readonly_fields = ("user", "username", "outcome", "created_at", "ip_address", "user_agent")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def short_ua(self, obj):
        """Truncated user-agent for the list view."""
        return (obj.user_agent[:80] + "…") if len(obj.user_agent) > 80 else obj.user_agent
    short_ua.short_description = "User-Agent"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ── HoneywordUserState ───────────────────────────────────────────────


@admin.register(HoneywordUserState)
class HoneywordUserStateAdmin(admin.ModelAdmin):
    list_display = ("user", "must_reset", "is_locked_now", "lock_count", "locked_until")
    list_filter = ("must_reset",)
    search_fields = ("user__username",)
    readonly_fields = ("lock_count", "last_lock_at")
    actions = ["clear_reset", "clear_lock"]

    def is_locked_now(self, obj):
        return obj.locked_until is not None and obj.locked_until > timezone.now()
    is_locked_now.boolean = True
    is_locked_now.short_description = "Locked?"

    @admin.action(description="Clear must-reset flag for selected users")
    def clear_reset(self, request, queryset):
        updated = queryset.filter(must_reset=True).update(must_reset=False)
        self.message_user(request, f"Cleared reset flag for {updated} user(s).")

    @admin.action(description="Unlock selected users")
    def clear_lock(self, request, queryset):
        updated = queryset.filter(locked_until__isnull=False).update(
            locked_until=None, lock_count=0
        )
        self.message_user(request, f"Unlocked {updated} user(s).")
