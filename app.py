import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "tasknest_secure_super_secret_key_2026"
DB_NAME = "tasknest.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('customer', 'provider')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            service_title TEXT NOT NULL,
            specialist_name TEXT,
            service_type TEXT NOT NULL,
            date_time TEXT NOT NULL,
            address TEXT NOT NULL,
            notes TEXT,
            total_price INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT DEFAULT 'Pending',
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

# Service Catalog with Individual Verified Specialists
SERVICES = [
    {
        "id": "doc",
        "title": "Doctor Consultation",
        "cat": "Health",
        "icon": "user-doctor",
        "desc": "General physicians, pediatricians, and certified medical officers.",
        "specialists": [
            {"name": "Dr. Sameer Kulkarni", "exp": "12 yrs exp", "qual": "MBBS, MD (General Medicine)", "rating": "4.9", "fee": 599},
            {"name": "Dr. Ananya Sharma", "exp": "8 yrs exp", "qual": "MBBS, DNB (Family Medicine)", "rating": "4.8", "fee": 499},
            {"name": "Dr. Rajesh Varma", "exp": "15 yrs exp", "qual": "MD (Internal Medicine)", "rating": "4.95", "fee": 699}
        ]
    },
    {
        "id": "phy",
        "title": "Physiotherapist",
        "cat": "Health",
        "icon": "spa",
        "desc": "Post-injury rehab, muscle stiffness, and joint mobility.",
        "specialists": [
            {"name": "Dr. Pooja Deshmukh (PT)", "exp": "7 yrs exp", "qual": "BPT, MPT (Ortho)", "rating": "4.8", "fee": 699},
            {"name": "Dr. Rohit Nair (PT)", "exp": "10 yrs exp", "qual": "MPT (Sports Rehab)", "rating": "4.9", "fee": 799}
        ]
    },
    {
        "id": "mas",
        "title": "Massage Therapist",
        "cat": "Wellness",
        "icon": "hands",
        "desc": "Deep tissue, stress relief, and Ayurvedic body therapy.",
        "specialists": [
            {"name": "Mahesh Jadhav", "exp": "9 yrs exp", "qual": "Certified Ayurvedic Practitioner", "rating": "4.9", "fee": 899},
            {"name": "Sunita Patil", "exp": "6 yrs exp", "qual": "Swedish & Deep Tissue Specialist", "rating": "4.7", "fee": 799}
        ]
    },
    {
        "id": "fit",
        "title": "Yoga & Fitness Coach",
        "cat": "Wellness",
        "icon": "dumbbell",
        "desc": "Personal 1-on-1 fitness and mobility workout sessions.",
        "specialists": [
            {"name": "Karan Singhania", "exp": "6 yrs exp", "qual": "Certified ACE Personal Trainer", "rating": "4.8", "fee": 549},
            {"name": "Priyanka Joshi", "exp": "8 yrs exp", "qual": "Ashtanga & Hatha Yoga Master", "rating": "4.9", "fee": 599}
        ]
    },
    {
        "id": "plm",
        "title": "Plumbing Expert",
        "cat": "Repairs",
        "icon": "faucet",
        "desc": "Leak repair, pipe blockage, drainage, and bathroom fittings.",
        "specialists": [
            {"name": "Ramesh Shinde", "exp": "11 yrs exp", "qual": "Master Plumber (Certified)", "rating": "4.9", "fee": 299},
            {"name": "Vijay Gaikwad", "exp": "5 yrs exp", "qual": "Sanitary & Drainage Tech", "rating": "4.7", "fee": 249}
        ]
    },
    {
        "id": "elc",
        "title": "Master Electrician",
        "cat": "Repairs",
        "icon": "bolt",
        "desc": "Wiring, appliance setups, and short circuit resolution.",
        "specialists": [
            {"name": "Santosh More", "exp": "14 yrs exp", "qual": "Licensed High-Voltage Tech", "rating": "4.9", "fee": 299},
            {"name": "Imran Khan", "exp": "6 yrs exp", "qual": "Home Wiring & Breaker Tech", "rating": "4.8", "fee": 249}
        ]
    },
    {
        "id": "crp",
        "title": "Woodwork & Carpenter",
        "cat": "Repairs",
        "icon": "hammer",
        "desc": "Furniture assembly, door hinges, locks, and custom builds.",
        "specialists": [
            {"name": "Dinesh Sharma", "exp": "12 yrs exp", "qual": "Master Wood Artisan", "rating": "4.9", "fee": 349},
            {"name": "Bablu Ansari", "exp": "7 yrs exp", "qual": "Modular Fittings & Repair", "rating": "4.7", "fee": 299}
        ]
    },
    {
        "id": "mch",
        "title": "Doorstep Mechanic",
        "cat": "Automobile",
        "icon": "wrench",
        "desc": "Car and bike maintenance, battery jumpstarts, and oil check.",
        "specialists": [
            {"name": "Ganesh Kadam", "exp": "10 yrs exp", "qual": "Auto Diagnostics Specialist", "rating": "4.9", "fee": 449},
            {"name": "Akash Solanki", "exp": "8 yrs exp", "qual": "2/4-Wheeler Master Tech", "rating": "4.8", "fee": 399}
        ]
    }
]

