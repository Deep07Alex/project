# home/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home_page'),
    path('books/<slug:slug>/', views.book_detail, name='book_detail'),
    
    # Category pages
    path('sale/', views.sale_page, name='sale'),
    path('romance/', views.romance_page, name='romance'),
    path('trading-finance/', views.trading_finance_page, name='trading-finance'),
    path('manga/', views.manga_page, name='manga'),
]