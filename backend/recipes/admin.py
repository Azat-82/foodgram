from django.contrib import admin
from .models import Tag, Ingredient, Recipe, RecipeIngredient


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    min_num = 1


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'get_favorite_count')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    inlines = (RecipeIngredientInline,)

    @admin.display(description='Добавлений в избранное')
    def get_favorite_count(self, obj):
        return 0
