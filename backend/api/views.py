from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated, IsAuthenticatedOrReadOnly
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
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Subscription
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
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,),
    )
    def shopping_cart(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            shopping_cart, created = ShoppingCart.objects.get_or_create(
                user=user,
                recipe=recipe
            )
            if not created:
                return Response(
                    {'errors': 'Рецепт уже в списке покупок!'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = ShoppingCartSerializer(
                shopping_cart, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            deleted_count, _ = ShoppingCart.objects.filter(
                user=user,
                recipe=recipe
            ).delete()

            if deleted_count == 0:
                return Response(
                    {'errors': 'Рецепта не было в списке покупок!'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)

        if request.method == 'POST':
            favorite, created = Favorite.objects.get_or_create(
                user=user,
                recipe=recipe
            )
            if not created:
                return Response(
                    {'errors': 'Рецепт уже в избранном!'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = FavoriteSerializer(
                favorite, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            deleted_count, _ = Favorite.objects.filter(
                user=user,
                recipe=recipe
            ).delete()

            if deleted_count == 0:
                return Response(
                    {'errors': 'Рецепта не было в избранном!'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
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
        methods=('get',),
        url_path='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = request.build_absolute_uri(f'/recipes/{recipe.id}/')
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)


class FoodgramUserViewSet(UserViewSet):
    """Вьюсет для работы с пользователями, подписками и аватарами."""

    @action(
        detail=False,
        methods=['get'],
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        user = request.user
        queryset = Subscription.objects.filter(user=user)

        paginator = LimitPageNumberPagination()

        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = SubscriptionSerializer(
                page, many=True, context={'request': request}
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,),
    )
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(get_user_model(), id=id)

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'errors': 'Нельзя подписаться на самого себя!'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subscription, created = Subscription.objects.get_or_create(
                user=user,
                author=author
            )
            if not created:
                return Response(
                    {'errors': 'Вы уже подписаны на этого автора!'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = SubscriptionSerializer(
                subscription, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            deleted_count, _ = Subscription.objects.filter(
                user=user,
                author=author
            ).delete()

            if deleted_count == 0:
                return Response(
                    {'errors': 'Вы не были подписаны на этого автора!'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(status=status.HTTP_204_NO_CONTENT)
