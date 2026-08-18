from django.urls import include, path
from rest_framework.routers import DefaultRouter


def get_router():
    """Ленивый импорт вьюсетов для обхода циклической зависимости."""
    from api.views import (
        FoodgramUserViewSet,
        IngredientViewSet,
        RecipeViewSet,
        TagViewSet,
    )

    router = DefaultRouter()
    router.register('tags', TagViewSet, basename='tags')
    router.register('ingredients', IngredientViewSet, basename='ingredients')
    router.register('recipes', RecipeViewSet, basename='recipes')
    router.register('users', FoodgramUserViewSet, basename='users')
    return router


urlpatterns = [
    path('', include(get_router().urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
