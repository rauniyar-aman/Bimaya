"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { useProviderPortal } from "@/components/provider/provider-portal";
import { Alert } from "@/components/ui/alert";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { FileInput } from "@/components/ui/file-input";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  errorCode,
  errorMessage,
  fieldErrors,
  type KycStatus,
  type ProviderProfile,
  type ProviderProfileInput,
} from "@/lib/api";

const KYC_META: Record<
  KycStatus,
  { variant: "active" | "pending" | "failed"; label: string }
> = {
  PENDING: { variant: "pending", label: "KYC pending" },
  VERIFIED: { variant: "active", label: "KYC verified" },
  REJECTED: { variant: "failed", label: "KYC rejected" },
};

/** Up to two initials from the company name, for the logo placeholder. */
function companyInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.slice(0, 2).map((part) => part[0]);
  return letters.join("").toUpperCase() || "?";
}

type LoadState =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; profile: ProviderProfile | null };

export function ProviderProfileForm() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<LoadState>({ phase: "loading" });

  useEffect(() => {
    let cancelled = false;
    api.provider
      .getProfile(authFetch)
      .then((profile) => {
        if (!cancelled) setState({ phase: "ready", profile });
      })
      .catch((error) => {
        if (cancelled) return;
        // No profile yet is the expected first-run case, not an error.
        if (errorCode(error) === "provider_profile_missing")
          setState({ phase: "ready", profile: null });
        else setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch]);

  if (state.phase === "loading") {
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner className="h-6 w-6 text-brand-500" />
      </div>
    );
  }

  if (state.phase === "error") {
    return (
      <Alert variant="error">
        We could not load your provider profile. Please refresh and try again.
      </Alert>
    );
  }

  // Remount the fields when switching identity so state re-seeds cleanly.
  return (
    <ProfileFields
      key={state.profile?.id ?? "new"}
      profile={state.profile}
    />
  );
}

