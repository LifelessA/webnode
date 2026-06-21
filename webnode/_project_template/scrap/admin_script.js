
        // Session validation on load
        document.addEventListener("DOMContentLoaded", () => {
            fetchSessionData();
            loadOrders();
            loadProducts();
            initDepotMap();
        });

        async function fetchSessionData() {
            try {
                const res = await fetch('/api/admin/session');
                const data = await res.json();
                if (!data.loggedIn) {
                    window.location.href = '/login.html';
                } else {
                    document.getElementById('adminUsernameTag').textContent = `Logged in: ${data.username}`;
                }
            } catch (err) {
                window.location.href = '/login.html';
            }
        }

        async function logoutAdmin() {
            try {
                const res = await fetch('/api/admin/logout');
                const result = await res.json();
                if (result.success) {
                    window.location.href = '/login.html';
                }
            } catch (err) {
                alert('Could not sign out.');
            }
        }

        function switchAdminTab(tabId, btn) {
            const sections = document.querySelectorAll('.admin-content-section');
            const buttons = document.querySelectorAll('.admin-tab-btn');
            
            sections.forEach(s => s.classList.remove('active'));
            buttons.forEach(b => b.classList.remove('active'));

            document.getElementById(`${tabId}-tab-section`).classList.add('active');
            btn.classList.add('active');

            if (tabId === 'logistics' && map) {
                // Leaflet requires invalidating size if rendered in hidden container
                setTimeout(() => {
                    map.invalidateSize();
                }, 100);
            }
        }

        /* ==========================================================================
           Orders Dashboard Logic
           ========================================================================== */
        async function loadOrders() {
            try {
                const res = await fetch('/api/orders');
                const orders = await res.json();
                
                const tableBody = document.getElementById('adminOrdersTableBody');
                if (orders.length === 0) {
                    tableBody.innerHTML = `<tr><td colspan="6" style="text-align: center;">No orders recorded.</td></tr>`;
                    return;
                }

                let html = "";
                orders.forEach(order => {
                    const date = new Date(order.created_at).toLocaleString('en-IN');
                    const itemsText = order.items.map(i => `${i.name} (x${i.quantity} ${i.unit})`).join(', ');
                    
                    let statusClass = "pending";
                    if (order.status.toLowerCase() === 'successful') statusClass = 'successful';
                    if (order.status.toLowerCase() === 'unsuccessful') statusClass = 'unsuccessful';

                    html += `
                        <tr>
                            <td style="font-weight: 700;">#RT-${order.id}</td>
                            <td>${date}</td>
                            <td>
                                <strong>${order.customer_name}</strong><br>
                                <span style="font-size: 12px;"><i class="fa-solid fa-phone"></i> ${order.customer_phone}</span><br>
                                <span style="font-size: 11px;"><i class="fa-solid fa-location-dot"></i> ${order.customer_address}</span><br>
                                <span style="font-size: 11px; color: var(--text-muted);">Note: ${order.customer_notes}</span>
                            </td>
                            <td>${itemsText}</td>
                            <td style="font-weight: 700; color: var(--text-primary);">₹${order.total_cost.toLocaleString("en-IN")}</td>
                            <td>
                                <select class="order-status-select ${statusClass}" onchange="updateOrderStatus(${order.id}, this.value, this)">
                                    <option value="Pending" ${order.status === 'Pending' ? 'selected' : ''}>Pending</option>
                                    <option value="Successful" ${order.status === 'Successful' ? 'selected' : ''}>Successful</option>
                                    <option value="Unsuccessful" ${order.status === 'Unsuccessful' ? 'selected' : ''}>Unsuccessful</option>
                                </select>
                            </td>
                        </tr>
                    `;
                });
                tableBody.innerHTML = html;
            } catch (err) {
                console.error(err);
            }
        }

        async function updateOrderStatus(orderId, status, selectEl) {
            try {
                const res = await fetch(`/api/orders/${orderId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status })
                });
                
                const result = await res.json();
                if (result.success) {
                    // Update classes for color formatting
                    selectEl.className = "order-status-select " + status.toLowerCase();
                    alert(`Order #${orderId} status set to: ${status}`);
                }
            } catch (err) {
                alert('Failed to update status.');
            }
        }

        /* ==========================================================================
           Products Editor Form Controls
           ========================================================================== */
        let loadedProducts = [];

        async function loadProducts() {
            try {
                const res = await fetch('/api/products');
                loadedProducts = await res.json();
                
                const container = document.getElementById('adminProductsList');
                let html = "";
                loadedProducts.forEach(p => {
                    html += `
                        <div class="product-list-card glass-card hover-glow" onclick="selectProductToEdit('${p.key}')" id="card-${p.key}">
                            <div class="p-info">
                                <img src="${p.image}" alt="${p.name}" onerror="this.src='https://cdn.pixabay.com/photo/2019/12/10/20/59/site-4686908_640.jpg'">
                                <div>
                                    <h4>${p.name}</h4>
                                    <span class="p-price">₹${p.price.toLocaleString("en-IN")} / ${p.unit.slice(0,-1)}</span>
                                </div>
                            </div>
                            <button class="row-remove-btn" onclick="deleteProduct(event, '${p.key}')" title="Delete Product"><i class="fa-solid fa-trash-can"></i></button>
                        </div>
                    `;
                });
                container.innerHTML = html;
                
                // Select first product by default if list has items
                if (loadedProducts.length > 0) {
                    selectProductToEdit(loadedProducts[0].key);
                }
            } catch (err) {
                console.error(err);
            }
        }

        let currentProductUploadedImages = []; // stores base64 strings of newly selected images
        let currentProductExistingImages = []; // stores existing image urls/paths

        function renderAdminImagesPreview() {
            const container = document.getElementById('adminImagePreviewGrid');
            if (!container) return;

            let html = "";
            
            // Render existing images
            currentProductExistingImages.forEach((src, idx) => {
                html += `
                    <div class="upload-preview-card" style="position: relative; width: 80px; height: 80px; border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.08);">
                        <img src="${src}" alt="existing-${idx}" style="width: 100%; height: 100%; object-fit: cover;">
                        <span style="position: absolute; bottom: 4px; left: 4px; background: rgba(34,197,94,0.85); color: #fff; font-size: 8px; font-weight: 700; padding: 1px 4px; border-radius: 4px;">Saved</span>
                        <button type="button" onclick="removeExistingAdminImage(${idx})" style="position: absolute; top: 2px; right: 2px; background: rgba(0,0,0,0.6); color: #fff; border: none; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center; font-size: 11px; cursor: pointer; line-height: 1;">&times;</button>
                    </div>
                `;
            });

            // Render newly uploaded base64 images
            currentProductUploadedImages.forEach((base64, idx) => {
                html += `
                    <div class="upload-preview-card" style="position: relative; width: 80px; height: 80px; border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.08);">
                        <img src="${base64}" alt="new-${idx}" style="width: 100%; height: 100%; object-fit: cover;">
                        <span style="position: absolute; bottom: 4px; left: 4px; background: rgba(245,158,11,0.85); color: #fff; font-size: 8px; font-weight: 700; padding: 1px 4px; border-radius: 4px;">New</span>
                        <button type="button" onclick="removeUploadedAdminImage(${idx})" style="position: absolute; top: 2px; right: 2px; background: rgba(0,0,0,0.6); color: #fff; border: none; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center; font-size: 11px; cursor: pointer; line-height: 1;">&times;</button>
                    </div>
                `;
            });

            container.innerHTML = html;
        }

        window.removeExistingAdminImage = (idx) => {
            currentProductExistingImages.splice(idx, 1);
            renderAdminImagesPreview();
        };

        window.removeUploadedAdminImage = (idx) => {
            currentProductUploadedImages.splice(idx, 1);
            renderAdminImagesPreview();
        };

        window.handleAdminImageSelect = (event) => {
            const files = event.target.files;
            if (!files || files.length === 0) return;

            Array.from(files).forEach(file => {
                const reader = new FileReader();
                reader.onload = (e) => {
                    currentProductUploadedImages.push(e.target.result);
                    renderAdminImagesPreview();
                };
                reader.readAsDataURL(file);
            });
            event.target.value = "";
        };

        function selectProductToEdit(key) {
            // Update active states
            const cards = document.querySelectorAll('.product-list-card');
            cards.forEach(c => c.classList.remove('active'));
            const selectedCard = document.getElementById(`card-${key}`);
            if (selectedCard) selectedCard.classList.add('active');

            const p = loadedProducts.find(item => item.key === key);
            if (!p) return;

            document.getElementById('formTitle').textContent = `Edit Product: ${p.name}`;
            document.getElementById('prodKey').value = p.key;
            document.getElementById('prodKeyDisplay').value = p.key;
            document.getElementById('prodKeyDisplay').disabled = true; // Key cannot be edited
            document.getElementById('prodName').value = p.name;
            document.getElementById('prodPrice').value = p.price;
            document.getElementById('prodOrigPrice').value = p.original_price;
            document.getElementById('prodDiscount').value = p.discount || '';
            document.getElementById('prodUnit').value = p.unit;
            document.getElementById('prodImage').value = p.image;
            document.getElementById('prodBrand').value = p.brand || '';
            document.getElementById('prodSpeed').value = p.speed || '';
            document.getElementById('prodRating').value = p.rating || '';
            document.getElementById('prodRatingCount').value = p.rating_count || '';
            document.getElementById('prodKeywords').value = p.keywords || '';

            // Initialize image collections
            currentProductUploadedImages = [];
            currentProductExistingImages = Array.isArray(p.thumbnails) ? [...p.thumbnails] : (p.image ? [p.image] : []);
            renderAdminImagesPreview();

            // Set highlights
            const highlightContainer = document.getElementById('prodHighlightsContainer');
            highlightContainer.innerHTML = "";
            p.highlights.forEach(h => {
                addHighlightRow(h);
            });

            // Set specs table
            const specsContainer = document.getElementById('prodSpecsContainer');
            specsContainer.innerHTML = "";
            Object.entries(p.specs).forEach(([k, val]) => {
                addSpecRow(k, val);
            });
        }

        function loadProductFormForCreate() {
            document.getElementById('formTitle').textContent = "Add New Product";
            document.getElementById('prodKey').value = "";
            document.getElementById('prodKeyDisplay').value = "";
            document.getElementById('prodKeyDisplay').disabled = false; // key required for new product
            document.getElementById('prodName').value = "";
            document.getElementById('prodPrice').value = "";
            document.getElementById('prodOrigPrice').value = "";
            document.getElementById('prodDiscount').value = "";
            document.getElementById('prodUnit').value = "";
            document.getElementById('prodImage').value = "";
            document.getElementById('prodBrand').value = "";
            document.getElementById('prodSpeed').value = "";
            document.getElementById('prodRating').value = "4.5";
            document.getElementById('prodRatingCount').value = "(0 reviews)";
            document.getElementById('prodKeywords').value = "";
            
            document.getElementById('prodHighlightsContainer').innerHTML = "";
            document.getElementById('prodSpecsContainer').innerHTML = "";
            
            // Initialize image collections
            currentProductUploadedImages = [];
            currentProductExistingImages = [];
            renderAdminImagesPreview();

            // Remove active list item selection
            const cards = document.querySelectorAll('.product-list-card');
            cards.forEach(c => c.classList.remove('active'));

            // Focus name
            document.getElementById('prodName').focus();
        }

        function addHighlightRow(value = "") {
            const container = document.getElementById('prodHighlightsContainer');
            const div = document.createElement('div');
            div.className = "row-item";
            div.innerHTML = `
                <input type="text" class="highlight-input" value="${value}" placeholder="Highlight description point...">
                <button type="button" class="row-remove-btn" onclick="this.parentElement.remove()">&times;</button>
            `;
            container.appendChild(div);
        }

        function addSpecRow(key = "", value = "") {
            const container = document.getElementById('prodSpecsContainer');
            const div = document.createElement('div');
            div.className = "row-item";
            div.innerHTML = `
                <input type="text" class="spec-key-input" value="${key}" placeholder="Attribute Name (e.g. Dimensions)" style="flex: 0.8;">
                <input type="text" class="spec-val-input" value="${value}" placeholder="Value (e.g. 9x4.5x3 Inches)" style="flex: 1.2;">
                <button type="button" class="row-remove-btn" onclick="this.parentElement.remove()">&times;</button>
            `;
            container.appendChild(div);
        }

        async function saveProductConfig(event) {
            event.preventDefault();
            
            const isNew = document.getElementById('prodKey').value === "";
            const key = isNew ? document.getElementById('prodKeyDisplay').value.trim() : document.getElementById('prodKey').value;
            
            if (!key) {
                alert('Please provide a unique product key identifier.');
                return;
            }

            // Gather highlights
            const highlightInputs = document.querySelectorAll('.highlight-input');
            const highlights = [];
            highlightInputs.forEach(i => {
                if (i.value.trim()) highlights.push(i.value.trim());
            });

            // Gather specs key-value
            const specKeyInputs = document.querySelectorAll('.spec-key-input');
            const specValInputs = document.querySelectorAll('.spec-val-input');
            const specs = {};
            specKeyInputs.forEach((input, index) => {
                const k = input.value.trim();
                const v = specValInputs[index]?.value.trim();
                if (k && v) {
                    specs[k] = v;
                }
            });

            const data = {
                key,
                name: document.getElementById('prodName').value,
                price: parseFloat(document.getElementById('prodPrice').value),
                original_price: parseFloat(document.getElementById('prodOrigPrice').value),
                discount: document.getElementById('prodDiscount').value || null,
                unit: document.getElementById('prodUnit').value,
                image: document.getElementById('prodImage').value || '',
                brand: document.getElementById('prodBrand').value || null,
                speed: document.getElementById('prodSpeed').value || null,
                rating: document.getElementById('prodRating').value || null,
                rating_count: document.getElementById('prodRatingCount').value || null,
                keywords: document.getElementById('prodKeywords').value || '',
                highlights,
                specs,
                uploadedImages: currentProductUploadedImages,
                existingImages: currentProductExistingImages
            };

            try {
                const res = await fetch('/api/products', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await res.json();
                if (result.success) {
                    alert('Product configuration saved successfully!');
                    loadProducts(); // reload listings
                } else {
                    alert('Error saving product: ' + result.error);
                }
            } catch (err) {
                alert('Error connecting to backend.');
            }
        }

        async function deleteProduct(event, key) {
            event.stopPropagation(); // prevent clicking card selection
            if (!confirm(`Are you sure you want to delete product '${key}' from catalog?`)) return;

            try {
                const res = await fetch(`/api/products/${key}`, {
                    method: 'DELETE'
                });
                const result = await res.json();
                if (result.success) {
                    alert('Product deleted.');
                    loadProducts();
                } else {
                    alert('Failed to delete: ' + result.error);
                }
            } catch (err) {
                alert('Failed to delete product.');
            }
        }

        /* ==========================================================================
           Logistics Leaflet Map Drawing Widgets
           ========================================================================== */
        let map;
        let mapCircle;
        let mapMarker;
        
        let currentLat = 25.611;
        let currentLng = 85.144;
        let currentRadius = 30; // 30 km radius boundary

        async async function initDepotMap() {
            // Fetch existing settings coordinates if any
            try {
                const res = await fetch('/api/settings/logistics_boundary');
                const result = await res.json();
                if (result.success && result.value) {
                    const saved = JSON.parse(result.value);
                    currentLat = saved.lat || currentLat;
                    currentLng = saved.lng || currentLng;
                    currentRadius = saved.radius || currentRadius;
                }
            } catch (err) {
                console.error('Failed to load settings:', err);
            }

            // Draw map canvas centered around current depot coordinates
            map = L.map('adminLogisticsMap').setView([currentLat, currentLng], 9);

            // Add standard OpenStreetMap tiles
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);

            // Create depot marker (draggable)
            mapMarker = L.marker([currentLat, currentLng], { draggable: true }).addTo(map);
            
            // Create range area circle
            mapCircle = L.circle([currentLat, currentLng], {
                color: 'var(--accent-color)',
                fillColor: 'rgba(245, 158, 11, 0.15)',
                fillOpacity: 0.35,
                radius: currentRadius * 1000 // Convert km to meters
            }).addTo(map);

            // Sync coordinates on drag
            mapMarker.on('drag', function (e) {
                const position = mapMarker.getLatLng();
                currentLat = parseFloat(position.lat.toFixed(5));
                currentLng = parseFloat(position.lng.toFixed(5));
                
                mapCircle.setLatLng(position);
                updateCoordsDisplay();
            });

            // Set coordinates on click anywhere on map
            map.on('click', function(e) {
                const coords = e.latlng;
                currentLat = parseFloat(coords.lat.toFixed(5));
                currentLng = parseFloat(coords.lng.toFixed(5));
                
                mapMarker.setLatLng(coords);
                mapCircle.setLatLng(coords);
                updateCoordsDisplay();
            });

            // Set initial controls value
            document.getElementById('mapRadiusSlider').value = currentRadius;
            updateCoordsDisplay();
        }

        function updateMapRadius(val) {
            currentRadius = parseInt(val) || 30;
            document.getElementById('radiusValText').textContent = `${currentRadius} km`;
            
            if (mapCircle) {
                mapCircle.setRadius(currentRadius * 1000);
            }
            updateCoordsDisplay();
        }

        function updateCoordsDisplay() {
            document.getElementById('coordLat').textContent = currentLat;
            document.getElementById('coordLng').textContent = currentLng;
            document.getElementById('coordRad').textContent = `${currentRadius} km`;
            document.getElementById('coordRad').textContent = `${currentRadius} km`;
        }

        async function saveLogisticsSettings() {
            const data = {
                key: 'logistics_boundary',
                value: JSON.stringify({
                    lat: currentLat,
                    lng: currentLng,
                    radius: currentRadius
                })
            };

            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await res.json();
                if (result.success) {
                    alert('Logistics delivery boundary coordinates saved to database!');
                } else {
                    alert('Failed to save settings: ' + result.error);
                }
            } catch (err) {
                alert('Could not save logistics settings to server.');
            }
        }
    