from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User, Subscription
from .serializers import CustomUserSerializer


class CustomUserViewSet(UserViewSet):
    """Кастомный вьюсет для работы с пользователями, подписками и аватарами."""

    @action(detail=False, permission_classes=[IsAuthenticated], url_path='me/avatar')
    def avatar(self, request):
        """Метод для сохранения или удаления аватара текущего пользователя."""
        user = request.user
        if request.method == 'PUT':
            if 'avatar' not in request.data:
                return Response({'error': 'Файл аватара обязателен'}, status=status.HTTP_400_BAD_REQUEST)
            user.avatar = request.data['avatar']
            user.save()
            return Response({'avatar': user.avatar.url}, status=status.HTTP_200_OK)

        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        """Метод для оформления и отмены подписки на автора."""
        author = get_object_or_404(User, id=id)
        user = request.user

        if request.method == 'POST':
            if user == author:
                return Response({'errors': 'Нельзя подписаться на самого себя'}, status=status.HTTP_400_BAD_REQUEST)
            if Subscription.objects.filter(user=user, author=author).exists():
                return Response({'errors': 'Вы уже подписаны на этого автора'}, status=status.HTTP_400_BAD_REQUEST)

            Subscription.objects.create(user=user, author=author)
            serializer = CustomUserSerializer(author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            subscription = Subscription.objects.filter(user=user, author=author)
            if subscription.exists():
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response({'errors': 'Вы не были подписаны на этого автора'}, status=status.HTTP_400_BAD_REQUEST)
