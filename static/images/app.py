import os, sqlite3, secrets, re
from pathlib import Path
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import quote
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import check_password_hash, generate_password_hash

BASE = Path(__file__).resolve().parent
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'local-development-only-change-me')
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.environ.get('HTTPS_ONLY') == '1', MAX_CONTENT_LENGTH=2*1024*1024)
DB = Path(os.environ.get('DATABASE_PATH', str(BASE / 'store.sqlite3')))
SHOP = {'name':'SWAT PERFUMES', 'brand':'RAVA PARFUME', 'email':'salam26090@gmail.com', 'whatsapp':'923454828100', 'currency':'PKR'}
REGIONS = ['سوات','پشاور','مردان','ملاکنڈ ڈویژن','دیر','بٹ خیلہ','دیگر خیبر پختونخوا']
SEED = [
 ('RAVA III Black Gold','RAVA','RAVA III','rava-iii.jpg','Bold, refined and unforgettable. عود اور عنبر کا شاہانہ انداز۔',8500),
 ('RAVA Dahab','RAVA','Dahab','rava-dahab.jpg','سنہری خوشبو، خاص لمحات کے لیے۔',9800),
 ('RAVA Guidance','RAVA','Guidance','rava-guidance.jpg','پھولوں کی نرم اور دلکش خوشبو۔',8000),
 ('ZAMEL Black Gold','ZAMEL','Zamel','zamel.jpg','بلیک اینڈ گولڈ ڈیزائن۔ تصویر تصوراتی نمونہ ہے۔',6500),
]
SIZES = (10,20,50,100)

