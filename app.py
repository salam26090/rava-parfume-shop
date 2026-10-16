import os
from urllib.parse import quote
from flask import Flask, render_template, request

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "rava-parfume-secret-key")

SHOP_INFO = {
    "name": "RAVA PARFUME",
    "brand": "RAVA PARFUME",
    "currency": "PKR",
    "whatsapp": "00923454828100",
    "whatsapp_url": "923454828100",
    "email": "salam26090@gmail.com"
}

COLLECTIONS = {
    "Luxury": {
        "name": "Luxury Collection",
        "perfumes": [
            {"id": "rava01", "name": "Rava Royal Oud", "desc": "A rich and luxurious fragrance.", "prices": {"10ml": 500, "20ml": 900, "50ml": 1800, "100ml": 3000}},
            {"id": "rava02", "name": "Rava Golden Amber", "desc": "A warm and elegant fragrance.", "prices": {"10ml": 500, "20ml": 900, "50ml": 1800, "100ml": 3000}},
            {"id": "rava03", "name": "Rava Velvet Rose", "desc": "A soft and beautiful floral fragrance.", "prices": {"10ml": 450, "20ml": 850, "50ml": 1700, "100ml": 2800}}
        ]
    }
}

@app.route("/")
def home():
    return render_template("index.html", shop=SHOP_INFO, collections=COLLECTIONS)

@app.route("/checkout", methods=["POST"])
def checkout():
    perfume_name = request.form.get("perfume_name", "").strip()
    size = request.form.get("size", "").strip()
    price = request.form.get("price", "").strip()
    customer_name = request.form.get("customer_name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    missing = []
    if not perfume_name: missing.append("Perfume")
    if not size: missing.append("Size")
    if not customer_name: missing.append("Name")
    if not phone: missing.append("Phone")
    if not address: missing.append("Address")

    if missing:
        return render_template("index.html", shop=SHOP_INFO, collections=COLLECTIONS,
                               error=f"براہ کرم یہ فیلڈز بھریں: {', '.join(missing)}"), 400

    message = (
        f"*New RAVA PARFUME Order*\n"
        f"──────────────\n"
        f"🌸 Perfume: {perfume_name}\n"
        f"📦 Size: {size}\n"
        f"💰 Price: PKR {price}\n"
        f"──────────────\n"
        f"👤 Customer: {customer_name}\n"
        f"📞 Phone: {phone}\n"
        f"📍 Address: {address}"
    )
    whatsapp_url = f"https://wa.me/{SHOP_INFO['whatsapp_url']}?text={quote(message)}"
    return render_template("success.html", shop=SHOP_INFO, whatsapp_url=whatsapp_url,
                           perfume_name=perfume_name, size=size, price=price,
                           customer_name=customer_name)

@app.route("/health")
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
