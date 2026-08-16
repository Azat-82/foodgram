from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

from .models import Subscription

User = get_user_model()


@admin.register(User)
class FoodgramUserAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name')

    search_fields = ('username', 'email')

    list_filter = ('email', 'username')

    ordering = ('username',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')

    search_fields = (
        'user__username',
        'user__email',
        'author__username',
        'author__email'
    )

    list_filter = ('user', 'author')