function ProfileFields({ profile }: { profile: ProviderProfile | null }) {
  const { authFetch } = useAuth();
  const { refresh } = useProviderPortal();
  const router = useRouter();
  const isCreate = profile === null;
  // Editing the company profile needs the `company.edit` permission (Owner and
  // Company Admin); everyone else sees it read-only. The backend enforces the
  // same rule — this only controls what the UI offers.
  const canEdit = isCreate || profile.my_permissions.includes("company.edit");

  const [companyName, setCompanyName] = useState(profile?.company_name ?? "");
  const [registrationNumber, setRegistrationNumber] = useState(
    profile?.registration_number ?? "",
  );
  const [website, setWebsite] = useState(profile?.website ?? "");
  const [supportEmail, setSupportEmail] = useState(profile?.support_email ?? "");
  const [supportPhone, setSupportPhone] = useState(profile?.support_phone ?? "");
  const [description, setDescription] = useState(profile?.description ?? "");

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [saved, setSaved] = useState(false);
  const [pending, setPending] = useState(false);

  // The logo uploads immediately (not on the details-form submit), so it carries
  // its own state. `logo` mirrors the saved image so the preview updates at once;
  // `pickerKey` remounts the file picker after each change to clear its preview.
  const [logo, setLogo] = useState<string | null>(profile?.logo ?? null);
  const [logoError, setLogoError] = useState("");
  const [logoPending, setLogoPending] = useState(false);
  const [pickerKey, setPickerKey] = useState(0);

  async function handleLogoFile(file: File | null) {
    // The picker also fires `null` when its selection is cleared; only a real
    // file means "upload this".
    if (!file) return;
    setLogoError("");
    setLogoPending(true);

    const body = new FormData();
    body.append("logo", file);
    try {
      const updated = await api.provider.saveLogo(authFetch, body);
      setLogo(updated.logo);
      // Keep the portal shell's cached profile (dashboard header) in step.
      refresh();
    } catch (error) {
      setLogoError(
        errorMessage(error, "We could not update your logo. Please try again."),
      );
    } finally {
      setLogoPending(false);
      setPickerKey((key) => key + 1);
    }
  }

  async function handleRemoveLogo() {
    setLogoError("");
    setLogoPending(true);
    try {
      const updated = await api.provider.removeLogo(authFetch);
      setLogo(updated.logo);
      refresh();
    } catch (error) {
      setLogoError(
        errorMessage(error, "We could not remove your logo. Please try again."),
      );
    } finally {
      setLogoPending(false);
      setPickerKey((key) => key + 1);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    setSaved(false);
    setPending(true);

    const payload: ProviderProfileInput = {
      company_name: companyName.trim(),
      registration_number: registrationNumber.trim(),
      description: description.trim(),
      website: website.trim(),
      support_email: supportEmail.trim(),
      support_phone: supportPhone.trim(),
    };

    try {
      await api.provider.saveProfile(authFetch, payload, isCreate ? "PUT" : "PATCH");
      // Refresh the portal shell so the nav, dashboard and cached profile pick
      // up the new details (and, on first setup, switch out of the setup state).
      refresh();
      if (isCreate) {
        router.push("/provider");
        return;
      }
      setSaved(true);
      setPending(false);
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(
        errorMessage(error, "We could not save your profile. Please try again."),
      );
      setPending(false);
    }
  }

  const kyc = profile ? KYC_META[profile.kyc_status] : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {isCreate ? "Set up your provider profile" : "Company profile"}
        </CardTitle>
        <p className="mt-1.5 text-sm text-muted">
          {isCreate
            ? "Tell customers who you are. You can list policies once this is saved; our team approves new providers before their plans go public."
            : "Keep your company details up to date. Approval and KYC status are managed by our team."}
        </p>
        {profile && kyc && (
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusPill status={profile.is_approved ? "active" : "pending"}>
              {profile.is_approved ? "Approved to sell" : "Awaiting approval"}
            </StatusPill>
            <StatusPill status={kyc.variant}>{kyc.label}</StatusPill>
          </div>
        )}
      </CardHeader>

      <CardContent>
        {!isCreate && (
          <div className="mb-6 border-b border-line pb-6">
            <p className="text-sm font-medium text-ink">Company logo</p>
            <div className="mt-3 flex items-start gap-4">
              <Avatar
                src={logo}
                fallback={companyInitials(companyName)}
                alt={`${companyName} logo`}
                size="lg"
                shape="square"
              />
              {canEdit && (
                <div className="min-w-0 flex-1">
                  <FileInput
                    key={pickerKey}
                    id="provider_logo"
                    onFile={handleLogoFile}
                    disabled={logoPending}
                  />
                  {logo && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="mt-2"
                      disabled={logoPending}
                      onClick={handleRemoveLogo}
                    >
                      Remove logo
                    </Button>
                  )}
                </div>
              )}
            </div>
            {logoError && (
              <Alert variant="error" className="mt-3">
                {logoError}
              </Alert>
            )}
          </div>
        )}

        {!canEdit && (
          <Alert variant="info" className="mb-5">
            You do not have permission to edit the company profile. These details
            are shown to you read-only.
          </Alert>
        )}
        {saved && (
          <Alert variant="success" className="mb-5">
            Your profile has been saved.
          </Alert>
        )}
        {formError && (
          <Alert variant="error" className="mb-5">
            {formError}
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <fieldset disabled={!canEdit} className="space-y-4 border-0 p-0 disabled:opacity-70">
          <Field
            label="Company name"
            htmlFor="company_name"
            error={errors.company_name}
            required
          >
            <Input
              id="company_name"
              name="company_name"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Everest Life Insurance"
              aria-invalid={Boolean(errors.company_name)}
            />
          </Field>

          <Field
            label="Registration number"
            htmlFor="registration_number"
            error={errors.registration_number}
            hint="Your Insurance Board of Nepal registration, if you have one."
          >
            <Input
              id="registration_number"
              name="registration_number"
              value={registrationNumber}
              onChange={(e) => setRegistrationNumber(e.target.value)}
              aria-invalid={Boolean(errors.registration_number)}
            />
          </Field>

          <Field
            label="About your company"
            htmlFor="description"
            error={errors.description}
          >
            <Textarea
              id="description"
              name="description"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A short introduction customers will see on your plans."
              aria-invalid={Boolean(errors.description)}
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Website" htmlFor="website" error={errors.website}>
              <Input
                id="website"
                name="website"
                type="url"
                inputMode="url"
                value={website}
                onChange={(e) => setWebsite(e.target.value)}
                placeholder="https://example.com.np"
                aria-invalid={Boolean(errors.website)}
              />
            </Field>

            <Field
              label="Support email"
              htmlFor="support_email"
              error={errors.support_email}
            >
              <Input
                id="support_email"
                name="support_email"
                type="email"
                inputMode="email"
                value={supportEmail}
                onChange={(e) => setSupportEmail(e.target.value)}
                placeholder="care@example.com.np"
                aria-invalid={Boolean(errors.support_email)}
              />
            </Field>
          </div>

          <Field
            label="Support phone"
            htmlFor="support_phone"
            error={errors.support_phone}
            className="sm:max-w-xs"
          >
            <Input
              id="support_phone"
              name="support_phone"
              type="tel"
              inputMode="tel"
              value={supportPhone}
              onChange={(e) => setSupportPhone(e.target.value)}
              placeholder="01-XXXXXXX"
              aria-invalid={Boolean(errors.support_phone)}
            />
          </Field>
          </fieldset>

          {canEdit && (
            <Button type="submit" loading={pending}>
              {isCreate ? "Create profile" : "Save changes"}
            </Button>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
