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
    """Сериализатор для создания, валидации и отображения подписок."""

    class Meta:
        model = Subscription
        fields = ('user', 'author')

    def validate(self, data):
        user = data['user']
        author = data['author']
        if user == author:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя!'
            )
        if user.subscriptions.filter(author=author).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого автора!'
            )
        return data

    def to_representation(self, instance):
        author = instance.author
        request = self.context.get('request')

        recipes_limit = (
            request.query_params.get('recipes_limit')
            if request else None
        )
        recipes_queryset = author.recipes.all()

        if recipes_limit and recipes_limit.isdigit():
            recipes_queryset = recipes_queryset[:int(recipes_limit)]

        recipes_data = [
            {
                'id': recipe.id,
                'name': recipe.name,
                'image': (
                    request.build_absolute_uri(recipe.image.url)
                    if recipe.image and request else (
                        recipe.image.url if recipe.image else None
                    )
                ),
                'cooking_time': recipe.cooking_time
            }
            for recipe in recipes_queryset
        ]

        avatar_url = None
        if hasattr(author, 'avatar') and author.avatar:
            avatar_url = (
                request.build_absolute_uri(author.avatar.url)
                if request else author.avatar.url
            )

        return {
            'email': author.email,
            'id': author.id,
            'username': author.username,
            'first_name': author.first_name,
            'last_name': author.last_name,
            'is_subscribed': True,
            'recipes': recipes_data,
            'recipes_count': author.recipes.count(),
            'avatar': avatar_url,
        }
