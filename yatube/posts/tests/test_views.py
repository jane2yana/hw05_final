import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Follow, Group, Post
from posts.utils import print_func_info

User = get_user_model()


class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='TestPotest')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=('Тестовый пост' * 15),
            group=cls.group
        )

        cls.urls_names_templates = (
            ('posts:index', None, 'posts/index.html'),
            ('posts:group_list', (cls.group.slug,), 'posts/group_list.html',),
            ('posts:profile', (cls.user,), 'posts/profile.html',),
            ('posts:post_detail', (cls.post.id,), 'posts/post_detail.html',),
            ('posts:post_create', None, 'posts/create_post.html',),
            ('posts:post_edit', (cls.post.id,), 'posts/create_post.html',),
        )
        cls.user2 = User.objects.create_user(username='TestTestov')

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsPagesTests.user)
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(PostsPagesTests.user2)

    @print_func_info
    def test_pages_uses_correct_template(self):
        """Проверка соответствия пути namespace:name и шаблона"""
        cache.clear()
        for url, args, template in PostsPagesTests.urls_names_templates:
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse(url, args=args))
                self.assertTemplateUsed(response, template)

    @print_func_info
    def test_index_page_show_correct_context(self):
        """Главная страница получает правильный контекст."""
        cache.clear()
        response = self.guest_client.get(reverse("posts:index"))
        self.assertEqual(
            response.context['page_obj'].object_list,
            list(Post.objects.all()[:10]),
        )

    @print_func_info
    def test_group_list_show_correct_context(self):
        """Страница group list получает правильный контекст."""
        response = self.guest_client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
        )
        self.assertEqual(
            response.context.get('page_obj').object_list,
            list(Post.objects.filter(group_id=self.group.id)[:10]),
        )

    @print_func_info
    def test_post_detail_show_correct_context(self):
        """Страница post detail получает правильный контекст."""
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(
            response.context.get('post'),
            Post.objects.filter(id=self.post.id)[0],
        )

    @print_func_info
    def test_profile_show_correct_context(self):
        """Страница profile получает правильный контекст."""
        response = self.guest_client.get(
            reverse("posts:profile", kwargs={"username": self.post.author})
        )
        self.assertEqual(
            response.context.get('page_obj').object_list,
            list(Post.objects.filter(author=self.post.author)[:10]),
        )

    @print_func_info
    def test_create_show_correct_context(self):
        """Страница create получает правильный контекст."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    @print_func_info
    def test_post_edit_show_correct_context(self):
        """Страница post edit получает правильный контекст."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    @print_func_info
    def test_comment_correct_context(self):
        """Валидная форма создает запись комментария в Post."""
        comments_count = Comment.objects.count()
        form_data = {'text': 'Тестовый комментарий'}
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(Comment.objects.filter(
            text=form_data['text']).exists()
        )

    @print_func_info
    def test_check_cache(self):
        """Проверка кеша."""
        response = self.guest_client.get(reverse('posts:index'))
        Post.objects.create(text='cach_check', author=self.user,)
        response2 = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response.content, response2.content)
        cache.clear()
        response_new = self.guest_client.get(reverse('posts:index'))
        self.assertNotEqual(response2.content, response_new.content)

    @print_func_info
    def test_follow_page(self):
        """Тест правильной работы подписки."""
        response = self.authorized_client2.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 0)

        Follow.objects.get_or_create(user=self.user2, author=self.post.author)
        response = self.authorized_client2.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertIn(self.post, response.context['page_obj'])

        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(self.post, response.context['page_obj'])

    @print_func_info
    def test_unfollow_page(self):
        """Проверка отписок."""
        Follow.objects.get_or_create(user=self.user2, author=self.post.author)
        response = self.authorized_client2.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 1)
        
        Follow.objects.all().delete()
        response = self.authorized_client2.get(reverse("posts:follow_index"))
        self.assertEqual(len(response.context["page_obj"]), 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.posts = Post.objects.bulk_create(
            Post(
                author=cls.user,
                text='Тестовый пост' * 15,
                group=cls.group
            )
            for i in range(13)
        )

    @print_func_info
    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorViewsTest.user)
        self.cache = cache.clear()

    @print_func_info
    def test_first_page_contains_ten_records(self):
        """Количество постов на первой странице равно 10."""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)

    @print_func_info
    def test_second_page_contains_three_records(self):
        """Проверка продолжения на второй странице."""
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class MediaPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="ImageTestov")
        cls.group = Group.objects.create(
            title="Test group",
            slug="test_group_slug",
            description="Test group description",
        )
        cls.small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        cls.uploaded = SimpleUploadedFile(
            name="small.gif", content=cls.small_gif, content_type="image/gif"
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            image=cls.uploaded
        )
        cls.urls_names_templates = (
            ('posts:index', None,),
            ('posts:group_list', (cls.group.slug,),),
            ('posts:profile', (cls.user,),),
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.cache = cache.clear()

    def test_image_in_pages(self):
        """Картинка передается на основные страницы."""
        for name, args in MediaPagesTests.urls_names_templates:
            with self.subTest(name=name):
                response = self.guest_client.get(reverse(name, args=args))
                obj = response.context['page_obj'][0]
                self.assertEqual(obj.image, self.post.image)

    def test_image_in_post_detail_page(self):
        """Картинка передается на страницу post_detail."""
        response = self.guest_client.get(
            reverse("posts:post_detail", kwargs={'post_id': self.post.id})
        )
        obj = response.context['post']
        self.assertEqual(obj.image, self.post.image)

    def test_image_in_page(self):
        """Проверяем что пост с картинкой создается в БД"""
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый текст',
                image='posts/small.gif'
            ).exists()
        )
