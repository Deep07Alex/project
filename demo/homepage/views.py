# home/views.py
from django.shortcuts import render, get_object_or_404
from .models import Book

def home_page(request):
    context = {
        'sale_books': Book.objects.filter(category='self_help', on_sale=True).order_by('title'),
        'romance_books': Book.objects.filter(category='romance').order_by('title'),
        'trading_finance_books': Book.objects.filter(category='trading_finance').order_by('title'),
        'manga_books': Book.objects.filter(category='manga').order_by('title'),
    }
    return render(request, 'index.html', context)

def book_detail(request, slug):
    book = get_object_or_404(Book, slug=slug)
    return render(request, 'book_detail.html', {'book': book})

# --- NEW: Category-specific views ---
def sale_page(request):
    books = Book.objects.filter(category='self_help', on_sale=True).order_by('title')
    return render(request, 'pages/sale.html', {'sale_books': books})

def romance_page(request):
    books = Book.objects.filter(category='romance').order_by('title')
    return render(request, 'pages/romance.html', {'romance_books': books})

def trading_finance_page(request):
    books = Book.objects.filter(category='trading_finance').order_by('title')
    return render(request, 'pages/trading_finance.html', {'trading_finance_books': books})

def manga_page(request):
    books = Book.objects.filter(category='manga').order_by('title')
    return render(request, 'pages/manga.html', {'manga_books': books})