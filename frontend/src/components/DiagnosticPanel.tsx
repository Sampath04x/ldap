import type { DiagnosticRun, DiagnosticCheck } from '@/lib/types'
import { CheckCircle2, XCircle, MinusCircle, AlertTriangle, Info, Terminal, Wrench } from 'lucide-react'

export function DiagnosticPanel({ run }: { run: DiagnosticRun }) {
  const statusColor = {
    HEALTHY: 'bg-status-healthy',
    DEGRADED: 'bg-status-degraded',
    FAILED: 'bg-status-failed',
  }[run.overall_status] || 'bg-gray-600'

  return (
    <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
      {/* Overall Banner */}
      <div className={`${statusColor} text-white px-6 py-4 flex justify-between items-center`} data-testid="diagnostic-overall-status">
        <div>
          <span className="text-xs uppercase tracking-widest opacity-80 block font-semibold">Diagnostic Result</span>
          <h2 className="text-2xl font-bold">{run.overall_status}</h2>
        </div>
        <div className="text-right">
          <span className="font-mono bg-black/25 px-3 py-1 rounded-full text-sm font-semibold inline-block">
            {run.overall_result}
          </span>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Summary text */}
        <p className="text-gray-800 text-base leading-relaxed bg-gray-50 p-4 rounded-lg border border-gray-100 font-medium" data-testid="diagnostic-summary">
          {run.summary}
        </p>

        {/* Diagnostic Check Pipeline */}
        <div className="space-y-4">
          <h3 className="font-semibold text-gray-900 border-b pb-2 text-lg">Diagnostic Check Sequence</h3>
          <div className="space-y-4">
            {run.checks.map((check: DiagnosticCheck, idx: number) => {
              const passed = check.passed
              const isSkipped = check.code === 'SKIPPED'
              const statusStr = check.status || (passed ? 'PASSED' : isSkipped ? 'SKIPPED' : check.severity === 'critical' ? 'FAILED' : 'WARNING')
              const actionStr = check.action
              const detailStr = check.detail

              return (
                <div 
                  key={idx} 
                  data-testid="diagnostic-check" 
                  className={`p-4 rounded-xl border transition-all ${
                    !passed && !isSkipped 
                      ? check.severity === 'critical' 
                        ? 'bg-red-50/50 border-red-200' 
                        : 'bg-amber-50/50 border-amber-200' 
                      : isSkipped 
                        ? 'bg-gray-50 border-gray-200 opacity-60' 
                        : 'bg-white border-gray-200'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className="mt-0.5 flex-shrink-0">
                      {passed ? (
                        <CheckCircle2 className="w-5 h-5 text-green-600" />
                      ) : isSkipped ? (
                        <MinusCircle className="w-5 h-5 text-gray-400" />
                      ) : check.severity === 'critical' ? (
                        <XCircle className="w-5 h-5 text-red-600" />
                      ) : (
                        <AlertTriangle className="w-5 h-5 text-amber-600" />
                      )}
                    </div>

                    <div className="flex-1 min-w-0 space-y-2">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-gray-900">{check.name}</span>
                          <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-700 rounded font-mono border">{check.code}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className={`text-xs px-2 py-0.5 rounded font-bold uppercase ${
                            passed ? 'bg-green-100 text-green-800' : isSkipped ? 'bg-gray-200 text-gray-700' : 'bg-red-100 text-red-800'
                          }`}>
                            {statusStr}
                          </span>
                          {!passed && !isSkipped && (
                            <span className="text-xs px-2 py-0.5 bg-gray-900 text-white rounded font-mono uppercase">
                              {check.severity}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Detail / What Failed */}
                      <p className="text-sm text-gray-700">{detailStr}</p>

                      {/* Evidence block */}
                      {check.evidence && (
                        <div className="text-xs bg-gray-900 text-gray-200 p-2.5 rounded-md font-mono flex items-start space-x-2 border border-gray-800">
                          <Terminal className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                          <div className="break-all">
                            <span className="text-gray-400 font-sans font-semibold mr-2">EVIDENCE:</span>
                            {check.evidence}
                          </div>
                        </div>
                      )}

                      {/* Recommended Action */}
                      {actionStr && (
                        <div className="text-xs bg-blue-50 text-blue-900 p-2.5 rounded-md border border-blue-200 flex items-start space-x-2">
                          <Wrench className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <span className="font-semibold text-blue-950 mr-1.5">RECOMMENDED ACTION:</span>
                            {actionStr}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-gray-50 px-6 py-3 border-t text-xs text-gray-500 flex justify-between items-center font-mono">
        <span>Run ID: {run.run_id}</span>
        <span>Duration: {run.duration_ms}ms • {new Date(run.created_at).toLocaleString()}</span>
      </div>
    </div>
  )
}
