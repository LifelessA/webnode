function process_logic(request) {
    const store_name = request.store_name || "My Store";
    const cart_count = request.cart_count || 0;
    const featured_products = request.featured_products || [];
    const categories = request.categories || [];
    const testimonials = request.testimonials || [];
    const store_email = request.store_email || "";
    const store_phone = request.store_phone || "";
    const store_address = request.store_address || "";

    let product_grid_html = '';
    featured_products.forEach(product => {
        product_grid_html += `
                <div class="product-card">
                    <img src="${product.image_url}" alt="${product.name}">
                    <h3>${product.name}</h3>
                    <p class="price">$${product.price}</p>
                    <a href="/product/${product.id}" class="btn-secondary">View Details</a>
                </div>
        `;
    });

    let category_grid_html = '';
    categories.forEach(category => {
        category_grid_html += `
                <a href="/category/${category.id}" class="category-card">
                    <img src="${category.image_url}" alt="${category.name}">
                    <h3>${category.name}</h3>
                </a>
        `;
    });

    let testimonial_grid_html = '';
    testimonials.forEach(testimonial => {
        testimonial_grid_html += `
                <div class="testimonial-card">
                    <p>"${testimonial.comment}"</p>
                    <p class="customer">- ${testimonial.customer_name}</p>
                </div>
        `;
    });

    return {
        html: `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${store_name} - Home</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="/static/css/home.css">
  </head>
  <body>
    <!-- Header -->
    <header class="header">
      <div class="container">
        <div class="logo">
          <h1>${store_name}</h1>
        </div>
        <nav class="navigation">
          <ul>
            <li><a href="/">Home</a></li>
            <li><a href="/products">Products</a></li>
            <li><a href="/categories">Categories</a></li>
            <li><a href="/about">About</a></li>
            <li><a href="/contact">Contact</a></li>
          </ul>
        </nav>
        <div class="header-actions">
          <a href="/cart" class="cart-icon">
            <span>Cart (${cart_count})</span>
          </a>
          <a href="/account" class="account-icon">
            <span>Account</span>
          </a>
        </div>
      </div>
    </header>

    <!-- Hero Section -->
    <section class="hero">
      <div class="container">
        <div class="hero-content">
          <h2>Welcome to ${store_name}</h2>
          <p>Your one-stop shop for all your needs</p>
          <a href="/products" class="btn-primary">Shop Now</a>
        </div>
      </div>
    </section>

    <!-- Featured Products -->
    <section class="featured-products">
      <div class="container">
        <h2>Featured Products</h2>
        <div class="product-grid">
          ${product_grid_html}
        </div>
      </div>
    </section>

    <!-- Categories -->
    <section class="categories">
      <div class="container">
        <h2>Shop by Category</h2>
        <div class="category-grid">
          ${category_grid_html}
        </div>
      </div>
    </section>

    <!-- Testimonials -->
    <section class="testimonials">
      <div class="container">
        <h2>What Our Customers Say</h2>
        <div class="testimonial-grid">
          ${testimonial_grid_html}
        </div>
      </div>
    </section>

    <!-- Newsletter -->
    <section class="newsletter">
      <div class="container">
        <h2>Subscribe to Our Newsletter</h2>
        <p>Get the latest updates and offers</p>
        <form action="/subscribe" method="post">
          <input type="email" name="email" placeholder="Enter your email" required>
          <button type="submit" class="btn-primary">Subscribe</button>
        </form>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="container">
        <div class="footer-content">
          <div class="footer-section">
            <h3>${store_name}</h3>
            <p>Your trusted online shopping destination</p>
          </div>
          <div class="footer-section">
            <h4>Quick Links</h4>
            <ul>
              <li><a href="/">Home</a></li>
              <li><a href="/products">Products</a></li>
              <li><a href="/about">About Us</a></li>
              <li><a href="/contact">Contact</a></li>
            </ul>
          </div>
          <div class="footer-section">
            <h4>Contact Info</h4>
            <p>Email: ${store_email}</p>
            <p>Phone: ${store_phone}</p>
            <p>Address: ${store_address}</p>
          </div>
        </div>
        <div class="footer-bottom">
          <p>&copy; 2023 ${store_name}. All rights reserved.</p>
        </div>
      </div>
    </footer>

    <script src="/static/js/main.js"></script>
  </body>
</html>`
    };
}