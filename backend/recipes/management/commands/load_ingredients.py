import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
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

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        ingredients_to_create = []
        for item in data:
            ingredients_to_create.append(
                Ingredient(
                    name=item['name'],
                    measurement_unit=item['measurement_unit']
                )
            )

        Ingredient.objects.bulk_create(
            ingredients_to_create,
            ignore_conflicts=True
        )

        self.stdout.write(
            self.style.SUCCESS('Ингредиенты успешно загружены в базу данных!')
        )
