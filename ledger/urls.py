"""URL routing for the ledger application."""

from django.urls import path

from ledger import views

app_name = "ledger"

urlpatterns = [
    path("", views.AccountOverview.as_view(), name="overview"),
    path("accounts/", views.AccountListView.as_view(), name="accounts"),
    path(
        "accounts/<int:pk>/transactions/",
        views.AccountTransactionsView.as_view(),
        name="account_transactions",
    ),
    path("transactions/", views.MetricDrilldownView.as_view(), name="metric"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("review/", views.ReviewListView.as_view(), name="review"),
    path("review/<int:pk>/", views.ReviewDetailView.as_view(), name="review_detail"),
    path("uploads/", views.UploadListView.as_view(), name="uploads"),
    path("uploads/<int:pk>/", views.UploadDetailView.as_view(), name="upload_detail"),
    path(
        "uploads/<int:pk>/original",
        views.UploadOriginalView.as_view(),
        name="upload_original",
    ),
]
