// 라인3(module_3_polymer_electronic) 전용 — 데이터셋별 '핵심 컬럼'(제약 폼 기본 노출).
// 모든 컬럼명은 라이브 catalog 컬럼명과 정확 일치 + 숫자형(integer/float)임을 대조 확인(2026-06).
// 맵에 없는 데이터셋(다른 라인 등)은 전체 컬럼을 그대로 표시(현행).
export const ESSENTIAL_COLUMNS = {
  L1_injection_production: ['Max Injection Pressure', 'Actual Barrel Temperature H3', 'Cycle Time', 'Max Injection Velocity'],
  L1_injection_optimize: ['Max_Injection_Pressure', 'Barrel_Temperature_3', 'Cycle_Time', 'Max_Injection_Speed'],
  L1_cnc_machine_optimize: ['3RD INJECTION VELOCITY', '4TH INJECTION VELOCITY', 'BACK PRESSURE 1', 'EXTRUDER STEP'],
  L3_extrusion_pdm: ['MELT_TEMP', 'SCREW_CURRENT', 'OUTSIDE_CURRENT', 'DIES1_TEMP'],
  L3_vacuum_pump: ['C3', 'C5', 'C6', 'C8'],
  L4_ict_inspection: ['기준값', '표준값', '측정값'],
  L4_ict_checker: ['기준값', 'Hi 핀', 'Low 핀'],
  order_planning: ['안전재고', '현재고량', '보유율(%)'],
}
