let productDatabase = {};

// --- GLOBAL FETCH OVERRIDE FOR CSRF ---
const originalFetch = window.fetch;
window.csrfToken = null;

window.fetch = async function(resource, config) {
    if (config && config.method && config.method.toUpperCase() !== 'GET') {
        if (!window.csrfToken) {
            try {
                const res = await originalFetch('/api/csrf');
                const data = await res.json();
                if (data && data.csrf_token) {
                    window.csrfToken = data.csrf_token;
                }
            } catch (e) {
                console.error("Failed to fetch CSRF token", e);
            }
        }
        config.headers = config.headers || {};
        if (window.csrfToken) {
            config.headers['X-CSRF-Token'] = window.csrfToken;
        }
    }
    return originalFetch.call(this, resource, config);
};
// --------------------------------------

// Fetch products dynamically from backend SQLite database
async function fetchProductsFromDb() {
    try {
        const response = await fetch('/api/products');
        const productsList = await response.json();
        
        productDatabase = {};
        productsList.forEach(p => {
            productDatabase[p.key] = p;
        });

        renderProductsGrid(productsList);
        updateCartUI();
    } catch (err) {
        console.error('Error fetching catalog products:', err);
    }
}

function renderProductsGrid(products) {
    const grid = document.getElementById('mainProductsGrid');
    if (!grid) return;
    
    if (products.length === 0) {
        grid.innerHTML = `<p style="text-align: center; color: var(--text-secondary); width: 100%; grid-column: 1/-1;">No products available in catalog.</p>`;
        return;
    }

    let html = "";
    products.forEach(p => {
        const badgeHtml = p.discount ? `<span class="badge">${p.key === 'iron' ? 'Premium' : p.key === 'cement' ? 'Standard' : 'Trending'}</span>` : '';
        
        html += `
            <div class="product-card glass-card hover-glow" data-category="${p.key}" data-keywords="${p.keywords || ''}">
                ${badgeHtml}
                <div class="card-rating"><i class="fa-solid fa-star"></i> ${p.rating || '4.5'} <span class="rating-count">${p.rating_count || ''}</span></div>
                <div class="product-image-container" onclick="openDetailsModal('${p.key}')" style="cursor: pointer;">
                    <img src="${p.image}" alt="${p.name}" class="product-img" onerror="this.src='https://cdn.pixabay.com/photo/2019/12/10/20/59/site-4686908_640.jpg'">
                </div>
                <div class="product-info">
                    <h3 onclick="openDetailsModal('${p.key}')" style="cursor: pointer;">${p.name}</h3>
                    <div class="price-container">
                        <span class="original-price">₹${p.original_price.toLocaleString("en-IN")}</span>
                        <span class="product-price">₹${p.price.toLocaleString("en-IN")}</span>
                        ${p.discount ? `<span class="price-discount">${p.discount}</span>` : ''}
                        <div class="price-unit">per ${p.unit.slice(0, -1) || p.unit}</div>
                    </div>
                    <p>${p.highlights[0] || p.name}</p>
                    
                    <div class="delivery-speed"><i class="fa-solid fa-bolt"></i> ${p.speed || 'Same Day Unloading'}</div>
                    
                    <div class="product-actions" style="margin-top: 15px;">
                        <button class="btn btn-secondary btn-sm" onclick="openDetailsModal('${p.key}')">Details</button>
                        <div class="cart-control-wrapper" id="control-${p.key}">
                            <button class="btn-add-to-cart" onclick="addProductToCartClick('${p.key}')">ADD</button>
                        </div>
                    </div>
                </div>
                <div class="card-glow-bg"></div>
            </div>
        `;
    });
    grid.innerHTML = html;
}

// Track open modal item
let currentModalProductKey = null;

// Wait for DOM to load
document.addEventListener("DOMContentLoaded", () => {
    // Initialize Scroll Reveal Intersection Observer
    initScrollReveal();

    // Initialize Hero Slideshow
    initHeroSlideshow();

    // Initialize Mobile Navigation Toggle
    initMobileNav();

    // Close modals on overlay click
    initModalClosures();

    // Fetch dynamic product database
    fetchProductsFromDb();

    // Initialize Calculator Estimate
    calculateRates();

    // Check customer login session
    checkUserSession();
});

/* ==========================================================================
   Intersection Observer (Scroll Animations)
   ========================================================================== */
function initScrollReveal() {
    const revealElements = document.querySelectorAll(".scroll-reveal, .scroll-scale");
    
    const revealCallback = (entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
            } else {
                entry.target.classList.remove("visible");
            }
        });
    };

    const revealObserver = new IntersectionObserver(revealCallback, {
        root: null, // viewport
        threshold: 0.1, // Trigger slightly earlier for a smoother transition
        rootMargin: "0px 0px -50px 0px"
    });

    revealElements.forEach(el => {
        revealObserver.observe(el);
    });
}

/* ==========================================================================
   Hero Slideshow & Carousel
   ========================================================================== */
let currentSlideIndex = 0;
let slideInterval;

function initHeroSlideshow() {
    const slides = document.querySelectorAll(".banner-slider .banner-slide");
    const dots = document.querySelectorAll(".banner-dots .dot");
    
    if (slides.length === 0) return;

    // Reset timer function
    const startSlideShow = () => {
        slideInterval = setInterval(() => {
            nextSlide();
        }, 5000); // changes every 5 seconds
    };

    const nextSlide = () => {
        slides[currentSlideIndex].classList.remove("active");
        if (dots[currentSlideIndex]) dots[currentSlideIndex].classList.remove("active");
        
        currentSlideIndex = (currentSlideIndex + 1) % slides.length;
        
        slides[currentSlideIndex].classList.add("active");
        if (dots[currentSlideIndex]) dots[currentSlideIndex].classList.add("active");
    };

    // Initialize auto slideshow
    startSlideShow();

    // Attach index callbacks for dots
    window.setBannerSlide = (index) => {
        clearInterval(slideInterval);
        
        slides[currentSlideIndex].classList.remove("active");
        if (dots[currentSlideIndex]) dots[currentSlideIndex].classList.remove("active");
        
        currentSlideIndex = index;
        
        slides[currentSlideIndex].classList.add("active");
        if (dots[currentSlideIndex]) dots[currentSlideIndex].classList.add("active");
        
        startSlideShow();
    };
}

