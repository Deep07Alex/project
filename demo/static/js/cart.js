// Wrap everything in DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded: Cart initializing...');
    
    class CartManager {
        constructor() {
            this.cartCountEl = document.getElementById('cartCount');
            this.cartSidebar = document.getElementById('cartSidebar');
            this.cartOverlay = document.getElementById('cartOverlay');
            this.cartIcon = document.getElementById('cartIcon');
            this.addonTotal = 0;
            
            console.log('CartManager: Elements found:', {
                cartCountEl: this.cartCountEl,
                cartSidebar: this.cartSidebar,
                cartOverlay: this.cartOverlay,
                cartIcon: this.cartIcon
            });
            
            if (!this.cartSidebar || !this.cartOverlay) {
                console.error('CartManager: Required elements missing');
                return;
            }
            
            this.init();
        }
        
        init() {
            this.attachEventListeners();
            this.updateCartDisplay();
            console.log('CartManager: Fully initialized');
        }
        
        attachEventListeners() {
            // Cart icon toggle
            if (this.cartIcon) {
                console.log('CartManager: Attaching cart icon listener');
                this.cartIcon.addEventListener('click', () => this.openCart());
            }
            
            // Close button
            const closeBtn = document.getElementById('closeCartBtn');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.closeCart());
            }
            
            // Overlay click to close
            this.cartOverlay.addEventListener('click', () => this.closeCart());
            
            // Add to cart buttons (event delegation)
            document.addEventListener('click', (e) => {
                if (e.target.classList.contains('add-to-cart-btn')) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const btn = e.target;
                    console.log('Add to cart clicked:', {
                        id: btn.dataset.id,
                        type: btn.dataset.type,
                        title: btn.dataset.title,
                        price: btn.dataset.price,
                        image: btn.dataset.image
                    });
                    
                    this.addToCart({
                        id: btn.dataset.id,
                        type: btn.dataset.type,
                        title: btn.dataset.title,
                        price: btn.dataset.price,
                        image: btn.dataset.image
                    });
                }
            });
        }
        
        async addToCart(product) {
            console.log('CartManager.addToCart called with:', product);
            
            try {
                const csrfToken = this.getCSRFToken();
                console.log('CSRF Token:', csrfToken);
                
                // Show visual feedback immediately
                this.showNotification('Adding to cart...');
                
                const response = await fetch('/cart/add/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify(product)
                });
                
                const data = await response.json();
                console.log('Add to cart response:', data);
                
                if (data.success) {
                    await this.updateCartDisplay();
                    this.showNotification('Added to cart!');
                    
                    // FIX: Auto-open cart after adding item
                    setTimeout(() => {
                        this.openCart();
                    }, 150);
                } else {
                    console.error('Add to cart failed:', data.error);
                    alert('Failed to add to cart: ' + data.error);
                }
            } catch (error) {
                console.error('Cart add error:', error);
                alert('Network error: ' + error.message);
            }
        }
        
        async removeFromCart(key) {
            await fetch('/cart/remove/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': this.getCSRFToken()},
                body: JSON.stringify({ key })
            });
            this.updateCartDisplay();
        }
        
        async updateQuantity(key, quantity) {
            await fetch('/cart/update/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': this.getCSRFToken()},
                body: JSON.stringify({ key, quantity })
            });
            this.updateCartDisplay();
        }
        
        async updateCartDisplay() {
            try {
                const response = await fetch('/cart/items/');
                const data = await response.json();
                
                console.log('Cart display data:', data);
                
                if (this.cartCountEl) {
                    if (data.cart_count > 0) {
                        this.cartCountEl.textContent = data.cart_count;
                        this.cartCountEl.style.display = 'flex';
                    } else {
                        this.cartCountEl.style.display = 'none';
                    }
                }
                
                this.addonTotal = data.addon_total || 0;
                this.renderCartItems(data.items || [], data.total || 0);
            } catch (error) {
                console.error('Display error:', error);
            }
        }
        
        renderCartItems(items, total) {
            const container = document.getElementById('cartItems');
            const footer = document.getElementById('cartFooter');
            
            if (!container) return;
            
            if (items.length === 0) {
                container.innerHTML = '<p class="empty-cart">Your cart is empty</p>';
                if (footer) footer.style.display = 'none';
                this.addonTotal = 0;
                return;
            }
            
            container.innerHTML = items.map((item, index) => `
                <div class="cart-item">
                    <img src="${item.image}" alt="${item.title}" onerror="this.src='/static/images/placeholder.png'; this.onerror=null;">
                    <div class="cart-item-details">
                        <div class="cart-item-title">${item.title}</div>
                        <div class="cart-item-price">₹${item.price}</div>
                        <div class="cart-item-controls">
                            <button class="quantity-btn" onclick="cartManager.updateQuantity('${item.type}_${item.id}', ${item.quantity - 1})">-</button>
                            <input type="number" class="quantity-input" value="${item.quantity}" min="1" 
                                   onchange="cartManager.updateQuantity('${item.type}_${item.id}', this.value)">
                            <button class="quantity-btn" onclick="cartManager.updateQuantity('${item.type}_${item.id}', ${item.quantity + 1})">+</button>
                            <span class="remove-item" onclick="cartManager.removeFromCart('${item.type}_${item.id}')">
                                <i class="fas fa-trash"></i>
                            </span>
                        </div>
                    </div>
                </div>
            `).join('');
            
            // Add-ons section with IMAGES
            const addonsContainer = document.createElement('div');
            addonsContainer.className = 'Reader Essentials';
            addonsContainer.innerHTML = `
              <h4 style="margin: 15px 0 10px; font-size: 14px; font-weight: 600;">Reader Essentials</h4>
              <div style="display: flex; flex-direction: column; gap: 12px;">
                <label style="display: flex; align-items: center; gap: 10px; font-size: 13px; cursor: pointer;">
                  <input type="checkbox" class="addon-checkbox" data-addon="Bag" data-price="15">
                  <img src="/static/images/todebag.jpg" alt="Bag" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px; border: 1px solid #ddd;">
                  <span style="font-weight: 500;">Bag - ₹15</span>
                </label>
                <label style="display: flex; align-items: center; gap: 10px; font-size: 13px; cursor: pointer;">
                  <input type="checkbox" class="addon-checkbox" data-addon="bookmark" data-price="10">
                  <img src="/static/images/book_mark.jpg" alt="Bookmark" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px; border: 1px solid #ddd;">
                  <span style="font-weight: 500;">Bookmark - ₹10</span>
                </label>
                <label style="display: flex; align-items: center; gap: 10px; font-size: 13px; cursor: pointer;">
                  <input type="checkbox" class="addon-checkbox" data-addon="packing" data-price="20">
                  <img src="/static/images/giftwrap.webp" alt="Packing" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px; border: 1px solid #ddd;">
                  <span style="font-weight: 500;">Gift Wrap - ₹20</span>
                </label>
              </div>
            `;
            container.appendChild(addonsContainer);
            
            // Load saved add-ons and attach event listeners
            this.loadAddons();
            
            if (footer) {
                footer.style.display = 'block';
                document.getElementById('cartTotal').textContent = `₹${total.toFixed(2)}`;
            }
        }
        
        async loadAddons() {
            try {
                const response = await fetch('/cart/addons/get/');
                const data = await response.json();
                
                document.querySelectorAll('.addon-checkbox').forEach(checkbox => {
                    const addon = checkbox.dataset.addon;
                    checkbox.checked = data.addons[addon] || false;
                    checkbox.addEventListener('change', () => this.updateAddons());
                });
                
                this.addonTotal = data.addon_total || 0;
                
            } catch (error) {
                console.error('Load addons error:', error);
            }
        }
        
        async updateAddons() {
            try {
                const addons = {};
                document.querySelectorAll('.addon-checkbox').forEach(checkbox => {
                    addons[checkbox.dataset.addon] = checkbox.checked;
                });
                
                const response = await fetch('/cart/addons/update/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({ addons })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.addonTotal = data.addon_total;
                    this.updateCartDisplay();
                }
                
            } catch (error) {
                console.error('Update addons error:', error);
            }
        }
        
        openCart() {
            console.log('openCart() called');
            
            if (!this.cartSidebar || !this.cartOverlay) {
                console.error('Cart elements not found in openCart()');
                return;
            }
            
            this.cartSidebar.classList.add('active');
            this.cartOverlay.classList.add('active');
            document.body.style.overflow = 'hidden';
            
            console.log('Cart opened - active classes added');
        }
        
        closeCart() {
            this.cartSidebar?.classList.remove('active');
            this.cartOverlay?.classList.remove('active');
            document.body.style.overflow = '';
        }
        
        showNotification(message) {
            const notification = document.createElement('div');
            notification.textContent = message;
            notification.style.cssText = `
                position: fixed; top: 20px; right: 20px; background: #4CAF50; color: white;
                padding: 14px 24px; border-radius: 8px; z-index: 10000; font-weight: 500;
                transform: translateX(400px); transition: transform 0.3s ease;
            `;
            document.body.appendChild(notification);
            setTimeout(() => notification.style.transform = 'translateX(0)', 100);
            setTimeout(() => {
                notification.style.transform = 'translateX(400px)';
                setTimeout(() => document.body.removeChild(notification), 300);
            }, 3000);
        }
        
        getCSRFToken() {
            const cookie = document.cookie.match(/csrftoken=([\w-]+)/);
            const token = cookie ? cookie[1] : '';
            console.log('getCSRFToken:', token);
            return token;
        }
    }
    
    // Create global instance
    window.cartManager = new CartManager();
    console.log('CartManager global instance created:', window.cartManager);
});