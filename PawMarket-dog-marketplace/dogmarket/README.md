# 🐾 PawMarket — dog marketplace (Python / Flask)

A complete buy-and-sell website for dogs. Every listing carries full characteristics
(breed, colour, size, sex, age, weight, temperament, health records, price, delivery),
the exact location of the dog, and the **direct contact details of the seller who posted it**.
There are three dashboards: **buyer**, **seller** and **admin**.

---

## Run it

```bash
cd dogmarket
pip install -r requirements.txt
python seed.py --reset     # creates DB + demo accounts + 12 listings
python run.py              # http://localhost:8000
```

`seed.py` without `--reset` only seeds when the database is empty.

## Demo logins

| Role   | Email                  | Password    |
|--------|------------------------|-------------|
| Admin  | admin@pawmarket.ng     | admin123    |
| Buyer  | buyer@pawmarket.ng     | buyer123    |
| Seller | amina@pawmarket.ng     | seller123   |
| Seller | chidi@pawmarket.ng     | seller123   |
| Seller | fatima@pawmarket.ng    | seller123   |
| Seller | tunde@pawmarket.ng     | seller123   |

---

## What each role can do

### Public (no account)
- Home page with search (keyword + size + location) and featured listings
- Browse page with filters: breed, size, colour, sex, age group, location, price range,
  vaccinated / pedigree / delivery, plus 4 sort orders and pagination
- Dog detail page — full characteristics table, photo gallery, health records
- Seller public profile page
- Seller phone / WhatsApp / email are **hidden until sign-in** (🔒 prompt instead)

### Buyer
- Register / sign in, edit profile & contact info, change password
- Save dogs to a wishlist (❤️)
- Message a seller about a specific dog (they reply in their dashboard)
- Checkout → order → demo payment → printable receipt (PDF-able)
- Buyer dashboard: orders with status timeline, total spent, saved dogs, message threads

### Seller
- Register as seller, publish listings with up to several photos (first = cover)
- Edit / delete listings, swap the cover photo, remove photos
- Change listing status instantly: available / reserved / sold / hidden
- Seller dashboard: live listings, views, orders, earnings, profile-completeness meter
- Read buyer enquiries and reply; view buyer phone/email on paid orders
- Mark orders “handed over” or cancel them

### Admin
- **Overview**: sellers, buyers, listings, orders, platform revenue
- **Seller moderation table**: every seller's phone, WhatsApp, email, location,
  which profile fields are missing, listing counts, order counts and revenue
- **Verify / unverify** sellers, **suspend / reactivate** accounts (suspended users can't log in)
- **Seller file page**: full contact block + everything that seller posted, with per-listing
  moderation (feature on homepage, change status, delete)
- All listings and all orders across the platform, filterable by status
- All user accounts filterable by role

---

## Route map

| Area | Routes |
|------|--------|
| Public | `/` `/dogs` `/dogs/<id>` `/sellers/<id>` |
| Auth | `/auth/register` `/auth/login` `/auth/logout` `/auth/profile` |
| Buyer | `/buyer/dashboard` `/checkout/<dog_id>` `/orders/<id>` `/orders/<id>/pay` `/orders/<id>/receipt` |
| Seller | `/seller/dashboard` `/seller/dogs/new` `/seller/dogs/<id>/edit` `/seller/orders/...` `/seller/inquiries/<id>/reply` |
| Admin | `/admin/` `/admin/sellers` `/admin/sellers/<id>` `/admin/dogs` `/admin/orders` `/admin/users` |

Role protection is enforced in `app/helpers.py` (`role_required`) plus per-object ownership
checks — a seller can never edit or delete another seller's dog, and one buyer can't open
another buyer's order.

## Project structure

```
dogmarket/
├── run.py               # entry point (python run.py)
├── seed.py              # demo data / reset
├── config.py            # settings, currency, upload limits
├── smoke_test.py        # 63 automated end-to-end checks (python smoke_test.py)
├── app/
│   ├── __init__.py      # app factory, filters, error pages
│   ├── models.py        # User, Dog, DogImage, Favorite, Order, Inquiry
│   ├── auth.py          # register / login / profile
│   ├── views.py         # public pages, checkout, payments, buyer dashboard
│   ├── seller.py        # seller dashboard, listing CRUD, order & enquiry handling
│   ├── admin.py         # admin moderation & monitoring
│   └── uploads.py       # image saving/validation
├── templates/           # Jinja2 templates (base + role folders)
├── static/css/app.css   # all styling, responsive
└── instance/pawmarket.db  # SQLite database
```

Tech: Flask 3, Flask-SQLAlchemy (SQLite by default — set `DATABASE_URL` for Postgres),
Flask-Login, Werkzeug password hashing.

---

## Going live — the 5 things to change

1. **Secret key & database** — set `SECRET_KEY` and `DATABASE_URL` (e.g. Postgres) as env vars.
2. **Payments** — `main.pay_order()` in `app/views.py` is a sandbox stub. Replace it with
   Paystack/Flutterwave: initialise a transaction, redirect to checkout, verify in a webhook,
   then set `order.status = "paid"` and `order.dog.status = "reserved"`.
3. **Server** — run behind gunicorn/uvicorn workers instead of the Flask dev server:
   `gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"`.
4. **Emails / SMS** — hook up notifications for new enquiries, orders and admin verification.
5. **Storage** — uploads currently go to `static/uploads/`; move to S3/Cloudinary for scale.

Extra hardening worth adding later: rate-limiting on login, CSRF tokens (Flask-WTF),
image re-encoding on upload, and a moderation queue before listings go public.

## Tests

```bash
python smoke_test.py     # 66 checks, all green
```

Covers the guest, buyer, seller and admin journeys plus security checks:
cross-seller listing access, cross-buyer order access, role escalation,
bad-password rejection, and suspension (blocked at login *and* kicked out of an
already-signed-in session).

> Harness note: each `with app.test_client()` block disables Flask's context
> preservation. Left on, one application context lives for the whole block, so
> `flask.g` — and Flask-Login's cached `g._login_user` — leaks between requests,
> which real HTTP traffic never does. The module docstring explains this.
