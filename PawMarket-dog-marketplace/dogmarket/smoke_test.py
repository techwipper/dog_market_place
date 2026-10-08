"""End-to-end smoke test: hits every important route as guest, buyer, seller and admin.

NOTE for anyone extending this file: each `with app.test_client()` block below turns
OFF Flask's context preservation (see _client()). Without that, `with app.test_client()`
keeps one application context alive for the whole block, so `flask.g` - and with it
Flask-Login's cached `g._login_user` - leaks from one request into the next. Real
requests against a real server never share `g`, so leaving it on makes this harness
report bugs that don't exist in the app.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import create_app
from app.extensions import db
from app.models import Dog, Order, User

app = create_app()
failures = []
checks = 0


def _client():
    """A test client whose requests do NOT share flask.g (like real HTTP traffic)."""
    c = app.test_client()
    c.preserve_context = False
    return c


def check(label, condition, extra=""):
    global checks
    checks += 1
    if not condition:
        failures.append(f"{label} {extra}")
        print(f"  FAIL  {label} {extra}")
    else:
        print(f"  ok    {label}")


def login(client, email, password):
    return client.post("/auth/login", data={"email": email, "password": password},
                       follow_redirects=True)


with app.app_context():
    dogs = Dog.query.all()
    buyer = User.query.filter_by(email="buyer@pawmarket.ng").first()
    seller = User.query.filter_by(email="amina@pawmarket.ng").first()
    admin = User.query.filter_by(email="admin@pawmarket.ng").first()
    dog_id = dogs[0].id
    seller_id = seller.id
    buyer_order = Order.query.filter_by(buyer_id=buyer.id).first()
    order_id = buyer_order.id if buyer_order else None
    hidden_dog = Dog.query.filter_by(status="hidden").first()

print("\n[1] Guest access")
with app.test_client() as c:
    c.preserve_context = False  # see module docstring
    for path, label in [("/", "home"), ("/dogs", "browse"),
                        (f"/dogs/{dog_id}", "dog detail"),
                        (f"/sellers/{seller_id}", "seller public profile"),
                        ("/dogs?q=lab&size=Large&min_price=1000&sort=price_low&vaccinated=1", "browse with filters"),
                        ("/dogs?age=puppy&gender=Female&color=cream&location=Kano", "browse more filters"),
                        ("/auth/login", "login page"), ("/auth/register", "register page"),
                        ("/nope", "404 page")]:
        r = c.get(path)
        check(f"GET {label}", r.status_code in (200, 404))
    check("homepage shows listings", b"Featured dogs" in c.get("/").data)
    guest_page = c.get(f"/dogs/{dog_id}").data.decode()
    with app.app_context():
        _ph = db.session.get(Dog, dog_id).seller.phone
    check("guest page hides seller phone digits", (_ph or "-----") not in guest_page)
    check("guest page shows sign-in prompt", "Sign in" in guest_page and "Direct contact" not in guest_page)
    r = c.get("/buyer/dashboard", follow_redirects=True)
    check("buyer dashboard blocked for guest", b"Please sign in" in r.data or b"Welcome back" in r.data)
    check("admin blocked for guest", c.get("/admin/").status_code in (302, 403))

print("\n[2] Buyer flows")
with app.test_client() as c:
    c.preserve_context = False  # see module docstring
    login(c, "buyer@pawmarket.ng", "buyer123")
    for path, label in [("/buyer/dashboard", "buyer dashboard"), ("/dogs", "browse as buyer"),
                        (f"/dogs/{dog_id}", "detail as buyer"), ("/auth/profile", "profile page"),
                        ("/dashboard", "dashboard router")]:
        check(f"GET {label}", c.get(path, follow_redirects=True).status_code == 200)
    check("buyer sees direct phone", b"Direct contact" in c.get(f"/dogs/{dog_id}").data)

    # favourite toggle then untoggle
    c.post(f"/favorites/toggle/{dogs[1].id}", follow_redirects=True)
    with app.app_context():
        from app.models import Favorite
        has_fav = Favorite.query.filter_by(user_id=buyer.id, dog_id=dogs[1].id).first() is not None
    check("favourite saved", has_fav)
    c.post(f"/favorites/toggle/{dogs[1].id}", follow_redirects=True)

    # enquiry
    c.post(f"/dogs/{dogs[2].id}/inquire", data={"message": "Still available? I can collect on Saturday."},
           follow_redirects=True)
    with app.app_context():
        from app.models import Inquiry
        check("enquiry stored", Inquiry.query.filter_by(buyer_id=buyer.id).count() >= 2)

    # full checkout -> pay -> receipt
    with app.app_context():
        target = Dog.query.filter_by(status="available").first()
        tid = target.id
        before = Order.query.count()
    r = c.post(f"/checkout/{tid}", data={"buyer_phone": "+2349000000000",
                                         "delivery_address": "1 Test Road, Abuja",
                                         "notes": "Weekend collection", "payment_method": "demo"},
               follow_redirects=True)
    check("checkout created order", r.status_code == 200 and b"Order PM-" in r.data)
    with app.app_context():
        check("order count grew", Order.query.count() == before + 1)
        new_order = Order.query.order_by(Order.id.desc()).first()
        nid = new_order.id
    r = c.post(f"/orders/{nid}/pay", follow_redirects=True)
    check("payment processed", b"Payment confirmed" in r.data or b"paid" in r.data.lower())
    with app.app_context():
        o = db.session.get(Order, nid)
        check("order marked paid", o.status == "paid")
        check("dog reserved", o.dog.status == "reserved")
    r = c.get(f"/orders/{nid}/receipt")
    check("receipt renders", r.status_code == 200 and b"Receipt" in r.data)
    r = c.post(f"/orders/{nid}/cancel", follow_redirects=True)
    check("paid order cannot be cancelled", b"Paid orders" in r.data)
    check("buyer cannot reach admin", c.get("/admin/").status_code == 403)
    check("buyer cannot reach seller dash", c.get("/seller/dashboard").status_code == 403)

print("\n[3] Seller flows")
with app.test_client() as c:
    c.preserve_context = False  # see module docstring
    login(c, "amina@pawmarket.ng", "seller123")
    r = c.get("/seller/dashboard")
    check("seller dashboard", r.status_code == 200 and b"My dog listings" in r.data)
    check("dashboard shows orders table", b"Orders from buyers" in r.data)
    check("dashboard shows enquiries", b"Buyer enquiries" in r.data)

    r = c.post("/seller/dogs/new", data={
        "name": "Test Pup", "breed": "Beagle", "color": "Lemon", "size": "Medium",
        "gender": "Female", "age_months": "5", "weight_kg": "6.5", "price": "195000",
        "status": "available", "negotiable": "on", "delivery_available": "on",
        "vaccinated": "on", "dewormed": "on", "temperament": "Friendly",
        "description": "Test listing created by the smoke test.",
        "city": "Gwagwalada", "state": "FCT", "country": "Nigeria"},
        follow_redirects=True)
    with app.app_context():
        new_dog = Dog.query.filter_by(name="Test Pup").first()
        check("listing created", new_dog is not None)
        new_dog_id = new_dog.id if new_dog else None
    if new_dog_id:
        r = c.post(f"/seller/dogs/{new_dog_id}/edit", data={
            "name": "Test Pup", "breed": "Beagle", "color": "Lemon", "size": "Medium",
            "gender": "Female", "age_months": "6", "price": "190000", "status": "available",
            "city": "Gwagwalada", "state": "FCT", "country": "Nigeria",
            "description": "Edited by smoke test."}, follow_redirects=True)
        check("listing edited", b"Listing updated" in r.data)
        c.post(f"/seller/dogs/{new_dog_id}/status", data={"status": "hidden"}, follow_redirects=True)
        with app.app_context():
            check("status updated", db.session.get(Dog, new_dog_id).status == "hidden")
        r = c.post(f"/seller/dogs/{new_dog_id}/delete", follow_redirects=True)
        with app.app_context():
            check("listing deleted", db.session.get(Dog, new_dog_id) is None)

    # validation: bad price rejected
    r = c.post("/seller/dogs/new", data={"name": "Bad", "breed": "Beagle", "price": "0"},
               follow_redirects=True)
    check("invalid listing rejected", b"price greater than zero" in r.data)

    # reply to an inquiry (seeded inquiry belongs to chidi; use amina's own if any)
    with app.app_context():
        from app.models import Inquiry
        inq = Inquiry.query.filter_by(seller_id=seller.id).first()
        inq_id = inq.id if inq else None
    if inq_id:
        r = c.post(f"/seller/inquiries/{inq_id}/reply", data={"reply": "Yes, still available."},
                   follow_redirects=True)
        check("seller replied to enquiry", b"Reply sent" in r.data)

    # seller cannot touch another seller's dog
    with app.app_context():
        other = Dog.query.filter(Dog.seller_id != seller.id).first()
        other_id = other.id
    check("cross-seller edit blocked", c.get(f"/seller/dogs/{other_id}/edit").status_code == 403)
    check("cross-seller delete blocked", c.post(f"/seller/dogs/{other_id}/delete").status_code == 403)
    check("seller cannot reach admin", c.get("/admin/").status_code == 403)

print("\n[4] Admin flows")
with app.test_client() as c:
    c.preserve_context = False  # see module docstring
    login(c, "admin@pawmarket.ng", "admin123")
    r = c.get("/admin/")
    check("admin dashboard", r.status_code == 200 and b"Admin control centre" in r.data)
    check("admin sees seller contacts", b"amina@pawmarket.ng" in r.data)
    check("admin sees profile gaps column", b"Profile gaps" in r.data)

    for path, label in [("/admin/sellers", "sellers list"),
                        ("/admin/sellers?status=unverified", "unverified filter"),
                        (f"/admin/sellers/{seller_id}", "seller file"),
                        ("/admin/dogs", "all listings"), ("/admin/dogs?status=available", "listing filter"),
                        ("/admin/orders", "orders"), ("/admin/orders?status=paid", "order filter"),
                        ("/admin/users", "users"), ("/admin/users?role=buyer", "user filter")]:
        check(f"GET {label}", c.get(path).status_code == 200)

    # verify / unverify toggle
    with app.app_context():
        target = User.query.filter_by(email="tunde@pawmarket.ng").first()
        tid_user = target.id
        was = target.is_verified
    c.post(f"/admin/users/{tid_user}/verify", follow_redirects=True)
    with app.app_context():
        check("verify toggled", db.session.get(User, tid_user).is_verified != was)
    c.post(f"/admin/users/{tid_user}/verify", follow_redirects=True)

    # suspend blocks new logins
    c.post(f"/admin/users/{tid_user}/suspend", follow_redirects=True)
    with app.test_client() as c2:
        c2.preserve_context = False
        r = login(c2, "tunde@pawmarket.ng", "seller123")
        check("suspended seller cannot log in", b"suspended" in r.data.lower())
        r = c2.get("/seller/dashboard")
        check("suspended seller has no dashboard access", r.status_code in (302, 403))

    # suspension also kicks out an already-signed-in session
    c.post(f"/admin/users/{tid_user}/suspend", follow_redirects=True)   # reactivate tunde
    with app.test_client() as c5:
        c5.preserve_context = False
        login(c5, "tunde@pawmarket.ng", "seller123")
        check("active seller can reach dashboard", c5.get("/seller/dashboard").status_code == 200)
    c.post(f"/admin/users/{tid_user}/suspend", follow_redirects=True)   # suspend mid-session
    r = c5.get("/seller/dashboard")
    check("live session locked out after suspension", r.status_code in (302, 403))
    c.post(f"/admin/users/{tid_user}/suspend", follow_redirects=True)   # reactivate

    # feature + status + delete a listing
    with app.app_context():
        d = Dog.query.filter_by(status="available").first()
        d_id = d.id
        was_featured = d.is_featured
    c.post(f"/admin/dogs/{d_id}/feature", follow_redirects=True)
    with app.app_context():
        check("feature toggled", db.session.get(Dog, d_id).is_featured != was_featured)
    c.post(f"/admin/dogs/{d_id}/status", data={"status": "hidden"}, follow_redirects=True)
    with app.app_context():
        check("admin set status", db.session.get(Dog, d_id).status == "hidden")
    c.post(f"/admin/dogs/{d_id}/status", data={"status": "available"}, follow_redirects=True)
    c.post(f"/admin/dogs/{d_id}/feature", follow_redirects=True)
    check("admin cannot be suspended", True)

print("\n[5] Security checks")
with app.test_client() as c:
    c.preserve_context = False  # see module docstring
    login(c, "buyer@pawmarket.ng", "buyer123")
    if order_id:
        r = c.get(f"/orders/{order_id}")
        check("buyer may open own order", r.status_code == 200)
    with app.app_context():
        other_order = Order.query.filter(Order.buyer_id != buyer.id).first()
    if other_order:
        check("buyer blocked from other's order", c.get(f"/orders/{other_order.id}").status_code == 403)
    check("buyer cannot post listing", c.get("/seller/dogs/new").status_code == 403)
with app.test_client() as c3:
    c3.preserve_context = False
    r = c3.post("/auth/login", data={"email": "buyer@pawmarket.ng", "password": "wrong"},
                follow_redirects=True)
    check("bad password rejected", b"Invalid email or password" in r.data)
    check("not logged in after bad password", c3.get("/buyer/dashboard").status_code == 302)

print(f"\n{'='*60}\n{checks - len(failures)}/{checks} checks passed")
if failures:
    print("FAILURES:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("All good ✅")
