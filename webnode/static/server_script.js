function process_logic(request) {
    // Simulated backend logic for e-commerce functionality
    const { action, data } = request;

    let response = {};

    switch (action) {
        case 'get_products':
            response = {
                products: [
                    { id: 1, name: "Product 1", price: 29.99, image: "/images/product1.jpg" },
                    { id: 2, name: "Product 2", price: 39.99, image: "/images/product2.jpg" },
                    { id: 3, name: "Product 3", price: 49.99, image: "/images/product3.jpg" }
                ]
            };
            break;

        case 'add_to_cart':
            response = {
                success: true,
                message: `Added to cart: ${data.productName} - $${data.productPrice}`
            };
            break;

        case 'get_cart_items':
            response = {
                items: [],
                total: 0
            };
            break;

        case 'scroll_to_section':
            response = {
                success: true,
                message: `Scrolled to section: ${data.sectionId}`
            };
            break;

        default:
            response = {
                error: "Unknown action"
            };
    }

    return response;
}