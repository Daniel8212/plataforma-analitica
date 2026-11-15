"""Lote reproducible de demo: cambios/fallas exclusivamente en bases Test únicas."""
import json
import os
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    target=ROOT/'data'/('demo-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    target.mkdir(parents=True,exist_ok=False)
    # Pytest fixtures copy a few source rows into new WWI_Test_*/SalesAnalytics_Test_* databases.
    cases=['tests/test_incremental_integration.py::test_update_late_row_and_idempotence',
           'tests/test_incremental_integration.py::test_quarantine_and_recovery',
           'tests/test_incremental_integration.py::test_failure_rolls_back_dw_and_watermark_then_recovers',
           'tests/test_notifications.py::test_integrated_alert_recovery_and_delivery']
    output=target/'pytest.xml'
    result=subprocess.run([sys.executable,'-m','pytest','-q',*cases,'--junitxml='+str(output)],cwd=ROOT,
                          env={**os.environ,'TEST_EVIDENCE_DIR':str(target)})
    report={'simulation':True,'status':'passed' if result.returncode==0 else 'failed','cases':cases,
            'reports':str(target.relative_to(ROOT)),
            'note':'Cambios tardíos, inválidos y fallas solo en bases Test únicas. No altera fuente/DW principales ni reportes históricos.'}
    (target/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(result.returncode)

if __name__=='__main__':main()
