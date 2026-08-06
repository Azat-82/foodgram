import json
import os
from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из JSON файла'

    def handle(self, *args, **options):
        file_path = '/app/ingredients.json'

        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'Файл не найден по пути: {file_path}')
            )
            return

        with open(file_path, 'r', encoding='utf-8') as ingredients_file:
            data = json.load(ingredients_file)

        ingredients_to_create = [
            Ingredient(
                name=item['name'],
                measurement_unit=item['measurement_unit']
            )
            for item in data
        ]

        Ingredient.objects.bulk_create(ingredients_to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно загружено {len(ingredients_to_create)} ингредиентов.'
            )
        )