/* ==========================================================================
   Mobile Navigation Drawer Control
   ========================================================================== */
function initMobileNav() {
    const menuToggle = document.querySelector(".mobile-menu-toggle");
    const mobileNav = document.querySelector(".mobile-nav");
    
    if (!menuToggle || !mobileNav) return;

    window.toggleMobileMenu = () => {
        const isActive = mobileNav.classList.contains("active");
        if (isActive) {
            mobileNav.classList.remove("active");
            menuToggle.innerHTML = '<i class="fa-solid fa-bars"></i>';
        } else {
            mobileNav.classList.add("active");
            menuToggle.innerHTML = '<i class="fa-solid fa-xmark"></i>';
        }
    };

    // Close mobile menu when a drawer link is clicked
    const mobileLinks = document.querySelectorAll(".mobile-link");
    mobileLinks.forEach(link => {
        link.addEventListener("click", () => {
            if (mobileNav.classList.contains("active")) {
                toggleMobileMenu();
            }
        });
    });
}

/* ==========================================================================
   Modals - Details and Custom Inquiries
   ========================================================================== */
const detailsModal = document.getElementById("detailsModal");
const inquiryModal = document.getElementById("inquiryModal");

// Open Details Modal
window.openDetailsModal = (productKey) => {
    const product = productDatabase[productKey];
    if (!product) return;

    currentModalProductKey = productKey;

    // Populate modal components
    const modalMainImg = document.getElementById("modalMainImg");
    const modalThumbnailsRow = document.getElementById("modalThumbnailsRow");
    const modalProductTitle = document.getElementById("modalProductTitle");
    const modalProductBrand = document.getElementById("modalProductBrand");
    const modalRatingVal = document.getElementById("modalRatingVal");
    const modalRatingCount = document.getElementById("modalRatingCount");
    const modalOrigPrice = document.getElementById("modalOrigPrice");
    const modalCurrentPrice = document.getElementById("modalCurrentPrice");
    const modalDiscount = document.getElementById("modalDiscount");
    const modalPriceUnit = document.getElementById("modalPriceUnit");
    const modalProductHighlights = document.getElementById("modalProductHighlights");
    const modalSpecTable = document.getElementById("modalSpecTable");

    if (modalMainImg) modalMainImg.src = product.image;
    if (modalProductTitle) modalProductTitle.textContent = product.name;
    if (modalProductBrand) modalProductBrand.textContent = product.brand;
    if (modalRatingVal) modalRatingVal.textContent = product.rating;
    if (modalRatingCount) modalRatingCount.textContent = `${product.ratingCount}`;
    if (modalOrigPrice) modalOrigPrice.textContent = `₹${product.originalPrice.toLocaleString("en-IN")}`;
    if (modalCurrentPrice) modalCurrentPrice.textContent = `₹${product.price.toLocaleString("en-IN")}`;
    if (modalDiscount) modalDiscount.textContent = product.discount;
    if (modalPriceUnit) modalPriceUnit.textContent = `per ${product.unit.slice(0, -1) || product.unit}`;

    // Set highlights bullet points
    if (modalProductHighlights) {
        modalProductHighlights.innerHTML = `
            <ul class="details-bullet-list">
                ${product.highlights.map(hl => `<li>${hl}</li>`).join("")}
            </ul>
        `;
    }

    // Set specifications table
    if (modalSpecTable) {
        modalSpecTable.innerHTML = Object.entries(product.specs).map(([key, val]) => `
            <tr>
                <td class="label">${key}</td>
                <td class="value">${val}</td>
            </tr>
        `).join("");
    }

    // Load thumbnails
    if (modalThumbnailsRow) {
        modalThumbnailsRow.innerHTML = product.thumbnails.map((thumbSrc, index) => `
            <div class="thumbnail-card ${index === 0 ? "active" : ""}" onclick="setModalMainImg('${thumbSrc}', this)">
                <img src="${thumbSrc}" alt="thumbnail-${index}">
            </div>
        `).join("");
    }

    // Update modal controls based on cart state
    updateCartUI();

    // Show details modal
    if (detailsModal) {
        detailsModal.classList.add("active");
        document.body.style.overflow = "hidden"; // lock page scroll
    }
};

// Close Details Modal
window.closeDetailsModal = () => {
    if (detailsModal) {
        detailsModal.classList.remove("active");
    }
    currentModalProductKey = null;
    if (!inquiryModal.classList.contains("active")) {
        document.body.style.overflow = ""; // release page scroll
    }
};

// Switch Modal Main Image from Thumbnails
window.setModalMainImg = (imgSrc, thumbEl) => {
    const mainImg = document.getElementById("modalMainImg");
    if (mainImg) {
        mainImg.src = imgSrc;
    }
    
    // Toggle active state in thumbnails row
    if (thumbEl) {
        const thumbnails = thumbEl.parentElement.querySelectorAll(".thumbnail-card");
        thumbnails.forEach(t => t.classList.remove("active"));
        thumbEl.classList.add("active");
    }
};

// Accordion toggle panel
window.toggleAccordion = (header) => {
    const item = header.parentElement;
    item.classList.toggle("active");
};

