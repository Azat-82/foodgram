import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Count, Sum, Min
from django.http import HttpResponse
from django.utils.module_loading import import_string
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
)
from rest_framework.response import Response

from api.filters import RecipeFilter
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

DjoserUserViewSet = import_string('djoser.views.UserViewSet')


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для просмотра тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = None


    def get_queryset(self):
        name = self.request.query_params.get('name')
        if not name:
            return Ingredient.objects.all()

        name = name.strip().lower()
        return Ingredient.objects.filter(name__icontains=name)


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
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        if request.method == 'DELETE':
            favorite_record = user.favorites.filter(recipe=recipe).first()
            if not favorite_record:
                raise serializers.ValidationError(
                    'Рецепта не было в избранном!'
                )
            favorite_record.delete()
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


class FoodgramUserViewSet(DjoserUserViewSet):
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
        from users.models import Subscription

        author_ids = Subscription.objects.filter(user=user).values_list(
            'author_id', flat=True
        )

        queryset = (
            get_user_model()
            .objects.filter(id__in=author_ids)
            .annotate(recipes_count=Count('recipes'))
            .prefetch_related('recipes')
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
        detail=False,
        methods=('put', 'delete'),
        permission_classes=(IsAuthenticated,),
        url_path='me/avatar',
    )
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            avatar_data = request.data.get('avatar')
            if not avatar_data:
                return Response(
                    {'errors': 'Поле avatar обязательно для заполнения.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                if (isinstance(avatar_data, str)
                        and avatar_data.startswith('data:image')):
                    format, imgstr = avatar_data.split(';base64,')
                    ext = format.split('/')[-1]
                    file_name = f'{user.username}_avatar.{ext}'
                    data = ContentFile(
                        base64.b64decode(imgstr),
                        name=file_name
                    )
                    user.avatar.save(file_name, data, save=True)

                    avatar_url = request.build_absolute_uri(
                        user.avatar.url
                    )
                    return Response(
                        {'avatar': avatar_url},
                        status=status.HTTP_200_OK
                    )
            except Exception as e:
                return Response(
                    {'errors': f'Ошибка сохранения картинки: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            return Response(
                {'errors': 'Неверный формат строки base64.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
        url_path='subscribe',
    )
    def subscribe(self, request, id=None):
        user = request.user

        try:
            author = User.objects.get(id=id)  # Ищем по id
        except User.DoesNotExist:
            return Response(
                {'errors': 'Пользователь не найден.'},
                status=status.HTTP_404_NOT_FOUND
            )

        from users.models import Subscription

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'errors': 'Нельзя подписаться на самого себя!'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Subscription.objects.filter(user=user, author=author).exists():
                return Response(
                    {'errors': 'Вы уже подписаны на этого автора!'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Subscription.objects.create(user=user, author=author)
            serializer = SubscriptionSerializer(
                author, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                user=user, author=author
            ).first()
            if not subscription:
                return Response(
                    {'errors': 'Вы не подписаны на этого автора!'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
