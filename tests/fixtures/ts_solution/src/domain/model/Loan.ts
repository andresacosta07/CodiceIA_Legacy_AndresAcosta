import { Decimal } from '../shared/decimal.ts';

export class LoanRequest {
  readonly principal: Decimal;
  readonly termMonths: number;
  readonly creditScore: number;
  readonly customerAge: number;

  constructor(principal: Decimal, termMonths: number, creditScore: number, customerAge: number) {
    this.principal = principal;
    this.termMonths = termMonths;
    this.creditScore = creditScore;
    this.customerAge = customerAge;
  }
}

export type RejectionCode = 'E01' | 'E02' | 'E03' | 'E04';

export class LoanResult {
  readonly status: 'APPROVED' | 'REJECTED';
  readonly errorCode: string;
  readonly annualRate: Decimal;
  readonly monthlyPayment: Decimal;
  readonly insurance: Decimal;
  readonly totalInterest: Decimal;
  readonly totalPaid: Decimal;

  private constructor(status: 'APPROVED' | 'REJECTED', errorCode: string, annualRate: Decimal, monthlyPayment: Decimal,
                      insurance: Decimal, totalInterest: Decimal, totalPaid: Decimal) {
    this.status = status;
    this.errorCode = errorCode;
    this.annualRate = annualRate;
    this.monthlyPayment = monthlyPayment;
    this.insurance = insurance;
    this.totalInterest = totalInterest;
    this.totalPaid = totalPaid;
  }

  static rejected(code: RejectionCode, annualRate: Decimal = Decimal.zero(4)): LoanResult {
    return new LoanResult('REJECTED', code, annualRate, Decimal.zero(2), Decimal.zero(2), Decimal.zero(2), Decimal.zero(2));
  }

  static approved(annualRate: Decimal, monthlyPayment: Decimal, insurance: Decimal, totalInterest: Decimal,
                  totalPaid: Decimal): LoanResult {
    return new LoanResult('APPROVED', '', annualRate, monthlyPayment, insurance, totalInterest, totalPaid);
  }
}
