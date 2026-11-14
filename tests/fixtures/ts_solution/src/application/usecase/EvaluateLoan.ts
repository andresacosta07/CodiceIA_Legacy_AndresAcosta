import type { LoanRequest, LoanResult } from '../../domain/model/Loan.ts';
import type { LoanEvaluator } from '../../domain/service/LoanEvaluator.ts';
import type { AuditPort } from '../port/out/AuditPort.ts';
import type { EvaluateLoanUseCase } from '../port/in/EvaluateLoanUseCase.ts';

export class EvaluateLoan implements EvaluateLoanUseCase {
  private readonly evaluator: LoanEvaluator;
  private readonly audit: AuditPort;

  constructor(evaluator: LoanEvaluator, audit: AuditPort) {
    this.evaluator = evaluator;
    this.audit = audit;
  }

  evaluate(request: LoanRequest): LoanResult {
    const result = this.evaluator.evaluate(request);
    this.audit.record(result);
    return result;
  }
}
