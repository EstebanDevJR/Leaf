const API_URL = import.meta.env.PUBLIC_API_URL ?? 'http://localhost:8000';

export const CATEGORY_COLORS: Record<string, string> = {
  comida:          '#4ade80',
  transporte:      '#60a5fa',
  vivienda:        '#a78bfa',
  salud:           '#34d399',
  entretenimiento: '#f472b6',
  ropa:            '#fbbf24',
  servicios:       '#fb923c',
  otro:            '#94a3b8',
};
type FetchLike = typeof fetch;

export interface Transaction {
  id: number;
  amount: number;
  description: string;
  category: string;
  type: 'expense' | 'income';
  merchant: string | null;
  date: string;
  notes: string | null;
}

export interface Stats {
  month: string;
  total_income: number;
  total_expenses: number;
  balance: number;
  transaction_count: number;
  expenses_by_category: Record<string, number>;
}

export interface AlertItem {
  id: number;
  type: string;
  severity: 'info' | 'warn' | 'urgent';
  message: string;
  detail: string;
  triggered_at: string;
  dismissed: boolean;
}

export interface Budget {
  id: number;
  category: string;
  monthly_limit: number;
  created_at: string;
  updated_at: string;
}

export interface ReceiptData {
  merchant: string | null;
  date: string | null;
  items: { name: string; amount: number }[];
  total: number;
  category: string;
}

export type ChatEvent =
  | { type: 'session'; session_id: string }
  | { type: 'chunk'; content: string }
  | { type: 'tool_call'; tool: string; input: Record<string, unknown> }
  | { type: 'tool_result'; tool: string; output: string }
  | { type: 'response'; content: string }
  | { type: 'done' }
  | { type: 'error'; message: string };

export async function* sendChatStream(message: string, sessionId?: string): AsyncGenerator<ChatEvent> {
  const res = await fetch(`${API_URL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId ?? null }),
  });

  if (!res.ok || !res.body) throw new Error('Error de conexión con Leaf');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (line.startsWith('data: ') && line.length > 6) {
          try {
            yield JSON.parse(line.slice(6)) as ChatEvent;
          } catch {
            // ignore malformed lines
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function extractReceipt(file: File): Promise<ReceiptData> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_URL}/ocr/extract`, { method: 'POST', body: form });
  if (!res.ok) {
    let detail = 'Error al procesar el recibo';
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      // keep fallback message when backend does not return JSON
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function getTransactions(limit = 20, fetchFn: FetchLike = fetch): Promise<Transaction[]> {
  const res = await fetchFn(`${API_URL}/transactions/?limit=${limit}`);
  if (!res.ok) throw new Error('Error al cargar transacciones');
  return res.json();
}

export async function getStats(fetchFn: FetchLike = fetch): Promise<Stats> {
  const res = await fetchFn(`${API_URL}/transactions/stats`);
  if (!res.ok) throw new Error('Error al cargar estadísticas');
  return res.json();
}

export async function deleteTransaction(id: number): Promise<void> {
  const res = await fetch(`${API_URL}/transactions/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Error al eliminar transacción');
}

export async function getAlerts(fetchFn: FetchLike = fetch): Promise<AlertItem[]> {
  const res = await fetchFn(`${API_URL}/alerts/`);
  if (!res.ok) throw new Error('Error al cargar alertas');
  return res.json();
}

export async function dismissAlert(id: number): Promise<void> {
  const res = await fetch(`${API_URL}/alerts/${id}/dismiss`, { method: 'POST' });
  if (!res.ok) throw new Error('Error al descartar alerta');
}

export async function getBudgets(fetchFn: FetchLike = fetch): Promise<Budget[]> {
  const res = await fetchFn(`${API_URL}/budgets/`);
  if (!res.ok) throw new Error('Error al cargar presupuestos');
  return res.json();
}

export async function upsertBudget(category: string, monthly_limit: number): Promise<Budget> {
  const res = await fetch(`${API_URL}/budgets/${category}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category, monthly_limit }),
  });
  if (!res.ok) throw new Error('Error al guardar presupuesto');
  return res.json();
}

