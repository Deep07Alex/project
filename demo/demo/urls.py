from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views
from user import views as user_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("homepage.urls")),
    path('productcatagory/', include("product_categories.urls")),
    path('aboutus/', views.Aboutus, name="aboutus"),
    path('contactinformation/', views.contact_information, name="contactinformation"),
    path('search/', views.search, name="search"),
    path('search/suggestions/', views.search_suggestions, name="search_suggestions"),
    path('buy-now/<int:book_id>/', views.buy_now, name='buy_now'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/addons/update/', views.update_cart_addons, name='update_cart_addons'),
    path('cart/addons/get/', views.get_cart_addons, name='get_cart_addons'),
    path('cart/items/', views.get_cart_items, name='get_cart_items'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/', views.update_cart_quantity, name='update_cart_quantity'),
    path('checkout/', views.checkout, name='checkout'),
    path('bulkpurchase/', views.bulk_purchase, name='bulk_purchase'),
     path('api/initiate-payment/', user_views.initiate_payu_payment, name='initiate_payu_payment'),
    path('payment/success/', user_views.payment_success, name='payment_success'),
    path('payment/failure/', user_views.payment_failure, name='payment_failure'),
    path('test-hash/', user_views.test_hash, name='test_hash'),
    path('', include("user.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 
