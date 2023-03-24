from django.core.paginator import Paginator


def paginate_page(request, post_list, post_per_page=10):
    paginator = Paginator(post_list, post_per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def print_func_info(func):
    def wrapper(*args, **kwargs):
        if func.__doc__:
            print(f'>{func.__doc__}<')
        return func(*args, **kwargs)
    return wrapper
