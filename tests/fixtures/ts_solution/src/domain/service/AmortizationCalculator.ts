import { Decimal } from '../shared/decimal.ts';

/**
 * Tasa mensual = tasa anual / 12, redondeada (ROUNDED) a 9 decimales.
 * @rule R-007
 */
export function monthlyRate(annualRate: Decimal): Decimal {
  return annualRate.dividedBy(12, 9, 'HALF_UP');
}

/**
 * Cuota francesa = P * i * F / (F - 1) con F = (1+i)^n redondeado a 9 decimales; cuota redondeada a 2 decimales.
 * @rule R-007
 */
export function monthlyPayment(principal: Decimal, rate: Decimal, termMonths: number): Decimal {
  const factor = Decimal.of(1).plus(rate).pow(termMonths).setScale(9, 'HALF_UP');
  const numerator = principal.times(rate).times(factor);
  return numerator.dividedBy(factor.minus(1), 2, 'HALF_UP');
}

/**
 * Seguro mensual sobre el monto inicial: <40 años 0.00035, <60 años 0.00055, resto 0.00095; redondeado a 2 decimales.
 * @rule R-008
 */
export function monthlyInsurance(principal: Decimal, customerAge: number): Decimal {
  const rate = customerAge < 40 ? '0.00035' : customerAge < 60 ? '0.00055' : '0.00095';
  return principal.times(rate).setScale(2, 'HALF_UP');
}

/**
 * Interés total = cuota * plazo - monto; truncado a 2 decimales (sin ROUNDED).
 * @rule R-009
 */
export function totalInterest(payment: Decimal, termMonths: number, principal: Decimal): Decimal {
  return payment.times(termMonths).minus(principal).setScale(2, 'DOWN');
}

/**
 * Total pagado = (cuota + seguro) * plazo; truncado a 2 decimales (sin ROUNDED).
 * @rule R-009
 */
export function totalPaid(payment: Decimal, insurance: Decimal, termMonths: number): Decimal {
  return payment.plus(insurance).times(termMonths).setScale(2, 'DOWN');
}
