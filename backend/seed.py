"""Seed database with realistic demo data for testing and development."""
import logging
import secrets

from app.core.config import settings, validate_admin_seed_password
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.project import Project
from app.models.site_survey import SiteSurvey
from app.models.blog import BlogPost
from app.models.faq import FAQ
from app.models.calculator import CalculatorSubmission, CalculatorSettings
from app.models.settings import SystemSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")


def ensure_seed_admin(db):
    admin = db.query(User).filter(User.email == "admin@solara.com").first()
    if admin:
        if admin.role.strip().casefold() != "admin":
            raise RuntimeError(
                "admin@solara.com already exists but is not an administrator; "
                "resolve the account explicitly before seeding."
            )
        return admin

    try:
        admin_password = validate_admin_seed_password(settings.SEED_ADMIN_PASSWORD)
    except ValueError as exc:
        raise RuntimeError(
            "Set a unique SEED_ADMIN_PASSWORD of at least 12 characters "
            "with uppercase, lowercase, and numeric characters before seeding."
        ) from exc

    admin = User(
        name="Alex Sterling",
        email="admin@solara.com",
        password_hash=get_password_hash(admin_password),
        phone="+1 (555) 234-5678",
        role="Admin",
        status="Active",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    logger.info("Created the initial administrator account.")
    return admin


def seed_data():
    db = SessionLocal()
    try:
        # Seed the administrator independently; never reset an existing password.
        seed_demo_users = db.query(User).count() == 0
        admin_user = ensure_seed_admin(db)

        # 1. Seed demo staff only for a new user table.
        if seed_demo_users:
            logger.info("Seeding users...")
            users = [
                User(
                    name="Marcus Chen",
                    email="marcus.c@solara.com",
                    password_hash=get_password_hash(secrets.token_urlsafe(32)),
                    phone="+91 98111 22334",
                    role="Sales Rep",
                    status="Active",
                ),
                User(
                    name="Elena Rodriguez",
                    email="elena.r@solara.com",
                    password_hash=get_password_hash(secrets.token_urlsafe(32)),
                    phone="+91 98222 33445",
                    role="Sales Rep",
                    status="Active",
                ),
                User(
                    name="David Kim",
                    email="david.k@solara.com",
                    password_hash=get_password_hash(secrets.token_urlsafe(32)),
                    phone="+91 98333 44556",
                    role="Sales Rep",
                    status="Invited",
                ),
                User(
                    name="Priya Patel",
                    email="priya.p@solara.com",
                    password_hash=get_password_hash(secrets.token_urlsafe(32)),
                    phone="+91 98444 55667",
                    role="Sales Rep",
                    status="Inactive",
                ),
            ]
            db.add_all(users)
            db.commit()

        # 2. Seed Customers
        if db.query(Customer).count() == 0:
            logger.info("Seeding customers...")
            customers = [
                Customer(name="Rohan Patil", contact="+91 98765 43210", email="rohan@example.com", phone="+91 98765 43210", location="Mumbai", property_type="Residential", customer_since="12 Sep 2026", status="Active", assigned_user_id=admin_user.id if admin_user else None),
                Customer(name="Sneha Sharma", contact="+91 91234 56789", email="sneha@example.com", phone="+91 91234 56789", location="Pune", property_type="Commercial", customer_since="11 Sep 2026", status="Active", assigned_user_id=admin_user.id if admin_user else None),
                Customer(name="Amit Verma", contact="+91 99887 66554", email="amit@example.com", phone="+91 99887 66554", location="Nashik", property_type="Residential", customer_since="2 Aug 2026", status="Active"),
                Customer(name="Priya Desai", contact="+91 97654 32109", email="priya@example.com", phone="+91 97654 32109", location="Thane", property_type="Industrial", customer_since="15 Jul 2026", status="Inactive"),
                Customer(name="Karan Mehta", contact="+91 88990 12345", email="karan@example.com", phone="+91 88990 12345", location="Mumbai", property_type="Residential", customer_since="20 Jun 2026", status="Active"),
                Customer(name="Neha Gupta", contact="+91 98761 23456", email="neha@example.com", phone="+91 98761 23456", location="Pune", property_type="Residential", customer_since="18 Jun 2026", status="Active"),
                Customer(name="Vikram Singh", contact="+91 90654 77889", email="vikram@example.com", phone="+91 90654 77889", location="Nagpur", property_type="Commercial", customer_since="5 Jun 2026", status="Active"),
                Customer(name="Anjali Kulkarni", contact="+91 88776 55443", email="anjali@example.com", phone="+91 88776 55443", location="Solapur", property_type="Residential", customer_since="28 May 2026", status="Inactive"),
            ]
            db.add_all(customers)
            db.commit()

        # 3. Seed Leads
        if db.query(Lead).count() == 0:
            logger.info("Seeding leads...")
            cust_by_name = {c.name: c.id for c in db.query(Customer).all()}
            leads = [
                Lead(name="Rohan Patil", contact="+91 98765 43210", email="rohan@example.com", phone="+91 98765 43210", location="Mumbai", property_type="Residential", source="Website", status="New", estimated_value=250000.0, customer_id=cust_by_name.get("Rohan Patil")),
                Lead(name="Sneha Sharma", contact="+91 91234 56789", email="sneha@example.com", phone="+91 91234 56789", location="Pune", property_type="Commercial", source="Google Ads", status="Contacted", estimated_value=850000.0, customer_id=cust_by_name.get("Sneha Sharma")),
                Lead(name="Amit Verma", contact="+91 99887 66554", email="amit@example.com", phone="+91 99887 66554", location="Nashik", property_type="Residential", source="Referral", status="Site Survey", estimated_value=320000.0, customer_id=cust_by_name.get("Amit Verma")),
                Lead(name="Priya Desai", contact="+91 97654 32109", email="priya@example.com", phone="+91 97654 32109", location="Thane", property_type="Industrial", source="Website", status="Quoted", estimated_value=1500000.0, customer_id=cust_by_name.get("Priya Desai")),
                Lead(name="Karan Mehta", contact="+91 88990 12345", email="karan@example.com", phone="+91 88990 12345", location="Mumbai", property_type="Residential", source="Social Media", status="Converted", estimated_value=400000.0, customer_id=cust_by_name.get("Karan Mehta")),
                Lead(name="Neha Gupta", contact="+91 98761 23456", email="neha@example.com", phone="+91 98761 23456", location="Pune", property_type="Residential", source="Website", status="Lost", estimated_value=200000.0, customer_id=cust_by_name.get("Neha Gupta")),
                Lead(name="Vikram Singh", contact="+91 90654 77889", email="vikram@example.com", phone="+91 90654 77889", location="Nagpur", property_type="Commercial", source="Google Ads", status="New", estimated_value=1200000.0, customer_id=cust_by_name.get("Vikram Singh")),
                Lead(name="Anjali Kulkarni", contact="+91 88776 55443", email="anjali@example.com", phone="+91 88776 55443", location="Solapur", property_type="Residential", source="Referral", status="Contacted", estimated_value=280000.0, customer_id=cust_by_name.get("Anjali Kulkarni")),
            ]
            db.add_all(leads)
            db.commit()

        # 4. Seed Projects
        if db.query(Project).count() == 0:
            logger.info("Seeding projects...")
            cust1 = db.query(Customer).filter(Customer.name == "Rohan Patil").first()
            cust2 = db.query(Customer).filter(Customer.name == "Sneha Sharma").first()
            lead1 = db.query(Lead).filter(Lead.name == "Rohan Patil").first()
            lead2 = db.query(Lead).filter(Lead.name == "Sneha Sharma").first()
            projects = [
                Project(name="Green Valley Solar Residence", category="Residential", location="Pune, Maharashtra", capacity="12 kW", capacity_kw=12.0, status="In Progress", customer_id=cust1.id if cust1 else None, source_lead_id=lead1.id if lead1 else None, image_url="https://placehold.co/400x280/E8F0EC/1F5C3E?text=Residential+Project", is_public=True),
                Project(name="Apex Logistics Hub", category="Commercial", location="Navi Mumbai, Maharashtra", capacity="250 kW", capacity_kw=250.0, status="Completed", customer_id=cust2.id if cust2 else None, source_lead_id=lead2.id if lead2 else None, image_url="https://placehold.co/400x280/FDF3E0/1F5C3E?text=Commercial+Project", is_public=True),
                Project(name="Summit Steel Heavy Microgrid", category="Industrial", location="Nagpur, Maharashtra", capacity="750 kW", capacity_kw=750.0, status="Planning", image_url="https://placehold.co/400x280/E9EEF5/1F5C3E?text=Industrial+Project", is_public=True),
                Project(name="Skyline Eco Apartments", category="Residential", location="Bengaluru, Karnataka", capacity="45 kW", capacity_kw=45.0, status="Completed", image_url="https://placehold.co/400x280/E8F0EC/1F5C3E?text=Residential+Project", is_public=True),
                Project(name="Horizon Tech Park Array", category="Commercial", location="Hyderabad, Telangana", capacity="180 kW", capacity_kw=180.0, status="Completed", image_url="https://placehold.co/400x280/FDF3E0/1F5C3E?text=Commercial+Project", is_public=True),
                Project(name="Precision Motors Solar Plant", category="Industrial", location="Ahmedabad, Gujarat", capacity="1.2 MW", capacity_kw=1200.0, status="In Progress", image_url="https://placehold.co/400x280/E9EEF5/1F5C3E?text=Industrial+Project", is_public=True),
            ]
            db.add_all(projects)
            db.commit()

        # 5. Seed Site Surveys
        if db.query(SiteSurvey).count() == 0:
            logger.info("Seeding site surveys...")
            cust_by_name = {c.name: c.id for c in db.query(Customer).all()}
            lead_by_cust = {l.customer_id: l.id for l in db.query(Lead).filter(Lead.customer_id.isnot(None)).all()}
            surveys = [
                SiteSurvey(customer_name="Rohan Patil", location="Mumbai", property_type="Residential", survey_date="15 Sep 2026", time_slot="10:00 AM", assigned_to="Rahul", status="Scheduled", customer_id=cust_by_name.get("Rohan Patil"), lead_id=lead_by_cust.get(cust_by_name.get("Rohan Patil"))),
                SiteSurvey(customer_name="Sneha Sharma", location="Pune", property_type="Commercial", survey_date="16 Sep 2026", time_slot="11:30 AM", assigned_to="Priya", status="Completed", customer_id=cust_by_name.get("Sneha Sharma"), lead_id=lead_by_cust.get(cust_by_name.get("Sneha Sharma"))),
                SiteSurvey(customer_name="Amit Verma", location="Nashik", property_type="Residential", survey_date="17 Sep 2026", time_slot="02:00 PM", assigned_to="Karan", status="Scheduled", customer_id=cust_by_name.get("Amit Verma"), lead_id=lead_by_cust.get(cust_by_name.get("Amit Verma"))),
                SiteSurvey(customer_name="Priya Desai", location="Thane", property_type="Industrial", survey_date="18 Sep 2026", time_slot="10:30 AM", assigned_to="Neha", status="In Progress", customer_id=cust_by_name.get("Priya Desai"), lead_id=lead_by_cust.get(cust_by_name.get("Priya Desai"))),
                SiteSurvey(customer_name="Karan Mehta", location="Mumbai", property_type="Residential", survey_date="19 Sep 2026", time_slot="01:00 PM", assigned_to="Rahul", status="Completed", customer_id=cust_by_name.get("Karan Mehta"), lead_id=lead_by_cust.get(cust_by_name.get("Karan Mehta"))),
                SiteSurvey(customer_name="Neha Gupta", location="Pune", property_type="Residential", survey_date="20 Sep 2026", time_slot="03:00 PM", assigned_to="Priya", status="Scheduled", customer_id=cust_by_name.get("Neha Gupta"), lead_id=lead_by_cust.get(cust_by_name.get("Neha Gupta"))),
                SiteSurvey(customer_name="Vikram Singh", location="Nagpur", property_type="Commercial", survey_date="21 Sep 2026", time_slot="11:00 AM", assigned_to="Karan", status="Cancelled", customer_id=cust_by_name.get("Vikram Singh"), lead_id=lead_by_cust.get(cust_by_name.get("Vikram Singh"))),
                SiteSurvey(customer_name="Anjali Kulkarni", location="Solapur", property_type="Residential", survey_date="22 Sep 2026", time_slot="04:00 PM", assigned_to="Neha", status="Scheduled", customer_id=cust_by_name.get("Anjali Kulkarni"), lead_id=lead_by_cust.get(cust_by_name.get("Anjali Kulkarni"))),
            ]
            db.add_all(surveys)
            db.commit()

        # 6. Seed Blogs
        if db.query(BlogPost).count() == 0:
            logger.info("Seeding blog posts...")
            posts = [
                BlogPost(title="Understanding Solar Microgrids: The Future of Energy Independence", slug="understanding-solar-microgrids", category="Technology", status="Published", author="Admin", date="Sep 12, 2026", excerpt="Discover how battery storage paired with high-efficiency rooftop solar arrays creates self-sustaining microgrids during utility grid outages.", cover_image="https://placehold.co/600x400/EFF3EC/1F5C3E?text=Technology+Article", read_time="6 min read"),
                BlogPost(title="10 Simple Ways Solar Panels Lower Your Heating & Cooling Bills", slug="10-ways-solar-lowers-bills", category="Savings", status="Published", author="Elena Rostova", date="Sep 08, 2026", excerpt="Optimize your home's HVAC consumption by pairing smart thermostats with peak solar generation hours for maximum ROI.", cover_image="https://placehold.co/600x400/EFF3EC/1F5C3E?text=Savings+Article", read_time="4 min read"),
                BlogPost(title="Guide to 2026 Solar Tax Incentives and Federal Rebates", slug="guide-to-2026-solar-tax-incentives", category="Policy", status="Published", author="Marcus Vance", date="Sep 01, 2026", excerpt="Navigate the updated clean energy tax credit policies to save up to 30% on your system installation costs.", cover_image="https://placehold.co/600x400/EFF3EC/1F5C3E?text=Policy+Guide", read_time="5 min read"),
                BlogPost(title="Seasonal Maintenance Checklist for Commercial Solar Installations", slug="seasonal-maintenance-checklist", category="Maintenance", status="Draft", author="Admin", date="Aug 28, 2026", excerpt="Essential advice for seasonal panel cleaning, shade mitigation, inverter diagnostics, and wire inspection.", cover_image="https://placehold.co/600x400/EFF3EC/1F5C3E?text=Maintenance+Checklist", read_time="3 min read"),
                BlogPost(title="EV Charging at Home: Integrating Solar Panels with Electric Vehicles", slug="ev-charging-at-home", category="Guides", status="Published", author="Sarah Jenkins", date="Aug 22, 2026", excerpt="Calculate the exact solar kilowatt capacity needed to charge your electric vehicle using 100% clean, self-generated power.", cover_image="https://placehold.co/600x400/EFF3EC/1F5C3E?text=EV+Charging", read_time="6 min read"),
                BlogPost(title="How Apex Logistics Cut Energy Overhead by 65% with Rooftop Solar", slug="how-apex-logistics-cut-energy-overhead", category="Case Study", status="Draft", author="David Chen", date="Aug 15, 2026", excerpt="A deep dive into how a 500 kW rooftop solar array transformed operating margins and cash flow for a regional hub.", cover_image="https://placehold.co/600x400/EFF3EC/1F5C3E?text=Case+Study", read_time="5 min read"),
            ]
            db.add_all(posts)
            db.commit()

        # 7. Seed FAQs
        if db.query(FAQ).count() == 0:
            logger.info("Seeding FAQs...")
            faqs = [
                FAQ(question="How long does a typical solar panel installation take?", answer="Most residential installations take 1 to 3 days. Commercial projects take 1 to 3 weeks.", category="Installation", display_order=1, is_published=True),
                FAQ(question="Will my property remain connected to the electrical grid?", answer="Yes, your system remains connected via a net meter for power credits.", category="Grid & Metering", display_order=2, is_published=True),
                FAQ(question="What maintenance is required for rooftop solar panels?", answer="Solar panels require minimal maintenance, mostly occasional cleaning and annual inspection.", category="Maintenance", display_order=3, is_published=True),
                FAQ(question="How much can I save on my electricity bill each month?", answer="Depending on roof space and sunlight, customers typically reduce electric bills by 70% to 90%.", category="Savings", display_order=4, is_published=True),
                FAQ(question="Are government subsidies and tax credits available in 2026?", answer="Yes, current PM Surya Ghar and state rooftop solar schemes provide substantial upfront capital subsidies.", category="Policy", display_order=5, is_published=True),
            ]
            db.add_all(faqs)
            db.commit()

        # 8. Seed Calculator Submissions & Settings
        if db.query(CalculatorSubmission).count() == 0:
            logger.info("Seeding calculator submissions...")
            subs = [
                CalculatorSubmission(name="Rajesh Sharma", phone="+91 98765 43210", property_type="Residential", monthly_bill=8500.0, roof_area=650.0, system_size_kw=6.5, annual_savings=73440.0, payback_years=4.8, co2_tons=7.8, date="2026-09-15"),
                CalculatorSubmission(name="SunTech Logistics", phone="+91 98123 45678", property_type="Industrial", monthly_bill=65000.0, roof_area=5200.0, system_size_kw=52.0, annual_savings=561600.0, payback_years=5.1, co2_tons=62.4, date="2026-09-14"),
                CalculatorSubmission(name="Ananya Gupta", phone="+91 97654 32109", property_type="Residential", monthly_bill=4200.0, roof_area=350.0, system_size_kw=3.2, annual_savings=36288.0, payback_years=4.9, co2_tons=3.8, date="2026-09-12"),
                CalculatorSubmission(name="GreenPlaza Retail", phone="+91 99887 76655", property_type="Commercial", monthly_bill=28000.0, roof_area=2100.0, system_size_kw=22.0, annual_savings=237600.0, payback_years=5.1, co2_tons=26.4, date="2026-09-10"),
                CalculatorSubmission(name="Vikram Malhotra", phone="+91 96543 21098", property_type="Residential", monthly_bill=12000.0, roof_area=950.0, system_size_kw=9.5, annual_savings=102600.0, payback_years=5.1, co2_tons=11.4, date="2026-09-08"),
            ]
            db.add_all(subs)
            db.commit()

        if db.query(CalculatorSettings).count() == 0:
            logger.info("Seeding calculator settings...")
            calc_settings = CalculatorSettings(
                electricity_rate=8.0,
                generation_per_kw=120.0,
                installation_cost_per_kw=55000.0,
                bill_offset_percent=85.0,
            )
            db.add(calc_settings)
            db.commit()

        # 9. Seed System Settings
        if db.query(SystemSettings).count() == 0:
            logger.info("Seeding system settings...")
            sys_settings = SystemSettings(
                company_name="SOLARA Energy Solutions",
                support_email="support@solara.com",
                email_notifications=True,
                sms_notifications=False,
                lead_alerts=True,
                two_factor_auth=False,
            )
            db.add(sys_settings)
            db.commit()

        logger.info("Demo database seeding completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
