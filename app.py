import os
import json
import secrets
from pathlib import Path
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from werkzeug.utils import secure_filename
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
ADMIN_FILE = DATA_DIR / "admin.json"
DEFAULT_PRODUCTS = [
    {
        "id": 1,
        "name": "Rava Oud",
        "description": "ایک نفیس اور دیرپا عود کی خوشبو",
        "image": "",
        "prices": {"50": 1800, "80": 2500, "100": 3000}
    },
    {
        "id": 2,
        "name": "Rava Rose",
        "description": "گلاب کی نرم اور دلکش خوشبو",
        "image": "",
        "prices": {"50": 1600, "80": 2200, "100": 2700}
    },
    {
        "id": 3,
        "name": "Rava Blue",
        "description": "تازہ اور جدید خوشبو",
        "image": "",
        "prices": {"50": 1500, "80": 2100, "100": 2600}
    },
    {
        "id": 4,
        "name": "Rava Amber",
        "description": "امبر کی گرم اور پُرکشش خوشبو",
        "image": "",
        "prices": {"50": 1700, "80": 2350, "100": 2850}
    }
]
DEFAULT_SETTINGS = {
    "whatsapp": "923454828100",
    "easypaisa": "03454828100",
    "delivery_kabal": 0,
    "delivery_nearby": 200,
    "delivery_city": 250,
    "delivery_far": 500,
    "delivery_very_far": 600
}
def read_json(path, default):
    if not path.exists():
        write_json(path, default)
        return default
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return default
def write_json(path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
def get_products():
    return read_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)
def get_settings():
    return read_json(SETTINGS_FILE, DEFAULT_SETTINGS)
def is_admin():
    return session.get("is_admin") is True
@app.route("/")
def index():
    products = get_products()
    settings = get_settings()
    return render_template(
        "index.html",
        products=products,
        settings=settings
    )
