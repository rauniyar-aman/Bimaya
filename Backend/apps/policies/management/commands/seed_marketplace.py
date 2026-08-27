"""Seed the marketplace with demo categories, providers and policies.

Idempotent: safe to run repeatedly. Every record is looked up before it is
created, so re-running only fills in what is missing.

    python manage.py seed_marketplace
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import Provider

User = get_user_model()

PROVIDER_PASSWORD = "Provider#2026"

CATEGORIES = [
    {
        "name": "Life",
        "slug": "life",
        "icon": "heart",
        "order": 1,
        "description": "Protect your family's future with term, whole-life and endowment cover.",
    },
    {
        "name": "Health",
        "slug": "health",
        "icon": "health",
        "order": 2,
        "description": "Hospitalisation, critical-illness and family health plans.",
    },
    {
        "name": "Vehicle",
        "slug": "vehicle",
        "icon": "car",
        "order": 3,
        "description": "Comprehensive and third-party cover for two-wheelers and cars.",
    },
    {
        "name": "Travel",
        "slug": "travel",
        "icon": "plane",
        "order": 4,
        "description": "Domestic and international travel protection for every trip.",
    },
]

PROVIDERS = [
    {
        "email": "everest.life@bimaya.test",
        "company_name": "Everest Life Assurance",
        "full_name": "Everest Life Assurance",
        "registration_number": "NIA-LIFE-001",
        "support_email": "care@everestlife.test",
        "support_phone": "+977-1-4001001",
        "website": "https://everestlife.test",
        "description": "One of Nepal's trusted life insurers, protecting families since 1998.",
    },
    {
        "email": "himalayan.health@bimaya.test",
        "company_name": "Himalayan Health Insurance",
        "full_name": "Himalayan Health Insurance",
        "registration_number": "NIA-HLTH-014",
        "support_email": "care@himalayanhealth.test",
        "support_phone": "+977-1-4002002",
        "website": "https://himalayanhealth.test",
        "description": "Health-first cover with a nationwide network of cashless hospitals.",
    },
    {
        "email": "sagarmatha.general@bimaya.test",
        "company_name": "Sagarmatha General Insurance",
        "full_name": "Sagarmatha General Insurance",
        "registration_number": "NIA-GEN-027",
        "support_email": "care@sagarmatha.test",
        "support_phone": "+977-1-4003003",
        "website": "https://sagarmatha.test",
        "description": "Motor and travel specialists with fast, fair claim settlement.",
    },
    {
        "email": "annapurna.insurance@bimaya.test",
        "company_name": "Annapurna Insurance",
        "full_name": "Annapurna Insurance",
        "registration_number": "NIA-GEN-041",
        "support_email": "care@annapurna.test",
        "support_phone": "+977-1-4004004",
        "website": "https://annapurna.test",
        "description": "Broad protection across life, health and motor lines of business.",
    },
]

# Each policy references a provider by email and a category by slug.
POLICIES = [
    # --- Life ---
    {
        "provider": "everest.life@bimaya.test",
        "category": "life",
        "name": "Everest Term Life Shield",
        "summary": "High cover, low premium term life for young earners.",
        "description": "A pure protection term plan that pays a lump sum to your nominees, keeping your family financially secure if the unexpected happens.",
        "premium": "12000.00",
        "premium_frequency": Policy.Frequency.YEARLY,
        "coverage_amount": "5000000.00",
        "term_months": 240,
        "min_age": 18,
        "max_age": 60,
        "features": ["Sum assured up to NPR 50 lakh", "Optional accidental death benefit", "Tax benefits on premium"],
        "add_ons": ["Accidental death rider", "Waiver of premium"],
        "is_featured": True,
    },
    {
        "provider": "everest.life@bimaya.test",
        "category": "life",
        "name": "Everest Whole Life Secure",
        "summary": "Lifelong cover with a maturity payout.",
        "description": "Whole-life protection that combines a guaranteed death benefit with savings that build over the life of the policy.",
        "premium": "25000.00",
        "premium_frequency": Policy.Frequency.YEARLY,
        "coverage_amount": "3000000.00",
        "term_months": 360,
        "min_age": 18,
        "max_age": 55,
        "features": ["Cover up to age 99", "Guaranteed maturity benefit", "Loan against policy"],
        "add_ons": ["Critical illness rider"],
        "is_featured": False,
    },
    {
        "provider": "annapurna.insurance@bimaya.test",
        "category": "life",
        "name": "Annapurna Endowment Plan",
        "summary": "Protection plus disciplined savings.",
        "description": "An endowment plan that returns your sum assured with bonuses on maturity, or pays your family on an earlier claim.",
        "premium": "30000.00",
        "premium_frequency": Policy.Frequency.YEARLY,
        "coverage_amount": "2000000.00",
        "term_months": 180,
        "min_age": 21,
        "max_age": 55,
        "features": ["Maturity + death benefit", "Annual bonuses", "Tax-efficient savings"],
        "add_ons": ["Accidental death rider"],
        "is_featured": False,
    },
    # --- Health ---
    {
        "provider": "himalayan.health@bimaya.test",
        "category": "health",
        "name": "Himalayan Family Health Care",
        "summary": "Cashless hospitalisation for the whole family.",
        "description": "Covers hospitalisation, surgery and day-care procedures for you and your dependents across a nationwide hospital network.",
        "premium": "18000.00",
        "premium_frequency": Policy.Frequency.YEARLY,
        "coverage_amount": "1000000.00",
        "term_months": 12,
        "min_age": 1,
        "max_age": 65,
        "features": ["Cashless network hospitals", "Covers spouse and children", "No claim bonus"],
        "add_ons": ["Maternity cover", "Room rent upgrade"],
        "is_featured": True,
    },
    {
        "provider": "himalayan.health@bimaya.test",
        "category": "health",
        "name": "Himalayan Senior Citizen Health",
        "summary": "Designed for parents and elders.",
        "description": "Health cover tailored for senior citizens with pre-existing condition support after a short waiting period.",
        "premium": "22000.00",
        "premium_frequency": Policy.Frequency.YEARLY,
        "coverage_amount": "800000.00",
        "term_months": 12,
        "min_age": 55,
        "max_age": 80,
        "features": ["Pre-existing cover after waiting period", "Annual health check-up", "Cashless claims"],
        "add_ons": ["Domiciliary treatment"],
        "is_featured": False,
    },
    {
        "provider": "annapurna.insurance@bimaya.test",
        "category": "health",
        "name": "Annapurna Critical Illness Cover",
        "summary": "Lump sum on diagnosis of major illnesses.",
        "description": "Pays a one-time benefit on the first diagnosis of a covered critical illness so you can focus on recovery, not bills.",
        "premium": "9000.00",
        "premium_frequency": Policy.Frequency.YEARLY,
        "coverage_amount": "1500000.00",
        "term_months": 12,
        "min_age": 18,
        "max_age": 60,
        "features": ["Covers 20+ critical illnesses", "Lump-sum payout", "Premium waiver on claim"],
        "add_ons": ["Second medical opinion"],
        "is_featured": False,
    },
    # --- Vehicle ---
    {
        "provider": "sagarmatha.general@bimaya.test",
        "category": "vehicle",
        "name": "Sagarmatha Two-Wheeler Cover",
        "summary": "Affordable comprehensive cover for your bike.",
        "description": "Protects your motorcycle against accident, theft and third-party liability with quick garage claims.",
        "premium": "3500.00",
        "premium_frequency": Policy.Frequency.YEARLY,
        "coverage_amount": "250000.00",
        "term_months": 12,
        "features": ["Own-damage + third-party", "Theft protection", "Cashless garages"],
        "add_ons": ["Zero depreciation", "Pillion rider cover"],
        "is_featured": True,
    },
    {
        "provider": "sagarmatha.general@bimaya.test",
        "category": "vehicle",
        "name": "Sagarmatha Private Car Comprehensive",
        "summary": "Complete protection for your car.",
        "description": "Comprehensive motor cover for private cars including own damage, third-party liability and personal accident cover for the owner-driver.",
        "premium": "15000.00",
        "premium_frequency": Policy.Frequency.YEARLY,
        "coverage_amount": "2500000.00",
        "term_months": 12,
        "features": ["Own-damage + third-party", "Owner-driver PA cover", "24x7 roadside help"],
        "add_ons": ["Zero depreciation", "Engine protection", "Return to invoice"],
        "is_featured": False,
    },
    {
        "provider": "annapurna.insurance@bimaya.test",
        "category": "vehicle",
        "name": "Annapurna Commercial Vehicle Plan",
        "summary": "Keep your business fleet on the road.",
        "description": "Tailored cover for commercial vehicles with liability protection and fast claim turnaround to minimise downtime.",
        "premium": "28000.00",
        "premium_frequency": Policy.Frequency.YEARLY,
        "coverage_amount": "3000000.00",
        "term_months": 12,
        "features": ["Goods & passenger vehicles", "Third-party liability", "Fast claim settlement"],
        "add_ons": ["Driver & cleaner cover"],
        "is_featured": False,
    },
    # --- Travel ---
    {
        "provider": "sagarmatha.general@bimaya.test",
        "category": "travel",
        "name": "Sagarmatha Domestic Travel Guard",
        "summary": "Single-trip cover for travel within Nepal.",
        "description": "Covers trip cancellation, baggage loss and medical emergencies during domestic travel.",
        "premium": "800.00",
        "premium_frequency": Policy.Frequency.ONE_TIME,
        "coverage_amount": "200000.00",
        "term_months": 1,
        "features": ["Trip cancellation", "Baggage loss", "Emergency medical"],
        "add_ons": ["Adventure sports cover"],
        "is_featured": False,
    },
    {
        "provider": "sagarmatha.general@bimaya.test",
        "category": "travel",
        "name": "Sagarmatha International Travel Plus",
        "summary": "Worldwide protection for overseas trips.",
        "description": "Comprehensive international travel cover including emergency medical, evacuation, baggage and flight-delay benefits.",
        "premium": "4500.00",
        "premium_frequency": Policy.Frequency.ONE_TIME,
        "coverage_amount": "5000000.00",
        "term_months": 1,
        "features": ["Worldwide medical cover", "Emergency evacuation", "Flight delay benefit"],
        "add_ons": ["Adventure sports cover", "Cruise cover"],
        "is_featured": True,
    },
    {
        "provider": "everest.life@bimaya.test",
        "category": "travel",
        "name": "Everest Student Travel Abroad",
        "summary": "Health and study protection for students overseas.",
        "description": "Annual travel and health cover for students studying abroad, including study-interruption and sponsor-protection benefits.",
        "premium": "6000.00",
        "premium_frequency": Policy.Frequency.YEARLY,
        "coverage_amount": "4000000.00",
        "term_months": 12,
        "min_age": 16,
        "max_age": 40,
        "features": ["Medical cover abroad", "Study interruption", "Sponsor protection"],
        "add_ons": ["Mental health support"],
        "is_featured": False,
    },
]


class Command(BaseCommand):
    help = "Populate the marketplace with demo categories, providers and policies."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = self._seed_categories()
        providers = self._seed_providers()
        created, existing = self._seed_policies(categories, providers)

        self.stdout.write(self.style.SUCCESS("Marketplace seed complete."))
        self.stdout.write(f"  Categories: {len(categories)}")
        self.stdout.write(f"  Providers:  {len(providers)}")
        self.stdout.write(f"  Policies:   {created} created, {existing} already present")
        self.stdout.write(
            "  Demo provider logins use password: " + PROVIDER_PASSWORD
        )

    def _seed_categories(self):
        categories = {}
        for data in CATEGORIES:
            category, _ = InsuranceCategory.objects.get_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "icon": data["icon"],
                    "order": data["order"],
                    "description": data["description"],
                },
            )
            categories[data["slug"]] = category
        return categories

    def _seed_providers(self):
        providers = {}
        for data in PROVIDERS:
            user = User.objects.filter(email=data["email"]).first()
            if user is None:
                user = User.objects.create_user(
                    email=data["email"],
                    password=PROVIDER_PASSWORD,
                    full_name=data["full_name"],
                    role=User.Role.PROVIDER,
                    is_verified=True,
                )
            provider, _ = Provider.objects.get_or_create(
                user=user,
                defaults={
                    "company_name": data["company_name"],
                    "registration_number": data["registration_number"],
                    "description": data["description"],
                    "website": data["website"],
                    "support_email": data["support_email"],
                    "support_phone": data["support_phone"],
                    "kyc_status": Provider.KycStatus.VERIFIED,
                    "is_approved": True,
                },
            )
            providers[data["email"]] = provider
        return providers

    def _seed_policies(self, categories, providers):
        created = existing = 0
        for data in POLICIES:
            provider = providers[data["provider"]]
            category = categories[data["category"]]
            _, was_created = Policy.objects.get_or_create(
                provider=provider,
                name=data["name"],
                defaults={
                    "category": category,
                    "summary": data["summary"],
                    "description": data["description"],
                    "premium": Decimal(data["premium"]),
                    "premium_frequency": data["premium_frequency"],
                    "coverage_amount": Decimal(data["coverage_amount"]),
                    "term_months": data["term_months"],
                    "min_age": data.get("min_age"),
                    "max_age": data.get("max_age"),
                    "features": data["features"],
                    "add_ons": data["add_ons"],
                    "status": Policy.Status.APPROVED,
                    "is_featured": data["is_featured"],
                },
            )
            if was_created:
                created += 1
            else:
                existing += 1
        return created, existing
