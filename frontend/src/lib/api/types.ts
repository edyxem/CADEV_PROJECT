/** Types des ressources renvoyées par l'API (voir /api/schema/). */

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type GlobalRole = "MEMBER" | "MODERATOR" | "ADMIN";

export interface Account {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: GlobalRole;
  email_verified: boolean;
  is_active: boolean;
  date_joined: string;
}

export interface AuthResponse {
  access: string;
  user: Account;
}

export interface Author {
  username: string;
  display_name: string;
  avatar: string | null;
}

export interface Ref {
  id: string;
  name: string;
  slug: string;
}

export interface Country {
  code: string;
  name: string;
}

export type PostType = "DISCUSSION" | "QUESTION" | "ARTICLE" | "ANNOUNCEMENT" | "PROJECT_UPDATE";
export type ContentStatus = "DRAFT" | "PUBLISHED" | "HIDDEN" | "DELETED";

export interface Post {
  id: string;
  type: PostType;
  title: string;
  excerpt: string;
  author: Author;
  category: Ref | null;
  tags: Ref[];
  technologies: Ref[];
  status: ContentStatus;
  vote_count: number;
  comment_count: number;
  answer_count: number;
  has_accepted_answer: boolean;
  has_voted: boolean;
  has_bookmarked: boolean;
  community: string | null;
  published_at: string | null;
  created_at: string;
}

export interface PostDetail extends Post {
  content: string;
  environment: string;
  can_edit: boolean;
}

export interface Comment {
  id: string;
  parent: string | null;
  author: Author | null;
  content: string;
  is_removed: boolean;
  created_at: string;
}

export interface Answer {
  id: string;
  question: string;
  author: Author;
  content: string;
  is_accepted: boolean;
  vote_count: number;
  has_voted: boolean;
  created_at: string;
}

export interface Skill {
  id: string;
  technology: Ref;
  level: string;
  years_experience: number | null;
  verification_status: string;
  verification_label: string;
  is_verified: boolean;
  evidence_url: string;
}

export interface Profile {
  username: string;
  display_name: string;
  headline?: string;
  bio?: string;
  avatar: string | null;
  country?: Country | null;
  city?: string | null;
  languages?: string[];
  experience_level?: string;
  availability_status?: string | null;
  domains?: Ref[];
  skills?: Skill[];
  links?: { id: string; platform: string; url: string; is_public?: boolean }[];
  member_since?: string;
  is_private: boolean;
}

export interface OwnProfile extends Omit<Profile, "country" | "domains"> {
  country: string | null;
  domains: string[];
  profile_visibility: "PUBLIC" | "PRIVATE";
  show_city: boolean;
  show_availability: boolean;
  show_reputation: boolean;
}

export type ProjectStatus = "IDEA" | "RECRUITING" | "IN_PROGRESS" | "PAUSED" | "COMPLETED" | "ARCHIVED";

export interface RoleNeed {
  id: string;
  role_name: string;
  description: string;
  expected_level: string;
  required_technologies: Ref[];
  slots: number;
  is_open: boolean;
}

export interface Project {
  id: string;
  slug: string;
  name: string;
  short_description: string;
  owner: Author;
  category: Ref | null;
  technologies: Ref[];
  status: ProjectStatus;
  visibility: "PUBLIC" | "PRIVATE";
  collaboration_mode: string;
  member_count: number;
  open_role_count: number;
  is_accepting_members: boolean;
  created_at: string;
}

export interface ProjectDetail extends Project {
  description: string;
  problem: string;
  objectives: string;
  expected_availability: string;
  repository_url: string;
  demo_url: string;
  role_needs: RoleNeed[];
  my_role: string | null;
  permissions: {
    edit_settings: boolean;
    manage_members: boolean;
    manage_tasks: boolean;
    create_tasks: boolean;
    view_tasks: boolean;
  };
  task_stats: Record<string, number>;
}

export interface Member {
  id: string;
  user: Author;
  role: string;
  title: string;
  joined_at: string;
}

export interface JoinRequest {
  id: string;
  project: { id: string; slug: string; name: string };
  user: Author;
  requested_role: RoleNeed | null;
  message: string;
  status: "PENDING" | "ACCEPTED" | "REJECTED" | "WITHDRAWN";
  response_message: string;
  created_at: string;
}

export type TaskStatus = "TODO" | "IN_PROGRESS" | "IN_REVIEW" | "DONE" | "BLOCKED";

export interface Task {
  id: string;
  title: string;
  description: string;
  assignee: Author | null;
  status: TaskStatus;
  priority: "LOW" | "MEDIUM" | "HIGH";
  due_date: string | null;
  can_edit: boolean;
}

export interface AppNotification {
  id: string;
  type: string;
  title: string;
  message: string;
  target_url: string;
  is_read: boolean;
  created_at: string;
}

export interface ModerationReport {
  id: string;
  reporter: string;
  target_type: string;
  target: { title: string; excerpt: string; status: string; url: string } | null;
  target_author: Author | null;
  reason: string;
  details: string;
  status: string;
  can_handle: boolean;
  open_reports_on_target: number;
  created_at: string;
}
