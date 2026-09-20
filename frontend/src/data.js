// Mock data representing the full AffordAI dataset
// In production this connects to the FastAPI backend

export const MOCK_USERS = [
  { id: 'user_01', name: 'Priya Sharma', currency: 'INR', balance: 285000, minBalance: 50000 },
  { id: 'user_04', name: 'Budi Santoso', currency: 'IDR', balance: 52206950, minBalance: 30686600 },
  { id: 'user_08', name: 'Lena Müller', currency: 'EUR', balance: 1536.57, minBalance: 800 },
  { id: 'user_16', name: 'Alex Chen', currency: 'USD', balance: 12400, minBalance: 2000 },
  { id: 'user_22', name: 'Fatima Al-Hassan', currency: 'SAR', balance: 8800, minBalance: 1500 },
];

export const STATUS_CONFIG = {
  affordable_now: {
    label: 'Affordable Now',
    color: '#4ade80',
    bg: 'rgba(74,222,128,0.1)',
    border: 'rgba(74,222,128,0.3)',
    icon: '✓',
    cls: 'badge-now',
    desc: 'You can safely purchase this today.',
  },
  affordable_with_plan: {
    label: 'Affordable With Plan',
    color: '#60a5fa',
    bg: 'rgba(96,165,250,0.1)',
    border: 'rgba(96,165,250,0.3)',
    icon: '📋',
    cls: 'badge-plan',
    desc: 'Affordable via installments or spending adjustments.',
  },
  affordable_later: {
    label: 'Affordable Later',
    color: '#fbbf24',
    bg: 'rgba(251,191,36,0.1)',
    border: 'rgba(251,191,36,0.3)',
    icon: '⏳',
    cls: 'badge-later',
    desc: 'Wait until after your next income payment.',
  },
  not_affordable: {
    label: 'Not Affordable',
    color: '#f87171',
    bg: 'rgba(248,113,113,0.1)',
    border: 'rgba(248,113,113,0.3)',
    icon: '✗',
    cls: 'badge-no',
    desc: 'No safe payment path exists at this time.',
  },
};

export const METHOD_LABELS = {
  full_payment: { label: 'Full Payment', icon: '💳' },
  installments: { label: 'Installments', icon: '📅' },
  partial_payment: { label: 'Partial Payment', icon: '💰' },
  wait: { label: 'Wait & Save', icon: '⏰' },
  not_recommended: { label: 'Not Recommended', icon: '🚫' },
};

export const SAMPLE_DECISIONS = [
  {
    request_id: 'request_01',
    user_id: 'user_01',
    item: 'MacBook Pro 16"',
    requested_amount: 285000,
    currency: 'INR',
    affordability_status: 'affordable_now',
    amount_safe_to_pay: 235000,
    recommended_payment_method: 'full_payment',
    payment_plan: 'none',
    earliest_date_for_full_payment: '',
    spending_changes_needed: 'none',
    decision_explanation: 'Your current balance comfortably covers this purchase after reserving your minimum balance and accounting for upcoming expenses.',
    request_date: '2024-03-01',
    desired_completion_date: '2024-03-15',
  },
  {
    request_id: 'request_07',
    user_id: 'user_07',
    item: 'Living Room Renovation',
    requested_amount: 95000,
    currency: 'THB',
    affordability_status: 'affordable_with_plan',
    amount_safe_to_pay: 95000,
    recommended_payment_method: 'installments',
    payment_plan: '2024-04-15:47500|2024-05-15:47500',
    earliest_date_for_full_payment: '2024-04-15',
    spending_changes_needed: 'none',
    decision_explanation: 'A 2-installment plan spreads the cost safely across your next two salary cycles.',
    request_date: '2024-03-15',
    desired_completion_date: '2024-05-31',
  },
  {
    request_id: 'request_03',
    user_id: 'user_03',
    item: 'International Flight Tickets',
    requested_amount: 873000,
    currency: 'IDR',
    affordability_status: 'affordable_later',
    amount_safe_to_pay: 873000,
    recommended_payment_method: 'wait',
    payment_plan: '2024-04-25:873000',
    earliest_date_for_full_payment: '2024-04-25',
    spending_changes_needed: 'none',
    decision_explanation: 'Your current cash flow is tight until your April salary. Waiting 3 weeks gives you a comfortable buffer.',
    request_date: '2024-03-20',
    desired_completion_date: '2024-05-01',
  },
  {
    request_id: 'request_10',
    user_id: 'user_10',
    item: 'Emergency Car Repair',
    requested_amount: 45000,
    currency: 'MXN',
    affordability_status: 'not_affordable',
    amount_safe_to_pay: 12700,
    recommended_payment_method: 'not_recommended',
    payment_plan: 'none',
    earliest_date_for_full_payment: '',
    spending_changes_needed: 'none',
    decision_explanation: 'Monthly recurring commitments exceed income. No safe payment window exists within the forecast period.',
    request_date: '2024-03-10',
    desired_completion_date: '2024-03-20',
  },
];

export const SAMPLE_METRICS = {
  total_evaluated: 25,
  status_accuracy: 0.96,
  method_accuracy: 0.96,
  plan_accuracy: 0.96,
  changes_accuracy: 0.96,
  date_accuracy: 0.96,
  amount_accuracy: 0.92,
  avg_score: 0.952,
};

export const OUTPUT_DISTRIBUTION = {
  affordable_now: 69,
  affordable_with_plan: 80,
  affordable_later: 36,
  not_affordable: 90,
};

export const METHOD_DISTRIBUTION = {
  full_payment: 76,
  installments: 72,
  wait: 36,
  not_recommended: 90,
  partial_payment: 1,
};


export function formatCurrency(amount, currency) {
  if (!amount && amount !== 0) return '-';
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      maximumFractionDigits: 2,
      notation: Math.abs(amount) >= 1e6 ? 'compact' : 'standard',
    }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString()}`;
  }
}

export function parsePlan(planStr) {
  if (!planStr || planStr === 'none') return [];
  return planStr.split('|').map(p => {
    const [date, amount] = p.split(':');
    return { date, amount: parseFloat(amount) };
  });
}
