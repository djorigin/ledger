from django.contrib import admin

from apps.entities.models import Entity, EntityMembership


class EntityMembershipInline(admin.TabularInline):
    model = EntityMembership
    extra = 1
    autocomplete_fields = ["user"]


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "is_active", "created_at"]
    list_filter = ["type", "is_active"]
    search_fields = ["name"]
    inlines = [EntityMembershipInline]


@admin.register(EntityMembership)
class EntityMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "entity", "role", "created_at"]
    list_filter = ["role"]
    autocomplete_fields = ["user", "entity"]
    search_fields = ["user__email", "entity__name"]
