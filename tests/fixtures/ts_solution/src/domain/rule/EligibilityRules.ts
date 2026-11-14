import { Decimal } from '../shared/decimal.ts';
import type { LoanRequest, RejectionCode } from '../model/Loan.ts';

const MIN_PRINCIPAL = Decimal.of('1000.00');
const MAX_PRINCIPAL = Decimal.of('500000.00');
const MIN_TERM = 6;
const MAX_TERM = 360;
const MAX_MATURITY_AGE = 75;

/**
 * Monto del préstamo entre 1,000.00 y 500,000.00 (inclusive).
 * @rule R-001
 */
export function validatePrincipal(req: LoanRequest): RejectionCode | null {
  return req.principal.lt(MIN_PRINCIPAL) || req.principal.gt(MAX_PRINCIPAL) ? 'E01' : null;
}

/**
 * Plazo entre 6 y 360 meses (inclusive).
 * @rule R-002
 */
export function validateTerm(req: LoanRequest): RejectionCode | null {
  return req.termMonths < MIN_TERM || req.termMonths > MAX_TERM ? 'E02' : null;
}

/**
 * Edad al vencimiento (años enteros del plazo, truncados) no mayor a 75.
 * @rule R-003
 */
export function validateMaturityAge(req: LoanRequest): RejectionCode | null {
  const termYears = Math.trunc(req.termMonths / 12);
  return req.customerAge + termYears > MAX_MATURITY_AGE ? 'E03' : null;
}

export const ELIGIBILITY_RULES = [validatePrincipal, validateTerm, validateMaturityAge];
