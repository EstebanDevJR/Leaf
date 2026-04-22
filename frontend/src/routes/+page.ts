import { getAlerts, getBudgets, getStats, getTransactions } from '$lib/api';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
  try {
    const [transactions, stats, budgets, alerts] = await Promise.all([
      getTransactions(20, fetch),
      getStats(fetch),
      getBudgets(fetch),
      getAlerts(fetch),
    ]);
    return { transactions, stats, budgets, alerts };
  } catch {
    return { transactions: [], stats: null, budgets: [], alerts: [] };
  }
};
