      *----------------------------------------------------------------
      * LOANREC - REGISTROS DE SOLICITUD Y RESULTADO DE PRESTAMO
      * (DATOS SINTETICOS - USO EXCLUSIVO DE DEMOSTRACION)
      *----------------------------------------------------------------
       01 LOAN-REQUEST.
          05 LR-PRINCIPAL         PIC S9(9)V99 COMP-3.
          05 LR-TERM-MONTHS       PIC 9(3).
          05 LR-CREDIT-SCORE      PIC 9(3).
          05 LR-CUSTOMER-AGE      PIC 9(3).
       01 LOAN-RESULT.
          05 LR-STATUS            PIC X(8).
          05 LR-ERROR-CODE        PIC X(3).
          05 LR-ANNUAL-RATE       PIC 9V9(4).
          05 LR-MONTHLY-PAYMENT   PIC S9(9)V99 COMP-3.
          05 LR-INSURANCE         PIC S9(7)V99 COMP-3.
          05 LR-TOTAL-INTEREST    PIC S9(9)V99 COMP-3.
          05 LR-TOTAL-PAID        PIC S9(9)V99 COMP-3.
