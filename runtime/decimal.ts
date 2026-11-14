// Aritmética decimal exacta con escala y modos de redondeo (equivalente a COBOL COMPUTE / ROUNDED / truncamiento).
// Biblioteca de plataforma verificada por pruebas; el código generado la usa para evitar float/double en importes.
// Solo sintaxis borrable (compatible con ejecución directa en Node sin compilar).

export type Rounding = 'HALF_UP' | 'HALF_EVEN' | 'DOWN' | 'UP' | 'FLOOR' | 'CEILING';

function pow10(n: number): bigint {
  return 10n ** BigInt(n);
}

function abs(n: bigint): bigint {
  return n < 0n ? -n : n;
}

function divRound(n: bigint, d: bigint, mode: Rounding): bigint {
  if (d === 0n) {
    throw new RangeError('División por cero');
  }
  const q = n / d;
  const r = n % d;
  if (r === 0n) {
    return q;
  }
  const negative = (n < 0n) !== (d < 0n);
  const twiceR = abs(r) * 2n;
  const absD = abs(d);
  let increment = false;
  switch (mode) {
    case 'DOWN':
      increment = false;
      break;
    case 'UP':
      increment = true;
      break;
    case 'HALF_UP':
      increment = twiceR >= absD;
      break;
    case 'HALF_EVEN':
      increment = twiceR > absD || (twiceR === absD && q % 2n !== 0n);
      break;
    case 'FLOOR':
      increment = negative;
      break;
    case 'CEILING':
      increment = !negative;
      break;
  }
  if (!increment) {
    return q;
  }
  return negative ? q - 1n : q + 1n;
}

export class Decimal {
  readonly unscaled: bigint;
  readonly scale: number;

  private constructor(unscaled: bigint, scale: number) {
    this.unscaled = unscaled;
    this.scale = scale;
  }

  static of(value: string | number | bigint | Decimal): Decimal {
    if (value instanceof Decimal) {
      return value;
    }
    if (typeof value === 'bigint') {
      return new Decimal(value, 0);
    }
    if (typeof value === 'number') {
      if (!Number.isInteger(value)) {
        throw new TypeError('Decimal.of(number) solo acepta enteros; use una cadena para valores con decimales');
      }
      return new Decimal(BigInt(value), 0);
    }
    const text = value.trim();
    const m = /^([+-]?)(\d+)(?:\.(\d+))?$/.exec(text);
    if (!m) {
      throw new TypeError(`Valor decimal inválido: ${JSON.stringify(value)}`);
    }
    const frac = m[3] ?? '';
    const unscaled = BigInt(m[2] + frac) * (m[1] === '-' ? -1n : 1n);
    return new Decimal(unscaled, frac.length);
  }

  static zero(scale = 0): Decimal {
    return new Decimal(0n, scale);
  }

  private static align(a: Decimal, b: Decimal): [bigint, bigint, number] {
    const scale = Math.max(a.scale, b.scale);
    return [a.unscaled * pow10(scale - a.scale), b.unscaled * pow10(scale - b.scale), scale];
  }

  plus(other: Decimal | string | number): Decimal {
    const [x, y, s] = Decimal.align(this, Decimal.of(other));
    return new Decimal(x + y, s);
  }

  minus(other: Decimal | string | number): Decimal {
    const [x, y, s] = Decimal.align(this, Decimal.of(other));
    return new Decimal(x - y, s);
  }

  times(other: Decimal | string | number): Decimal {
    const o = Decimal.of(other);
    return new Decimal(this.unscaled * o.unscaled, this.scale + o.scale);
  }

  /** Cociente redondeado a `scale` decimales con el modo indicado. */
  dividedBy(other: Decimal | string | number, scale: number, mode: Rounding = 'HALF_UP'): Decimal {
    const o = Decimal.of(other);
    const num = this.unscaled * pow10(scale + o.scale);
    const den = o.unscaled * pow10(this.scale);
    return new Decimal(divRound(num, den, mode), scale);
  }

  /** Potencia entera no negativa, exacta. */
  pow(exponent: number): Decimal {
    if (!Number.isInteger(exponent) || exponent < 0) {
      throw new RangeError('pow solo admite exponentes enteros no negativos');
    }
    return new Decimal(this.unscaled ** BigInt(exponent), this.scale * exponent);
  }

  /** Ajusta a `scale` decimales (ROUNDED = HALF_UP; sin ROUNDED = DOWN, truncamiento). */
  setScale(scale: number, mode: Rounding = 'HALF_UP'): Decimal {
    if (scale >= this.scale) {
      return new Decimal(this.unscaled * pow10(scale - this.scale), scale);
    }
    return new Decimal(divRound(this.unscaled, pow10(this.scale - scale), mode), scale);
  }

  /** Emula el truncamiento de PIC: conserva solo `intDigits` dígitos enteros (los de mayor orden se pierden). */
  truncateToPic(intDigits: number, scale: number): Decimal {
    const d = this.setScale(scale, 'DOWN');
    const limit = pow10(intDigits + scale);
    const sign = d.unscaled < 0n ? -1n : 1n;
    return new Decimal((abs(d.unscaled) % limit) * sign, scale);
  }

  /**
   * Almacena el valor en un campo PIC numérico: ajusta la escala (ROUNDED = HALF_UP; sin ROUNDED = DOWN),
   * trunca los dígitos enteros excedentes y descarta el signo si el campo no lleva signo.
   */
  toPic(intDigits: number, scale: number, signed: boolean, rounded: boolean): Decimal {
    const truncated = this.setScale(scale, rounded ? 'HALF_UP' : 'DOWN').truncateToPic(intDigits, scale);
    return signed ? truncated : truncated.abs();
  }

  compareTo(other: Decimal | string | number): number {
    const [x, y] = Decimal.align(this, Decimal.of(other));
    return x < y ? -1 : x > y ? 1 : 0;
  }

  equals(other: Decimal | string | number): boolean {
    return this.compareTo(other) === 0;
  }

  lt(other: Decimal | string | number): boolean {
    return this.compareTo(other) < 0;
  }

  lte(other: Decimal | string | number): boolean {
    return this.compareTo(other) <= 0;
  }

  gt(other: Decimal | string | number): boolean {
    return this.compareTo(other) > 0;
  }

  gte(other: Decimal | string | number): boolean {
    return this.compareTo(other) >= 0;
  }

  isZero(): boolean {
    return this.unscaled === 0n;
  }

  isNegative(): boolean {
    return this.unscaled < 0n;
  }

  negate(): Decimal {
    return new Decimal(-this.unscaled, this.scale);
  }

  abs(): Decimal {
    return new Decimal(abs(this.unscaled), this.scale);
  }

  /** Parte entera truncada (hacia cero) como número seguro. */
  toInteger(): number {
    return Number(this.unscaled / pow10(this.scale));
  }

  toString(): string {
    const negative = this.unscaled < 0n;
    const digits = abs(this.unscaled).toString().padStart(this.scale + 1, '0');
    const intPart = this.scale === 0 ? digits : digits.slice(0, digits.length - this.scale);
    const fracPart = this.scale === 0 ? '' : '.' + digits.slice(digits.length - this.scale);
    return (negative ? '-' : '') + intPart + fracPart;
  }
}
