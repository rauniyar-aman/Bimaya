"""Lead-side notifications.

Kept out of the view so the delivery mechanism (console in dev, a real
mail/SMS backend at go-live) can be swapped in one place.
"""

from django.conf import settings
from django.core.mail import send_mail


def notify_admin_of_lead(lead):
    """Email the platform inbox that a new provider wants to onboard.

    Uses ``DEFAULT_FROM_EMAIL`` as the recipient for now — there is no separate
    admin address configured yet. Never fails the request if mail is down.
    """
    body = (
        "A new insurance provider has asked to onboard to Bimaya.\n\n"
        f"Company:  {lead.company_name}\n"
        f"Contact:  {lead.contact_name}\n"
        f"Email:    {lead.email}\n"
        f"Phone:    {lead.phone or '—'}\n\n"
        f"Message:\n{lead.message or '—'}\n\n"
        "Review this lead in the admin panel, then contact the company to "
        "onboard them.\n\n"
        "— Bimaya"
    )
    send_mail(
        subject=f"New provider enquiry: {lead.company_name}",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.DEFAULT_FROM_EMAIL],
        fail_silently=True,
    )
