"""Carga completa con el mismo contrato transaccional que el incremental."""
import json
from etl.pipeline import PROJECTIONS, PipelineError, run_pipeline

def main():
    try:
        report=run_pipeline(full=True)
    except PipelineError as exc:
        raise SystemExit(str(exc)) from None
    print(json.dumps(report,default=str))

if __name__=='__main__':
    main()
