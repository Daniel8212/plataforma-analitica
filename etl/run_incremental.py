"""Ejecutar desde raíz: python -m etl.run_incremental [--full]."""
import argparse
import json
from etl.pipeline import PipelineError, run_pipeline

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--full',action='store_true',help='Reconciliación completa, incluso cambios fuera del solapamiento')
    parser.add_argument('--overlap-hours',type=int,default=48)
    parser.add_argument('--fail-at',choices=['after_raw','after_publish','before_commit'],help='Falla simulada explícita para recuperación')
    args=parser.parse_args()
    try:
        report=run_pipeline(full=args.full,overlap_hours=args.overlap_hours,fail_at=args.fail_at)
    except PipelineError as exc:
        raise SystemExit(str(exc)) from None
    print(json.dumps(report,default=str))

if __name__=='__main__':
    main()
