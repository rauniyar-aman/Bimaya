"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { FileInput } from "@/components/ui/file-input";
import { Input } from "@/components/ui/input";
import { ROLE_LABELS, displayName, initials } from "@/lib/user";
import { type AuthUser, errorMessage, fieldErrors } from "@/lib/api";

export function ProfileForm() {
  const { user, authFetch, reloadUser } = useAuth();

  // Only rendered behind `RequireAuth`, so the user is already loaded and the
  // inputs can be seeded straight from it.
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [saved, setSaved] = useState(false);
  const [pending, setPending] = useState(false);

  // Avatar uploads happen immediately (not on the details form submit), so they
  // carry their own state. `pickerKey` remounts the file picker after each
  // change to clear its transient preview.
  const [avatarError, setAvatarError] = useState("");
  const [avatarPending, setAvatarPending] = useState(false);
  const [pickerKey, setPickerKey] = useState(0);

  if (!user) return null;

  const dirty =
    fullName.trim() !== (user.full_name ?? "") ||
    phone.trim() !== (user.phone ?? "");

  async function handleAvatarFile(file: File | null) {
    // The picker also fires `null` when its own selection is cleared; only an
    // actual file means "upload this".
    if (!file) return;
    setAvatarError("");
    setAvatarPending(true);

    const body = new FormData();
    body.append("avatar", file);
    try {
      await authFetch<AuthUser>("/auth/me/", { method: "PATCH", form: body });
      await reloadUser();
    } catch (error) {
      setAvatarError(
        errorMessage(error, "We could not update your photo. Please try again."),
      );
    } finally {
      setAvatarPending(false);
      setPickerKey((key) => key + 1);
    }
  }

  async function handleRemoveAvatar() {
    setAvatarError("");
    setAvatarPending(true);
    try {
      // A JSON null clears the stored image (the field allows it server-side).
      await authFetch<AuthUser>("/auth/me/", {
        method: "PATCH",
        json: { avatar: null },
      });
      await reloadUser();
    } catch (error) {
      setAvatarError(
        errorMessage(error, "We could not remove your photo. Please try again."),
      );
    } finally {
      setAvatarPending(false);
      setPickerKey((key) => key + 1);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    setSaved(false);
    setPending(true);

    try {
      await authFetch<AuthUser>("/auth/me/", {
        method: "PATCH",
        json: { full_name: fullName.trim(), phone: phone.trim() },
      });
      await reloadUser();
      setSaved(true);
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(
        errorMessage(error, "We could not save your details. Please try again."),
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your details</CardTitle>
        <p className="mt-1.5 text-sm text-muted">
          Your email address and account type ({ROLE_LABELS[user.role]}) cannot
          be changed here — contact support if either is wrong.
        </p>
      </CardHeader>

      <CardContent>
        <div className="mb-6 border-b border-line pb-6">
          <p className="text-sm font-medium text-ink">Profile picture</p>
          <div className="mt-3 flex items-start gap-4">
            <Avatar
              src={user.avatar}
              fallback={initials(user)}
              alt={displayName(user)}
              size="lg"
            />
            <div className="min-w-0 flex-1">
              <FileInput
                key={pickerKey}
                id="profile_avatar"
                onFile={handleAvatarFile}
                disabled={avatarPending}
              />
              {user.avatar && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="mt-2"
                  disabled={avatarPending}
                  onClick={handleRemoveAvatar}
                >
                  Remove photo
                </Button>
              )}
            </div>
          </div>
          {avatarError && (
            <Alert variant="error" className="mt-3">
              {avatarError}
            </Alert>
          )}
        </div>

        {saved && (
          <Alert variant="success" className="mb-5">
            Your details have been saved.
          </Alert>
        )}

        {formError && (
          <Alert variant="error" className="mb-5">
            {formError}
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <Field label="Email address" htmlFor="profile_email">
            <Input id="profile_email" value={user.email} disabled readOnly />
          </Field>

          <Field
            label="Full name"
            htmlFor="profile_full_name"
            error={errors.full_name}
          >
            <Input
              id="profile_full_name"
              name="full_name"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              aria-invalid={Boolean(errors.full_name)}
            />
          </Field>

          <Field
            label="Mobile number"
            htmlFor="profile_phone"
            error={errors.phone}
            hint="Used for policy and renewal reminders."
          >
            <Input
              id="profile_phone"
              name="phone"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="98XXXXXXXX"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              aria-invalid={Boolean(errors.phone)}
            />
          </Field>

          <Button type="submit" loading={pending} disabled={!dirty}>
            {pending ? "Saving…" : "Save changes"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
