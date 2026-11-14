import { LoanEvaluator } from './domain/service/LoanEvaluator.ts';
import { EvaluateLoan } from './application/usecase/EvaluateLoan.ts';
import { InMemoryAudit } from './infrastructure/adapter/out/InMemoryAudit.ts';
import { toOutput, toRequest } from './infrastructure/adapter/in/LoanMapper.ts';

// Composition root: sin lógica de negocio.
const useCase = new EvaluateLoan(new LoanEvaluator(), new InMemoryAudit());

export function execute(input: Record<string, string>): Record<string, string> {
  return toOutput(useCase.evaluate(toRequest(input)));
}