// Open Inquiry Modal with customizable links
window.openInquiryModal = (productName) => {
    const productSpan = document.getElementById("inquiryProduct");
    const whatsapp1 = document.getElementById("whatsapp1");
    const whatsapp2 = document.getElementById("whatsapp2");

    if (productSpan) {
        productSpan.textContent = productName;
    }

    // Prepare WhatsApp Inquiry Messages
    const message = encodeURIComponent(`Hello Sri Ram Traders, I'm interested in inquiring about "${productName}". Please share the current wholesale price list and delivery timeline for my location. Thanks!`);
    
    if (whatsapp1) {
        whatsapp1.href = `https://wa.me/919471089535?text=${message}`;
    }
    if (whatsapp2) {
        whatsapp2.href = `https://wa.me/918405986541?text=${message}`;
    }

    inquiryModal.classList.add("active");
    document.body.style.overflow = "hidden"; // lock page scroll
};

// Close Inquiry Modal
window.closeInquiryModal = () => {
    inquiryModal.classList.remove("active");
    if (!detailsModal.classList.contains("active")) {
        document.body.style.overflow = ""; // release page scroll
    }
};

// Setup close listeners for outer clicks
function initModalClosures() {
    const overlays = [detailsModal, inquiryModal];
    overlays.forEach(overlay => {
        if (!overlay) return;
        overlay.addEventListener("click", (e) => {
            // Click occurred exactly on the backdrop (not on cards)
            if (e.target === overlay) {
                overlay.classList.remove("active");
                document.body.style.overflow = "";
            }
        });
    });

    // Close with Escape key
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            if (detailsModal) detailsModal.classList.remove("active");
            if (inquiryModal) inquiryModal.classList.remove("active");
            document.body.style.overflow = "";
        }
    });
}

/* ==========================================================================
   Newsletter Signup Simulation
   ========================================================================== */
window.handleSubscribe = (event) => {
    event.preventDefault();
    const emailInput = event.target.querySelector(".email");
    if (!emailInput) return;

    const email = emailInput.value;
    
    // Create modern glass toast notification
    showToast(`Thank you! Registration details requested for ${email}. A sales representative will email you shorty.`);
    emailInput.value = "";
};

/* ==========================================================================
   Toast Notification System
   ========================================================================== */
function showToast(message) {
    // Remove existing toast if present
    const existingToast = document.querySelector(".glass-toast");
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement("div");
    toast.className = "glass-toast glass-card";
    toast.style.cssText = `
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translate(-50%, 100px);
        background: rgba(15, 20, 35, 0.9);
        border: 1px solid rgba(245, 158, 11, 0.4);
        padding: 16px 28px;
        border-radius: 12px;
        z-index: 3000;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(245, 158, 11, 0.1);
        opacity: 0;
        pointer-events: none;
        transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
        text-align: center;
        max-width: 90%;
        font-weight: 500;
        font-size: 14px;
        color: var(--text-primary);
    `;
    
    toast.innerHTML = `<i class="fa-solid fa-circle-check" style="color: #22c55e; margin-right: 8px;"></i> ${message}`;
    document.body.appendChild(toast);

    // Animate in
    setTimeout(() => {
        toast.style.transform = "translate(-50%, 0)";
        toast.style.opacity = "1";
    }, 50);

    // Animate out
    setTimeout(() => {
        toast.style.transform = "translate(-50%, 100px)";
        toast.style.opacity = "0";
        setTimeout(() => {
            toast.remove();
        }, 500);
    }, 4000);
}

/* ==========================================================================
   E-Commerce Cart State & Logic
   ========================================================================== */

// Initialize Cart State from LocalStorage
let cart = JSON.parse(localStorage.getItem("ram_traders_cart")) || [];

// Add product to cart (Quick commerce style ADD button)
window.addProductToCartClick = (productKey) => {
    const product = productDatabase[productKey];
    if (!product) return;

    const existingIndex = cart.findIndex(item => item.key === productKey);
    if (existingIndex > -1) {
        cart[existingIndex].quantity += 1;
    } else {
        cart.push({
            key: productKey,
            name: product.name,
            price: product.price,
            unit: product.unit,
            image: product.image,
            quantity: 1
        });
    }

    saveCart();
    showToast(`Added ${product.name} to cart.`);
};

// Adjust quantity of item in cart (synced with the card controls)
window.adjustProductQty = (productKey, delta) => {
    const existingIndex = cart.findIndex(item => item.key === productKey);
    if (existingIndex > -1) {
        cart[existingIndex].quantity += delta;
        if (cart[existingIndex].quantity <= 0) {
            const name = cart[existingIndex].name;
            cart.splice(existingIndex, 1);
            showToast(`Removed ${name} from cart.`);
        }
        saveCart();
    }
};

// Toggle Cart Drawer view
window.toggleCartDrawer = () => {
    const cartDrawer = document.getElementById("cartDrawer");
    if (!cartDrawer) return;

    cartDrawer.classList.toggle("active");
    if (cartDrawer.classList.contains("active")) {
        const profileDrawer = document.getElementById("profileDrawer");
        if (profileDrawer) profileDrawer.classList.remove("active");
    }
};

// Adjust quantity directly in the cart drawer
window.adjustCartItemQty = (productKey, delta) => {
    const itemIndex = cart.findIndex(item => item.key === productKey);
    if (itemIndex === -1) return;

    cart[itemIndex].quantity = Math.max(1, cart[itemIndex].quantity + delta);
    saveCart();
};

// Remove single item from cart
window.removeCartItem = (productKey) => {
    const itemIndex = cart.findIndex(item => item.key === productKey);
    if (itemIndex === -1) return;

    const itemName = cart[itemIndex].name;
    cart.splice(itemIndex, 1);
    saveCart();
    showToast(`Removed ${itemName} from cart.`);
};