export async function deleteBudget(category: string): Promise<void> {
  const res = await fetch(`${API_URL}/budgets/${category}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Error al eliminar presupuesto');
}

export async function createTransaction(data: {
  amount: number;
  description: string;
  category: string;
  type: 'expense' | 'income';
  merchant?: string;
}): Promise<Transaction> {
  const res = await fetch(`${API_URL}/transactions/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Error al registrar transacción');
  return res.json();
}

export function formatCOP(amount: number): string {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

// ── Savings Goals ─────────────────────────────────────────────────────────────

export interface SavingsGoal {
  id: number;
  name: string;
  target_amount: number;
  current_amount: number;
  monthly_contribution: number;
  inflation_rate: number;
  profile_id: string;
  created_at: string;
  completed_at: string | null;
}

export async function getSavingsGoals(profileId = 'default'): Promise<SavingsGoal[]> {
  const res = await fetch(`${API_URL}/savings-goals/?profile_id=${profileId}`);
  if (!res.ok) throw new Error('Error al cargar metas');
  return res.json();
}

export async function createSavingsGoal(data: Omit<SavingsGoal, 'id' | 'created_at' | 'completed_at'>): Promise<SavingsGoal> {
  const res = await fetch(`${API_URL}/savings-goals/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Error al crear meta');
  return res.json();
}

export async function updateSavingsGoal(id: number, data: Partial<SavingsGoal>): Promise<SavingsGoal> {
  const res = await fetch(`${API_URL}/savings-goals/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Error al actualizar meta');
  return res.json();
}

export async function deleteSavingsGoal(id: number): Promise<void> {
  const res = await fetch(`${API_URL}/savings-goals/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Error al eliminar meta');
}

// ── Profiles ──────────────────────────────────────────────────────────────────

export interface UserProfile {
  id: number;
  profile_id: string;
  name: string;
  color: string;
  monthly_income: number;
  created_at: string;
}

export async function getProfiles(): Promise<UserProfile[]> {
  const res = await fetch(`${API_URL}/profiles/`);
  if (!res.ok) throw new Error('Error al cargar perfiles');
  return res.json();
}

export async function createProfile(data: Omit<UserProfile, 'id' | 'created_at'>): Promise<UserProfile> {
  const res = await fetch(`${API_URL}/profiles/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Error al crear perfil');
  return res.json();
}

// ── Import / Export ───────────────────────────────────────────────────────────

export async function importCSV(file: File, bank: string): Promise<{ imported: number; expenses: number; incomes: number }> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_URL}/io/csv?bank=${encodeURIComponent(bank)}`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error de importación' }));
    throw new Error((err as { detail?: string }).detail ?? 'Error de importación');
  }
  return res.json();
}

export function exportExcelUrl(year?: number, month?: number): string {
  const y = year ?? new Date().getFullYear();
  const m = month ?? new Date().getMonth() + 1;
  return `${API_URL}/io/excel?year=${y}&month=${m}`;
}

export function exportPdfUrl(year?: number, month?: number, mode = 'standard'): string {
  const y = year ?? new Date().getFullYear();
  const m = month ?? new Date().getMonth() + 1;
  return `${API_URL}/io/pdf?year=${y}&month=${m}&mode=${mode}`;
}

// ── Investigador ──────────────────────────────────────────────────────────────

export async function getInvestigadorStatus(): Promise<{ enabled: boolean; user_id: string; updated_at: string }> {
  const res = await fetch(`${API_URL}/investigador/status`);
  if (!res.ok) throw new Error('Error al consultar estado del investigador');
  return res.json();
}

export async function toggleInvestigador(enabled: boolean): Promise<void> {
  await fetch(`${API_URL}/investigador/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface DashboardSummary {
  balance: number;
  month_income: number;
  month_expenses: number;
  month_savings: number;
  savings_rate: number;
  income_delta_pct: number;
  expenses_delta_pct: number;
  transaction_count: number;
}

export interface CashflowPoint {
  label: string;
  month: string;
  income: number;
  expenses: number;
}

export interface EmergencyFund {
  balance: number;
  avg_monthly_expenses: number;
  coverage_months: number;
  target_min: number;
  target_recommended: number;
  target_optimal: number;
  coverage_pct: number;
  gap: number;
  monthly_savings: number;
  months_to_goal: number | null;
  status: 'complete' | 'warning' | 'critical';
}

export interface CdtBank {
  bank: string;
  rates: Record<string, number>;
  best_rate: number;
  best_term: number;
}

export interface InvestmentsData {
  is_live: boolean;
  banks: CdtBank[];
  inflation_rate: number;
  banrep_rate: number;
}

export interface WhatIfResult {
  scenario: string;
  label: string;
  base_income: number;
  base_expenses: number;
  base_savings: number;
  new_savings: number;
  monthly_diff: number;
  projections: Record<string, { extra_savings: number; total_savings: number; vs_current: number }>;
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const res = await fetch(`${API_URL}/dashboard/summary`);
  if (!res.ok) throw new Error('Error al cargar resumen del dashboard');
  return res.json();
}

export async function getDashboardCashflow(months = 12): Promise<CashflowPoint[]> {
  const res = await fetch(`${API_URL}/dashboard/cashflow?months=${months}`);
  if (!res.ok) throw new Error('Error al cargar cashflow');
  return res.json();
}

export async function getEmergencyFund(): Promise<EmergencyFund> {
  const res = await fetch(`${API_URL}/dashboard/emergency-fund`);
  if (!res.ok) throw new Error('Error al cargar fondo de emergencia');
  return res.json();
}

export async function getInvestments(): Promise<InvestmentsData> {
  const res = await fetch(`${API_URL}/dashboard/investments`);
  if (!res.ok) throw new Error('Error al cargar inversiones');
  return res.json();
}

export async function simulateWhatIf(params: {
  scenario: string;
  change_pct?: number;
  change_amount?: number;
}): Promise<WhatIfResult> {
  const res = await fetch(`${API_URL}/dashboard/whatif`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error('Error en la simulación');
  return res.json();
}

export const TOOL_LABELS: Record<string, string> = {
  register_expense:      'registrando gasto',
  register_income:       'registrando ingreso',
  edit_transaction:      'editando transacción',
  query_history:         'consultando historial',
  delete_transaction:    'eliminando transacción',
  extract_receipt:       'leyendo recibo',
  check_budget:          'verificando presupuesto',
  set_budget:            'configurando presupuesto',
  predict_expenses:      'proyectando gastos',
  summarize_month:       'resumiendo mes',
  check_obligacion:      'verificando obligación tributaria',
  calculate_renta:       'calculando renta',
  calcular_retencion:    'calculando retención en la fuente',
  calcular_gmf:          'calculando GMF 4×1000',
  calcular_deducciones:  'calculando deducciones',
  generar_borrador:      'generando borrador de renta',
  get_uvt_vigente:       'consultando UVT vigente',
  check_deadlines:       'consultando fechas DIAN',
  generate_report:       'generando reporte',
  analyze_patterns:      'analizando patrones',
  detect_anomaly:        'detectando anomalías',
  find_subscriptions:    'buscando suscripciones',
  calculate_savings_goal:'calculando meta de ahorro',
  get_cdt_rates:         'consultando tasas CDT',
  get_live_cdt_rates:    'consultando tasas CDT en vivo',
  analyze_weekday:       'analizando días de la semana',
  find_idle_money:       'buscando dinero inactivo',
  emergency_fund_status: 'evaluando fondo de emergencia',
  generate_insight_report:'generando informe',
  explain_concept:       'explicando concepto',
  create_savings_goal:   'creando meta de ahorro',
  list_savings_goals:    'listando metas',
  update_savings_goal:   'actualizando meta',
  whatif_simulator:      'simulando escenario',
  formulario_210:        'generando Formulario 210',
  import_dian_factura:   'importando factura DIAN',
};
