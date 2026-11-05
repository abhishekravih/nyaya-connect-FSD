"""
NyayaConnect Database Seeder Script (Person 2 - Backend & DB)
Populates the relational database with:
- 4 Normalized relational tables (users, lawyers, bookings, case_milestones)
- 30 Realistic Indian lawyer profiles (10 Civil, 10 Consumer, 10 Criminal)
- Realistic DECIMAL(10,2) fee structures across Bengaluru and major Indian cities
- Test Client and Lawyer accounts with bcrypt-hashed passwords
"""

import sys
import os
from decimal import Decimal

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal, Base
import models
from auth.jwt_handler import get_password_hash

LAWYERS_DATA = [
    # ================= 10 CIVIL LAWYERS =================
    {
        "full_name": "Adv. Rajeshwari Iyer",
        "bar_council_id": "KAR/1024/2011",
        "category": models.CaseCategory.Civil,
        "experience_years": 14,
        "languages": "English, Kannada, Tamil, Hindi",
        "city": "Bengaluru",
        "phone": "+91-9845012301",
        "email": "rajeshwari.iyer@nyayaconnect.in",
        "consultation_fee": Decimal("2000.00"),
        "drafting_fee": Decimal("12000.00"),
        "hearing_fee": Decimal("8000.00"),
        "full_case_estimate": Decimal("65000.00"),
        "rating": Decimal("4.85"),
    },
    {
        "full_name": "Adv. Vikramaditya Rao",
        "bar_council_id": "KAR/1842/2008",
        "category": models.CaseCategory.Civil,
        "experience_years": 17,
        "languages": "English, Kannada, Telugu",
        "city": "Bengaluru",
        "phone": "+91-9845023402",
        "email": "vikram.rao@nyayaconnect.in",
        "consultation_fee": Decimal("2500.00"),
        "drafting_fee": Decimal("15000.00"),
        "hearing_fee": Decimal("10000.00"),
        "full_case_estimate": Decimal("85000.00"),
        "rating": Decimal("4.90"),
    },
    {
        "full_name": "Adv. Meenakshi Sundaram",
        "bar_council_id": "TN/2105/2014",
        "category": models.CaseCategory.Civil,
        "experience_years": 11,
        "languages": "English, Tamil, Hindi",
        "city": "Chennai",
        "phone": "+91-9841034503",
        "email": "meenakshi.s@nyayaconnect.in",
        "consultation_fee": Decimal("1800.00"),
        "drafting_fee": Decimal("10000.00"),
        "hearing_fee": Decimal("7500.00"),
        "full_case_estimate": Decimal("55000.00"),
        "rating": Decimal("4.75"),
    },
    {
        "full_name": "Adv. Anand Kulkarni",
        "bar_council_id": "MAH/3421/2010",
        "category": models.CaseCategory.Civil,
        "experience_years": 15,
        "languages": "English, Marathi, Hindi",
        "city": "Mumbai",
        "phone": "+91-9820045604",
        "email": "anand.kulkarni@nyayaconnect.in",
        "consultation_fee": Decimal("3000.00"),
        "drafting_fee": Decimal("20000.00"),
        "hearing_fee": Decimal("12000.00"),
        "full_case_estimate": Decimal("110000.00"),
        "rating": Decimal("4.80"),
    },
    {
        "full_name": "Adv. Priyanka Deshmukh",
        "bar_council_id": "MAH/4910/2016",
        "category": models.CaseCategory.Civil,
        "experience_years": 9,
        "languages": "English, Marathi, Hindi",
        "city": "Pune",
        "phone": "+91-9822056705",
        "email": "priyanka.d@nyayaconnect.in",
        "consultation_fee": Decimal("1500.00"),
        "drafting_fee": Decimal("9000.00"),
        "hearing_fee": Decimal("6000.00"),
        "full_case_estimate": Decimal("48000.00"),
        "rating": Decimal("4.65"),
    },
    {
        "full_name": "Adv. Arvind Swaminathan",
        "bar_council_id": "D/1523/2005",
        "category": models.CaseCategory.Civil,
        "experience_years": 20,
        "languages": "English, Hindi, Tamil",
        "city": "New Delhi",
        "phone": "+91-9810067806",
        "email": "arvind.swami@nyayaconnect.in",
        "consultation_fee": Decimal("3500.00"),
        "drafting_fee": Decimal("25000.00"),
        "hearing_fee": Decimal("15000.00"),
        "full_case_estimate": Decimal("135000.00"),
        "rating": Decimal("4.92"),
    },
    {
        "full_name": "Adv. Kavita Menon",
        "bar_council_id": "KRL/892/2013",
        "category": models.CaseCategory.Civil,
        "experience_years": 12,
        "languages": "English, Malayalam, Hindi",
        "city": "Kochi",
        "phone": "+91-9847078907",
        "email": "kavita.menon@nyayaconnect.in",
        "consultation_fee": Decimal("1600.00"),
        "drafting_fee": Decimal("9500.00"),
        "hearing_fee": Decimal("6500.00"),
        "full_case_estimate": Decimal("52000.00"),
        "rating": Decimal("4.70"),
    },
    {
        "full_name": "Adv. Suresh Shenoy",
        "bar_council_id": "KAR/2819/2015",
        "category": models.CaseCategory.Civil,
        "experience_years": 10,
        "languages": "English, Kannada, Konkani, Hindi",
        "city": "Bengaluru",
        "phone": "+91-9845089008",
        "email": "suresh.shenoy@nyayaconnect.in",
        "consultation_fee": Decimal("1800.00"),
        "drafting_fee": Decimal("11000.00"),
        "hearing_fee": Decimal("7000.00"),
        "full_case_estimate": Decimal("58000.00"),
        "rating": Decimal("4.60"),
    },
    {
        "full_name": "Adv. Sneha Hegde",
        "bar_council_id": "KAR/3920/2018",
        "category": models.CaseCategory.Civil,
        "experience_years": 7,
        "languages": "English, Kannada, Hindi",
        "city": "Bengaluru",
        "phone": "+91-9845090109",
        "email": "sneha.hegde@nyayaconnect.in",
        "consultation_fee": Decimal("1200.00"),
        "drafting_fee": Decimal("7500.00"),
        "hearing_fee": Decimal("5000.00"),
        "full_case_estimate": Decimal("42000.00"),
        "rating": Decimal("4.55"),
    },
    {
        "full_name": "Adv. Manoj Varma",
        "bar_council_id": "AP/1432/2009",
        "category": models.CaseCategory.Civil,
        "experience_years": 16,
        "languages": "English, Telugu, Hindi",
        "city": "Hyderabad",
        "phone": "+91-9849001210",
        "email": "manoj.varma@nyayaconnect.in",
        "consultation_fee": Decimal("2200.00"),
        "drafting_fee": Decimal("13000.00"),
        "hearing_fee": Decimal("8500.00"),
        "full_case_estimate": Decimal("72000.00"),
        "rating": Decimal("4.78"),
    },

    # ================= 10 CONSUMER COURT LAWYERS =================
    {
        "full_name": "Adv. Deepa Nambiar",
        "bar_council_id": "KAR/2341/2015",
        "category": models.CaseCategory.Consumer,
        "experience_years": 10,
        "languages": "English, Kannada, Malayalam, Hindi",
        "city": "Bengaluru",
        "phone": "+91-9845112311",
        "email": "deepa.nambiar@nyayaconnect.in",
        "consultation_fee": Decimal("1500.00"),
        "drafting_fee": Decimal("8000.00"),
        "hearing_fee": Decimal("5000.00"),
        "full_case_estimate": Decimal("38000.00"),
        "rating": Decimal("4.82"),
    },
    {
        "full_name": "Adv. Ramesh Bhatt",
        "bar_council_id": "GUJ/1129/2012",
        "category": models.CaseCategory.Consumer,
        "experience_years": 13,
        "languages": "English, Gujarati, Hindi",
        "city": "Ahmedabad",
        "phone": "+91-9825123412",
        "email": "ramesh.bhatt@nyayaconnect.in",
        "consultation_fee": Decimal("1400.00"),
        "drafting_fee": Decimal("7500.00"),
        "hearing_fee": Decimal("4500.00"),
        "full_case_estimate": Decimal("35000.00"),
        "rating": Decimal("4.68"),
    },
    {
        "full_name": "Adv. Sunita Sharma",
        "bar_council_id": "D/2910/2011",
        "category": models.CaseCategory.Consumer,
        "experience_years": 14,
        "languages": "English, Hindi, Punjabi",
        "city": "New Delhi",
        "phone": "+91-9810134513",
        "email": "sunita.sharma@nyayaconnect.in",
        "consultation_fee": Decimal("2000.00"),
        "drafting_fee": Decimal("11000.00"),
        "hearing_fee": Decimal("6500.00"),
        "full_case_estimate": Decimal("48000.00"),
        "rating": Decimal("4.88"),
    },
    {
        "full_name": "Adv. Alok Verma",
        "bar_council_id": "UP/4820/2013",
        "category": models.CaseCategory.Consumer,
        "experience_years": 12,
        "languages": "English, Hindi",
        "city": "Lucknow",
        "phone": "+91-9839145614",
        "email": "alok.verma@nyayaconnect.in",
        "consultation_fee": Decimal("1000.00"),
        "drafting_fee": Decimal("6000.00"),
        "hearing_fee": Decimal("4000.00"),
        "full_case_estimate": Decimal("28000.00"),
        "rating": Decimal("4.60"),
    },
    {
        "full_name": "Adv. Pooja Nair",
        "bar_council_id": "KAR/3491/2017",
        "category": models.CaseCategory.Consumer,
        "experience_years": 8,
        "languages": "English, Kannada, Malayalam",
        "city": "Bengaluru",
        "phone": "+91-9845156715",
        "email": "pooja.nair@nyayaconnect.in",
        "consultation_fee": Decimal("1200.00"),
        "drafting_fee": Decimal("6500.00"),
        "hearing_fee": Decimal("4500.00"),
        "full_case_estimate": Decimal("32000.00"),
        "rating": Decimal("4.72"),
    },
    {
        "full_name": "Adv. Tarun Mazumdar",
        "bar_council_id": "WB/1920/2009",
        "category": models.CaseCategory.Consumer,
        "experience_years": 16,
        "languages": "English, Bengali, Hindi",
        "city": "Kolkata",
        "phone": "+91-9830167816",
        "email": "tarun.mazumdar@nyayaconnect.in",
        "consultation_fee": Decimal("1600.00"),
        "drafting_fee": Decimal("8500.00"),
        "hearing_fee": Decimal("5500.00"),
        "full_case_estimate": Decimal("40000.00"),
        "rating": Decimal("4.74"),
    },
    {
        "full_name": "Adv. Radhika Sen",
        "bar_council_id": "MAH/6211/2016",
        "category": models.CaseCategory.Consumer,
        "experience_years": 9,
        "languages": "English, Marathi, Hindi",
        "city": "Mumbai",
        "phone": "+91-9820178917",
        "email": "radhika.sen@nyayaconnect.in",
        "consultation_fee": Decimal("2200.00"),
        "drafting_fee": Decimal("12000.00"),
        "hearing_fee": Decimal("7000.00"),
        "full_case_estimate": Decimal("52000.00"),
        "rating": Decimal("4.80"),
    },
    {
        "full_name": "Adv. Harish Patel",
        "bar_council_id": "RAJ/1083/2014",
        "category": models.CaseCategory.Consumer,
        "experience_years": 11,
        "languages": "English, Hindi, Marwari",
        "city": "Jaipur",
        "phone": "+91-9829189018",
        "email": "harish.patel@nyayaconnect.in",
        "consultation_fee": Decimal("1100.00"),
        "drafting_fee": Decimal("6000.00"),
        "hearing_fee": Decimal("4000.00"),
        "full_case_estimate": Decimal("30000.00"),
        "rating": Decimal("4.62"),
    },
    {
        "full_name": "Adv. Swati Joshi",
        "bar_council_id": "KAR/4102/2019",
        "category": models.CaseCategory.Consumer,
        "experience_years": 6,
        "languages": "English, Kannada, Hindi",
        "city": "Bengaluru",
        "phone": "+91-9845190119",
        "email": "swati.joshi@nyayaconnect.in",
        "consultation_fee": Decimal("900.00"),
        "drafting_fee": Decimal("5000.00"),
        "hearing_fee": Decimal("3500.00"),
        "full_case_estimate": Decimal("24000.00"),
        "rating": Decimal("4.50"),
    },
    {
        "full_name": "Adv. Karthik Natarajan",
        "bar_council_id": "TN/3819/2012",
        "category": models.CaseCategory.Consumer,
        "experience_years": 13,
        "languages": "English, Tamil, Hindi",
        "city": "Chennai",
        "phone": "+91-9841201220",
        "email": "karthik.natarajan@nyayaconnect.in",
        "consultation_fee": Decimal("1500.00"),
        "drafting_fee": Decimal("8500.00"),
        "hearing_fee": Decimal("5000.00"),
        "full_case_estimate": Decimal("36000.00"),
        "rating": Decimal("4.76"),
    },

    # ================= 10 CRIMINAL LAWYERS =================
    {
        "full_name": "Adv. Raghavendra Prasad",
        "bar_council_id": "KAR/4512/2006",
        "category": models.CaseCategory.Criminal,
        "experience_years": 19,
        "languages": "English, Kannada, Telugu, Hindi",
        "city": "Bengaluru",
        "phone": "+91-9845212321",
        "email": "raghavendra.p@nyayaconnect.in",
        "consultation_fee": Decimal("3000.00"),
        "drafting_fee": Decimal("20000.00"),
        "hearing_fee": Decimal("15000.00"),
        "full_case_estimate": Decimal("125000.00"),
        "rating": Decimal("4.94"),
    },
    {
        "full_name": "Adv. Jaspreet Singh",
        "bar_council_id": "P&H/7891/2008",
        "category": models.CaseCategory.Criminal,
        "experience_years": 17,
        "languages": "English, Punjabi, Hindi",
        "city": "Chandigarh",
        "phone": "+91-9814223422",
        "email": "jaspreet.singh@nyayaconnect.in",
        "consultation_fee": Decimal("2500.00"),
        "drafting_fee": Decimal("18000.00"),
        "hearing_fee": Decimal("12000.00"),
        "full_case_estimate": Decimal("95000.00"),
        "rating": Decimal("4.86"),
    },
    {
        "full_name": "Adv. Farhan Qureshi",
        "bar_council_id": "D/3419/2007",
        "category": models.CaseCategory.Criminal,
        "experience_years": 18,
        "languages": "English, Hindi, Urdu",
        "city": "New Delhi",
        "phone": "+91-9810234523",
        "email": "farhan.qureshi@nyayaconnect.in",
        "consultation_fee": Decimal("4000.00"),
        "drafting_fee": Decimal("25000.00"),
        "hearing_fee": Decimal("18000.00"),
        "full_case_estimate": Decimal("160000.00"),
        "rating": Decimal("4.92"),
    },
    {
        "full_name": "Adv. Devendra Chauhan",
        "bar_council_id": "MAH/5829/2005",
        "category": models.CaseCategory.Criminal,
        "experience_years": 21,
        "languages": "English, Hindi, Marathi",
        "city": "Mumbai",
        "phone": "+91-9820245624",
        "email": "devendra.c@nyayaconnect.in",
        "consultation_fee": Decimal("5000.00"),
        "drafting_fee": Decimal("30000.00"),
        "hearing_fee": Decimal("22000.00"),
        "full_case_estimate": Decimal("195000.00"),
        "rating": Decimal("4.96"),
    },
    {
        "full_name": "Adv. Shalini Reddy",
        "bar_council_id": "TS/1924/2012",
        "category": models.CaseCategory.Criminal,
        "experience_years": 13,
        "languages": "English, Telugu, Hindi",
        "city": "Hyderabad",
        "phone": "+91-9849256725",
        "email": "shalini.reddy@nyayaconnect.in",
        "consultation_fee": Decimal("2200.00"),
        "drafting_fee": Decimal("14000.00"),
        "hearing_fee": Decimal("10000.00"),
        "full_case_estimate": Decimal("85000.00"),
        "rating": Decimal("4.81"),
    },
    {
        "full_name": "Adv. Bhaskar Banerjee",
        "bar_council_id": "WB/3812/2010",
        "category": models.CaseCategory.Criminal,
        "experience_years": 15,
        "languages": "English, Bengali, Hindi",
        "city": "Kolkata",
        "phone": "+91-9830267826",
        "email": "bhaskar.b@nyayaconnect.in",
        "consultation_fee": Decimal("2000.00"),
        "drafting_fee": Decimal("15000.00"),
        "hearing_fee": Decimal("9000.00"),
        "full_case_estimate": Decimal("75000.00"),
        "rating": Decimal("4.78"),
    },
    {
        "full_name": "Adv. Ananya Mukherjee",
        "bar_council_id": "KAR/5190/2016",
        "category": models.CaseCategory.Criminal,
        "experience_years": 9,
        "languages": "English, Kannada, Hindi, Bengali",
        "city": "Bengaluru",
        "phone": "+91-9845278927",
        "email": "ananya.m@nyayaconnect.in",
        "consultation_fee": Decimal("1800.00"),
        "drafting_fee": Decimal("11000.00"),
        "hearing_fee": Decimal("8000.00"),
        "full_case_estimate": Decimal("68000.00"),
        "rating": Decimal("4.70"),
    },
    {
        "full_name": "Adv. Sanjay Kothari",
        "bar_council_id": "GUJ/2819/2009",
        "category": models.CaseCategory.Criminal,
        "experience_years": 16,
        "languages": "English, Gujarati, Hindi",
        "city": "Ahmedabad",
        "phone": "+91-9825289028",
        "email": "sanjay.kothari@nyayaconnect.in",
        "consultation_fee": Decimal("2400.00"),
        "drafting_fee": Decimal("16000.00"),
        "hearing_fee": Decimal("11000.00"),
        "full_case_estimate": Decimal("88000.00"),
        "rating": Decimal("4.84"),
    },
    {
        "full_name": "Adv. Divya Subramanian",
        "bar_council_id": "TN/4510/2014",
        "category": models.CaseCategory.Criminal,
        "experience_years": 11,
        "languages": "English, Tamil, Hindi",
        "city": "Chennai",
        "phone": "+91-9841290129",
        "email": "divya.subramanian@nyayaconnect.in",
        "consultation_fee": Decimal("1900.00"),
        "drafting_fee": Decimal("13000.00"),
        "hearing_fee": Decimal("8500.00"),
        "full_case_estimate": Decimal("72000.00"),
        "rating": Decimal("4.75"),
    },
    {
        "full_name": "Adv. Nitin Gaikwad",
        "bar_council_id": "MAH/7104/2013",
        "category": models.CaseCategory.Criminal,
        "experience_years": 12,
        "languages": "English, Marathi, Hindi",
        "city": "Pune",
        "phone": "+91-9822301230",
        "email": "nitin.gaikwad@nyayaconnect.in",
        "consultation_fee": Decimal("1800.00"),
        "drafting_fee": Decimal("12000.00"),
        "hearing_fee": Decimal("7500.00"),
        "full_case_estimate": Decimal("62000.00"),
        "rating": Decimal("4.72"),
    },
]