// Clear all items in cart
window.clearCart = () => {
    if (cart.length === 0) return;
    
    cart = [];
    saveCart();
    showToast("Shopping cart cleared.");
};

// Save cart to local storage and update views
function saveCart() {
    localStorage.setItem("ram_traders_cart", JSON.stringify(cart));
    updateCartUI();
}

// Update Cart Count Badges and items lists in DOM
function updateCartUI() {
    const badge = document.getElementById("cartCountBadge");
    const mobileBadge = document.getElementById("mobileCartCount");
    const drawerItemsContainer = document.getElementById("cartDrawerItems");
    const drawerTotal = document.getElementById("cartDrawerTotal");
    const checkoutBtn = document.getElementById("checkoutBtn");
    const headerCartTotal = document.getElementById("headerCartTotal");

    // Calculate total item count
    const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);

    // Update count badges
    if (badge) {
        badge.textContent = totalItems;
        badge.style.display = totalItems > 0 ? "flex" : "none";
    }
    if (mobileBadge) {
        mobileBadge.textContent = totalItems;
    }

    // Calculate total cost
    const totalCost = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    
    if (drawerTotal) {
        drawerTotal.textContent = `₹${totalCost.toLocaleString("en-IN")}`;
    }
    if (headerCartTotal) {
        headerCartTotal.textContent = `₹${totalCost.toLocaleString("en-IN")}`;
    }

    // Toggle checkout button state
    if (checkoutBtn) {
        checkoutBtn.disabled = cart.length === 0;
    }

    // Populate drawer items list
    if (!drawerItemsContainer) return;

    if (cart.length === 0) {
        drawerItemsContainer.innerHTML = `
            <div class="cart-empty-message">
                <i class="fa-solid fa-basket-shopping" style="font-size: 48px; color: var(--text-muted); margin-bottom: 15px;"></i>
                <p>Your cart is empty.</p>
                <button class="btn btn-secondary btn-sm" onclick="toggleCartDrawer()" style="margin-top: 15px;">Start Shopping</button>
            </div>
        `;
    } else {
        let itemsHtml = "";
        cart.forEach(item => {
            itemsHtml += `
                <div class="cart-item">
                    <img src="${item.image}" alt="${item.name}" class="cart-item-img" onerror="this.src='https://cdn.pixabay.com/photo/2019/12/10/20/59/site-4686908_640.jpg'">
                    <div class="cart-item-info">
                        <h4>${item.name}</h4>
                        <div class="cart-item-price">₹${item.price.toLocaleString("en-IN")} / ${item.unit.slice(0, -1)}</div>
                        <div class="cart-item-qty-row">
                            <div class="qty-selector">
                                <button class="qty-btn" onclick="adjustCartItemQty('${item.key}', -1)">-</button>
                                <span class="qty-display">${item.quantity}</span>
                                <button class="qty-btn" onclick="adjustCartItemQty('${item.key}', 1)">+</button>
                            </div>
                            <span class="qty-unit">${item.unit}</span>
                        </div>
                    </div>
                    <button class="cart-item-remove-btn" onclick="removeCartItem('${item.key}')" title="Remove Item">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            `;
        });
        drawerItemsContainer.innerHTML = itemsHtml;
    }

    // Update product card controls on the page dynamically
    Object.keys(productDatabase).forEach(productKey => {
        const wrapper = document.getElementById(`control-${productKey}`);
        if (!wrapper) return;

        const cartItem = cart.find(item => item.key === productKey);
        if (cartItem) {
            wrapper.innerHTML = `
                <div class="qty-counter">
                    <button class="counter-btn" onclick="adjustProductQty('${productKey}', -1)">-</button>
                    <span class="counter-val">${cartItem.quantity}</span>
                    <button class="counter-btn" onclick="adjustProductQty('${productKey}', 1)">+</button>
                </div>
            `;
        } else {
            wrapper.innerHTML = `
                <button class="btn-add-to-cart" onclick="addProductToCartClick('${productKey}')">ADD</button>
            `;
        }
    });

    // Update details modal control if active
    const modalControl = document.getElementById("modalCartControl");
    if (modalControl && currentModalProductKey) {
        const cartItem = cart.find(item => item.key === currentModalProductKey);
        if (cartItem) {
            modalControl.innerHTML = `
                <div class="qty-counter" style="margin-left: 0;">
                    <button class="counter-btn" onclick="adjustProductQty('${currentModalProductKey}', -1)">-</button>
                    <span class="counter-val">${cartItem.quantity}</span>
                    <button class="counter-btn" onclick="adjustProductQty('${currentModalProductKey}', 1)">+</button>
                </div>
            `;
        } else {
            modalControl.innerHTML = `
                <button class="btn-add-to-cart" onclick="addProductToCartClick('${currentModalProductKey}')" style="margin-left: 0; width: 120px; height: 40px; font-size: 14px;">ADD</button>
            `;
        }
    }
}

/* ==========================================================================
   Checkout Modal Controls & WhatsApp Dispatch
   ========================================================================== */
const checkoutModal = document.getElementById("checkoutModal");

window.openCheckoutModal = () => {
    if (cart.length === 0) return;

    // Close the cart drawer first
    toggleCartDrawer();

    const summaryList = document.getElementById("checkoutSummaryList");
    const summaryTotal = document.getElementById("checkoutSummaryTotal");
    
    // Populate summary items list
    if (summaryList) {
        let summaryHtml = "";
        cart.forEach(item => {
            const itemTotal = item.price * item.quantity;
            summaryHtml += `
                <div class="checkout-summary-item">
                    <span>${item.name} (x${item.quantity} ${item.unit})</span>
                    <span>₹${itemTotal.toLocaleString("en-IN")}</span>
                </div>
            `;
        });
        summaryList.innerHTML = summaryHtml;
    }

    // Update grand total
    const totalCost = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    if (summaryTotal) {
        summaryTotal.textContent = `₹${totalCost.toLocaleString("en-IN")}`;
    }

    checkoutModal.classList.add("active");
    document.body.style.overflow = "hidden"; // lock page scroll
};

