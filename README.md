# Foodgram — Продуктовый помощник

## Описание проекта
**Foodgram** — это онлайн-платформа и технологичный сервис для любителей готовить. Проект объединяет авторов и кулинаров, позволяя публиковать пошаговые рецепты, подписываться на публикации других пользователей, добавлять понравившиеся блюда в «Избранное». Главная фишка проекта — автоматическое формирование сводного «Списка покупок» со всеми необходимыми ингредиентами для удобного похода в магазин.

## Деплой и тестирование (Production)
Проект развернут на удаленном сервере и полностью готов к проверке:
* **Адрес сайта:** http://51.250.44.45/recipes
* **Панель администратора (Django Admin):** http://51.250.44.45/admin/

### Данные суперпользователя (is_superuser=True) для проверки:
* **Логин (Email):** admin@foodgram.ru
* **Пароль:** Dlffood9+

---

## Стек технологий
* **Backend:** Python 3.12, Django 4.2, Django REST Framework (DRF), Djoser (авторизация)
* **Database:** PostgreSQL
* **Frontend:** React, JavaScript
* **DevOps & Infrastructure:** Docker, Docker Compose, Nginx, Gunicorn, GitHub Actions (CI/CD)

---

## Как запустить проект локально в Docker

1. Клонируйте репозиторий и перейдите в папку проекта:
   ```bash
   git clone git@github.com:Azat-82/foodgram.git
   cd foodgram
   ```
2. Создайте файл `.env` в папке `infra/` и заполните его переменными окружения (DB_ENGINE, DB_NAME, POSTGRES_USER, POSTGRES_PASSWORD, DB_HOST, DB_PORT, SECRET_KEY).
3. Находясь в папке `infra/`, запустите контейнеры:
   ```bash
   docker compose up -d --build
   ```
4. Выполните миграции и соберите статику внутри контейнера бэкенда:
   ```bash
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py collectstatic --no-input
   ```
5. Проект будет доступен локально по адресу: http://localhost/  
   Документация API (Swagger/Redoc): http://localhost/api/docs/

---

## Примеры запросов к API

* **Получение списка рецептов (с пагинацией по 6 элементов):**
  `GET /api/recipes/?page=1&limit=6`
* **Регистрация нового пользователя:**
  `POST /api/users/` (в Body передать: email, username, first_name, last_name, password)
* **Получение токена авторизации:**
  `POST /api/auth/token/login/` (в Body передать: email, password)

---

## Автор
* **Имя:** Азат Тукбаев
* **GitHub:** [Azat-82](https://github.com/Azat-82/foodgram)
