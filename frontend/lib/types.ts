export type UserRole =
  | "super_admin"
  | "firm_admin"
  | "accountant"
  | "reviewer"
  | "client";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  firm_id: string | null;
  is_active: boolean;
  is_email_verified: boolean;
  two_factor_enabled: boolean;
}

export type FilingStage =
  | "requested"
  | "documents_uploaded"
  | "under_review"
  | "approval_required"
  | "filed"
  | "completed";

export type FilingType =
  | "income_tax_return"
  | "gst_return"
  | "tds_return"
  | "audit"
  | "other";

export interface FilingStageEvent {
  id: string;
  stage: FilingStage;
  responsible_user_id: string | null;
  notes: string | null;
  created_at: string;
}

export interface FilingRequest {
  id: string;
  client_id: string;
  filing_type: FilingType;
  stage: FilingStage;
  assigned_accountant_id: string | null;
  period_label: string | null;
  due_date: string | null;
  filed_date: string | null;
  notes: string | null;
  stage_history: FilingStageEvent[];
}

export interface FirmOverview {
  active_clients: number;
  pending_filings: number;
  overdue_tasks: number;
  documents_awaiting_review: number;
  upcoming_deadlines_14d: number;
}

export interface ClientOverview {
  client_id: string;
  assigned_accountant_id: string | null;
  filing_status: {
    id: string;
    type: FilingType;
    stage: FilingStage;
    due_date: string | null;
  }[];
  pending_uploads: number;
}

export const FILING_STAGES: { key: FilingStage; label: string }[] = [
  { key: "requested", label: "Requested" },
  { key: "documents_uploaded", label: "Documents Uploaded" },
  { key: "under_review", label: "Under Review" },
  { key: "approval_required", label: "Approval Required" },
  { key: "filed", label: "Filed Successfully" },
  { key: "completed", label: "Completed" },
];

export const FILING_TYPE_LABELS: Record<FilingType, string> = {
  income_tax_return: "Income Tax Return",
  gst_return: "GST Return",
  tds_return: "TDS Return",
  audit: "Audit",
  other: "Other",
};

export type DocumentCategory =
  | "pan_card"
  | "aadhaar"
  | "gst_reports"
  | "salary_slips"
  | "investment_proofs"
  | "bank_statements"
  | "other";

export type DocumentStatus =
  | "missing"
  | "uploaded"
  | "under_review"
  | "approved"
  | "rejected";

export const DOCUMENT_CATEGORY_LABELS: Record<DocumentCategory, string> = {
  pan_card: "PAN Card",
  aadhaar: "Aadhaar",
  gst_reports: "GST Reports",
  salary_slips: "Salary Slips",
  investment_proofs: "Investment Proofs",
  bank_statements: "Bank Statements",
  other: "Other",
};

export interface ChecklistItem {
  id: string;
  filing_request_id: string;
  category: DocumentCategory;
  required: boolean;
  status: DocumentStatus;
  fulfilling_document_id: string | null;
}

export interface Client {
  id: string;
  user_id: string;
  firm_id: string;
  company_name: string | null;
  pan_number: string | null;
  gstin: string | null;
  assigned_accountant_id: string | null;
}

export interface PaginatedClients {
  items: Client[];
  total: number;
  page: number;
  page_size: number;
}

export type TaskStatus =
  | "new"
  | "waiting_for_documents"
  | "review"
  | "approval"
  | "filed"
  | "completed";

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  firm_id: string | null;
  client_id: string | null;
  filing_request_id: string | null;
  assigned_to_id: string | null;
  due_date: string | null;
  created_at: string;
}

export interface KanbanBoard {
  columns: Record<TaskStatus, Task[]>;
}

export const KANBAN_COLUMNS: { key: TaskStatus; label: string }[] = [
  { key: "new", label: "New Client" },
  { key: "waiting_for_documents", label: "Waiting for Documents" },
  { key: "review", label: "Review" },
  { key: "approval", label: "Approval" },
  { key: "filed", label: "Filed" },
  { key: "completed", label: "Completed" },
];

// --- Billing / subscription (own-firm TaxFlow account) ------------------

export type PlanTier = "free" | "solo" | "team" | "firm" | "enterprise";
export type BillingPeriod = "monthly" | "annual";
export type SubscriptionStatus = "trialing" | "active" | "past_due" | "cancelled";

export interface Plan {
  id: string;
  tier: PlanTier;
  name: string;
  description: string | null;
  price_per_seat_inr: number | null;
  billing_period: BillingPeriod;
  min_seats: number;
  max_seats: number | null;
  max_clients: number | null;
  is_active: boolean;
}

export interface Subscription {
  id: string;
  firm_id: string;
  plan_id: string;
  plan: Plan;
  seats: number;
  billing_period: BillingPeriod;
  status: SubscriptionStatus;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  cancelled_at: string | null;
  payment_gateway_ref: string | null;
}

export type NotificationType =
  | "deadline_reminder"
  | "missing_document"
  | "approval_request"
  | "filing_completed"
  | "new_message";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  body: string | null;
  is_read: boolean;
  link_url: string | null;
  created_at: string;
}

export interface NotificationPage {
  items: Notification[];
  total: number;
  page: number;
  page_size: number;
}

export interface Message {
  id: string;
  sender_id: string;
  recipient_id: string;
  client_id: string | null;
  body: string;
  attachment_document_id: string | null;
  read_at: string | null;
  created_at: string;
}

export interface MessagePage {
  items: Message[];
  total: number;
  page: number;
  page_size: number;
}
