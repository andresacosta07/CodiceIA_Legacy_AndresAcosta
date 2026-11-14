-- LIQUIDACION DE SINIESTROS - DATOS SINTETICOS (DEMO)
CREATE OR REPLACE PACKAGE BODY PKG_SINIESTROS AS

  C_MAX_DIAS_REPORTE CONSTANT NUMBER := 30;

  FUNCTION CALC_INDEMNIZACION(
      p_monto_reclamado IN NUMBER,
      p_suma_asegurada  IN NUMBER,
      p_deducible_pct   IN NUMBER,
      p_dias_reporte    IN NUMBER,
      p_alerta_fraude   IN VARCHAR2
  ) RETURN NUMBER IS
      v_base       NUMBER(15,2);
      v_deducible  NUMBER(15,2);
      v_resultado  NUMBER(15,2);
  BEGIN
      -- REGLA: siniestros con alerta de fraude no se liquidan automaticamente
      IF p_alerta_fraude = 'S' THEN
          RETURN -1;
      END IF;
      -- REGLA: reporte extemporaneo (> 30 dias) se rechaza
      IF p_dias_reporte > C_MAX_DIAS_REPORTE THEN
          RETURN -2;
      END IF;
      -- REGLA: el monto base no puede exceder la suma asegurada
      v_base := LEAST(p_monto_reclamado, p_suma_asegurada);
      -- REGLA: deducible porcentual redondeado a 2 decimales (half-up)
      v_deducible := ROUND(v_base * p_deducible_pct / 100, 2);
      v_resultado := v_base - v_deducible;
      RETURN v_resultado;
  END CALC_INDEMNIZACION;

  PROCEDURE BUSCAR_POR_POLIZA(p_poliza IN VARCHAR2) IS
      v_sql VARCHAR2(500);
  BEGIN
      -- SQL DINAMICO CONCATENADO (vulnerable a inyeccion SQL)
      v_sql := 'SELECT * FROM SINIESTROS WHERE POLIZA = ''' || p_poliza || '''';
      EXECUTE IMMEDIATE v_sql;
  END BUSCAR_POR_POLIZA;

END PKG_SINIESTROS;
