# Modération — fonctionnement et règles

Module `apps.moderation` — exigences P0-12, P0-13, module Q, §11.3, §11.14.

## 1. Signaler

`POST /api/v1/reports/` (membre connecté, limité à 20 signalements / heure).

| `target_type` | `target_id` | Remarque |
|---|---|---|
| `POST` | id de la publication | publiée uniquement |
| `COMMENT` | id du commentaire | publié uniquement |
| `ANSWER` | id de la réponse | publiée uniquement |
| `PROFILE` | id du **compte** | compte actif |
| `PROJECT` | id du projet | visible par le signaleur |

Motifs : `SPAM`, `SCAM`, `HARASSMENT`, `HATE`, `IMPERSONATION`, `DANGEROUS`,
`INTELLECTUAL_PROPERTY`, `OTHER` (précisions obligatoires, 10 caractères minimum).

Règles : impossible de signaler son propre contenu ou son propre compte ; un seul signalement
ouvert par membre et par cible (contrainte en base). Un signalement ne présume pas de la
culpabilité : le contenu reste visible tant qu'aucune action n'est prise.

## 2. Workflow

```
PENDING ──claim──▶ REVIEWING ──action──▶ ACTION_TAKEN ──close──▶ CLOSED
   │                   │
   └──── NO_ACTION ────┴──────────────▶ REJECTED ──────close──▶ CLOSED
```

Toute autre transition renvoie `409 invalid_transition`.

## 3. Actions

| Action | Effet | Qui |
|---|---|---|
| `NO_ACTION` | rejette le signalement | modération (avec signalement) |
| `WARNING` | notifie l'auteur, sans autre effet | modération |
| `HIDE` | contenu `HIDDEN` / projet masqué | modération |
| `RESTORE` | contenu masqué → `PUBLISHED` ; projet visible | modération |
| `RESTORE` d'un contenu `DELETED` | restauration | **administrateur** |
| `DELETE` | suppression logique (`DELETED`) | modération |
| `SUSPEND` | compte inactif jusqu'à J + n (1 à 90 jours), sessions révoquées | modération (membres) ; admin (modérateurs) |
| `UNSUSPEND` | lève la suspension | modération |
| `BAN` / `UNBAN` | bannissement définitif / levée | **administrateur** |

- Un modérateur ne traite **ni ses propres signalements, ni ses propres contenus, ni son
  propre compte**.
- Un compte administrateur ne peut pas être sanctionné par l'API.
- `HIDE`, `DELETE`, `SUSPEND` et `BAN` règlent aussi les autres signalements ouverts sur la
  même cible.
- Une suspension échue est levée automatiquement à la connexion suivante ; un bannissement ne
  l'est jamais.

## 4. Traçabilité

Chaque décision crée :

1. une ligne `ModerationAction` : modérateur, date, action, **motif**, cible, état avant/après,
   échéance éventuelle ;
2. une entrée `AuditLog` (`moderation.<action>`), consultable par les administrateurs
   (`GET /api/v1/moderation/audit-logs/`).

Les actions faites depuis Django Admin (masquer, restaurer, traiter un signalement, désactiver
ou réactiver un compte, changer un rôle) passent par les mêmes services et sont journalisées de
la même façon. Les journaux sont en lecture seule dans l'admin.

## 5. Information du membre concerné

Le membre dont le contenu ou le compte est visé reçoit une notification `MODERATION_ACTION`
avec le type de décision et le motif. **L'identité du signaleur n'est jamais communiquée.**
Les notifications de suspension restent consultables à la réactivation du compte.

## 6. Points à valider par l'équipe (§19, point 9)

- Charte communautaire publique et procédure d'appel (aujourd'hui : contact d'un
  administrateur, qui peut restaurer un contenu ou lever une sanction).
- Durée de conservation des signalements et journaux (proposition : 12 mois après clôture).
- Seuils éventuels de masquage automatique après N signalements (non implémenté : la
  modération reste manuelle, conformément au §19.1).
