import { Decimal } from '../../../domain/shared/decimal.ts';
import { LoanRequest } from '../../../domain/model/Loan.ts';
import type { LoanResult } from '../../../domain/model/Loan.ts';

export function toRequest(input: Record<string, string>): LoanRequest {
  return new LoanRequest(
    Decimal.of(input['principal']),
    Number.parseInt(input['term_months'], 10),
    Number.parseInt(input['credit_score'], 10),
    Number.parseInt(input['customer_age'], 10),
  );
}

export function toOutput(result: LoanResult): Record<string, string> {
  return {
    status: result.status,
    error_code: result.errorCode,
    annual_rate: result.annualRate.toString(),
    monthly_payment: result.monthlyPayment.toString(),
    insurance: result.insurance.toString(),
    total_interest: result.totalInterest.toString(),
    total_paid: result.totalPaid.toString(),
  };
}
