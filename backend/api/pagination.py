from rest_framework.pagination import PageNumberPagination


class LimitPageNumberPagination(PageNumberPagination):
    """Кастомный пагинатор с изменением имени параметра размера страницы."""

    page_size = 6
    page_size_query_param = 'limit'
