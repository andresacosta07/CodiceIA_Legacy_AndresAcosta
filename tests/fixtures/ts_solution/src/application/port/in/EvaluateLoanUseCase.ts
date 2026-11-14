import type { LoanRequest, LoanResult } from '../../../domain/model/Loan.ts';

export interface EvaluateLoanUseCase {
  evaluate(request: LoanRequest): LoanResult;
}