window.closeCheckoutModal = () => {
    if (checkoutModal) {
        checkoutModal.classList.remove("active");
        document.body.style.overflow = ""; // release page scroll
    }
};

window.submitOrder = async (event) => {
    event.preventDefault();

    const name = document.getElementById("custName").value;
    const phone = document.getElementById("custPhone").value;
    const address = document.getElementById("custAddress").value;
    const notes = document.getElementById("custNotes").value || "N/A";

    const totalCost = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);

    // Save order data to SQLite backend
    const orderData = {
        name,
        phone,
        address,
        notes,
        items: cart.map(i => ({ key: i.key, name: i.name, price: i.price, quantity: i.quantity, unit: i.unit })),
        totalCost
    };

    try {
        const response = await fetch('/api/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(orderData)
        });
        const result = await response.json();
        
        if (result.success) {
            // Build the invoice WhatsApp summary text
            let orderSummaryText = `*NEW ORDER - SRI RAM TRADERS*\n`;
            orderSummaryText += `=====================================\n`;
            orderSummaryText += `*Order ID:* #RT-${result.orderId}\n`;
            orderSummaryText += `*Customer:* ${name}\n`;
            orderSummaryText += `*Mobile:* ${phone}\n`;
            orderSummaryText += `*Delivery Site:* ${address}\n`;
            orderSummaryText += `*Instructions:* ${notes}\n\n`;
            orderSummaryText += `*Materials List:*\n`;

            cart.forEach((item, index) => {
                const itemTotal = item.price * item.quantity;
                orderSummaryText += `${index + 1}. ${item.name} (x${item.quantity} ${item.unit}) - ₹${itemTotal.toLocaleString("en-IN")}\n`;
            });

            orderSummaryText += `\n*Total Estimated Amount:* ₹${totalCost.toLocaleString("en-IN")}\n`;
            orderSummaryText += `=====================================\n`;
            orderSummaryText += `Please confirm dispatch schedules. Thank you!`;

            const encodedText = encodeURIComponent(orderSummaryText);

            // Close checkout modal
            closeCheckoutModal();

            // Clear cart drawer
            cart = [];
            saveCart();

            showToast("Order entry saved in DB! Redirecting you to WhatsApp...");

            // Launch WhatsApp redirect link pointing to Manager's number
            setTimeout(() => {
                const whatsappUrl = `https://wa.me/919471089535?text=${encodedText}`;
                window.open(whatsappUrl, "_blank");
            }, 1200);
        } else {
            alert('Failed to register order: ' + result.error);
        }
    } catch (err) {
        alert('Could not submit order. Verify backend server is active.');
    }
};

/* ==========================================================================
   E-Commerce Storefront Features (Search, Category Chip Filters, Calculator)
   ========================================================================== */

// Filter products by category chip click
window.filterCategory = (category, chipEl) => {
    const chips = document.querySelectorAll(".category-chip");
    chips.forEach(c => c.classList.remove("active"));
    if (chipEl) {
        chipEl.classList.add("active");
    }

    // Reset search inputs
    const searchDesk = document.getElementById("storeSearchInput");
    const searchMob = document.getElementById("storeSearchInputMobile");
    if (searchDesk) searchDesk.value = "";
    if (searchMob) searchMob.value = "";
    const clearBtn = document.getElementById("searchClearBtn");
    if (clearBtn) clearBtn.style.display = "none";

    const cards = document.querySelectorAll(".products-grid .product-card");
    let hasResults = false;
    
    cards.forEach(card => {
        const cat = card.getAttribute("data-category");
        if (category === "all" || cat === category) {
            card.style.display = "block";
            hasResults = true;
        } else {
            card.style.display = "none";
        }
    });

    const noResults = document.getElementById("searchNoResults");
    if (noResults) {
        noResults.style.display = hasResults ? "none" : "block";
    }
};

// Handle Search Filter query
window.handleSearch = (query) => {
    const cleanQuery = query.toLowerCase().trim();
    
    // Sync search input fields across viewports
    const searchDesk = document.getElementById("storeSearchInput");
    const searchMob = document.getElementById("storeSearchInputMobile");
    if (searchDesk && searchDesk.value !== query) searchDesk.value = query;
    if (searchMob && searchMob.value !== query) searchMob.value = query;

    const clearBtn = document.getElementById("searchClearBtn");
    if (clearBtn) {
        clearBtn.style.display = cleanQuery.length > 0 ? "flex" : "none";
    }

    // Reset active category chip when user is searching
    if (cleanQuery.length > 0) {
        const chips = document.querySelectorAll(".category-chip");
        chips.forEach(c => c.classList.remove("active"));
        const allChip = document.querySelector(".category-chip");
        if (allChip) allChip.classList.add("active");
    }

    const cards = document.querySelectorAll(".products-grid .product-card");
    let hasResults = false;

    cards.forEach(card => {
        const keywords = (card.getAttribute("data-keywords") || "").toLowerCase();
        const title = (card.querySelector("h3")?.textContent || "").toLowerCase();
        
        if (keywords.includes(cleanQuery) || title.includes(cleanQuery)) {
            card.style.display = "block";
            hasResults = true;
        } else {
            card.style.display = "none";
        }
    });

    const noResults = document.getElementById("searchNoResults");
    if (noResults) {
        noResults.style.display = hasResults ? "none" : "block";
    }
};

