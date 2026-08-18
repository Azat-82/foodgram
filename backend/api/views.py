from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated, IsAuthenticatedOrReadOnly,  AllowAny
)
from rest_framework.response import Response

from api.filters import IngredientSearchFilter, RecipeFilter
from api.serializers import (
    FavoriteSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    ShoppingCartSerializer,
    SubscriptionSerializer,
    TagSerializer,
)
from recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Tag,
)
from .pagination import LimitPageNumberPagination

User = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для просмотра тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для просмотра ингредиентов с поиском по названию."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = None
    filter_backends = (IngredientSearchFilter,)
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с рецептами (создание, чтение, обновление)."""

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = LimitPageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def shopping_cart(self, request, pk=None):
        user = request.user
        recipe = self.get_object()

        if request.method == 'POST':
            serializer = ShoppingCartSerializer(
                data={'user': user.id, 'recipe': recipe.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            deleted_count, _ = (
                user.shopping_carts.filter(recipe=recipe).delete()
            )
            if deleted_count == 0:
                # Сериализатор не используется, так как нет
                # входящих данных для валидации.
                raise serializers.ValidationError(
                    'Рецепта не было в списке покупок!'
                )

            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        user = request.user
        recipe = self.get_object()

        if request.method == 'POST':
            serializer = FavoriteSerializer(
                data={'user': user.id, 'recipe': recipe.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            deleted_count, _ = user.favorites.filter(recipe=recipe).delete()
            if deleted_count == 0:
                raise serializers.ValidationError(
                    'Рецепта не было в избранном!'
                )

            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart_recipes__user=user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        header = f'Список покупок для пользователя: {user.username}\n'

        shopping_list = '\n'.join(
            f'• {item["ingredient__name"]} '
            f'({item["ingredient__measurement_unit"]}) — '
            f'{item["total_amount"]}'
            for item in ingredients
        )

        wishlist_text = f'{header}\n{shopping_list}'

        response = HttpResponse(
            wishlist_text,
            content_type='text/plain; charset=utf-8',
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    @action(
        detail=True,
        url_path='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = request.build_absolute_uri(f'/s/{recipe.id}/')
        return Response(
            {'short-link': short_link},
            status=status.HTTP_200_OK
        )


class FoodgramUserViewSet(UserViewSet):
    """Вьюсет для работы с пользователями, подписками и аватарами."""

    lookup_url_kwarg = 'id'

    def get_queryset(self):
        return get_user_model().objects.all()

    def get_permissions(self):
        if self.action == 'retrieve':
            return (AllowAny(),)
        return super().get_permissions()

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        user = request.user

        queryset = (
            user.follower
            .select_related('author')
            .annotate(recipes_count=Count('author__recipes'))
            .prefetch_related('author__recipes')
        )

        paginator = (
            self.pagination_class()
            if self.pagination_class
            else LimitPageNumberPagination()
        )

        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = SubscriptionSerializer(
                page, many=True, context={'request': request}
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(
            {
                'count': queryset.count(),
                'next': None,
                'previous': None,
                'results': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def subscribe(self, request, pk=None):
        user = request.user
        author = self.get_object()

        if request.method == 'POST':
            if user == author:
                raise serializers.ValidationError(
                    'Нельзя подписаться на самого себя!'
                )
            if user.follower.filter(author=author).exists():
                raise serializers.ValidationError(
                    'Вы уже подписаны на этого автора!'
                )

            Subscription.objects.create(user=user, author=author)

            serializer = SubscriptionSerializer(
                author,
                context={'request': request}
            )
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        if request.method == 'DELETE':
            deleted_count, _ = user.follower.filter(author=author).delete()
            if deleted_count == 0:
                raise serializers.ValidationError(
                    'Вы не были подписаны на этого автора!'
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('put', 'delete'),
        permission_classes=(IsAuthenticated,),
        url_path='me/avatar',
    )
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            serializer = AvatarSerializer(
                user,
                data=request.data
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=True)
            return Response(
                status=status.HTTP_204_NO_CONTENT
            )


def short_link_redirect(request, pk):
    return redirect(f'/recipes/{pk}/')
