from django.urls import include, path
from rest_framework.routers import DefaultRouter

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

urlpatterns = [
    path(
        'recipes/<int:pk>/get-link/',
        RecipeViewSet.as_view({'get': 'get_link'}),
        name='recipe_get_link'
    ),
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
