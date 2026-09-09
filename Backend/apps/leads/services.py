"""Lead-side notifications.

Kept out of the view so the delivery mechanism (console in dev, a real
mail/SMS backend at go-live) can be swapped in one place.
"""

from django.conf import settings
from django.core.mail import send_mail


def notify_admin_of_lead(lead):
    """Email the platform inbox that a new enquiry has come in.

    Handles both provider-onboarding and general contact enquiries — the copy
    adapts to ``lead.kind``. Uses ``DEFAULT_FROM_EMAIL`` as the recipient for
    now (there is no separate admin address configured yet) and never fails the
    request if mail is down.
    """
    from .models import ProviderLead

    if lead.kind == ProviderLead.Kind.CONTACT:
        subject = f"New contact enquiry: {lead.contact_name}"
        intro = "Someone has sent a message through the Bimaya contact page."
        follow_up = "Review this message in the admin panel and reply to the sender."
        company_line = ""
    else:
        subject = f"New provider enquiry: {lead.company_name}"
        intro = "A new insurance provider has asked to onboard to Bimaya."
        follow_up = (
            "Review this lead in the admin panel, then contact the company to "
            "onboard them."
        )
        company_line = f"Company:  {lead.company_name}\n"

    body = (
        f"{intro}\n\n"
        f"{company_line}"
        f"Contact:  {lead.contact_name}\n"
        f"Email:    {lead.email}\n"
        f"Phone:    {lead.phone or '—'}\n\n"
        f"Message:\n{lead.message or '—'}\n\n"
        f"{follow_up}\n\n"
        "— Bimaya"
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.DEFAULT_FROM_EMAIL],
        fail_silently=True,
    )
