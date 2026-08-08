from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from .models import Subscription

User = get_user_model()


class FoodgramUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для регистрации пользователей (все поля обязательны)."""

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }


class FoodgramUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(
            user=request.user,
            author=obj,
        ).exists()

class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и валидации подписок."""

    class Meta:
        model = Subscription
        fields = ('user', 'author')

    def validate(self, data):
        user = data['user']
        author = data['author']

        if user == author:
            raise serializers.ValidationError('Нельзя подписаться на самого себя!')

        if user.subscriptions.filter(author=author).exists():
            raise serializers.ValidationError('Вы уже подписаны на этого автора!')

        return data

    def to_representation(self, instance):
        return FoodgramUserSerializer(
            instance.author, 
            context=self.context
        ).data
