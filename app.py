import os
import json
import secrets
import threading
from datetime import datetime, timedelta
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
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ==================================================
# APP CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)

# --------------------------------------------------
# SECRET_KEY — پروڈکشن میں لازمی environment variable
# --------------------------------------------------
_secret_key = os.environ.get("SECRET_KEY")

if not _secret_key:
    # fallback: فائل میں محفوظ کریں تاکہ restart پر sessions نہ ٹوٹیں
    _key_file = DATA_DIR / ".secret_key"
    if _key_file.exists():
        _secret_key = _key_file.read_text().strip()
    else:
        _secret_key = secrets.token_hex(32)
        _key_file.write_text(_secret_key)
        try:
            _key_file.chmod(0o600)
        except OSError:
            pass

app.secret_key = _secret_key

# --------------------------------------------------
# PRODUCTION SETTINGS
# --------------------------------------------------
app.config.update(
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,   # 5 MB
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("HTTPS", "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    PREFERRED_URL_SCHEME="https" if os.environ.get("HTTPS") == "1" else "http",
)

PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
ADMIN_FILE = DATA_DIR / "admin.json"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

_file_lock = threading.Lock()


# ==================================================
# CONSTANTS
# ==================================================

STATUS_NEW = "نیا آرڈر"
STATUS_CHECKING = "ادائیگی کی جانچ"
STATUS_CONFIRMED = "تصدیق شدہ"
STATUS_SHIPPED = "بھیج دیا گیا"
STATUS_DONE = "مکمل"
STATUS_CANCELLED = "منسوخ"

ALLOWED_STATUSES = {
    STATUS_NEW,
    STATUS_CHECKING,
    STATUS_CONFIRMED,
    STATUS_SHIPPED,
    STATUS_DONE,
    STATUS_CANCELLED,
}

DELIVERY_AREAS = ("kabal", "nearby", "city", "far", "very_far")


# ==================================================
# ⚠️  ADMIN CREDENTIALS — یہیں تبدیل کریں
# ==================================================
# جب آپ پاس ورڈ بدلنا چاہیں، صرف نیچے "12345" کی جگہ نیا لکھ دیں
# اور app کو دوبارہ start کریں — یا admin panel سے بھی بدل سکتے ہیں۔
# --------------------------------------------------

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "12345"


# ==================================================
# DEFAULT DATA
# ==================================================

DEFAULT_PRODUCTS = [
    {
        "id": 1,
        "name": "Rava Oud",
        "description": "ایک نفیس اور دیرپا عود کی خوشبو",
        "image": "",
        "prices": {"50": 1800, "80": 2500, "100": 3000},
    },
    {
        "id": 2,
        "name": "Rava Rose",
        "description": "گلاب کی نرم اور دلکش خوشبو",
        "image": "",
        "prices": {"50": 1600, "80": 2200, "100": 2700},
    },
    {
        "id": 3,
        "name": "Rava Blue",
        "description": "تازہ اور جدید خوشبو",
        "image": "",
        "prices": {"50": 1500, "80": 2100, "100": 2600},
    },
    {
        "id": 4,
        "name": "Rava Amber",
        "description": "امبر کی گرم اور پُرکشش خوشبو",
        "image": "",
        "prices": {"50": 1700, "80": 2350, "100": 2850},
    },
]

DEFAULT_SETTINGS = {
    "whatsapp": "923454828100",
    "easypaisa": "03454828100",
    "easypaisa_name": "Rava Perfumes",
    "delivery_kabal": 0,
    "delivery_nearby": 200,
    "delivery_city": 250,
    "delivery_far": 500,
    "delivery_very_far": 600,
    "shop_name": "Rava Perfumes",
}


# ==================================================
# HELPERS
# ==================================================

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with _file_lock:
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        temp_path.replace(path)


def read_json(path: Path, default):
    if not path.exists():
        write_json(path, default)
        return default

    try:
        with _file_lock:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
    except (json.JSONDecodeError, OSError):
        app.logger.exception("JSON file could not be read: %s", path)
        return default


def safe_int(value, default=0, minimum=0):
    try:
        return max(minimum, int(value))
    except (TypeError, ValueError):
        return default


def get_products():
    products = read_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)
    return products if isinstance(products, list) else DEFAULT_PRODUCTS


def get_settings():
    settings = read_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    if not isinstance(settings, dict):
        settings = DEFAULT_SETTINGS.copy()
    for key, value in DEFAULT_SETTINGS.items():
        settings.setdefault(key, value)
    return settings


