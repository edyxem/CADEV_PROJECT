/** Libellés français des valeurs renvoyées par l'API. */

export const POST_TYPES: Record<string, string> = {
  DISCUSSION: "Discussion",
  QUESTION: "Question",
  ARTICLE: "Article",
  ANNOUNCEMENT: "Annonce",
  PROJECT_UPDATE: "Mise à jour de projet",
};

export const LEVELS: Record<string, string> = {
  BEGINNER: "Débutant",
  INTERMEDIATE: "Intermédiaire",
  ADVANCED: "Avancé",
  EXPERT: "Expert",
};

export const AVAILABILITY: Record<string, string> = {
  NOT_AVAILABLE: "Non disponible",
  OPEN_TO_COLLABORATION: "Ouvert aux collaborations",
  LOOKING_FOR_PROJECT: "Recherche un projet",
  AVAILABLE_FOR_MENTORING: "Disponible pour du mentorat",
};

export const PROJECT_STATUS: Record<string, string> = {
  IDEA: "Idée",
  RECRUITING: "Recherche d'équipe",
  IN_PROGRESS: "En cours",
  PAUSED: "Suspendu",
  COMPLETED: "Terminé",
  ARCHIVED: "Archivé",
};

export const PROJECT_ROLES: Record<string, string> = {
  OWNER: "Propriétaire",
  MANAGER: "Responsable",
  CONTRIBUTOR: "Contributeur",
  OBSERVER: "Observateur",
};

export const TASK_STATUS: Record<string, string> = {
  TODO: "À faire",
  IN_PROGRESS: "En cours",
  IN_REVIEW: "En revue",
  DONE: "Terminée",
  BLOCKED: "Bloquée",
};

export const PRIORITY: Record<string, string> = { LOW: "Basse", MEDIUM: "Moyenne", HIGH: "Haute" };

export const REPORT_REASONS: Record<string, string> = {
  SPAM: "Spam",
  SCAM: "Arnaque ou offre trompeuse",
  HARASSMENT: "Harcèlement ou intimidation",
  HATE: "Contenu haineux ou discriminatoire",
  IMPERSONATION: "Usurpation d'identité",
  DANGEROUS: "Contenu dangereux ou illégal",
  INTELLECTUAL_PROPERTY: "Violation de propriété intellectuelle",
  OTHER: "Autre motif",
};

export const MODERATION_ACTIONS: Record<string, string> = {
  NO_ACTION: "Rejeter (aucune action)",
  WARNING: "Avertir l'auteur",
  HIDE: "Masquer le contenu",
  DELETE: "Supprimer le contenu",
  SUSPEND: "Suspendre le compte",
};

const dateFormatter = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });

/** Les dates de l'API sont en UTC ; elles s'affichent dans le fuseau du navigateur. */
export function formatDate(value: string | null | undefined): string {
  return value ? dateFormatter.format(new Date(value)) : "";
}

export function label(map: Record<string, string>, value: string | null | undefined): string {
  return value ? (map[value] ?? value) : "";
}
