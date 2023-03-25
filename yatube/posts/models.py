from core.models import CreatedModel
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Group(models.Model):
    title = models.CharField(
        max_length=200,
        verbose_name='Название группы',
        help_text='Не больше 200 знаков'
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='Имя ссылки',
        help_text=(
            'Введите название ссылки на стр. после "/"\n'
            'Не больше 100 знаков'
        )
    )
    description = models.TextField(
        max_length=1000,
        verbose_name='Описание группы',
        help_text='Не больше 1000 знаков'
    )

    def __str__(self) -> str:
        return self.title


class Post(models.Model):
    text = models.TextField(
        max_length=3000,
        verbose_name='Текст поста',
        help_text='Не больше 3000 знаков'
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор поста',
        help_text='Выберите автора'
    )
    group = models.ForeignKey(
        Group,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name='Сообщество',
        help_text='Выберите группу для поста'
    )

    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ('-pub_date',)
        default_related_name = 'posts'

    def __str__(self):
        return self.text[:15]


class Comment(CreatedModel):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        verbose_name='Комментарий',
        help_text='Напишите свое мнение',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор комментария',
    )
    text = models.TextField(
        max_length=500,
        verbose_name='Текст комментария',
        help_text='Не больше 500 знаков'
    )

    class Meta:
        ordering = ('-created',)
        default_related_name = 'comments'


class Follow(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'user'],
                name='unique_author_user'
            ),
        ]
