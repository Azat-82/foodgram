from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from recipes.models import (
    Tag, Ingredient, Recipe, RecipeIngredient, Favorite, ShoppingCart
)
from users.models import Subscription
from .fields import Base64ImageField

User = get_user_model()


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
        return request.user.follower.filter(author=obj).exists()


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с тегами."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с ингредиентами."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения ингредиентов внутри рецепта."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для записи ингредиентов при создании рецепта."""

    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        validators=(
            MinValueValidator(1, message='Минимальное количество — 1!'),
        )
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для безопасного отображения рецептов (GET)."""

    tags = TagSerializer(many=True, read_only=True)
    author = FoodgramUserSerializer(read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        many=True,
        source='recipe_ingredients'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return obj.favorite_recipes.filter(user=request.user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return obj.shopping_cart_recipes.filter(user=request.user).exists()


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов (POST, PATCH)."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    ingredients = RecipeIngredientWriteSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )

    def _save_ingredients(self, recipe, ingredients_data):
        recipe.recipe_ingredients.all().delete()

        ingredients_to_create = [
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients_data
        ]

        RecipeIngredient.objects.bulk_create(ingredients_to_create)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self._save_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        instance = super().update(instance, validated_data)

        if tags_data is not None:
            instance.tags.set(tags_data)
        if ingredients_data is not None:
            self._save_ingredients(instance, ingredients_data)

        return instance

    def to_representation(self, instance):
        context = {'request': self.context.get('request')}
        return RecipeReadSerializer(instance, context=context).data


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления рецептов в избранное."""

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if user.favorites.filter(recipe=recipe).exists():
            raise serializers.ValidationError(
                'Рецепт уже добавлен в избранное.'
            )
        return data

    def to_representation(self, instance):
        return {
            'id': instance.recipe.id,
            'name': instance.recipe.name,
            'image': (
                instance.recipe.image.url
                if instance.recipe.image else None
            ),
            'cooking_time': instance.recipe.cooking_time,
        }


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления рецептов в список покупок."""

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if user.shopping_carts.filter(recipe=recipe).exists():
            raise serializers.ValidationError('Рецепт уже в списке покупок.')
        return data

    def to_representation(self, instance):
        return {
            'id': instance.recipe.id,
            'name': instance.recipe.name,
            'image': (
                instance.recipe.image.url
                if instance.recipe.image else None
            ),
            'cooking_time': instance.recipe.cooking_time,
        }


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
        if user.follower.filter(author=author).exists():
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

        recipes_data = tuple(
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
        )

        avatar_url = None
        if hasattr(author, 'avatar') and author.avatar:
            try:
                avatar_url = (
                    request.build_absolute_uri(author.avatar.url)
                    if request else author.avatar.url
                )
            except ValueError:
                avatar_url = None

        return {
            'email': author.email,
            'id': author.id,
            'username': author.username,
            'first_name': author.first_name,
            'last_name': author.last_name,
            'is_subscribed': True,
            'recipes': list(recipes_data),
            'recipes_count': int(author.recipes.count()),
            'avatar': avatar_url,
        }
