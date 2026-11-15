"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useId, useMemo, useRef, useState, type DragEvent } from "react";

import { Avatar } from "@/components/ui/Misc";
import { api, ApiError } from "@/lib/api/client";
import type { OwnProfile } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { AVATAR_TYPES, checkAvatarFile } from "@/lib/avatar";

/** Aperçu local d'un fichier choisi (URL temporaire libérée automatiquement). */
function useObjectUrl(file: File | null): string | null {
  const url = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => {
    if (url) URL.revokeObjectURL(url);
  }, [url]);
  return url;
}

function CameraIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
      <path d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1Z" />
      <circle cx="12" cy="13" r="3.5" />
    </svg>
  );
}

/**
 * Zone photo circulaire : clic ou glisser-déposer, aperçu animé.
 * `image` est l'image affichée ; `onFile` reçoit un fichier déjà contrôlé.
 */
function PhotoZone({
  image,
  name,
  busy,
  onFile,
  onError,
}: {
  image: string | null;
  name: string;
  busy?: boolean;
  onFile: (file: File) => void;
  onError: (message: string) => void;
}) {
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function accept(file: File | undefined) {
    if (!file) return;
    const problem = checkAvatarFile(file);
    if (problem) onError(problem);
    else onFile(file);
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    accept(event.dataTransfer.files[0]);
  }

  return (
    <label
      htmlFor={inputId}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className="group relative block h-28 w-28 shrink-0 cursor-pointer rounded-full"
      title="Choisir une photo"
    >
      <motion.span
        className={`absolute -inset-1 rounded-full bg-gradient-to-br from-brand-400 via-ocre-400 to-brand-600 ${dragging ? "opacity-100" : "opacity-40 group-hover:opacity-80"}`}
        animate={busy ? { rotate: 360 } : { rotate: 0 }}
        transition={busy ? { repeat: Infinity, duration: 1.2, ease: "linear" } : { duration: 0.3 }}
        aria-hidden
      />
      <span className="absolute inset-0 overflow-hidden rounded-full bg-panel-2">
        <AnimatePresence mode="popLayout">
          <motion.span
            key={image ?? "vide"}
            className="absolute inset-0 grid place-items-center"
            initial={{ opacity: 0, scale: 1.15, filter: "blur(6px)" }}
            animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          >
            {image ? (
              // Aperçu local ou image déjà réencodée par l'API.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={image} alt="" className="h-full w-full object-cover" />
            ) : (
              <Avatar author={{ display_name: name || "?", avatar: null }} size={112} />
            )}
          </motion.span>
        </AnimatePresence>
        <span className={`absolute inset-0 grid place-items-center bg-night/60 text-ink transition-opacity ${dragging ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
          <span className="flex flex-col items-center gap-1 text-[11px] font-semibold">
            <CameraIcon />
            {dragging ? "Déposer" : "Changer"}
          </span>
        </span>
      </span>
      <input
        ref={input}
        id={inputId}
        type="file"
        accept={AVATAR_TYPES.join(",")}
        className="sr-only"
        onChange={(event) => {
          accept(event.target.files?.[0]);
          // Permet de choisir à nouveau le même fichier.
          event.target.value = "";
        }}
      />
    </label>
  );
}

/** Choix d'une photo à l'inscription : le fichier est envoyé une fois le compte créé. */
export function AvatarChooser({ name, file, onChange }: { name: string; file: File | null; onChange: (file: File | null) => void }) {
  const preview = useObjectUrl(file);
  const [error, setError] = useState("");

  return (
    <div className="mb-5 flex items-center gap-4">
      <PhotoZone
        image={preview}
        name={name}
        onFile={(chosen) => {
          setError("");
          onChange(chosen);
        }}
        onError={setError}
      />
      <div className="text-sm">
        <p className="font-medium">Photo de profil <span className="font-normal text-muted">(facultative)</span></p>
        <p className="mt-0.5 text-xs text-muted">Cliquez ou glissez une image. JPEG, PNG ou WebP, 2 Mo maximum.</p>
        {file && (
          <button type="button" onClick={() => onChange(null)} className="mt-1 text-xs text-rose-300 hover:underline">
            Retirer la photo
          </button>
        )}
        {error && (
          <p className="mt-1 text-xs text-rose-300" role="alert">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

/** Gestion de la photo dans les paramètres : envoi immédiat, suppression. */
export function AvatarUploader({ name }: { name: string }) {
  const { avatar, setAvatar } = useAuth();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  async function upload(file: File) {
    setBusy(true);
    setMessage(null);
    try {
      const body = new FormData();
      body.append("avatar", file);
      const profile = await api<OwnProfile>("/profiles/me/avatar/", { method: "PUT", body });
      setAvatar(profile.avatar);
      setMessage({ kind: "ok", text: "Photo mise à jour." });
    } catch (caught) {
      const error = caught as ApiError;
      setMessage({ kind: "error", text: error.field("avatar") ?? error.message });
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setMessage(null);
    try {
      await api("/profiles/me/avatar/", { method: "DELETE" });
      setAvatar(null);
      setMessage({ kind: "ok", text: "Photo supprimée." });
    } catch (caught) {
      setMessage({ kind: "error", text: (caught as ApiError).message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-5">
      <PhotoZone image={avatar} name={name} busy={busy} onFile={upload} onError={(text) => setMessage({ kind: "error", text })} />
      <div className="text-sm">
        <p className="font-semibold">Photo de profil</p>
        <p className="mt-0.5 max-w-xs text-xs text-muted">
          Cliquez sur la photo ou glissez une image. JPEG, PNG ou WebP, 2 Mo maximum ; elle est recadrée et
          optimisée automatiquement.
        </p>
        {avatar && (
          <button type="button" onClick={remove} disabled={busy} className="mt-2 text-xs text-rose-300 hover:underline disabled:opacity-50">
            Supprimer la photo
          </button>
        )}
        <AnimatePresence>
          {message && (
            <motion.p
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              role={message.kind === "error" ? "alert" : "status"}
              className={`mt-2 text-xs ${message.kind === "ok" ? "text-brand-300" : "text-rose-300"}`}
            >
              {message.text}
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