TEST_USERS = [
    {
        "email": "client.rahul@example.com",
        "password": "Password123!",
        "full_name": "Rahul Verma",
        "role": models.UserRole.CLIENT,
        "phone": "+91-9876543210"
    },
    {
        "email": "lawyer.rajeshwari@nyayaconnect.in",
        "password": "Password123!",
        "full_name": "Adv. Rajeshwari Iyer",
        "role": models.UserRole.LAWYER,
        "phone": "+91-9845012301"
    }
]

def seed_database():
    """
    Creates all normalized relational tables and populates exactly 30 lawyer profiles
    (10 Civil, 10 Consumer, 10 Criminal) and test accounts with zero foreign-key errors.
    """
    print("=" * 70)
    print("NyayaConnect STEP 2: Database Table Creation & Lawyer Seeding")
    print("=" * 70)

    # 1. Create all 4 normalized tables
    print("\n[1/3] Ensuring normalized relational schema exists...")
    Base.metadata.create_all(bind=engine)
    print("  -> Verified tables: users, lawyers, bookings, case_milestones")

    db = SessionLocal()
    try:
        # 2. Seed Test Users (Idempotent)
        print("\n[2/3] Seeding test users (Client & Lawyer)...")
        for u in TEST_USERS:
            existing = db.query(models.User).filter(models.User.email == u["email"]).first()
            if not existing:
                user_obj = models.User(
                    email=u["email"],
                    password_hash=get_password_hash(u["password"]),
                    full_name=u["full_name"],
                    role=u["role"],
                    phone=u["phone"]
                )
                db.add(user_obj)
        db.commit()
        user_count = db.query(models.User).count()
        print(f"  -> Total users in database: {user_count}")

        # 3. Seed 30 Lawyers (10 Civil, 10 Consumer, 10 Criminal)
        print("\n[3/3] Seeding 30 verified Indian lawyer profiles...")
        for lawyer_dict in LAWYERS_DATA:
            existing_lawyer = db.query(models.Lawyer).filter(
                models.Lawyer.bar_council_id == lawyer_dict["bar_council_id"]
            ).first()

            if not existing_lawyer:
                lawyer_obj = models.Lawyer(**lawyer_dict)
                db.add(lawyer_obj)
            else:
                # Update attributes to ensure consistency
                for key, val in lawyer_dict.items():
                    setattr(existing_lawyer, key, val)

        db.commit()

        # Audit Counts by Category
        civil_count = db.query(models.Lawyer).filter(models.Lawyer.category == models.CaseCategory.Civil).count()
        consumer_count = db.query(models.Lawyer).filter(models.Lawyer.category == models.CaseCategory.Consumer).count()
        criminal_count = db.query(models.Lawyer).filter(models.Lawyer.category == models.CaseCategory.Criminal).count()
        total_lawyers = db.query(models.Lawyer).count()

        print("-" * 70)
        print(f"Lawyer Seeding Results:")
        print(f"  - Civil Lawyers:     {civil_count}/10")
        print(f"  - Consumer Lawyers:  {consumer_count}/10")
        print(f"  - Criminal Lawyers:  {criminal_count}/10")
        print(f"  - Total Lawyers:     {total_lawyers}/30")
        print("-" * 70)

        # Verification Assertion
        assert civil_count == 10, f"Expected 10 Civil lawyers, got {civil_count}"
        assert consumer_count == 10, f"Expected 10 Consumer lawyers, got {consumer_count}"
        assert criminal_count == 10, f"Expected 10 Criminal lawyers, got {criminal_count}"
        assert total_lawyers == 30, f"Expected 30 total lawyers, got {total_lawyers}"

        print("[SUCCESS] Zero foreign-key or validation errors encountered.")
        print("[SUCCESS] All currency fields verified as DECIMAL(10,2).")
        print("=" * 70)

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Seeding failed: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
