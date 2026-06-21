document.addEventListener('DOMContentLoaded', () => {
    // ---------- Mobile Navigation Toggle ----------
    const toggleBtn = document.querySelector('.mobile-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (toggleBtn && navLinks) {
        toggleBtn.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    // ---------- Category Card Backgrounds ----------
    document.querySelectorAll('.category-card').forEach(card => {
        const bgUrl = card.dataset.bg;
        if (bgUrl) {
            card.style.backgroundImage = `url('${bgUrl}')`;
        }
    });

    // ---------- Add-to-Cart Functionality & Cart Counter Update ----------
    function updateCartCounter() {
        const cart = JSON.parse(localStorage.getItem('cart')) || [];
        const totalQty = cart.reduce((sum, item) => sum + (item.qty || 1), 0);
        const counterEl = document.querySelector('.cart-count');
        if (counterEl) {
            counterEl.textContent = totalQty;
        }
    }

    function showToast(message) {
        // Simple toast notification
        let toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.textContent = message;
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.left = '50%';
        toast.style.transform = 'translateX(-50%)';
        toast.style.backgroundColor = '#28a745';
        toast.style.color = '#fff';
        toast.style.padding = '10px 20px';
        toast.style.borderRadius = '5px';
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        document.body.appendChild(toast);
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
        });
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 2000);
    }

    document.addEventListener('click', event => {
        if (event.target.matches('.add-to-cart')) {
            const btn = event.target;
            // Retrieve product id, name, price from DOM attributes or dataset
            const prodId = btn.dataset.id || btn.getAttribute('data-id');
            let prodName = '';
            let prodPrice = 0;

            // Try to find name/price in nearest .product-card or similar container
            const cardEl = btn.closest('.product-card') || btn.closest('.category-card') || btn.parentElement;
            if (cardEl) {
                prodName = cardEl.dataset.name || cardEl.getAttribute('data-name') || '';
                prodPrice = parseFloat(cardEl.dataset.price || cardEl.getAttribute('data-price')) || 0;
            }

            // Build product object
            const product = { id: prodId, name: prodName, price: prodPrice, qty: 1 };

            // Retrieve or initialise cart array from localStorage
            let cart = JSON.parse(localStorage.getItem('cart')) || [];
            // Check if same item already exists and increment quantity
            const existingIdx = cart.findIndex(item => String(item.id) === String(product.id));
            if (existingIdx !== --1) {
                cart[existingIdx].qty += 1;
            } else {
                cart.push(product);
            }

            localStorage.setItem('cart', JSON.stringify(cart));
            updateCartCounter();
            showToast(`${product.name} added to cart!`);
        }
    });

    // ---------- Smooth Scrolling for Anchor Links ----------
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (!targetId || targetId === '#') return;
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // Initial cart count on page load
    updateCartCounter();
});