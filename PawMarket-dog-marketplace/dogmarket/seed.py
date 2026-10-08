"""Seed the database with demo accounts and dog listings.

Run with:  python seed.py           (only seeds when empty)
           python seed.py --reset   (drops everything and re-seeds)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import create_app
from app.extensions import db
from app.models import Dog, DogImage, Inquiry, Order, User

app = create_app()

SELLERS = [
    dict(full_name="Amina Bello", email="amina@pawmarket.ng", phone="+2348031234567",
         whatsapp="+2348031234567", business_name="Bello Kennels",
         bio="Family-run kennel in Abuja breeding healthy, well-socialised companion dogs. "
             "All puppies come with vaccination cards and a 7-day health guarantee.",
         city="Gwagwalada", state="FCT", country="Nigeria", is_verified=True),
    dict(full_name="Chidi Okeke", email="chidi@pawmarket.ng", phone="+2348129876543",
         whatsapp="+2348129876543", business_name="Okeke Guard Dogs",
         bio="Working-line guard dogs and family protectors. We train basic obedience and "
             "handler commands before handover.",
         city="Port Harcourt", state="Rivers", country="Nigeria", is_verified=True),
    dict(full_name="Fatima Yusuf", email="fatima@pawmarket.ng", phone="+2347091112223",
         whatsapp="+2347091112223", business_name="Sahel Pets",
         bio="Small-breed specialists. Home-raised puppies, vet-checked and delivered "
             "in climate-controlled crates nationwide.",
         city="Kano", state="Kano", country="Nigeria", is_verified=False),
    dict(full_name="Tunde Adeyemi", email="tunde@pawmarket.ng", phone="+2348065554444",
         whatsapp="+2348065554444", business_name="Lagos Dog Hub",
         bio="Lagos-based breeder and rehomer. Visit our facility in Lekki any day of the week.",
         city="Lekki", state="Lagos", country="Nigeria", is_verified=False),
]

DOGS = [
    dict(seller="amina@pawmarket.ng", name="Simba", breed="Labrador Retriever", color="Golden",
         size="Large", gender="Male", age_months=4, weight_kg=9.5, price=180000,
         negotiable=True, delivery_available=True, vaccinated=True, dewormed=True,
         pedigree=True, temperament="Playful, gentle with children, food-motivated",
         health_notes="Full vaccination card, vet-checked at 8 weeks.",
         description="Simba is a confident, social pup raised around kids and other dogs. "
                     "He walks well on a leash and already responds to his name. Ready for "
                     "a loving family home.",
         city="Gwagwalada", state="FCT", is_featured=True, image="dogs/labrador.jpg"),
    dict(seller="chidi@pawmarket.ng", name="Rex", breed="German Shepherd", color="Black and Tan",
         size="Giant", gender="Male", age_months=14, weight_kg=34, price=450000,
         delivery_available=True, vaccinated=True, dewormed=True, trained=True,
         kennel_club_registered=True, temperament="Alert, obedient, protective",
         health_notes="Hip-scored, annual vaccines up to date.",
         description="Working-line German Shepherd trained in basic protection and on-lead "
                     "obedience (sit, stay, heel, recall). Suits a compound or estate home "
                     "with an experienced handler.",
         city="Port Harcourt", state="Rivers", is_featured=True, image="dogs/german-shepherd.jpg"),
    dict(seller="fatima@pawmarket.ng", name="Coco", breed="French Bulldog", color="Cream",
         size="Small", gender="Female", age_months=3, weight_kg=4.2, price=520000,
         negotiable=True, delivery_available=True, vaccinated=True, dewormed=True,
         temperament="Affectionate, low exercise needs, good with apartment living",
         health_notes="Vet report available. Brachycephalic care guide included.",
         description="Coco is an apartment-friendly companion who loves laps and short "
                     "evening walks. She is crate-trained and nearly house-trained.",
         city="Kano", state="Kano", is_featured=True, image="dogs/french-bulldog.jpg"),
    dict(seller="chidi@pawmarket.ng", name="Kali", breed="Boerboel", color="Brindle",
         size="Giant", gender="Female", age_months=9, weight_kg=38, price=380000,
         negotiable=True, delivery_available=False, vaccinated=True, dewormed=True,
         pedigree=True, temperament="Calm, territorial, loyal to family",
         health_notes="Registered with the Boerboel Breeders Society of Nigeria.",
         description="Kali is a South African Boerboel with an excellent guarding instinct. "
                     "She is calm indoors and alerts on unusual activity at the gate.",
         city="Port Harcourt", state="Rivers", image="dogs/boerboel.jpg"),
    dict(seller="tunde@pawmarket.ng", name="Bruno", breed="Rottweiler", color="Black and Mahogany",
         size="Large", gender="Male", age_months=6, weight_kg=22, price=300000,
         delivery_available=True, vaccinated=True, dewormed=True, trained=True,
         temperament="Bold, energetic, needs daily exercise",
         health_notes="Vaccinated, dewormed, microchipped.",
         description="Six-month-old Rottweiler with strong drive and a friendly disposition "
                     "toward people he knows. Ideal for a family that will keep up his training.",
         city="Lekki", state="Lagos", image="dogs/rottweiler.jpg"),
    dict(seller="fatima@pawmarket.ng", name="Mimi", breed="Pomeranian", color="Orange Sable",
         size="Small", gender="Female", age_months=5, weight_kg=2.4, price=250000,
         negotiable=True, delivery_available=True, vaccinated=True, dewormed=True,
         temperament="Chatty, affectionate, perfect handbag companion",
         health_notes="Vet-checked, no known issues.",
         description="Mimi is a fluffy little character who adores attention and travels "
                     "well in a carrier. Grooming every six weeks recommended.",
         city="Kano", state="Kano", image="dogs/pomeranian.jpg"),
    dict(seller="amina@pawmarket.ng", name="Zara", breed="Beagle", color="Tricolour",
         size="Medium", gender="Female", age_months=4, weight_kg=7.1, price=210000,
         delivery_available=True, vaccinated=True, dewormed=True, pedigree=True,
         temperament="Curious, nose-driven, great with children",
         health_notes="Full puppy vaccination schedule completed.",
         description="Zara follows her nose everywhere and would love a home with a secure "
                     "yard. She is crate-trained and sleeps through the night.",
         city="Gwagwalada", state="FCT", image="dogs/beagle.jpg"),
    dict(seller="tunde@pawmarket.ng", name="Tiger", breed="Mixed Breed (Local)", color="Tan and White",
         size="Medium", gender="Male", age_months=8, weight_kg=14, price=55000,
         negotiable=True, delivery_available=False, vaccinated=True, dewormed=True,
         temperament=" Hardy, intelligent, very adaptable",
         health_notes="Naturally robust; vaccinated and dewormed.",
         description="Tiger was rescued as a puppy and has grown into a hardy, loyal companion. "
                     "Zero-known hereditary issues and a great watchdog for a modest home.",
         city="Ikeja", state="Lagos", image="dogs/mongrel.jpg"),
    dict(seller="amina@pawmarket.ng", name="Biscuit", breed="Labrador Retriever", color="Chocolate",
         size="Large", gender="Male", age_months=2, weight_kg=5.0, price=165000,
         delivery_available=True, vaccinated=False, dewormed=True,
         temperament="Sleepy, cuddly, loves belly rubs",
         health_notes="First vaccination due at 6 weeks - booked with our vet.",
         description="Biscuit is the calmest of his litter and loves being carried around. "
                     "Reserve now and collect from 8 weeks of age.",
         city="Gwagwalada", state="FCT", image="dogs/labrador.jpg"),
    dict(seller="chidi@pawmarket.ng", name="Alpha", breed="German Shepherd", color="Sable",
         size="Giant", gender="Male", age_months=28, weight_kg=40, price=500000,
         negotiable=True, vaccinated=True, dewormed=True, trained=True,
         kennel_club_registered=True, temperament="Steady, command-trained, estate ready",
         health_notes="All vaccines current, wellness certificate attached.",
         description="Two-year-old trained guard dog for estate or office security. Alpha "
                     "responds to English and Igbo commands and works off-lead on a known perimeter.",
         city="Port Harcourt", state="Rivers", image="dogs/german-shepherd.jpg"),
    dict(seller="fatima@pawmarket.ng", name="Lulu", breed="French Bulldog", color="Blue Fawn",
         size="Small", gender="Female", age_months=6, weight_kg=8.0, price=480000,
         delivery_available=True, vaccinated=True, dewormed=True, pedigree=True,
         temperament="Sweet, loves people, minimal shedding",
         health_notes="Skin folded daily, vet-checked.",
         description="Lulu is a show-quality blue fawn Frenchie with a lovely temperament. "
                     "Pedigree papers available on request.",
         city="Kano", state="Kano", image="dogs/french-bulldog.jpg"),
    dict(seller="tunde@pawmarket.ng", name="Onyx", breed="Rottweiler", color="Black and Tan",
         size="Giant", gender="Male", age_months=15, weight_kg=45, price=420000,
         delivery_available=True, vaccinated=True, dewormed=True, trained=True,
         temperament="Protective, confident, requires strong leadership",
         health_notes="Annual booster done, hip assessment available.",
         description="Onyx is a proven night guard who has worked with our security team for "
                     "six months. Handover includes a two-week handler familiarisation session.",
         city="Lekki", state="Lagos", image="dogs/rottweiler.jpg"),
]


def seed(reset=False):
    if reset:
        db.drop_all()
        print("Dropped all tables.")

    db.create_all()

    if User.query.count() and not reset:
        print("Database already has data - skipping seed. Use --reset to rebuild.")
        return

    # --- admin ---
    admin = User(full_name="Site Administrator", email="admin@pawmarket.ng",
                 role="admin", phone="+2348000000000", city="Abuja", state="FCT",
                 country="Nigeria", is_verified=True,
                 bio="PawMarket platform administrator.")
    admin.set_password("admin123")
    db.session.add(admin)

    # --- demo buyer ---
    buyer = User(full_name="Grace Nwosu", email="buyer@pawmarket.ng", role="buyer",
                 phone="+2349012345678", whatsapp="+2349012345678", city="Abuja",
                 state="FCT", country="Nigeria", bio="Looking for a family companion dog.")
    buyer.set_password("buyer123")
    db.session.add(buyer)

    # --- sellers ---
    sellers = {}
    for data in SELLERS:
        s = User(role="seller", **data)
        s.set_password("seller123")
        db.session.add(s)
        sellers[s.email] = s

    db.session.flush()

    # --- dogs ---
    dogs = []
    for data in DOGS:
        img = data.pop("image")
        seller = sellers[data.pop("seller")]
        dog = Dog(seller_id=seller.id, **data)
        db.session.add(dog)
        db.session.flush()
        db.session.add(DogImage(dog_id=dog.id, filename=img, is_primary=True))
        dogs.append(dog)

    db.session.flush()

    # --- a sample order + inquiries so the dashboards aren't empty ---
    order = Order(reference="PM-DEMO1234", dog_id=dogs[0].id, buyer_id=buyer.id,
                  seller_id=dogs[0].seller_id, amount=dogs[0].price, status="paid",
                  payment_method="demo", payment_ref="DEMO-1234567890",
                  delivery_address="12 Ademola Street, Wuse 2, Abuja",
                  buyer_phone="+2349012345678", notes="Please deliver on a Saturday morning.")
    db.session.add(order)
    dogs[0].status = "reserved"

    db.session.add(Inquiry(dog_id=dogs[1].id, buyer_id=buyer.id,
                           seller_id=dogs[1].seller_id,
                           message="Is Rex comfortable around young children? I have a 6-year-old.",
                           reply="Yes - Rex has lived with children and is very tolerant. "
                                 "You are welcome to visit and see him interact."))
    db.session.add(Inquiry(dog_id=dogs[2].id, buyer_id=buyer.id,
                           seller_id=dogs[2].seller_id,
                           message="Do you deliver to Abuja, and is the price negotiable?"))

    db.session.commit()
    print("Seeded:")
    print("  admin : admin@pawmarket.ng / admin123")
    print("  buyer : buyer@pawmarket.ng / buyer123")
    print("  seller: amina@pawmarket.ng / seller123  (also chidi@, fatima@, tunde@)")
    print(f"  {len(DOGS)} dog listings created.")


if __name__ == "__main__":
    with app.app_context():
        seed(reset="--reset" in sys.argv)