def get_orders():
    orders = read_json(ORDERS_FILE, [])
    return orders if isinstance(orders, list) else []


def get_admin():
    """
    اگر admin.json موجود نہیں تو DEFAULT_ADMIN_USERNAME اور
    DEFAULT_ADMIN_PASSWORD سے بن جائے گا۔
    """
    if not ADMIN_FILE.exists():
        admin = {
            "username": DEFAULT_ADMIN_USERNAME,
            "password_hash": generate_password_hash(DEFAULT_ADMIN_PASSWORD),
        }
        write_json(ADMIN_FILE, admin)
        return admin

    admin = read_json(ADMIN_FILE, None)

    # پرانا format (plaintext password) → نئے hash format پر migrate
    if not isinstance(admin, dict) or "password_hash" not in admin:
        old_user = (admin or {}).get("username", DEFAULT_ADMIN_USERNAME)
        old_pass = (admin or {}).get("password", DEFAULT_ADMIN_PASSWORD)
        new_admin = {
            "username": old_user,
            "password_hash": generate_password_hash(old_pass),
        }
        write_json(ADMIN_FILE, new_admin)
        return new_admin

    return admin


def is_admin():
    return session.get("is_admin") is True


def save_uploaded_image(file):
    if not file or not file.filename:
        return None

    safe_name = secure_filename(file.filename)
    extension = Path(safe_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return None

    if PIL_AVAILABLE:
        try:
            file.stream.seek(0)
            img = Image.open(file.stream)
            img.verify()
            file.stream.seek(0)

            img = Image.open(file.stream)
            if img.format.lower() not in ("jpeg", "png", "webp"):
                return None
            file.stream.seek(0)
        except Exception:
            app.logger.warning("Invalid image rejected")
            return None

    image_name = secrets.token_hex(12) + extension
    file.save(UPLOAD_DIR / image_name)
    return "uploads/" + image_name


def normalize_image_path(image):
    if not image:
        return ""
    name = Path(image).name
    return f"uploads/{name}" if name else ""


# ==================================================
# CONTEXT PROCESSOR
# ==================================================

@app.context_processor
def inject_globals():
    settings = get_settings()
    return {
        "shop_name": settings.get("shop_name", "Rava Perfumes"),
        "whatsapp_number": settings.get("whatsapp", ""),
    }


# ==================================================
# HOME
# ==================================================

@app.route("/")
def index():
    products = get_products()
    settings = get_settings()

    whatsapp = settings.get("whatsapp", "").lstrip("+").replace(" ", "")
    shop = {
        "whatsapp": whatsapp,
        "whatsapp_url": f"https://wa.me/{whatsapp}" if whatsapp else "",
    }

    return render_template(
        "index.html",
        products=products,
        settings=settings,
        shop=shop,
    )


# ==================================================
# ORDER
# ==================================================

@app.route("/order/<int:product_id>", methods=["GET", "POST"])
def order(product_id):
    products = get_products()
    product = next(
        (item for item in products if int(item.get("id", 0)) == product_id),
        None,
    )

    if not product:
        flash("یہ پرفیوم دستیاب نہیں ہے۔", "error")
        return redirect(url_for("index"))

    settings = get_settings()

    if request.method == "GET":
        return render_template(
            "order.html",
            product=product,
            settings=settings,
            delivery_areas=DELIVERY_AREAS,
        )

    # ------- Validate -------
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()
    size = request.form.get("size", "").strip()
    payment = request.form.get("payment", "cod").strip()
    quantity_text = request.form.get("quantity", "1").strip()
    area = request.form.get("area", "city").strip()

    if not name or len(name) < 2:
        flash("براہِ کرم درست نام درج کریں۔", "error")
        return redirect(url_for("order", product_id=product_id))

    phone_digits = "".join(c for c in phone if c.isdigit())
    if len(phone_digits) < 9:
        flash("براہِ کرم درست فون نمبر درج کریں۔", "error")
        return redirect(url_for("order", product_id=product_id))

    if not address or len(address) < 5:
        flash("براہِ کرم مکمل پتہ درج کریں۔", "error")
        return redirect(url_for("order", product_id=product_id))

    quantity = safe_int(quantity_text, default=0)
    if quantity < 1 or quantity > 20:
        flash("تعداد 1 سے 20 کے درمیان درج کریں۔", "error")
        return redirect(url_for("order", product_id=product_id))

    prices = product.get("prices", {})
    if size not in prices:
        flash("براہِ کرم درست سائز منتخب کریں۔", "error")
        return redirect(url_for("order", product_id=product_id))

    unit_price = safe_int(prices.get(size), default=-1)
    if unit_price < 0:
        flash("اس سائز کی قیمت درست نہیں ہے۔", "error")
        return redirect(url_for("order", product_id=product_id))

    delivery_map = {
        "kabal": safe_int(settings.get("delivery_kabal")),
        "nearby": safe_int(settings.get("delivery_nearby")),
        "city": safe_int(settings.get("delivery_city")),
        "far": safe_int(settings.get("delivery_far")),
        "very_far": safe_int(settings.get("delivery_very_far")),
    }

    if area not in delivery_map:
        flash("براہِ کرم درست ڈیلیوری علاقہ منتخب کریں۔", "error")
        return redirect(url_for("order", product_id=product_id))

    delivery = delivery_map[area]

    if payment not in ("cod", "easypaisa"):
        flash("براہِ کرم ادائیگی کا درست طریقہ منتخب کریں۔", "error")
        return redirect(url_for("order", product_id=product_id))

    if area != "kabal" and payment == "cod":
        flash("کابل سے باہر فی الحال Easypaisa منتخب کریں۔", "error")
        return redirect(url_for("order", product_id=product_id))

    receipt_name = ""
    if payment == "easypaisa":
        receipt = request.files.get("receipt")
        if not receipt or not receipt.filename:
            flash("Easypaisa ادائیگی کے لیے رسید اپ لوڈ کریں۔", "error")
            return redirect(url_for("order", product_id=product_id))

        uploaded_path = save_uploaded_image(receipt)
        if not uploaded_path:
            flash("رسید JPG، PNG یا WEBP میں ہونی چاہیے۔", "error")
            return redirect(url_for("order", product_id=product_id))

        receipt_name = normalize_image_path(uploaded_path)

    order_record = {
        "id": "ORD-" + secrets.token_hex(4).upper(),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "name": name,
        "phone": phone_digits,
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
        "status": STATUS_NEW,
    }

    orders = get_orders()
    orders.insert(0, order_record)
    write_json(ORDERS_FILE, orders)

    flash("آپ کا آرڈر کامیابی سے موصول ہو گیا ہے۔", "success")

    return render_template(
        "order.html",
        product=product,
        settings=get_settings(),
        delivery_areas=DELIVERY_AREAS,
        order=order_record,
        order_success=True,
    )


# ==================================================
# LOGIN (rate-limited)
# ==================================================

_login_attempts = {}   # {ip: [timestamps]}
LOGIN_WINDOW = 300      # 5 منٹ
LOGIN_MAX_ATTEMPTS = 8


def _rate_limit_ok(ip):
    now = datetime.utcnow().timestamp()
    attempts = [t for t in _login_attempts.get(ip, []) if now - t < LOGIN_WINDOW]
    _login_attempts[ip] = attempts
    return len(attempts) < LOGIN_MAX_ATTEMPTS


def _record_attempt(ip):
    _login_attempts.setdefault(ip, []).append(datetime.utcnow().timestamp())


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if is_admin():
        return redirect(url_for("admin"))

    if request.method == "POST":
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        ip = ip.split(",")[0].strip()

        if not _rate_limit_ok(ip):
            flash("بہت زیادہ کوششیں۔ کچھ منٹ بعد دوبارہ کوشش کریں۔", "error")
            return render_template("login.html"), 429

        admin_data = get_admin()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        stored_user = str(admin_data.get("username", ""))
        stored_hash = str(admin_data.get("password_hash", ""))

        user_ok = secrets.compare_digest(username, stored_user)
        pass_ok = check_password_hash(stored_hash, password) if stored_hash else False

        if user_ok and pass_ok:
            session.clear()
            session["is_admin"] = True
            session.permanent = True
            _login_attempts.pop(ip, None)
            return redirect(url_for("admin"))

        _record_attempt(ip)
        flash("یوزر نیم یا پاس ورڈ غلط ہے۔", "error")

    return render_template("login.html")


# ==================================================
# LOGOUT
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

        # ---------- Settings ----------
        if action == "save_settings":
            new_settings = settings.copy()
            new_settings["whatsapp"] = request.form.get(
                "whatsapp", settings["whatsapp"]
            ).strip()
            new_settings["easypaisa"] = request.form.get(
                "easypaisa", settings["easypaisa"]
            ).strip()
            new_settings["easypaisa_name"] = request.form.get(
                "easypaisa_name", settings.get("easypaisa_name", "")
            ).strip()
            new_settings["shop_name"] = request.form.get(
                "shop_name", settings.get("shop_name", "")
            ).strip()

            for key in (
                "delivery_kabal",
                "delivery_nearby",
                "delivery_city",
                "delivery_far",
                "delivery_very_far",
            ):
                new_settings[key] = safe_int(request.form.get(key, "0"))

            write_json(SETTINGS_FILE, new_settings)
            flash("سیٹنگز محفوظ ہو گئیں۔", "success")

        # ---------- Product ----------
        elif action == "save_product":
            try:
                product_id = int(request.form.get("product_id", ""))
                product = next(
                    item for item in products if int(item["id"]) == product_id
                )

                new_name = request.form.get("name", "").strip()
                if not new_name:
                    raise ValueError("empty name")

                product["name"] = new_name
                product["description"] = request.form.get(
                    "description", ""
                ).strip()

                prices = {}
                for size in ("50", "80", "100"):
                    prices[size] = safe_int(request.form.get(f"price_{size}", "0"))
                product["prices"] = prices

                photo = request.files.get("image")
                if photo and photo.filename:
                    image_path = save_uploaded_image(photo)
                    if not image_path:
                        flash(
                            "تصویر JPG، PNG یا WEBP فارمیٹ میں ہونی چاہیے۔",
                            "error",
                        )
                        return redirect(url_for("admin"))
                    product["image"] = normalize_image_path(image_path)

                write_json(PRODUCTS_FILE, products)
                flash("پرفیوم کی معلومات محفوظ ہو گئیں۔", "success")

            except (TypeError, ValueError, StopIteration):
                flash("پرفیوم کی معلومات درست نہیں ہیں۔", "error")

        # ---------- Order status ----------
        elif action == "update_order":
            order_id = request.form.get("order_id", "")
            status = request.form.get("status", "")

            if status not in ALLOWED_STATUSES:
                flash("آرڈر کی حالت درست نہیں ہے۔", "error")
                return redirect(url_for("admin"))

            updated = False
            for item in orders:
                if item.get("id") == order_id:
                    item["status"] = status
                    updated = True
                    break

            if updated:
                write_json(ORDERS_FILE, orders)
                flash("آرڈر کی حالت اپ ڈیٹ ہو گئی۔", "success")
            else:
                flash("آرڈر نہیں ملا۔", "error")

        # ---------- Delete order ----------
        elif action == "delete_order":
            order_id = request.form.get("order_id", "")
            new_orders = [o for o in orders if o.get("id") != order_id]
            if len(new_orders) != len(orders):
                write_json(ORDERS_FILE, new_orders)
                flash("آرڈر حذف ہو گیا۔", "success")
            else:
                flash("آرڈر نہیں ملا۔", "error")

        # ---------- Change password ----------
        elif action == "change_password":
            old_password = request.form.get("old_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            admin_data = get_admin()

            if not check_password_hash(
                admin_data.get("password_hash", ""), old_password
            ):
                flash("پرانا پاس ورڈ غلط ہے۔", "error")
            elif new_password != confirm_password:
                flash("نیا پاس ورڈ اور تصدیقی پاس ورڈ مختلف ہیں۔", "error")
            elif len(new_password) < 5:
                flash("نیا پاس ورڈ کم از کم 5 حروف کا ہونا چاہیے۔", "error")
            elif new_password == old_password:
                flash("نیا پاس ورڈ پرانے سے مختلف ہونا چاہیے۔", "error")
            else:
                admin_data["password_hash"] = generate_password_hash(
                    new_password
                )
                write_json(ADMIN_FILE, admin_data)
                flash("پاس ورڈ کامیابی سے تبدیل ہو گیا۔", "success")

        else:
            flash("درخواست درست نہیں ہے۔", "error")

        return redirect(url_for("admin"))

    orders_sorted = sorted(
        orders,
        key=lambda o: o.get("created_at", ""),
        reverse=True,
    )

    return render_template(
        "admin.html",
        products=products,
        settings=settings,
        orders=orders_sorted,
        statuses=ALLOWED_STATUSES,
    )


# ==================================================
# ERROR HANDLERS
# ==================================================

@app.errorhandler(413)
def file_too_large(error):
    flash("اپ لوڈ کی گئی فائل بہت بڑی ہے۔ زیادہ سے زیادہ سائز 5 MB ہے۔", "error")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    app.logger.exception("Internal Server Error")
    return render_template("500.html"), 500


# ==================================================
# START
# ==================================================

if __name__ == "__main__":
    # پہلی بار admin.json بنائیں (اگر نہ ہو)
    get_admin()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
            
