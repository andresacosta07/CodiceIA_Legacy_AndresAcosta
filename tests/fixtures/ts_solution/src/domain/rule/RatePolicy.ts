import { Decimal } from '../shared/decimal.ts';
import type { LoanRequest } from '../model/Loan.ts';

interface RateTier {
  readonly minScore: number;
  readonly rate: Decimal;
}

const TIERS: readonly RateTier[] = [
  { minScore: 750, rate: Decimal.of('0.0899') },
  { minScore: 650, rate: Decimal.of('0.1299') },
  { minScore: 550, rate: Decimal.of('0.1899') },
];

const PROMO_DISCOUNT = Decimal.of('0.0025');
const PROMO_MIN_SCORE = 800;
const PROMO_MAX_TERM = 60;
const LONG_TERM_SURCHARGE = Decimal.of('0.0050');
const LONG_TERM_MONTHS = 120;

/**
 * Tasa anual base según puntaje crediticio; null si el puntaje es menor a 550 (rechazo E04).
 * @rule R-004
 */
export function baseRate(creditScore: number): Decimal | null {
  const tier = TIERS.find((t) => creditScore >= t.minScore);
  return tier ? tier.rate : null;
}

/**
 * Promoción: 0.25 puntos menos si puntaje >= 800 y plazo <= 60 meses.
 * @rule R-005
 */
export function promotionAdjustment(req: LoanRequest): Decimal {
  const eligible = req.creditScore >= PROMO_MIN_SCORE && req.termMonths <= PROMO_MAX_TERM;
  return eligible ? PROMO_DISCOUNT.negate() : Decimal.zero(4);
}

/**
 * Recargo de 0.50 puntos si el plazo supera 120 meses.
 * @rule R-006
 */
export function termSurcharge(req: LoanRequest): Decimal {
  return req.termMonths > LONG_TERM_MONTHS ? LONG_TERM_SURCHARGE : Decimal.zero(4);
}

/** Tasa anual final aplicable, o null si no califica. */
export function annualRate(req: LoanRequest): Decimal | null {
  const base = baseRate(req.creditScore);
  if (base === null) {
    return null;
  }
  return base.plus(promotionAdjustment(req)).plus(termSurcharge(req)).setScale(4);
}