window.clearSearch = () => {
    const searchDesk = document.getElementById("storeSearchInput");
    const searchMob = document.getElementById("storeSearchInputMobile");
    if (searchDesk) searchDesk.value = "";
    if (searchMob) searchMob.value = "";
    
    const clearBtn = document.getElementById("searchClearBtn");
    if (clearBtn) clearBtn.style.display = "none";

    const allChip = document.querySelector(".category-chip");
    filterCategory("all", allChip);
};

// Delivery Location picker widget
window.openLocationPrompt = () => {
    const currentAddress = document.getElementById("deliveryAddressText").textContent;
    const newAddress = prompt("Enter your Delivery Location or Site Address (e.g. Patna, Gangapatti, Sector-4):", currentAddress);
    
    if (newAddress !== null && newAddress.trim() !== "") {
        const cleanAddress = newAddress.trim();
        
        const destDesk = document.getElementById("deliveryAddressText");
        const destMob = document.getElementById("deliveryAddressTextMobile");
        if (destDesk) destDesk.textContent = cleanAddress;
        if (destMob) destMob.textContent = cleanAddress;
        
        const checkoutAddress = document.getElementById("custAddress");
        if (checkoutAddress) checkoutAddress.value = cleanAddress;
        
        showToast(`Delivery location updated to: ${cleanAddress}`);
    }
};

// Wholesale Cost Calculator
const calculatorRatesDb = {
    gitti: { rate: 2800, unit: "Ton", minQty: 1, baseDiscountQty: 5, discountPercent: 0.05 },
    iron: { rate: 55000, unit: "Ton", minQty: 1, baseDiscountQty: 3, discountPercent: 0.04 },
    cement: { rate: 420, unit: "Bag", minQty: 10, baseDiscountQty: 50, discountPercent: 0.03 },
    bricks: { rate: 7000, unit: "1K Bricks", minQty: 1, baseDiscountQty: 10, discountPercent: 0.05 }
};

window.updateCalcQuantityInput = (val) => {
    const input = document.getElementById("calcQuantityInput");
    if (input) input.value = val;
    calculateRates();
};

window.updateCalcQuantityRange = (val) => {
    const range = document.getElementById("calcQuantityRange");
    if (range) {
        const parsed = parseInt(val) || 1;
        range.value = Math.min(100, Math.max(1, parsed));
    }
    calculateRates();
};

window.calculateRates = () => {
    const selectEl = document.getElementById("calcMaterial");
    const qtyInput = document.getElementById("calcQuantityInput");
    const locSelect = document.getElementById("calcLocation");
    
    if (!selectEl || !qtyInput || !locSelect) return;
    
    const productKey = selectEl.value;
    const quantity = Math.max(1, parseFloat(qtyInput.value) || 1);
    const deliveryCharge = parseFloat(locSelect.value) || 0;
    
    const rateData = calculatorRatesDb[productKey];
    if (!rateData) return;

    const unitText = document.getElementById("calcUnitText");
    if (unitText) unitText.textContent = rateData.unit + (quantity !== 1 ? "s" : "");

    const basePrice = rateData.rate;
    const materialCost = basePrice * quantity;
    
    let discount = 0;
    if (quantity >= rateData.baseDiscountQty) {
        discount = Math.round(materialCost * rateData.discountPercent);
    }
    
    const grandTotal = materialCost - discount + deliveryCharge;

    const uiBaseRate = document.getElementById("calcBaseRate");
    const uiMaterialCost = document.getElementById("calcMaterialCost");
    const uiDeliveryCost = document.getElementById("calcDeliveryCost");
    const uiBulkDiscount = document.getElementById("calcBulkDiscount");
    const uiGrandTotal = document.getElementById("calcGrandTotal");

    if (uiBaseRate) uiBaseRate.textContent = `₹${basePrice.toLocaleString("en-IN")} / ${rateData.unit}`;
    if (uiMaterialCost) uiMaterialCost.textContent = `₹${materialCost.toLocaleString("en-IN")}`;
    if (uiDeliveryCost) uiDeliveryCost.textContent = `₹${deliveryCharge.toLocaleString("en-IN")}`;
    
    if (uiBulkDiscount) {
        if (discount > 0) {
            uiBulkDiscount.textContent = `-₹${discount.toLocaleString("en-IN")} (${rateData.discountPercent * 100}%)`;
            uiBulkDiscount.parentElement.style.display = "flex";
        } else {
            uiBulkDiscount.parentElement.style.display = "none";
        }
    }
    
    if (uiGrandTotal) uiGrandTotal.textContent = `₹${grandTotal.toLocaleString("en-IN")}`;
};

