let items = [];
let selectedTaxRate = 0.10; // Default 10% tax rate

function updateTotals() {
    let subtotal = 0;
    items.forEach(item => {
        subtotal += item.subtotal;
    });

    const taxAmount = subtotal * selectedTaxRate;
    const total = subtotal + taxAmount;

    document.getElementById('taxAmount').value = taxAmount.toFixed(2);
    document.getElementById('totalAmount').value = total.toFixed(2);
    document.getElementById('itemsJson').value = JSON.stringify(items);
}

function createItemRow(index) {
    return `
        <div class="row mb-3 item-row" data-index="${index}">
            <div class="col-md-5">
                <input type="text" class="form-control" placeholder="Item Description" required
                    onchange="updateItem(${index}, 'description', this.value)">
            </div>
            <div class="col-md-2">
                <input type="number" class="form-control" placeholder="Quantity" value="1" min="1" required
                    onchange="updateItem(${index}, 'quantity', this.value)">
            </div>
            <div class="col-md-2">
                <input type="number" class="form-control" placeholder="Price" value="0" min="0" step="0.01" required
                    onchange="updateItem(${index}, 'price', this.value)">
            </div>
            <div class="col-md-2">
                <input type="number" class="form-control" placeholder="Subtotal" value="0" readonly>
            </div>
            <div class="col-md-1">
                <button type="button" class="btn btn-danger" onclick="removeItem(${index})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `;
}

function addItem() {
    const index = items.length;
    items.push({
        description: '',
        quantity: 1,
        price: 0,
        subtotal: 0
    });

    const itemsList = document.getElementById('itemsList');
    itemsList.insertAdjacentHTML('beforeend', createItemRow(index));
}

function updateItem(index, field, value) {
    items[index][field] = value;
    if (field === 'quantity' || field === 'price') {
        items[index].quantity = parseFloat(items[index].quantity) || 0;
        items[index].price = parseFloat(items[index].price) || 0;
        items[index].subtotal = items[index].quantity * items[index].price;

        const row = document.querySelector(`.item-row[data-index="${index}"]`);
        row.querySelector('input[placeholder="Subtotal"]').value = 'Rs. ' + items[index].subtotal.toFixed(2);
    }
    updateTotals();
}

function removeItem(index) {
    items.splice(index, 1);
    const itemsList = document.getElementById('itemsList');
    itemsList.innerHTML = '';
    items.forEach((item, i) => {
        itemsList.insertAdjacentHTML('beforeend', createItemRow(i));
        const row = document.querySelector(`.item-row[data-index="${i}"]`);
        row.querySelector('input[placeholder="Item Description"]').value = item.description;
        row.querySelector('input[placeholder="Quantity"]').value = item.quantity;
        row.querySelector('input[placeholder="Price"]').value = item.price;
        row.querySelector('input[placeholder="Subtotal"]').value = 'Rs. ' + item.subtotal.toFixed(2);
    });
    updateTotals();
}

// Handle tax rate changes
document.querySelectorAll('input[name="tax_rate"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        selectedTaxRate = parseFloat(e.target.value);
        updateTotals();
    });
});

document.getElementById('addItem').addEventListener('click', addItem);
document.addEventListener('DOMContentLoaded', () => addItem());