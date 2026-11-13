"""Convention unique de pagination de l'API."""

from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Pagination par numéro de page, taille configurable et bornée."""

    page_size_query_param = "page_size"

    @property
    def max_page_size(self) -> int:
        return settings.API_MAX_PAGE_SIZE