@app.route("/order/<int:product_id>", methods=["GET", "POST"])
def order(product_id):
    products = get_products()
    product = next(
        (p for p in products if int(p.get("id", 0)) == product_id),
        None
    )
    if not product:
        flash("یہ پرفیوم دستیاب نہیں ہے۔")
        return redirect(url_for("index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        size = request.form.get("size", "").strip()
        payment = request.form.get("payment", "cod").strip()
        quantity_text = request.form.get("quantity", "1").strip()
        if not name or not phone or not address:
            flash("براہِ کرم نام، فون نمبر اور مکمل پتہ درج کریں۔")
            return redirect(url_for("order", product_id=product_id))
        try:
            quantity = int(quantity_text)
            if quantity < 1 or quantity > 20:
                raise ValueError
        except ValueError:
            flash("تعداد 1 سے 20 کے درمیان درج کریں۔")
            return redirect(url_for("order", product_id=product_id))
        prices = product.get("prices", {})
        if size not in prices:
            flash("براہِ کرم درست سائز منتخب کریں۔")
            return redirect(url_for("order", product_id=product_id))
        try:
            unit_price = int(prices[size])
        except (TypeError, ValueError):
            flash("اس سائز کی قیمت درست نہیں ہے۔")
            return redirect(url_for("order", product_id=product_id))
        settings = get_settings()
        area = request.form.get("area", "city").strip()
        delivery_map = {
            "kabal": int(settings.get("delivery_kabal", 0)),
            "nearby": int(settings.get("delivery_nearby", 200)),
            "city": int(settings.get("delivery_city", 250)),
            "far": int(settings.get("delivery_far", 500)),
            "very_far": int(settings.get("delivery_very_far", 600))
        }
        delivery = delivery_map.get(area, delivery_map["city"])
        if payment not in ("cod", "easypaisa"):
            flash("براہِ کرم ادائیگی کا درست طریقہ منتخب کریں۔")
            return redirect(url_for("order", product_id=product_id))
        if area != "kabal" and payment == "cod":
            flash("کابل سے باہر فی الحال Easypaisa منتخب کریں۔")
            return redirect(url_for("order", product_id=product_id))
        receipt = request.files.get("receipt")
        receipt_name = ""
        if payment == "easypaisa":
            if not receipt or not receipt.filename:
                flash("Easypaisa ادائیگی کے لیے رسید کی تصویر اپ لوڈ کریں۔")
                return redirect(url_for("order", product_id=product_id))
            safe_name = secure_filename(receipt.filename)
            extension = Path(safe_name).suffix.lower()
            if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
                flash("رسید کے لیے JPG، PNG یا WEBP تصویر اپ لوڈ کریں۔")
                return redirect(url_for("order", product_id=product_id))
            receipt_name = secrets.token_hex(8) + extension
            receipt.save(UPLOAD_DIR / receipt_name)
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
            "status": "نیا آرڈر"
        }
        orders = read_json(ORDERS_FILE, [])
        orders.insert(0, order_record)
        write_json(ORDERS_FILE, orders)
    @app.route("/")
def index():
    products = read_json(PRODUCTS_FILE, [])
    settings = read_json(SETTINGS_FILE, {})
    return render_template(
        "index.html",
        products=products,
        settings=settings,
        shop={
            "whatsapp_url": "966551709172",
            "whatsapp": "+966 55 170 9172"
        }
    )
    
    @app.route("/")
def index():
    return render_template(
        "index.html",
        shop={
            "whatsapp_url": "966551709172",
            "whatsapp": "+966 55 170 9172"
      
        
        }
    )
    "ind  }html", product=p@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin = read_json(ADMIN_FILE, {
            "username": "salam",
            "password": "salam123!"
        })
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if (
            secrets.compare_digest(username, str(admin.get("username", "")))
            and secrets.compare_digest(password, str(admin.get("password", "")))
        ):
            session["is_admin"] = True
            return redirect(url_for("admin"))
        flash("یوزر نیم یا پاس ورڈ غلط ہے۔")
    return render_template("login.html")
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not is_admin():
        return redirect(url_for("admin_login"))
    products = get_products()
    settings = get_settings()
    orders = read_json(ORDERS_FILE, [])
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "save_settings":
            settings["whatsapp"] = request.form.get(
                "whatsapp", settings["whatsapp"]
            ).strip()
            settings["easypaisa"] = request.form.get(
                "easypaisa", settings["easypaisa"]
            ).strip()
            for key in (
                "delivery_kabal", "delivery_nearby", "delivery_city",
                "delivery_far", "delivery_very_far"
            ):
                try:
                    settings[key] = max(0, int(request.form.get(key, "0")))
                except ValueError:
                    flash("ڈیلیوری چارجز میں درست عدد درج کریں۔")
                    return redirect(url_for("admin"))
            write_json(SETTINGS_FILE, settings)
            flash("سیٹنگز محفوظ ہو گئیں۔")
        elif action == "save_product":
            try:
                product_id = int(request.form.get("product_id", ""))
                product = next(
                    p for p in products if int(p["id"]) == product_id
                )
                product["name"] = request.form.get("name", "").strip()
                product["description"] = request.form.get(
                    "description", ""
                ).strip()
                prices = {}
                for size in ("50", "80", "100"):
                    prices[size] = max(
                        0, int(request.form.get(f"price_{size}", "0"))
                    )
                product["prices"] = prices
                photo = request.files.get("image")
                if photo and photo.filename:
                    safe_name = secure_filename(photo.filename)
                    extension = Path(safe_name).suffix.lower()
                    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
                        flash("تصویر JPG، PNG یا WEBP فارمیٹ میں ہونی چاہیے۔")
                        return redirect(url_for("admin"))
                    image_name = secrets.token_hex(8) + extension
                    photo.save(UPLOAD_DIR / image_name)
                    product["image"] = "uploads/" + image_name
                write_json(PRODUCTS_FILE, products)
                flash("پرفیوم کی معلومات محفوظ ہو گئیں۔")
            except (ValueError, StopIteration):
                flash("پرفیوم کی معلومات درست نہیں ہیں۔")
        elif action == "update_order":
            order_id = request.form.get("order_id", "")
            status = request.form.get("status", "نیا آرڈر")
            allowed = {"نیا آرڈر", "ادائیگی کی جانچ", "تصدیق شدہ", "بھیج دیا گیا", "مکمل", "منسوخ"}
            for item in orders:
                if item.get("id") == order_id and status in allowed:
                    item["status"] = status
                    break
            write_json(ORDERS_FILE, orders)
            flash("آرڈر کی حالت اپ ڈیٹ ہو گئی۔")
        elif action == "change_password":
            old_password = request.form.get("old_password", "")
            new_password = request.form.get("new_password", "")
            admin_data = read_json(ADMIN_FILE, {
                "username": "admin",
                "password": "ChangeMe123!"
            })
            if (
                secrets.compare_digest(
                    old_password, str(admin_data.get("password", ""))
                )
                and len(new_password) >= 12
            ):
                admin_data["password"] = new_password
                write_json(ADMIN_FILE, admin_data)
                flash("پاس ورڈ تبدیل ہو گیا۔")
            else:
                flash("پرانا پاس ورڈ درست ہونا چاہیے اور نیا پاس ورڈ کم از کم 12 حروف کا ہو۔")
        return redirect(url_for("admin"))
    return render_template(
        "admin.html",
        products=products,
        settings=settings,
        orders=orders
    )
@app.errorhandler(413)
def file_too_large(error):
    flash("اپ لوڈ کی گئی فائل بہت بڑی ہے۔")
    return redirect(url_for("index"))
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
