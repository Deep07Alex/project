from django.http import HttpResponse
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from homepage.models import Book
from product_categories.models import Product
from django.views.decorators.http import require_POST
import json
from django.shortcuts import redirect, get_object_or_404
from homepage.models import Book

def search_suggestions(request):
    """Return JSON search results for live autocomplete - no duplicates"""
    query = request.GET.get('q', '').strip()
    results = []
    seen_titles = set()  # Track titles to prevent duplicates
    
    if len(query) >= 2:  
        # Search books from homepage (prioritize these)
        books = Book.objects.filter(
            Q(title__icontains=query) | 
            Q(category__icontains=query)
        )[:5]
        
        # Add books first
        for book in books:
            title_lower = book.title.lower().strip()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                results.append({
                    'title': book.title,
                    'price': str(book.price),
                    'image': book.image.url if book.image else '',
                    'url': f"/books/{book.slug}/",
                    'type': 'Book'
                })
        
        # Search products from product_categories
        products = Product.objects.filter(
            Q(title__icontains=query) | 
            Q(category__name__icontains=query)
        )[:5]
        
        # Add products only if title hasn't been seen
        for product in products:
            title_lower = product.title.lower().strip()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                results.append({
                    'title': product.title,
                    'price': str(product.price),
                    'image': product.image.url if product.image else '',
                    'url': f"/product/{product.id}/",
                    'type': 'Product'
                })
    
    return JsonResponse({'results': results})

def buy_now(request, book_id):
    """Add a single book to cart and redirect to checkout"""
    book = get_object_or_404(Book, id=book_id)
    
    # Clear existing cart and add only this book
    cart = {}
    key = f"book_{book.id}"
    cart[key] = {
        'id': book.id,
        'type': 'book',
        'title': book.title,
        'price': str(book.price),
        'image': book.image.url if book.image else '',
        'quantity': 1
    }
    request.session['cart'] = cart
    request.session.modified = True
    
    return redirect('checkout')

# Cart helper functions
def get_cart(request):
    return request.session.get('cart', {})

def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True

@require_POST
def clear_cart(request):
    """Clear all items from cart"""
    request.session['cart'] = {}
    request.session.modified = True
    return JsonResponse({'success': True})

@require_POST
def add_to_cart(request):
    """Add item to cart via AJAX"""
    try:
        data = json.loads(request.body)
        key = f"{data.get('type')}_{data.get('id')}"
        cart = get_cart(request)
        
        if key in cart:
            cart[key]['quantity'] += 1
        else:
            cart[key] = {
                'id': data.get('id'),
                'type': data.get('type'),
                'title': data.get('title'),
                'price': float(data.get('price')),
                'image': data.get('image', ''),
                'quantity': 1
            }
        
        save_cart(request, cart)
        return JsonResponse({
            'success': True,
            'cart_count': sum(item['quantity'] for item in cart.values()),
            'total': sum(item['price'] * item['quantity'] for item in cart.values())
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
def update_cart_addons(request):
    """Update cart add-ons selection"""
    try:
        data = json.loads(request.body)
        addons = data.get('addons', {})
        request.session['cart_addons'] = addons
        request.session.modified = True
        
        # Calculate addon total
        addon_prices = {'highlighter': 15, 'bookmark': 10, 'packing': 20}
        addon_total = sum(addon_prices.get(key, 0) for key, selected in addons.items() if selected)
        
        return JsonResponse({
            'success': True,
            'addon_total': addon_total
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def get_cart_addons(request):
    """Get cart add-ons and their total"""
    addons = request.session.get('cart_addons', {})
    addon_prices = {'highlighter': 15, 'bookmark': 10, 'packing': 20}
    addon_total = sum(addon_prices.get(key, 0) for key, selected in addons.items() if selected)
    
    return JsonResponse({
        'addons': addons,
        'addon_total': addon_total
    })

# THE CORRECT VERSION WITH ADDON SUPPORT
def get_cart_items(request):
    """Get cart items for display"""
    cart = get_cart(request)
    items = list(cart.values())
    
    # Calculate addon total
    addons = request.session.get('cart_addons', {})
    addon_prices = {'highlighter': 15, 'bookmark': 10, 'packing': 20}
    addon_total = sum(addon_prices.get(key, 0) for key, selected in addons.items() if selected)
    
    product_total = sum(float(item['price']) * item['quantity'] for item in cart.values())
    total = product_total + addon_total
    
    return JsonResponse({
        'cart_count': sum(item['quantity'] for item in cart.values()),
        'items': items,
        'addon_total': addon_total,
        'total': total
    })

@require_POST
def remove_from_cart(request):
    """Remove item from cart"""
    data = json.loads(request.body)
    cart = get_cart(request)
    if data.get('key') in cart:
        del cart[data.get('key')]
        save_cart(request, cart)
    
    return JsonResponse({
        'success': True,
        'cart_count': sum(item['quantity'] for item in cart.values()),
        'total': sum(item['price'] * item['quantity'] for item in cart.values())
    })

@require_POST
def update_cart_quantity(request):
    """Update item quantity"""
    data = json.loads(request.body)
    cart = get_cart(request)
    key = data.get('key')
    
    if key in cart:
        quantity = int(data.get('quantity', 1))
        if quantity <= 0:
            del cart[key]
        else:
            cart[key]['quantity'] = quantity
        save_cart(request, cart)
    
    return JsonResponse({
        'success': True,
        'cart_count': sum(item['quantity'] for item in cart.values()),
        'total': sum(item['price'] * item['quantity'] for item in cart.values())
    })

def search(request):
    """Handle search page requests"""
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        # Search books
        book_results = Book.objects.filter(
            Q(title__icontains=query) | Q(category__icontains=query)
        )
        
        # Search products
        product_results = Product.objects.filter(
            Q(title__icontains=query) | Q(category__name__icontains=query)
        )
        
        # Combine results
        results = list(book_results) + list(product_results)
    
    return render(request, 'pages/search_results.html', {
        'query': query,
        'results': results
    })

# THE CORRECT VERSION WITH ADDON SUPPORT
def checkout(request):
    cart = get_cart(request)
    cart_items = list(cart.values())
    
    # Calculate product subtotal
    subtotal = sum(float(item['price']) * item['quantity'] for item in cart_items)
    
    # Calculate addon total from session
    addons = request.session.get('cart_addons', {})
    addon_prices = {'highlighter': 15, 'bookmark': 10, 'packing': 20}
    addon_total = sum(addon_prices.get(key, 0) for key, selected in addons.items() if selected)
    
    shipping = 49.00
    total = subtotal + shipping + addon_total
    
    # Add initials for placeholder images if image is missing
    for item in cart_items:
        if not item.get('image'):
            words = item['title'].split()
            item['initials'] = ''.join([word[0].upper() for word in words[:2]])
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'addon_total': addon_total,
        'total': total,
        'addons': addons,
    }
    
    return render(request, 'pages/payment.html', context)

def home_page(request):
    return render(request, 'index.html')

def Aboutus(request):
    return render(request, 'pages/Aboutus.html')

def contact_information(request):
    return render(request, 'pages/contactinformation.html')

def bulk_purchase(request):
    return render(request, 'pages/bulk.html')