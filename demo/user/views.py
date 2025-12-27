from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.shortcuts import render
from .models import PhoneVerification, Order, OrderItem
from .payu_utils import generate_payu_hash, generate_transaction_id, verify_payu_hash
from .utils import send_otp_to_user, send_customer_order_confirmation, send_admin_order_notification
import json
import logging
import uuid

logger = logging.getLogger(__name__)

@require_POST
def send_otp(request):
    """Send OTP to user's phone via SMS or WhatsApp"""
    try:
        data = json.loads(request.body)
        phone = data.get('phone', '').strip()
        delivery_method = data.get('delivery_method', 'sms')
        
        # Validate phone
        if not phone or len(phone) < 10:
            return JsonResponse({
                'success': False,
                'error': 'Please enter a valid phone number'
            })
        
        # Clean phone number
        if not phone.startswith('+'):
            phone = f"+91{phone}" 
        
        # Generate and save OTP
        verification = PhoneVerification(
            phone_number=phone,
            delivery_method=delivery_method
        )
        otp = verification.generate_otp()
        verification.save()
        
        # Send OTP to user
        success, message = send_otp_to_user(phone, otp, delivery_method)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'OTP sent via {delivery_method}',
                'verification_id': verification.id
            })
        else:
            # Delete the verification record if sending failed
            verification.delete()
            return JsonResponse({
                'success': False,
                'error': f'Failed to send OTP: {message}'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_POST
def verify_otp(request):
    """Verify OTP and unlock address section"""
    try:
        data = json.loads(request.body)
        verification_id = data.get('verification_id')
        otp = data.get('otp', '').strip()
        
        try:
            verification = PhoneVerification.objects.get(id=verification_id)
        except PhoneVerification.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid verification session'
            })
        
        # Check expiry
        if verification.is_expired():
            verification.delete()
            return JsonResponse({
                'success': False,
                'error': 'OTP has expired. Please request a new one.'
            })
        
        # Verify OTP
        if verification.otp == otp:
            verification.is_verified = True
            verification.save()
            
            # Store in session that phone is verified
            request.session['verified_phone'] = verification.phone_number
            request.session['verification_id'] = verification.id
            
            return JsonResponse({
                'success': True,
                'message': 'Phone verified successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid OTP. Please try again.'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_POST
def resend_otp(request):
    """Resend OTP for existing verification"""
    try:
        data = json.loads(request.body)
        verification_id = data.get('verification_id')
        
        try:
            verification = PhoneVerification.objects.get(id=verification_id)
        except PhoneVerification.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid verification session'
            })
        
        # Generate new OTP
        otp = verification.generate_otp()
        verification.save()
        
        # Send OTP to user
        success, message = send_otp_to_user(
            verification.phone_number, 
            otp, 
            verification.delivery_method
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'OTP resent via {verification.delivery_method}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Failed to resend OTP: {message}'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_POST
def initiate_payu_payment(request):
    try:
        if not request.session.get('verified_phone'):
            return JsonResponse({'success': False, 'error': 'Phone not verified'})
        
        data = json.loads(request.body)
        cart = request.session.get('cart', {})
        addons = request.session.get('cart_addons', {})
        
        if not cart:
            return JsonResponse({'success': False, 'error': 'Cart is empty'})
        
        verification = PhoneVerification.objects.get(
            id=request.session.get('verification_id'),
            is_verified=True
        )
        
        # Calculate totals
        subtotal = sum(float(item['price']) * item['quantity'] for item in cart.values())
        
        # Calculate addon total
        addon_prices = {'highlighter': 15, 'bookmark': 10, 'packing': 20}
        addon_total = sum(addon_prices.get(key, 0) for key, selected in addons.items() if selected)
        
        shipping = 49.00
        total = subtotal + shipping + addon_total
        
        # Create order
        order = Order.objects.create(
            phone_number=verification.phone_number,
            full_name=data.get('fullname'),
            email=data.get('email'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            pin_code=data.get('pin'),
            delivery_type=data.get('delivery'),
            payment_method=data.get('payment_method'),
            subtotal=subtotal,
            shipping=shipping,
            total=total,
            status='pending'
        )
        
        # Create order items for products
        for key, item in cart.items():
            OrderItem.objects.create(
                order=order,
                item_type=item['type'],
                item_id=item['id'],
                title=item['title'],
                price=float(item['price']),
                quantity=item['quantity'],
                image_url=item.get('image', '')
            )
        
        # Create order items for add-ons
        addon_names = {'highlighter': 'Highlighter', 'bookmark': 'Bookmark', 'packing': 'Packing'}
        for addon_key, selected in addons.items():
            if selected:
                OrderItem.objects.create(
                    order=order,
                    item_type='addon',
                    item_id=0,
                    title=addon_names[addon_key],
                    price=addon_prices[addon_key],
                    quantity=1,
                    image_url=''
                )
        
        # ... rest of the function continues as before ...
        # CRITICAL: Clean phone number
        phone = verification.phone_number
        phone = phone.replace('+91', '').replace(' ', '').strip()
        if len(phone) != 10:
            return JsonResponse({'success': False, 'error': 'Phone must be exactly 10 digits'})
        
        # Generate PayU params
        txnid = generate_transaction_id()
        product_info = f"Book Order {order.id}"  
        
        payu_params = {
            'key': settings.PAYU_MERCHANT_KEY,
            'txnid': txnid,
            'amount': f"{total:.2f}",  # This now includes addons
            'productinfo': product_info,
            'firstname': order.full_name.split()[0][:50],
            'email': order.email[:50],
            'phone': phone,
            'surl': request.build_absolute_uri('/payment/success/'),
            'furl': request.build_absolute_uri('/payment/failure/'),
            'udf1': str(order.id),
            'udf2': '',
            'udf3': '',
            'udf4': '',
            'udf5': '',
        }
        
        # Generate hash
        payu_params['hash'] = generate_payu_hash(payu_params)
        
        request.session['payu_txnid'] = txnid
        
        payu_url = settings.PAYU_TEST_URL
        
        return JsonResponse({
            'success': True,
            'payu_url': payu_url,
            'payu_params': payu_params
        })
        
    except Exception as e:
        logger.error(f"PAYMENT INIT ERROR: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
def payment_success(request):
    """Handle successful PayU payment return"""
    if request.method == 'POST':
        response_data = request.POST.dict()
        
        # Verify hash
        received_hash = response_data.get('hash', '')
        calculated_hash = verify_payu_hash(response_data)
        
        print(f"RECEIVED HASH: {received_hash}")
        print(f"CALCULATED HASH: {calculated_hash}")
        
        if received_hash == calculated_hash:
            # Hash verified - payment is legitimate
            order_id = response_data.get('udf1')
            status = response_data.get('status')
            
            try:
                order = Order.objects.get(id=order_id)
                
                if status == 'success':
                    order.status = 'processing'  # Payment successful
                    order.save()
                    
                    # Get order items for notifications
                    items = order.items.all()
                    
                    # Get customer's delivery preference from verification
                    try:
                        verification = PhoneVerification.objects.filter(
                            phone_number=order.phone_number
                        ).latest('created_at')
                        customer_delivery_method = verification.delivery_method
                    except:
                        customer_delivery_method = 'sms'  # Default fallback
                    
                    # --- SEND DUAL NOTIFICATIONS ---
                    
                    # 1. Notify ADMIN via EMAIL
                    admin_success, admin_msg = send_admin_order_notification(order, items)
                    if not admin_success:
                        print(f"⚠️ Admin notification failed: {admin_msg}")
                    
                    # 2. Notify CUSTOMER via SMS/WhatsApp
                    customer_success, customer_msg = send_customer_order_confirmation(
                        order, items, customer_delivery_method
                    )
                    if not customer_success:
                        print(f"⚠️ Customer notification failed: {customer_msg}")
                    
                    # Clear cart and session
                    if 'cart' in request.session:
                        del request.session['cart']
                    if 'verified_phone' in request.session:
                        del request.session['verified_phone']
                    if 'verification_id' in request.session:
                        del request.session['verification_id']
                    if 'payu_txnid' in request.session:
                        del request.session['payu_txnid']
                    
                    return render(request, 'pages/payment_success.html', {
                        'order': {
                            'order_id': order.id,
                            'total': order.total,
                            'status': 'Paid'
                        },
                        'notification_sent': customer_success
                    })
                else:
                    # Payment failed - delete the order
                    order.delete()
                    return render(request, 'pages/payment_failure.html', {
                        'error': f'Payment status: {status}'
                    })
                    
            except Order.DoesNotExist:
                return render(request, 'pages/payment_failure.html', {
                    'error': 'Order not found'
                })
        else:
            # Hash mismatch - possible tampering
            print("HASH MISMATCH - Possible tampering attempt!")
            return render(request, 'pages/payment_failure.html', {
                'error': 'Security verification failed'
            })
    
    return render(request, 'pages/payment_failure.html', {
        'error': 'Invalid request method'
    })


@csrf_exempt
def payment_failure(request):
    """Handle failed/cancelled PayU payment"""
    if request.method == 'POST':
        response_data = request.POST.dict()
        
        # Try to get order ID and delete pending order
        order_id = response_data.get('udf1')
        if order_id:
            try:
                order = Order.objects.get(id=order_id, status='pending')
                order.delete()  # Remove pending order
            except Order.DoesNotExist:
                pass
        
        error_message = response_data.get('error_Message', 'Payment failed')
        return render(request, 'pages/payment_failure.html', {
            'error': error_message
        })

    return render(request, 'pages/payment_failure.html', {
        'error': 'Payment cancelled or failed'
    })

def test_hash(request):
    """Test hash generation against PayU's example"""
    test_params = {
        'key': 'kdbOTy',
        'txnid': 'TXN-378A9FCDF2DB',
        'amount': '248.00',
        'productinfo': 'Book Order 9',
        'firstname': 'Aritra',
        'email': 'aritradatt39@gmail.com',
        'udf1': '9',
        'udf2': '',
        'udf3': '',
        'udf4': '',
        'udf5': '',
    }
    
    # Temporarily override salt
    original_salt = settings.PAYU_MERCHANT_SALT
    settings.PAYU_MERCHANT_SALT = 'BKipBlA1YKJopYdzyBtErUmRUkkXMPiU'
    
    generated_hash = generate_payu_hash(test_params)
    
    # Restore original salt
    settings.PAYU_MERCHANT_SALT = original_salt
    
    expected_hash = "c95324fa66e20bd8a4a080a22419a6a9bdfb92992b0096c09f7511629329f31ed6f85f7ebce004535e36009c26648a2333934135f903436f5f3e870cc4458f06"
    
    return HttpResponse(f"""
        <h1>Hash Test Results</h1>
        <p><strong>Generated:</strong> {generated_hash}</p>
        <p><strong>Expected:</strong> {expected_hash}</p>
        <p><strong>Match:</strong> {generated_hash == expected_hash}</p>
    """)
    