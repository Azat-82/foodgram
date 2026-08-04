from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Tag, Ingredient, Recipe, Favorite, ShoppingCart

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Tag, Ingredient, Recipe
from .pagination import CustomPagination
from .serializers import (TagSerializer, IngredientSerializer,
                          RecipeReadSerializer, RecipeWriteSerializer)


class IngredientSearchFilter(filters.SearchFilter):
    """Кастомный фильтр для поиска ингредиентов с начала строки."""
    search_param = 'name'


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
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('author', 'tags')

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавление и удаление рецепта из избранного."""
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user

        if request.method == 'POST':
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже в избранном.'}, status=status.HTTP_400_BAD_REQUEST)
            Favorite.objects.create(user=user, recipe=recipe)
            # Возвращаем облегченное представление рецепта для фронтенда
            return Response({'id': recipe.id, 'name': recipe.name, 'image': recipe.image.url, 'cooking_time': recipe.cooking_time}, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            obj = Favorite.objects.filter(user=user, recipe=recipe)
            if obj.exists():
                obj.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response({'errors': 'Рецепта не было в избранном.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавление и удаление рецепта из списка покупок."""
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже в списке покупок.'}, status=status.HTTP_400_BAD_REQUEST)
            ShoppingCart.objects.create(user=user, recipe=recipe)
            return Response({'id': recipe.id, 'name': recipe.name, 'image': recipe.image.url, 'cooking_time': recipe.cooking_time}, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            obj = ShoppingCart.objects.filter(user=user, recipe=recipe)
            if obj.exists():
                obj.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response({'errors': 'Рецепта не было в списке покупок.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """Суммирование ингредиентов из всех рецептов в корзине и выгрузка TXT-файла."""
        user = request.user
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart__user=user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        wishlist = [f'Список покупок для пользователя: {user.username}\n']
        for item in ingredients:
            wishlist.append(
                f'• {item["ingredient__name"]} '
                f'({item["ingredient__measurement_unit"]}) — '
                f'{item["total_amount"]}\n'
            )

        response = HttpResponse(wishlist, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response
