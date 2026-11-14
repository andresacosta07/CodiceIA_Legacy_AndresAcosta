import type { LoanResult } from '../../../domain/model/Loan.ts';

/** Puerto de salida: reemplaza el INSERT de auditoría (EXEC SQL) del legacy. */
export interface AuditPort {
  record(result: LoanResult): void;
}
