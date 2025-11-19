from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

# -------------------------------
# Product Management HTML Page
# -------------------------------
@router.get("/", response_class=HTMLResponse)
def product_management_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <title>Product Management</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
            th { background: #f0f0f0; }
            input, select { margin-right: 10px; padding: 4px; }
            button { padding: 4px 8px; margin-left: 5px; }
            /* Modal styles */
            #product_modal {
                display: none;
                position: fixed; top:0; left:0; right:0; bottom:0;
                background: rgba(0,0,0,0.5);
                justify-content: center; align-items: center;
            }
            #product_modal_content {
                background: white;
                padding: 20px;
                border-radius: 8px;
                width: 400px;
            }
            #product_modal_content input, #product_modal_content label {
                display: block;
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <h1>Product Management</h1>

        <div>
            <label>SKU: <input type="text" id="filter_sku"></label>
            <label>Name: <input type="text" id="filter_name"></label>
            <label>Active: 
                <select id="filter_active">
                    <option value="">All</option>
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                </select>
            </label>
            <button onclick="loadProducts()">Filter</button>
            <button onclick="openModal()">Create Product</button>
            <button onclick="bulkDeleteProducts()" style="background:red; color:white;">Delete All Products</button>
        </div>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>SKU</th>
                    <th>Name</th>
                    <th>Description</th>
                    <th>Active</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="product_table"></tbody>
        </table>

        <div style="margin-top:10px;">
            <button onclick="prevPage()">Prev</button>
            <span id="page_info"></span>
            <button onclick="nextPage()">Next</button>
        </div>

        <!-- Modal for Create/Update -->
        <div id="product_modal">
            <div id="product_modal_content">
                <h2 id="modal_title">Create Product</h2>
                <input type="text" id="modal_sku" placeholder="SKU" />
                <input type="text" id="modal_name" placeholder="Name" />
                <input type="text" id="modal_description" placeholder="Description" />
                <label>
                    <input type="checkbox" id="modal_active" checked /> Active
                </label>
                <div style="text-align: right;">
                    <button onclick="closeModal()">Cancel</button>
                    <button onclick="saveProduct()">Save</button>
                </div>
            </div>
        </div>

        <script>
            let page = 1;
            const size = 10;
            let editId = null; // null = create, number = update

            async function loadProducts() {
                const sku = document.getElementById('filter_sku').value || '';
                const name = document.getElementById('filter_name').value || '';
                const activeVal = document.getElementById('filter_active').value;

                const skip = (page-1)*size;
                const limit = size;

                const params = { skip, limit };
                if (sku) params.sku = sku;
                if (name) params.name = name;
                if (activeVal !== '') params.active = activeVal;

                const query = new URLSearchParams(params);
                const res = await fetch(`/products?${query}`);
                if (!res.ok) { alert("Failed to load products"); return; }

                const data = await res.json();
                const tbody = document.getElementById('product_table');
                tbody.innerHTML = "";
                data.forEach(p => {
                    tbody.innerHTML += `
                        <tr>
                            <td>${p.id}</td>
                            <td>${p.sku}</td>
                            <td>${p.name}</td>
                            <td>${p.description}</td>
                            <td>${p.active}</td>
                            <td>
                                <button onclick="openModal(${p.id}, '${p.sku}', '${p.name}', '${p.description}', ${p.active})">Edit</button>
                                <button onclick="deleteProduct(${p.id})">Delete</button>
                            </td>
                        </tr>
                    `;
                });
                document.getElementById('page_info').innerText = "Page " + page;
            }

            function prevPage() { if(page > 1){ page--; loadProducts(); } }
            function nextPage() { page++; loadProducts(); }

            function openModal(id=null, sku='', name='', desc='', active=true) {
                editId = id;
                document.getElementById('modal_title').innerText = id ? "Edit Product" : "Create Product";
                document.getElementById('modal_sku').value = sku;
                document.getElementById('modal_name').value = name;
                document.getElementById('modal_description').value = desc;
                document.getElementById('modal_active').checked = active;
                document.getElementById('product_modal').style.display = 'flex';
            }

            function closeModal() {
                document.getElementById('product_modal').style.display = 'none';
            }

            async function saveProduct() {
                const sku = document.getElementById('modal_sku').value;
                const name = document.getElementById('modal_name').value;
                const desc = document.getElementById('modal_description').value;
                const active = document.getElementById('modal_active').checked;

                let method = 'POST';
                let url = '/products';
                let body = {sku, name, description: desc, active};

                if(editId) {
                    method = 'PATCH';
                    url = `/products/${editId}`;
                    delete body.sku; // SKU is usually immutable on update
                }

                const res = await fetch(url, {
                    method,
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(body)
                });
                if(!res.ok) { alert("Failed to save product"); return; }

                closeModal();
                loadProducts();
            }

            async function deleteProduct(id) {
                if(confirm("Are you sure you want to delete this product?")) {
                    await fetch(`/products/${id}`, {method:"DELETE"});
                    loadProducts();
                }
            }

            async function bulkDeleteProducts() {
                // Ask for confirmation before deletion
                if (!confirm("Are you sure? This cannot be undone.")) return;

                try {
                    const res = await fetch('/products/bulk_delete?confirm=true', {
                        method: 'POST'
                    });

                    if (res.ok) {
                        alert("All products deleted successfully!");
                        // Optionally, reload product list or clear table
                        loadProducts();
                    } else {
                        const err = await res.json();
                        alert("Failed to delete products: " + (err.detail || "Unknown error"));
                    }
                } catch (err) {
                    console.error('Bulk delete error:', err);
                    alert('Failed to delete products.');
                }
            }


            window.addEventListener('DOMContentLoaded', () => { loadProducts(); });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
