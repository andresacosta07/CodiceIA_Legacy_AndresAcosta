"""Referencia escrita A MANO del comportamiento de LOANAMRT.cbl (oráculo de pruebas de la propia app).

Sirve para: (1) generar `cases.json` (E2, casos aportados) y (2) validar el pipeline sin LLM.
Semántica COBOL: ROUNDED = mitad hacia arriba (away from zero); sin ROUNDED = truncamiento.
"""
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, getcontext

getcontext().prec = 60


def q(v: Decimal, scale: int, mode=ROUND_HALF_UP) -> Decimal:
    return v.quantize(Decimal(1).scaleb(-scale), rounding=mode)


def run(inp: dict) -> dict:
    principal = Decimal(inp["principal"])
    term = int(inp["term_months"])
    score = int(inp["credit_score"])
    age = int(inp["customer_age"])
    out = {"status": "", "error_code": "", "annual_rate": "0.0000", "monthly_payment": "0.00",
           "insurance": "0.00", "total_interest": "0.00", "total_paid": "0.00"}

    def reject(code):
        out["status"], out["error_code"] = "REJECTED", code
        return out

    if principal < Decimal("1000.00") or principal > Decimal("500000.00"):
        return reject("E01")
    if term < 6 or term > 360:
        return reject("E02")
    if age + term // 12 > 75:
        return reject("E03")
    if score >= 750:
        rate = Decimal("0.0899")
    elif score >= 650:
        rate = Decimal("0.1299")
    elif score >= 550:
        rate = Decimal("0.1899")
    else:
        return reject("E04")
    if score >= 800 and term <= 60:
        rate -= Decimal("0.0025")
    if term > 120:
        rate += Decimal("0.0050")
    out["annual_rate"] = str(q(rate, 4))
    i = q(rate / 12, 9)
    factor = q((1 + i) ** term, 9)
    payment = q(principal * i * factor / (factor - 1), 2)
    ins_rate = Decimal("0.00035") if age < 40 else Decimal("0.00055") if age < 60 else Decimal("0.00095")
    insurance = q(principal * ins_rate, 2)
    total_interest = q(payment * term - principal, 2, ROUND_DOWN)
    total_paid = q((payment + insurance) * term, 2, ROUND_DOWN)
    out.update(status="APPROVED", monthly_payment=str(payment), insurance=str(insurance),
               total_interest=str(total_interest), total_paid=str(total_paid))
    return out


CASES = [
    ("nominal_score_alto", "R-RATE", {"principal": "100000.00", "term_months": "60", "credit_score": "780", "customer_age": "35"}),
    ("promocion_score_800_plazo_60", "R-PROMO", {"principal": "250000.00", "term_months": "60", "credit_score": "820", "customer_age": "45"}),
    ("sin_promocion_plazo_61", "R-PROMO", {"principal": "250000.00", "term_months": "61", "credit_score": "820", "customer_age": "45"}),
    ("recargo_plazo_121", "R-SURCHARGE", {"principal": "180000.50", "term_months": "121", "credit_score": "700", "customer_age": "30"}),
    ("recargo_no_aplica_plazo_120", "R-SURCHARGE", {"principal": "180000.50", "term_months": "120", "credit_score": "700", "customer_age": "30"}),
    ("score_medio", "R-RATE", {"principal": "75000.00", "term_months": "36", "credit_score": "600", "customer_age": "52"}),
    ("score_650_limite", "R-RATE", {"principal": "75000.00", "term_months": "36", "credit_score": "650", "customer_age": "52"}),
    ("score_749_limite", "R-RATE", {"principal": "75000.00", "term_months": "36", "credit_score": "749", "customer_age": "52"}),
    ("score_550_limite", "R-RATE", {"principal": "9999.99", "term_months": "12", "credit_score": "550", "customer_age": "29"}),
    ("score_bajo_rechazo", "R-RATE", {"principal": "50000.00", "term_months": "24", "credit_score": "549", "customer_age": "40"}),
    ("monto_minimo", "R-AMOUNT", {"principal": "1000.00", "term_months": "6", "credit_score": "700", "customer_age": "25"}),
    ("monto_bajo_rechazo", "R-AMOUNT", {"principal": "999.99", "term_months": "12", "credit_score": "700", "customer_age": "25"}),
    ("monto_maximo", "R-AMOUNT", {"principal": "500000.00", "term_months": "240", "credit_score": "760", "customer_age": "28"}),
    ("monto_alto_rechazo", "R-AMOUNT", {"principal": "500000.01", "term_months": "240", "credit_score": "760", "customer_age": "28"}),
    ("plazo_5_rechazo", "R-TERM", {"principal": "20000.00", "term_months": "5", "credit_score": "700", "customer_age": "30"}),
    ("plazo_361_rechazo", "R-TERM", {"principal": "20000.00", "term_months": "361", "credit_score": "700", "customer_age": "30"}),
    ("plazo_maximo_360", "R-TERM", {"principal": "20000.00", "term_months": "360", "credit_score": "700", "customer_age": "30"}),
    ("edad_vencimiento_75_ok", "R-AGE", {"principal": "30000.00", "term_months": "119", "credit_score": "700", "customer_age": "66"}),
    ("edad_vencimiento_76_rechazo", "R-AGE", {"principal": "30000.00", "term_months": "120", "credit_score": "700", "customer_age": "66"}),
    ("truncamiento_anios_11_meses", "R-AGE", {"principal": "30000.00", "term_months": "143", "credit_score": "700", "customer_age": "64"}),
    ("seguro_menor_40", "R-INSURANCE", {"principal": "123456.78", "term_months": "48", "credit_score": "700", "customer_age": "39"}),
    ("seguro_40_a_59", "R-INSURANCE", {"principal": "123456.78", "term_months": "48", "credit_score": "700", "customer_age": "40"}),
    ("seguro_60_o_mas", "R-INSURANCE", {"principal": "123456.78", "term_months": "48", "credit_score": "700", "customer_age": "60"}),
    ("redondeo_mitad_arriba", "R-ROUNDING", {"principal": "33333.33", "term_months": "7", "credit_score": "700", "customer_age": "33"}),
    ("redondeo_cuota_larga", "R-ROUNDING", {"principal": "477777.77", "term_months": "359", "credit_score": "560", "customer_age": "20"}),
]

if __name__ == "__main__":
    import json
    cases = []
    for name, rule, inp in CASES:
        cases.append({"name": name, "category": rule, "input": inp, "expected": run(inp)})
    print(json.dumps(cases, indent=2, ensure_ascii=False))
