from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def webhook_management_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Webhook Management</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            table { border-collapse: collapse; width: 100%; margin-top: 10px; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
            th { background: #f0f0f0; }
            input, select { padding: 4px; margin-right: 5px; }
            button { padding: 4px 8px; margin-right: 5px; }
        </style>
    </head>
    <body>
        <h1>Webhook Management</h1>

        <div>
            <button onclick="showAddModal()">Add Webhook</button>
        </div>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>URL</th>
                    <th>Event</th>
                    <th>Enabled</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="webhook_table"></tbody>
        </table>

        <!-- Add/Edit Modal -->
        <div id="webhook_modal" style="display:none; position:fixed; top:20%; left:30%; background:#fff; padding:20px; border:1px solid #ccc;">
            <h3 id="modal_title">Add Webhook</h3>
            <label>URL: <input type="text" id="modal_url"></label><br><br>
            <label>Event: <input type="text" id="modal_event"></label><br><br>
            <label>Enabled: 
                <select id="modal_enabled">
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                </select>
            </label><br><br>
            <button onclick="saveWebhook()">Save</button>
            <button onclick="closeModal()">Cancel</button>
        </div>

        <script>
            let editId = null;

            async function loadWebhooks() {
                const res = await fetch('/webhooks');
                const data = await res.json();
                const tbody = document.getElementById('webhook_table');
                tbody.innerHTML = "";
                data.forEach(w => {
                    tbody.innerHTML += `
                        <tr>
                            <td>${w.id}</td>
                            <td>${w.url}</td>
                            <td>${w.event}</td>
                            <td>${w.enabled}</td>
                            <td>
                                <button onclick="editWebhook(${w.id}, '${w.url}', '${w.event}', ${w.enabled})">Edit</button>
                                <button onclick="deleteWebhook(${w.id})">Delete</button>
                                <button onclick="testWebhook(${w.id})">Test</button>
                            </td>
                        </tr>
                    `;
                });
            }

            function showAddModal() {
                editId = null;
                document.getElementById('modal_title').innerText = "Add Webhook";
                document.getElementById('modal_url').value = "";
                document.getElementById('modal_event').value = "";
                document.getElementById('modal_enabled').value = "true";
                document.getElementById('webhook_modal').style.display = "block";
            }

            function editWebhook(id, url, event, enabled) {
                editId = id;
                document.getElementById('modal_title').innerText = "Edit Webhook";
                document.getElementById('modal_url').value = url;
                document.getElementById('modal_event').value = event;
                document.getElementById('modal_enabled').value = enabled ? "true" : "false";
                document.getElementById('webhook_modal').style.display = "block";
            }

            function closeModal() {
                document.getElementById('webhook_modal').style.display = "none";
            }

            async function saveWebhook() {
                const url = document.getElementById('modal_url').value;
                const event = document.getElementById('modal_event').value;
                const enabled = document.getElementById('modal_enabled').value === 'true';

                if (editId) {
                    await fetch(`/webhooks/${editId}`, {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({url, event, enabled})
                    });
                } else {
                    await fetch('/webhooks', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({url, event, enabled})
                    });
                }
                closeModal();
                loadWebhooks();
            }

            async function deleteWebhook(id) {
                if (!confirm("Are you sure you want to delete this webhook?")) return;
                await fetch(`/webhooks/${id}`, { method: 'DELETE' });
                loadWebhooks();
            }

            async function testWebhook(id) {
                const res = await fetch(`/webhooks/${id}/test`, { method: 'POST' });
                const data = await res.json();
                alert(`Webhook test triggered. Task ID: ${data.task_id || 'N/A'}`);
            }

            window.addEventListener('DOMContentLoaded', loadWebhooks);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
