"use client";

import { Suspense, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";

import { RequireAuth } from "@/components/layout/RequireAuth";
import { AvatarUploader } from "@/components/profiles/AvatarPicker";
import { Button } from "@/components/ui/Button";
import { Alert, ErrorState, Loading } from "@/components/ui/Feedback";
import { Input, Select, Textarea } from "@/components/ui/Field";
import { Badge, Card, PageTitle } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { OwnProfile, Skill } from "@/lib/api/types";
import { AVAILABILITY, label, LEVELS } from "@/lib/labels";
import { toOptions, useReferences } from "@/lib/references";
import { useApi } from "@/lib/useApi";

const fromMap = (map: Record<string, string>, empty?: string) => [
  ...(empty ? [{ value: "", label: empty }] : []),
  ...Object.entries(map).map(([value, text]) => ({ value, label: text })),
];

function ProfileForm({ profile, onSaved }: { profile: OwnProfile; onSaved: () => void }) {
  const { countries } = useReferences();
  const [form, setForm] = useState({
    display_name: profile.display_name,
    headline: profile.headline ?? "",
    bio: profile.bio ?? "",
    country: profile.country ?? "",
    city: profile.city ?? "",
    experience_level: profile.experience_level ?? "",
    availability_status: profile.availability_status ?? "NOT_AVAILABLE",
    profile_visibility: profile.profile_visibility,
    show_city: profile.show_city,
    show_availability: profile.show_availability,
    show_reputation: profile.show_reputation,
  });
  const [error, setError] = useState<ApiError | null>(null);
  const [saved, setSaved] = useState(false);
  const [pending, setPending] = useState(false);

  const update = (field: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const target = event.target as HTMLInputElement;
    setForm((previous) => ({ ...previous, [field]: target.type === "checkbox" ? target.checked : target.value }));
    setSaved(false);
  };

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await api("/profiles/me/", { method: "PATCH", body: { ...form, country: form.country || null } });
      setSaved(true);
      onSaved();
    } catch (caught) {
      setError(caught as ApiError);
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <h2 className="mb-4 font-semibold">Informations publiques</h2>
      {saved && <Alert kind="success">Profil enregistré.</Alert>}
      {error && <Alert kind="error">{error.message}</Alert>}
      <form onSubmit={submit} noValidate>
        <Input label="Nom d'affichage" value={form.display_name} onChange={update("display_name")} error={error?.field("display_name")} />
        <Input label="Titre" value={form.headline} onChange={update("headline")} placeholder="Ex. Développeuse backend Django" />
        <Textarea label="Biographie" value={form.bio} onChange={update("bio")} rows={4} maxLength={1000} />
        <div className="grid gap-x-3 sm:grid-cols-2">
          <Select label="Pays" options={[{ value: "", label: "Non renseigné" }, ...countries.map((c) => ({ value: c.code, label: c.name }))]} value={form.country} onChange={update("country")} />
          <Input label="Ville" value={form.city} onChange={update("city")} hint="Jamais d'adresse précise." />
          <Select label="Niveau déclaré" options={fromMap(LEVELS, "Non renseigné")} value={form.experience_level} onChange={update("experience_level")} />
          <Select label="Disponibilité" options={fromMap(AVAILABILITY)} value={form.availability_status} onChange={update("availability_status")} />
        </div>
        <fieldset className="mb-4 space-y-2 rounded-xl border border-line p-3 text-sm">
          <legend className="px-1 font-medium">Confidentialité</legend>
          <Select label="Visibilité du profil" options={[{ value: "PUBLIC", label: "Public" }, { value: "PRIVATE", label: "Privé" }]} value={form.profile_visibility} onChange={update("profile_visibility")} />
          <label className="flex items-center gap-2"><input type="checkbox" checked={form.show_city} onChange={update("show_city")} /> Afficher ma ville</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={form.show_availability} onChange={update("show_availability")} /> Afficher ma disponibilité</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={form.show_reputation} onChange={update("show_reputation")} /> Afficher ma réputation, mes badges et recommandations</label>
        </fieldset>
        <Button type="submit" loading={pending}>Enregistrer</Button>
      </form>
    </Card>
  );
}

function SkillsEditor({ skills, onSaved }: { skills: Skill[]; onSaved: () => void }) {
  const { technologies } = useReferences();
  const [technology, setTechnology] = useState("");
  const [level, setLevel] = useState("INTERMEDIATE");
  const [error, setError] = useState<string | null>(null);

  async function save(items: { technology: string; level: string; years_experience?: number | null; evidence_url?: string }[]) {
    setError(null);
    try {
      await api("/profiles/me/skills/", { method: "PUT", body: items });
      onSaved();
    } catch (caught) {
      setError((caught as ApiError).message);
    }
  }

  const current = skills.map((skill) => ({
    technology: skill.technology.slug,
    level: skill.level,
    years_experience: skill.years_experience,
    evidence_url: skill.evidence_url,
  }));

  return (
    <Card>
      <h2 className="mb-1 font-semibold">Compétences</h2>
      <p className="mb-4 text-xs text-muted">Niveau auto-évalué. Ajouter un lien de preuve ne rend pas une compétence « vérifiée ».</p>
      {error && <Alert kind="error">{error}</Alert>}
      <ul className="mb-4 space-y-2">
        {skills.map((skill) => (
          <li key={skill.id} className="flex items-center justify-between rounded-xl border border-line px-3 py-2 text-sm">
            <span>{skill.technology.name} · {label(LEVELS, skill.level)} <Badge>{skill.verification_label}</Badge></span>
            <button type="button" className="text-xs text-rose-700 hover:underline" onClick={() => save(current.filter((item) => item.technology !== skill.technology.slug))}>
              Retirer
            </button>
          </li>
        ))}
      </ul>
      <div className="grid gap-x-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <Select label="Technologie" options={toOptions(technologies.filter((t) => !current.some((c) => c.technology === t.slug)), "Choisir")} value={technology} onChange={(e) => setTechnology(e.target.value)} />
        <Select label="Niveau" options={fromMap(LEVELS)} value={level} onChange={(e) => setLevel(e.target.value)} />
        <div className="mb-4">
          <Button type="button" disabled={!technology} onClick={() => { save([...current, { technology, level }]); setTechnology(""); }}>Ajouter</Button>
        </div>
      </div>
    </Card>
  );
}

function SettingsContent() {
  const params = useSearchParams();
  const welcome = params.get("bienvenue") === "1";
  const photoFailed = params.get("photo") === "echec";
  const profile = useApi<OwnProfile>("/profiles/me/");
  const skills = useApi<Skill[]>("/profiles/me/skills/");

  if (profile.loading && !profile.data) return <Loading />;
  if (profile.error) return <ErrorState error={profile.error} onRetry={profile.reload} />;
  if (!profile.data) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <PageTitle title="Mon profil" subtitle="Complétez votre profil pour être trouvé par d'autres développeurs." />
      {welcome && <Alert kind="success">Bienvenue ! Votre compte est créé. Complétez votre profil quand vous le souhaitez.</Alert>}
      {photoFailed && <Alert kind="error">Votre photo n&apos;a pas pu être enregistrée. Réessayez ci-dessous.</Alert>}
      <Card>
        <AvatarUploader name={profile.data.display_name} />
      </Card>
      <ProfileForm profile={profile.data} onSaved={profile.reload} />
      <SkillsEditor skills={skills.data ?? []} onSaved={skills.reload} />
    </div>
  );
}

export default function SettingsPage() {
  return (
    <RequireAuth>
      <Suspense>
        <SettingsContent />
      </Suspense>
    </RequireAuth>
  );
}
