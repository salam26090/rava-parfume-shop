  ```python
import os
import json
import secrets
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from werkzeug.utils import secure_filename


# ==================================================
# APP CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")

if not app.secret_key:
    app.secret_key = secrets.token_hex(32)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
ADMIN_FILE = DATA_DIR / "admin.json"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


# ==================================================
# DEFAULT PRODUCTS
# ==================================================

DEFAULT_PRODUCTS = [
    {
        "id": 1,
        "name": "Rava Oud",
        "description": "ایک نفیس اور دیرپا عود کی خوشبو",
        "image": "",
        "prices": {
            "50": 1800,
            "80": 2500,
            "100": 3000,
        },
    },
    {
        "id": 2,
        "name": "Rava Rose",
        "description": "گلاب کی نرم اور دلکش خوشبو",
        "image": "",
        "prices": {
            "50": 1600,
            "80": 2200,
            "100": 2700,
        },
    },
    {
        "id": 3,
        "name": "Rava Blue",
        "description": "تازہ اور جدید خوشبو",
        "image": "",
        "prices": {
            "50": 1500,
            "80": 2100,
            "100": 2600,
        },
    },
    {
        "id": 4,
        "name": "Rava Amber",
        "description": "امبر کی گرم اور پُرکشش خوشبو",
        "image": "",
        "prices": {
            "50": 1700,
            "80": 2350,
            "100": 2850,
        },
    },
]


# ==================================================
# DEFAULT SETTINGS
# ==================================================

DEFAULT_SETTINGS = {
    "whatsapp": "923454828100",
    "easypaisa": "03454828100",
    "delivery_kabal": 0,
    "delivery_nearby": 200,
    "delivery_city": 250,
    "delivery_far": 500,
    "delivery_very_far": 600,
}


DEFAULT_ADMIN = {
    "username": "salam",
    "password": "salam123!",
}


# ==================================================
# JSON HELPERS
# ==================================================

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def read_json(path, default):
    if not path.exists():
        write_json(path, default)
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        app.logger.exception("JSON file could not be read: %s", path)
        return default


def get_products():
    return read_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)


def get_settings():
    settings = read_json(SETTINGS_FILE, DEFAULT_SETTINGS)

    if not isinstance(settings, dict):
        settings = DEFAULT_SETTINGS.copy()

    for key, value in DEFAULT_SETTINGS.items():
        settings.setdefault(key, value)

    return settings


def get_orders():
    orders = read_json(ORDERS_FILE, [])

    if not isinstance(orders, list):
        return []

    return orders


def is_admin():
    return session.get("is_admin") is True


def save_uploaded_image(file):
    if not file or not file.filename:
        return None

    safe_name = secure_filename(file.filename)
    extension = Path(safe_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return None

    image_name = secrets.token_hex(12) + extension
    file.save(UPLOAD_DIR / image_name)

    return "uploads/" + image_name


# ==================================================
# HOME PAGE
# ==================================================

@app.route("/")
def index():
    products = get_products()
    settings = get_settings()

    shop = {
        "whatsapp_url": settings["whatsapp"],
        "whatsapp": settings["whatsapp"],
    }

    return render_template(
        "index.html",
        products=products,
        settings=settings,
        shop=shop,
    )


# ==================================================
# PRODUCT ORDER
# ==================================================

@app.route("/order/<int:product_id>", methods=["GET", "POST"])
def order(product_id):
    products = get_products()

    product = next(
        (
            item
            for item in products
            if int(item.get("id", 0)) == product_id
        ),
        None,
    )

    if not product:
        flash("یہ پرفیوم دستیاب نہیں ہے۔")
        return redirect(url_for("index"))

    settings = get_settings()

    if request.method == "GET":
        return render_template(
            "order.html",
            product=product,
            settings=settings,
        )

    # Customer details
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    size = request.form.get("size", "").strip()
    payment = request.form.get("payment", "cod").strip()
    quantity_text = request.form.get("quantity", "1").strip()
    area = request.form.get("area", "city").strip()

    if not name or not phone or not address:
        flash("براہِ کرم نام، فون نمبر اور مکمل پتہ درج کریں۔")
        return redirect(url_for("order", product_id=product_id))

    # Validate quantity
    try:
        quantity = int(quantity_text)

        if quantity < 1 or quantity > 20:
            raise ValueError

    except (TypeError, ValueError):
        flash("تعداد 1 سے 20 کے درمیان درج کریں۔")
        return redirect(url_for("order", product_id=product_id))

    # Validate product price
    prices = product.get("prices", {})

    if size not in prices:
        flash("براہِ کرم درست سائز منتخب کریں۔")
        return redirect(url_for("order", product_id=product_id))

    try:
        unit_price = int(prices[size])

        if unit_price < 0:
            raise ValueError

    except (TypeError, ValueError):
        flash("اس سائز کی قیمت درست نہیں ہے۔")
        return redirect(url_for("order", product_id=product_id))

    # Delivery charges
    delivery_map = {
        "kabal": int(settings["delivery_kabal"]),
        "nearby": int(settings["delivery_nearby"]),
        "city": int(settings["delivery_city"]),
        "far": int(settings["delivery_far"]),
        "very_far": int(settings["delivery_very_far"]),
    }

    if area not in delivery_map:
        flash("براہِ کرم درست ڈیلیوری علاقہ منتخب کریں۔")
        return redirect(url_for("order", product_id=product_id))

    delivery = delivery_map[area]

    # Payment method
    if payment not in ("cod", "easypaisa"):
        flash("براہِ کرم ادائیگی کا درست طریقہ منتخب کریں۔")
        return redirect(url_for("order", product_id=product_id))

    if area != "kabal" and payment == "cod":
        flash("کابل سے باہر فی الحال Easypaisa منتخب کریں۔")
        return redirect(url_for("order", product_id=product_id))

    # Receipt upload
    receipt_name = ""

    if payment == "easypaisa":
        receipt = request.files.get("receipt")

        if not receipt or not receipt.filename:
            flash("Easypaisa ادائیگی کے لیے رسید کی تصویر اپ لوڈ کریں۔")
            return redirect(url_for("order", product_id=product_id))

        uploaded_path = save_uploaded_image(receipt)

        if not uploaded_path:
            flash("رسید کے لیے JPG، PNG یا WEBP تصویر اپ لوڈ کریں۔")
            return redirect(url_for("order", product_id=product_id))

        receipt_name = uploaded_path.replace("uploads/", "")

    # Create order record
    order_record = {
        "id": secrets.token_hex(4).upper(),
        "name": name,
        "phone": phone,
        "address": address,
        "area": area,
        "product_id": product_id,
        "product": product.get("name", "Perfume"),
        "size_ml": size,
        "quantity": quantity,
        "unit_price": unit_price,
        "delivery": delivery,
        "total": unit_price * quantity + delivery,
        "payment": payment,
        "receipt": receipt_name,
        "status": "نیا آرڈر",
    }

    # Save order
    orders = get_orders()
    orders.insert(0, order_record)
    write_json(ORDERS_FILE, orders)

    flash("آپ کا آرڈر کامیابی سے موصول ہو گیا ہے۔")

    # Return to the order page with a confirmation message.
    return render_template(
        "order.html",
        product=product,
        settings=settings,
        order=order_record,
        order_success=True,
    )


# ==================================================
# ADMIN LOGIN
# ==================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin_data = read_json(ADMIN_FILE, DEFAULT_ADMIN)

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (
            secrets.compare_digest(
                username,
                str(admin_data.get("username", "")),
            )
            and secrets.compare_digest(
                password,
                str(admin_data.get("password", "")),
            )
        ):
            session["is_admin"] = True
            return redirect(url_for("admin"))

        flash("یوزر نیم یا پاس ورڈ غلط ہے۔")

    return render_template("login.html")


# ==================================================
# ADMIN LOGOUT
# ==================================================

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))


# ==================================================
# ADMIN PANEL
# ==================================================

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not is_admin():
        return redirect(url_for("admin_login"))

    products = get_products()
    settings = get_settings()
    orders = get_orders()

    if request.method == "POST":
        action = request.form.get("action", "")

        # Save store settings
        if action == "save_settings":
            settings["whatsapp"] = request.form.get(
                "whatsapp",
                settings["whatsapp"],
            ).strip()

            settings["easypaisa"] = request.form.get(
                "easypaisa",
                settings["easypaisa"],
            ).strip()

            delivery_keys = (
                "delivery_kabal",
                "delivery_nearby",
                "delivery_city",
                "delivery_far",
                "delivery_very_far",
            )

            try:
                for key in delivery_keys:
                    settings[key] = max(
                        0,
                        int(request.form.get(key, "0")),
                    )

            except (TypeError, ValueError):
                flash("ڈیلیوری چارجز میں درست عدد درج کریں۔")
                return redirect(url_for("admin"))

            write_json(SETTINGS_FILE, settings)
            flash("سیٹنگز محفوظ ہو گئیں۔")

        # Update product
        elif action == "save_product":
            try:
                product_id = int(
                    request.form.get("product_id", "")
                )

                product = next(
                    item
                    for item in products
                    if int(item["id"]) == product_id
                )

                product["name"] = request.form.get(
                    "name",
                    "",
                ).strip()

                product["description"] = request.form.get(
                    "description",
                    "",
                ).strip()

                if not product["name"]:
                    raise ValueError

                prices = {}

                for size in ("50", "80", "100"):
                    price = int(
                        request.form.get(f"price_{size}", "0")
                    )

                    if price < 0:
                        raise ValueError

                    prices[size] = price

                product["prices"] = prices

                photo = request.files.get("image")

                if photo and photo.filename:
                    image_path = save_uploaded_image(photo)

                    if not image_path:
                        flash(
                            "تصویر JPG، PNG یا WEBP فارمیٹ میں ہونی چاہیے۔"
                        )
                        return redirect(url_for("admin"))

                    product["image"] = image_path

                write_json(PRODUCTS_FILE, products)
                flash("پرفیوم کی معلومات محفوظ ہو گئیں۔")

            except (TypeError, ValueError, StopIteration):
                flash("پرفیوم کی معلومات درست نہیں ہیں۔")

        # Update order status
        elif action == "update_order":
            order_id = request.form.get("order_id", "")
            status = request.form.get("status", "")

            allowed_statuses = {
                "نیا آرڈر",
                "ادائیگی کی جانچ",
                "تصدیق شدہ",
                "بھیج دیا گیا",
                "مکمل",
                "منسوخ",
            }

            if status not in allowed_statuses:
                flash("آرڈر کی حالت درست نہیں ہے۔")
                return redirect(url_for("admin"))

            for item in orders:
                if item.get("id") == order_id:
                    item["status"] = status
                    break

            write_json(ORDERS_FILE, orders)
            flash("آرڈر کی حالت اپ ڈیٹ ہو گئی۔")

        # Change admin password
        elif action == "change_password":
            old_password = request.form.get("old_password", "")
            new_password = request.form.get("new_password", "")

            admin_data = read_json(ADMIN_FILE, DEFAULT_ADMIN)

            current_password = str(
                admin_data.get("password", "")
            )

            if (
                secrets.compare_digest(
                    old_password,
                    current_password,
                )
                and len(new_password) >= 12
            ):
                admin_data["Akhan12345"] = new_password
                write_json(ADMIN_FILE, admin_data)
                flash("پاس ورڈ تبدیل ہو گیا۔")

            else:
                flash(
                    "پرانا پاس ورڈ درست ہونا چاہیے اور نیا پاس ورڈ کم از کم 12 حروف کا ہو۔"
                )

        else:
            flash("درخواست درست نہیں ہے۔")

        return redirect(url_for("admin"))

    return render_template(
        "admin.html",
        products=products,
        settings=settings,
        orders=orders,
    )


# ==================================================
# FILE TOO LARGE
# ==================================================

@app.errorhandler(413)
def file_too_large(error):
    flash("اپ لوڈ کی گئی فائل بہت بڑی ہے۔ زیادہ سے زیادہ سائز 5 MB ہے۔")
    return redirect(url_for("index"))


# ==================================================
# START APPLICATION
# ==================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
    )
```
            