window.submitCalcInquiry = () => {
    const selectEl = document.getElementById("calcMaterial");
    const qtyInput = document.getElementById("calcQuantityInput");
    const locSelect = document.getElementById("calcLocation");
    
    if (!selectEl || !qtyInput || !locSelect) return;
    
    const productKey = selectEl.value;
    const quantity = parseFloat(qtyInput.value) || 1;
    const deliveryLocationText = locSelect.options[locSelect.selectedIndex].text;
    const rateData = calculatorRatesDb[productKey];
    if (!rateData) return;

    const basePrice = rateData.rate;
    const materialCost = basePrice * quantity;
    let discount = 0;
    if (quantity >= rateData.baseDiscountQty) {
        discount = Math.round(materialCost * rateData.discountPercent);
    }
    const deliveryCharge = parseFloat(locSelect.value) || 0;
    const grandTotal = materialCost - discount + deliveryCharge;

    let message = `*WHOLESALE ESTIMATE - SRI RAM TRADERS*\n`;
    message += `=====================================\n`;
    message += `*Material:* ${productDatabase[productKey]?.name || productKey}\n`;
    message += `*Quantity:* ${quantity} ${rateData.unit}(s)\n`;
    message += `*Delivery Site:* ${deliveryLocationText}\n\n`;
    message += `*Base Wholesale Rate:* ₹${basePrice.toLocaleString("en-IN")} / ${rateData.unit}\n`;
    message += `*Material Subtotal:* ₹${materialCost.toLocaleString("en-IN")}\n`;
    if (discount > 0) {
        message += `*Bulk Discount:* -₹${discount.toLocaleString("en-IN")} (${rateData.discountPercent * 100}%)\n`;
    }
    message += `*Delivery Charge:* ₹${deliveryCharge.toLocaleString("en-IN")}\n`;
    message += `-------------------------------------\n`;
    message += `*Total Estimated Amount:* ₹${grandTotal.toLocaleString("en-IN")}\n`;
    message += `=====================================\n`;
    message += `Please confirm final freight dispatch schedules. Thanks!`;

    const encoded = encodeURIComponent(message);
    const whatsappUrl = `https://wa.me/919471089535?text=${encoded}`;
    window.open(whatsappUrl, "_blank");
    showToast("Calculator estimate sent! Redirecting you to WhatsApp...");
};


/* ==========================================================================
   Customer Profile & Authentication Actions
   ========================================================================== */

window.toggleProfileDrawer = () => {
    const profileDrawer = document.getElementById("profileDrawer");
    if (!profileDrawer) return;

    profileDrawer.classList.toggle("active");
    if (profileDrawer.classList.contains("active")) {
        const cartDrawer = document.getElementById("cartDrawer");
        if (cartDrawer) cartDrawer.classList.remove("active");
    }
};

window.switchUserAuthTab = (mode) => {
    const loginForm = document.getElementById('userLoginForm');
    const registerForm = document.getElementById('userRegisterForm');
    const loginToggle = document.getElementById('userLoginToggle');
    const registerToggle = document.getElementById('userRegisterToggle');
    const errorMsg = document.getElementById('userAuthErrorMsg');

    if (errorMsg) errorMsg.style.display = 'none';

    if (mode === 'login') {
        if (loginForm) loginForm.style.display = 'block';
        if (registerForm) registerForm.style.display = 'none';
        if (loginToggle) loginToggle.classList.add('active');
        if (registerToggle) registerToggle.classList.remove('active');
    } else {
        if (loginForm) loginForm.style.display = 'none';
        if (registerForm) registerForm.style.display = 'block';
        if (loginToggle) loginToggle.classList.remove('active');
        if (registerToggle) registerToggle.classList.add('active');
    }
};

async function checkUserSession() {
    try {
        const res = await fetch('/api/user/session');
        const data = await res.json();
        
        const unauthBlock = document.getElementById('profileUnauthenticated');
        const authBlock = document.getElementById('profileAuthenticated');
        const headerName = document.getElementById('headerProfileName');
        const mobileLabel = document.getElementById('mobileProfileLabel');

        if (data.loggedIn) {
            // Update auth state in sidebar and header
            if (unauthBlock) unauthBlock.style.display = 'none';
            if (authBlock) authBlock.style.display = 'block';
            if (headerName) headerName.textContent = data.user.name.split(' ')[0];
            if (mobileLabel) mobileLabel.textContent = `My Profile (${data.user.name})`;

            // Populate Profile display cards
            document.getElementById('profileDisplayName').textContent = data.user.name;
            document.getElementById('profileDisplayUsername').textContent = `@${data.user.username}`;
            document.getElementById('profileDisplayPhone').textContent = data.user.phone;
            document.getElementById('profileDisplayEmail').textContent = data.user.email || 'N/A';
            document.getElementById('profileDisplayAddress').textContent = data.user.address;

            // Pre-fill Checkout fields if empty
            const custNameInput = document.getElementById('custName');
            const custPhoneInput = document.getElementById('custPhone');
            const custAddressInput = document.getElementById('custAddress');
            
            if (custNameInput && !custNameInput.value) custNameInput.value = data.user.name;
            if (custPhoneInput && !custPhoneInput.value) custPhoneInput.value = data.user.phone;
            
            // Sync Location & Checkout Address
            if (custAddressInput && !custAddressInput.value) {
                custAddressInput.value = data.user.address;
                const destDesk = document.getElementById("deliveryAddressText");
                const destMob = document.getElementById("deliveryAddressTextMobile");
                if (destDesk) destDesk.textContent = data.user.address;
                if (destMob) destMob.textContent = data.user.address;
            }

            // Load purchase history
            loadUserOrders();
        } else {
            // Restore guest view
            if (unauthBlock) unauthBlock.style.display = 'block';
            if (authBlock) authBlock.style.display = 'none';
            if (headerName) headerName.textContent = 'Sign In';
            if (mobileLabel) mobileLabel.textContent = 'My Account (Sign In)';
            
            const list = document.getElementById('profileOrdersList');
            if (list) list.innerHTML = '';
        }
    } catch (err) {
        console.error('Session validation error:', err);
    }
}

window.handleUserLogin = async (event) => {
    event.preventDefault();
    const errorMsg = document.getElementById('userAuthErrorMsg');
    if (errorMsg) errorMsg.style.display = 'none';

    const usernameVal = document.getElementById('userLoginUsername').value;
    const passwordVal = document.getElementById('userLoginPassword').value;

    try {
        const response = await fetch('/api/user/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: usernameVal, password: passwordVal })
        });
        const result = await response.json();
        
        if (result.success) {
            showToast(`Welcome back!`);
            await checkUserSession();
            
            // clear form
            document.getElementById('userLoginUsername').value = '';
            document.getElementById('userLoginPassword').value = '';
        } else {
            if (errorMsg) {
                errorMsg.querySelector('.text').textContent = result.error || 'Invalid username or password.';
                errorMsg.style.display = 'flex';
            }
        }
    } catch (err) {
        if (errorMsg) {
            errorMsg.querySelector('.text').textContent = 'Server connection error.';
            errorMsg.style.display = 'flex';
        }
    }
};