def conn():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def init_db():
    with conn() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT NOT NULL, brand TEXT NOT NULL, collection TEXT NOT NULL, image TEXT NOT NULL, description TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS prices(product_id INTEGER NOT NULL, size INTEGER NOT NULL, amount INTEGER NOT NULL CHECK(amount>=0), PRIMARY KEY(product_id,size), FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, created TEXT NOT NULL, customer TEXT NOT NULL, phone TEXT NOT NULL, region TEXT NOT NULL, address TEXT NOT NULL, total INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending');
        CREATE TABLE IF NOT EXISTS order_items(order_id INTEGER NOT NULL, product_name TEXT NOT NULL, size INTEGER NOT NULL, qty INTEGER NOT NULL, unit_price INTEGER NOT NULL, FOREIGN KEY(order_id) REFERENCES orders(id));''')
        if c.execute('SELECT COUNT(*) FROM products').fetchone()[0] == 0:
            for name,brand,collection,image,description,base in SEED:
                cur=c.execute('INSERT INTO products(name,brand,collection,image,description) VALUES(?,?,?,?,?)',(name,brand,collection,image,description))
                for size, ratio in [(10,.15),(20,.27),(50,.56),(100,1)]:
                    c.execute('INSERT INTO prices VALUES(?,?,?)',(cur.lastrowid,size,round(base*ratio/50)*50))

def csrf():
    if 'csrf' not in session: session['csrf']=secrets.token_urlsafe(32)
    return session['csrf']
app.jinja_env.globals['csrf_token']=csrf

@app.before_request
def security():
    if request.method=='POST' and not secrets.compare_digest(request.form.get('csrf_token',''), csrf()): abort(400, 'Invalid form token')

@app.context_processor
def globals_(): return {'shop':SHOP, 'regions':REGIONS}

def admin_only(f):
    @wraps(f)
    def wrapped(*a,**k):
        if not session.get('admin'): return redirect(url_for('admin_login'))
        return f(*a,**k)
    return wrapped

@app.route('/')
def home():
    brand=request.args.get('brand','all')
    with conn() as c:
        products=c.execute('SELECT * FROM products WHERE active=1'+(' AND brand=?' if brand in ('RAVA','ZAMEL') else '')+' ORDER BY id', (brand,) if brand in ('RAVA','ZAMEL') else ()).fetchall()
        prices={p['id']:{r['size']:r['amount'] for r in c.execute('SELECT size,amount FROM prices WHERE product_id=? ORDER BY size',(p['id'],))} for p in products}
    return render_template('index.html',products=products,prices=prices,brand=brand)

@app.post('/checkout')
def checkout():
    try:
        pid=int(request.form.get('product_id','')); size=int(request.form.get('size','')); qty=int(request.form.get('qty','1'))
    except ValueError: abort(400)
    if size not in SIZES or not 1<=qty<=20: abort(400)
    name=request.form.get('customer','').strip()[:100]
    phone=request.form.get('phone','').strip()[:30]
    address=request.form.get('address','').strip()[:350]
    region=request.form.get('region','').strip()
    if not (2<=len(name)<=100 and re.fullmatch(r'[+0-9 ()-]{7,30}',phone) and len(address)>=8 and region in REGIONS):
        flash('براہ کرم نام، فون، علاقہ اور مکمل پتہ درست درج کریں۔'); return redirect(url_for('home'))
    with conn() as c:
        row=c.execute('SELECT p.name,pr.amount FROM products p JOIN prices pr ON pr.product_id=p.id WHERE p.id=? AND p.active=1 AND pr.size=?',(pid,size)).fetchone()
        if not row: abort(400)
        total=row['amount']*qty
        code='RV-'+datetime.now(timezone.utc).strftime('%y%m%d')+'-'+secrets.token_hex(3).upper()
        cur=c.execute('INSERT INTO orders(code,created,customer,phone,region,address,total) VALUES(?,?,?,?,?,?,?)',(code,datetime.now(timezone.utc).isoformat(),name,phone,region,address,total))
        c.execute('INSERT INTO order_items VALUES(?,?,?,?,?)',(cur.lastrowid,row['name'],size,qty,row['amount']))
    message=(f'🛍️ SWAT PERFUMES | New Order\nOrder: {code}\nProduct: {row["name"]}\nSize: {size}ml\nQty: {qty}\nUnit price: PKR {row["amount"]:,}\nSubtotal: PKR {total:,}\nDelivery: To be confirmed\nCustomer: {name}\nPhone: {phone}\nRegion: {region}\nAddress: {address}')
    whatsapp=f'https://wa.me/{SHOP["whatsapp"]}?text={quote(message)}'
    return render_template('success.html',code=code,product=row['name'],size=size,qty=qty,total=total,whatsapp=whatsapp)

@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        configured=os.environ.get('ADMIN_PASSWORD_HASH','')
        if configured and check_password_hash(configured,request.form.get('password','')):
            session.clear(); session['admin']=True; csrf(); return redirect(url_for('admin'))
        flash('غلط پاس ورڈ یا ایڈمن پاس ورڈ سیٹ نہیں ہے۔')
    return render_template('login.html')

@app.post('/admin/logout')
@admin_only
def admin_logout(): session.clear(); return redirect(url_for('home'))

@app.route('/admin')
@admin_only
def admin():
    with conn() as c:
        products=c.execute('SELECT * FROM products ORDER BY id').fetchall()
        prices={p['id']:{r['size']:r['amount'] for r in c.execute('SELECT size,amount FROM prices WHERE product_id=?',(p['id'],))} for p in products}
        orders=c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 100').fetchall()
    return render_template('admin.html',products=products,prices=prices,orders=orders)

@app.post('/admin/product/<int:pid>')
@admin_only
def edit_product(pid):
    name=request.form.get('name','').strip()[:100]
    description=request.form.get('description','').strip()[:500]
    brand=request.form.get('brand','').strip()[:40]
    collection=request.form.get('collection','').strip()[:60]
    if not all([name,description,brand,collection]): abort(400)
    try: prices={s:int(request.form[f'price_{s}']) for s in SIZES}
    except (ValueError,KeyError): abort(400)
    if any(not 0<=v<=10000000 for v in prices.values()): abort(400)
    with conn() as c:
        c.execute('UPDATE products SET name=?,description=?,brand=?,collection=?,active=? WHERE id=?',(name,description,brand,collection,1 if request.form.get('active')=='on' else 0,pid))
        for size,amount in prices.items(): c.execute('INSERT INTO prices(product_id,size,amount) VALUES(?,?,?) ON CONFLICT(product_id,size) DO UPDATE SET amount=excluded.amount',(pid,size,amount))
    flash('پروڈکٹ محفوظ ہوگیا۔'); return redirect(url_for('admin'))

@app.post('/admin/order/<int:oid>')
@admin_only
def edit_order(oid):
    status=request.form.get('status')
    if status not in ('pending','confirmed','shipped','completed','cancelled'): abort(400)
    with conn() as c: c.execute('UPDATE orders SET status=? WHERE id=?',(status,oid))
    return redirect(url_for('admin'))

init_db()
if __name__=='__main__': app.run(debug=True,port=5000)