@app.route("/")
def index():
    if "user_id" in session:
        if session.get("role") == "provider":
            return redirect(url_for("provider_dashboard"))
        return redirect(url_for("services_catalog"))
    return render_template("landing.html")

@app.route("/services")
def services_catalog():
    if "user_id" not in session:
        flash("Please sign in or register to view and book services.", "warning")
        return redirect(url_for("login"))

    selected_cat = request.args.get("category", "All")
    if selected_cat == "All":
        filtered = SERVICES
    else:
        filtered = [s for s in SERVICES if s["cat"] == selected_cat]
    
    categories = ["All", "Health", "Wellness", "Repairs", "Automobile"]
    return render_template("index.html", services=filtered, categories=categories, active_cat=selected_cat)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")
        role = request.form.get("role")

        hashed_pw = generate_password_hash(password)
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", 
                        (name, email, hashed_pw, role))
            conn.commit()
            flash("Account registered successfully! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered. Try logging in.", "danger")
        finally:
            conn.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["email"] = user["email"]
            session["role"] = user["role"]

            if user["role"] == "provider":
                return redirect(url_for("provider_dashboard"))
            return redirect(url_for("services_catalog"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/book", methods=["POST"])
def book_service():
    if "user_id" not in session:
        flash("You must be logged in to schedule a booking.", "warning")
        return redirect(url_for("login"))

    service_title = request.form.get("service")
    specialist_name = request.form.get("specialist_name", "Any Available Specialist")
    price = int(request.form.get("price", 399))

    session["checkout_data"] = {
        "name": request.form.get("name"),
        "phone": request.form.get("phone"),
        "service": service_title,
        "specialist": specialist_name,
        "service_type": request.form.get("service_type"),
        "datetime": request.form.get("datetime"),
        "address": request.form.get("address"),
        "notes": request.form.get("notes", ""),
        "price": price
    }
    return redirect(url_for("checkout"))

@app.route("/checkout")
def checkout():
    order = session.get("checkout_data")
    if not order:
        return redirect(url_for("services_catalog"))
    return render_template("checkout.html", order=order)

@app.route("/process-payment", methods=["POST"])
def process_payment():
    order = session.get("checkout_data")
    if not order:
        return redirect(url_for("services_catalog"))

    pay_method = request.form.get("payment_method")
    pay_status = "Paid" if pay_method in ["UPI", "CARD"] else "Pending (Pay on Visit)"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bookings (customer_id, customer_name, phone, service_title, specialist_name, service_type, date_time, address, notes, total_price, payment_method, payment_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        order["name"],
        order["phone"],
        order["service"],
        order["specialist"],
        order["service_type"],
        order["datetime"],
        order["address"],
        order["notes"],
        order["price"],
        pay_method,
        pay_status
    ))
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()

    session.pop("checkout_data", None)
    return render_template("booking_success.html", 
                           booking_id=booking_id, 
                           name=order["name"], 
                           service=order["service"] + f" ({order['specialist']})", 
                           price=order["price"], 
                           time=order["datetime"],
                           pay_method=pay_method,
                           pay_status=pay_status)

@app.route("/provider")
def provider_dashboard():
    if "user_id" not in session:
        flash("Please log in to access the provider portal.", "warning")
        return redirect(url_for("login"))
    
    if session.get("role") != "provider":
        flash("Access Denied: Only registered service providers can view this page.", "danger")
        return redirect(url_for("services_catalog"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bookings ORDER BY id DESC")
    bookings = cur.fetchall()
    
    total_rev = sum(b["total_price"] for b in bookings if b["status"] == "Completed")
    pending_count = sum(1 for b in bookings if b["status"] == "Pending")
    conn.close()

    return render_template("provider.html", bookings=bookings, revenue=total_rev, pending=pending_count)

@app.route("/update-status/<int:booking_id>/<string:new_status>")
def update_status(booking_id, new_status):
    if session.get("role") != "provider":
        flash("Unauthorized action.", "danger")
        return redirect(url_for("index"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE bookings SET status = ? WHERE id = ?", (new_status, booking_id))
    conn.commit()
    conn.close()
    return redirect(url_for("provider_dashboard"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)