/** Règles de la photo de profil, identiques à celles de l'API : JPEG, PNG ou WebP, 2 Mo au plus. */
export const AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const AVATAR_MAX_BYTES = 2 * 1024 * 1024;

/** Message d'erreur à afficher, ou null si le fichier peut être envoyé. */
export function checkAvatarFile(file: Pick<File, "type" | "size">): string | null {
  if (!AVATAR_TYPES.includes(file.type)) return "Format non accepté : choisissez une image JPEG, PNG ou WebP.";
  if (file.size > AVATAR_MAX_BYTES) return "Image trop lourde : 2 Mo au maximum.";
  return null;
}
