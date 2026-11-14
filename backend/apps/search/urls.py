from django.urls import path

from . import views

urlpatterns = [
    path("search/", views.GlobalSearchView.as_view(), name="search"),
    path("search/posts/", views.PostSearchView.as_view(), name="search-posts"),
    path("search/users/", views.UserSearchView.as_view(), name="search-users"),
    path("search/projects/", views.ProjectSearchView.as_view(), name="search-projects"),
]
