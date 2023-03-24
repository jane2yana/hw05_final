from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from posts.utils import print_func_info

from ..models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.user = User.objects.create_user(username='TestPotest')
        cls.authorized_client.force_login(cls.user)
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

        cls.urls_templates = (
            ('/', 'posts/index.html'),
            (f'/group/{cls.group.slug}/', 'posts/group_list.html',),
            (f'/profile/{cls.user}/', 'posts/profile.html',),
            (f'/posts/{cls.post.id}/', 'posts/post_detail.html',),
            ('/create/', 'posts/create_post.html',),
            (f'/posts/{cls.post.id}/edit/', 'posts/create_post.html',),
        )

    def setUp(self):
        self.cache = cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    @print_func_info
    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for url, template in PostsURLTests.urls_templates:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    @print_func_info
    def test_guest_client_url_access(self):
        url_for_all = (
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.user}/',
            f'/posts/{self.post.id}/',
        )
        for url in url_for_all:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    @print_func_info
    def test_unauthorised_reverse(self):
        url_for_auth = (
            '/create/',
            f'/posts/{self.post.id}/edit/',
        )
        for url in url_for_auth:
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(
                    response, f'/auth/login/?next={url}')

    @print_func_info
    def test_author_post_edit_url(self):
        post = PostsURLTests.post
        authorized_client = PostsURLTests.authorized_client
        response = authorized_client.get(f'/posts/{post.id}/edit/')
        self.assertEqual(
            response.status_code,
            HTTPStatus.OK,
            'Редактирование поста не доступно автору'
        )

    @print_func_info
    def test_unexisting_page_error(self):
        clients = (
            'guest_client',
            'authorized_client',
        )
        for client in clients:
            with self.subTest(client=client):
                response = self.client.get('/unexisting_page/')
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
