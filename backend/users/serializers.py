from djoser.serializers import UserSerializer, UserCreateSerializer
from rest_framework import serializers
from .models import User, Subscription


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для регистрации пользователей (все поля обязательны)."""
    
    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'password')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }


class CustomUserSerializer(UserSerializer):
    """Сериализатор для отображения профиля пользователя."""
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(user=request.user, author=obj).exists()
