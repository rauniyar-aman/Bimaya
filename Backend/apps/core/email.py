"""Branded transactional email.

One place builds the plain-text **and** HTML version of every transactional
email — OTP codes and notifications — so they carry the Bimaya brand and look
consistent. Clients that can't render HTML fall back to the plain-text part.

Delivery is best-effort: :func:`send_branded_email` passes ``fail_silently`` so
a mail outage can never break a signup, a payment or a claim decision (the
callers rely on this). Styling is inlined because email clients strip
``<style>`` blocks and external CSS.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import escape

# Bimaya brand palette (kept in sync with the frontend theme tokens).
_BRAND = "#1a5493"   # brand-600
_INK = "#1f2937"
_MUTED = "#6b7280"
_SURFACE = "#f8fafc"
_LINE = "#e5e7eb"
_FONT = "Arial, Helvetica, sans-serif"


def _absolute(url):
    """Turn an in-app relative path into a full link for email clients."""
    if url and url.startswith("/"):
        return settings.FRONTEND_URL.rstrip("/") + url
    return url


def send_branded_email(*, subject, to, heading, paragraphs, code=None, cta=None):
    """Send one branded email to ``to``.

    ``paragraphs`` is a list of plain strings (one ``<p>`` each). ``code`` shows
    a large, spaced-out value to copy (the OTP). ``cta`` is an optional
    ``(label, url)`` button; a relative ``url`` is made absolute against
    ``FRONTEND_URL``. Never raises.
    """
    send_mail(
        subject=subject,
        message=_text_body(heading, paragraphs, code, cta),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to],
        fail_silently=True,
        html_message=_html_body(heading, paragraphs, code, cta),
    )


def _text_body(heading, paragraphs, code, cta):
    lines = [heading, ""]
    for paragraph in paragraphs:
        lines += [paragraph, ""]
    if code:
        lines += [f"    {code}", ""]
    if cta:
        label, url = cta
        lines += [f"{label}: {_absolute(url)}", ""]
    lines.append("— Bimaya")
    return "\n".join(lines)


def _html_body(heading, paragraphs, code, cta):
    blocks = [
        f'<h1 style="margin:0 0 16px;font-size:20px;line-height:1.3;'
        f'color:{_INK};font-family:{_FONT};">{escape(heading)}</h1>'
    ]
    for paragraph in paragraphs:
        blocks.append(
            f'<p style="margin:0 0 16px;font-size:15px;line-height:1.6;'
            f'color:{_INK};font-family:{_FONT};">{escape(paragraph)}</p>'
        )
    if code:
        blocks.append(
            f'<div style="margin:24px 0;padding:18px;text-align:center;'
            f'background:{_SURFACE};border:1px solid {_LINE};border-radius:12px;">'
            f'<span style="font-family:\'Courier New\',monospace;font-size:32px;'
            f'font-weight:bold;letter-spacing:8px;color:{_BRAND};">'
            f"{escape(code)}</span></div>"
        )
    if cta:
        label, url = cta
        blocks.append(
            f'<p style="margin:24px 0 0;">'
            f'<a href="{escape(_absolute(url))}" '
            f'style="display:inline-block;padding:12px 24px;background:{_BRAND};'
            f'color:#ffffff;text-decoration:none;border-radius:8px;font-size:15px;'
            f'font-weight:600;font-family:{_FONT};">{escape(label)}</a></p>'
        )
    inner = "".join(blocks)
    return (
        f'<!DOCTYPE html><html><body style="margin:0;padding:0;background:{_SURFACE};">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{_SURFACE};padding:24px 0;"><tr><td align="center">'
        f'<table role="presentation" width="480" cellpadding="0" cellspacing="0" '
        f'style="width:480px;max-width:100%;background:#ffffff;border:1px solid '
        f'{_LINE};border-radius:16px;overflow:hidden;">'
        f'<tr><td style="background:{_BRAND};padding:20px 32px;">'
        f'<span style="font-family:{_FONT};font-size:20px;font-weight:bold;'
        f'color:#ffffff;letter-spacing:0.5px;">Bimaya</span></td></tr>'
        f'<tr><td style="padding:32px;">{inner}</td></tr>'
        f'<tr><td style="padding:18px 32px;border-top:1px solid {_LINE};">'
        f'<p style="margin:0;font-size:12px;line-height:1.5;color:{_MUTED};'
        f'font-family:{_FONT};">Bimaya — Nepal\'s digital insurance marketplace. '
        f"This is an automated message; please don't reply.</p>"
        f"</td></tr></table></td></tr></table></body></html>"
    )
