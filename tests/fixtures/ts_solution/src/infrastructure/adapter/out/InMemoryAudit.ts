import type { LoanResult } from '../../../domain/model/Loan.ts';
import type { AuditPort } from '../../../application/port/out/AuditPort.ts';

export class InMemoryAudit implements AuditPort {
  readonly entries: LoanResult[] = [];

  record(result: LoanResult): void {
    this.entries.push(result);
  }
}
