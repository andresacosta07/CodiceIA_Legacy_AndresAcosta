import { LoanRequest, LoanResult } from '../model/Loan.ts';
import { ELIGIBILITY_RULES } from '../rule/EligibilityRules.ts';
import { annualRate } from '../rule/RatePolicy.ts';
import { monthlyInsurance, monthlyPayment, monthlyRate, totalInterest, totalPaid } from './AmortizationCalculator.ts';

/** Servicio de dominio: evalúa una solicitud aplicando las reglas aprobadas en el orden del legacy. */
export class LoanEvaluator {
  evaluate(req: LoanRequest): LoanResult {
    for (const rule of ELIGIBILITY_RULES) {
      const code = rule(req);
      if (code !== null) {
        return LoanResult.rejected(code);
      }
    }
    const rate = annualRate(req);
    if (rate === null) {
      return LoanResult.rejected('E04');
    }
    const payment = monthlyPayment(req.principal, monthlyRate(rate), req.termMonths);
    const insurance = monthlyInsurance(req.principal, req.customerAge);
    return LoanResult.approved(
      rate,
      payment,
      insurance,
      totalInterest(payment, req.termMonths, req.principal),
      totalPaid(payment, insurance, req.termMonths),
    );
  }
}
