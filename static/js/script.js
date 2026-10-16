function updatePrice(selectEl) {
    const selectedOption = selectEl.options[selectEl.selectedIndex];
    const price = selectedOption.getAttribute('data-price');
    const form = selectEl.closest('form');
    const priceValue = form.querySelector('.price-value');
    const priceInput = form.querySelector('.price-input');
    if (price) {
        priceValue.textContent = Number(price).toLocaleString();
        priceInput.value = price;
    }
}
function prepareOrder(form) {
    const name = form.querySelector('[name="customer_name"]').value.trim();
    const phone = form.querySelector('[name="phone"]').value.trim();
    const address = form.querySelector('[name="address"]').value.trim();
    if (!name || !phone || !address) {
        alert('براہ کرم تمام فیلڈز بھریں');
        return false;
    }
    if (phone.length < 10) {
        alert('براہ کرم درست موبائل نمبر درج کریں');
        return false;
    }
    return true;
}
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.size-select').forEach(select => updatePrice(select));
});