window.handleUserRegister = async (event) => {
    event.preventDefault();
    const errorMsg = document.getElementById('userAuthErrorMsg');
    if (errorMsg) errorMsg.style.display = 'none';

    const username = document.getElementById('userRegUsername').value;
    const password = document.getElementById('userRegPassword').value;
    const name = document.getElementById('userRegName').value;
    const phone = document.getElementById('userRegPhone').value;
    const address = document.getElementById('userRegAddress').value;
    const email = document.getElementById('userRegEmail').value;

    try {
        const response = await fetch('/api/user/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, name, phone, address, email })
        });
        const result = await response.json();
        
        if (result.success) {
            alert('Registration successful! Please login.');
            switchUserAuthTab('login');
            
            document.getElementById('userLoginUsername').value = username;
            
            // clear register inputs
            document.getElementById('userRegUsername').value = '';
            document.getElementById('userRegPassword').value = '';
            document.getElementById('userRegName').value = '';
            document.getElementById('userRegPhone').value = '';
            document.getElementById('userRegAddress').value = '';
            document.getElementById('userRegEmail').value = '';
        } else {
            if (errorMsg) {
                errorMsg.querySelector('.text').textContent = result.error || 'Failed to create account.';
                errorMsg.style.display = 'flex';
            }
        }
    } catch (err) {
        if (errorMsg) {
            errorMsg.querySelector('.text').textContent = 'Could not reach server.';
            errorMsg.style.display = 'flex';
        }
    }
};

window.logoutUser = async () => {
    try {
        const response = await fetch('/api/user/logout', { method: 'POST' });
        const result = await response.json();
        if (result.success) {
            showToast('Signed out successfully.');
            
            // Reset checkout pre-fills
            const custNameInput = document.getElementById('custName');
            const custPhoneInput = document.getElementById('custPhone');
            const custAddressInput = document.getElementById('custAddress');
            
            if (custNameInput) custNameInput.value = '';
            if (custPhoneInput) custPhoneInput.value = '';
            if (custAddressInput) custAddressInput.value = '';
            
            await checkUserSession();
        }
    } catch (err) {
        showToast('Error during logout.');
    }
};

async function loadUserOrders() {
    const list = document.getElementById('profileOrdersList');
    if (!list) return;

    try {
        const res = await fetch('/api/user/orders');
        const orders = await res.json();

        if (orders.length === 0) {
            list.innerHTML = `
                <div style="text-align: center; color: var(--text-secondary); margin: 30px 0;">
                    <i class="fa-solid fa-receipt" style="font-size: 32px; color: var(--text-muted); margin-bottom: 10px;"></i>
                    <p style="font-size: 13px;">No past orders found.</p>
                </div>
            `;
            return;
        }

        let html = "";
        orders.forEach(order => {
            const date = new Date(order.created_at).toLocaleDateString('en-IN', {
                day: 'numeric',
                month: 'short',
                year: 'numeric'
            });
            const itemsText = order.items.map(i => `${i.name} (x${i.quantity} ${i.unit})`).join(', ');
            
            let statusStyle = 'color: #f59e0b; background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.25);';
            if (order.status.toLowerCase() === 'successful') {
                statusStyle = 'color: #22c55e; background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.25);';
            } else if (order.status.toLowerCase() === 'unsuccessful') {
                statusStyle = 'color: #ef4444; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.25);';
            }

            html += `
                <div class="user-order-card glass-card" style="padding: 15px; border-radius: 12px; background: rgba(0,0,0,0.15); border: 1px solid rgba(255,255,255,0.03); font-size: 12px; display: flex; flex-direction: column; gap: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: var(--text-primary); font-size: 13px;">#RT-${order.id}</span>
                        <span style="padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 10px; text-transform: uppercase; ${statusStyle}">${order.status}</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted);"><i class="fa-regular fa-calendar"></i> Ordered: ${date}</div>
                    <div style="color: var(--text-secondary); line-height: 1.4; border-top: 1px dashed rgba(255,255,255,0.05); padding-top: 8px; margin-top: 2px;">
                        <strong>Items:</strong> ${itemsText}
                    </div>
                    <div style="font-weight: 700; text-align: right; color: var(--accent-color); font-size: 13px;">₹${order.total_cost.toLocaleString('en-IN')}</div>
                </div>
            `;
        });
        list.innerHTML = html;
    } catch (err) {
        list.innerHTML = `<p style="color: #ef4444; text-align: center; font-size: 12px;">Failed to load order history.</p>`;
    }
}


/* ==========================================================================
   PWA & Service Worker Registration & Installation Controls
   ========================================================================== */

let deferredPrompt;

// Catch beforeinstallprompt event to enable PWA install trigger
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    console.log('beforeinstallprompt event triggered. PWA install is ready.');
});

window.triggerPWAInstall = () => {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                showToast('Installing Sri Ram Traders App on your Android device!');
            }
            deferredPrompt = null;
        });
    } else {
        // Fallback: download mock APK directly
        showToast('Downloading offline Android APK package...');
        setTimeout(() => {
            const downloadLink = document.createElement('a');
            downloadLink.href = '/uploads/RamTraders.apk';
            downloadLink.download = 'RamTraders.apk';
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
        }, 1000);
    }
};

// Register service worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then((reg) => {
                console.log('PWA Service Worker registered successfully: ', reg.scope);
            })
            .catch((err) => {
                console.warn('PWA Service Worker registration failed: ', err);
            });
    });
}

