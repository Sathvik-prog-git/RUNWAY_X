import { useRef, useState } from "react";
import { CheckCircle2, Download, FileWarning, Loader2, UploadCloud, X } from "lucide-react";
import Panel from "../ui/Panel.jsx";
import StatusBadge from "./StatusBadge.jsx";
import { BTN_GHOST, BTN_PRIMARY } from "./fieldStyles.js";
import { buildTemplateCsv, parseTransactionsCsv, validateFile, MAX_FILE_BYTES } from "../../services/csvImport.js";
import { formatDate, formatINR } from "../../utils/transactionUtils.js";

const PREVIEW_ROWS = 8;
const MAX_ERRORS_SHOWN = 15;

function downloadTemplate() {
  const url = URL.createObjectURL(new Blob([buildTemplateCsv()], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url; a.download = "runway-x-transactions-template.csv";
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Pick/drop a CSV → validate → preview → confirm.
 * `onImport(rows)` must return a promise (see TransactionsPage); `existingIds` is a Set used to flag duplicates.
 */
export default function CsvUploadPanel({ existingIds, onImport, onClose }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState("");
  const [fileError, setFileError] = useState("");
  const [result, setResult] = useState(null);       // output of parseTransactionsCsv
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");

  const reset = () => {
    setFileName(""); setFileError(""); setResult(null); setImportError("");
    if (inputRef.current) inputRef.current.value = "";
  };

  async function handleFile(file) {
    reset();
    if (!file) return;
    const problem = validateFile(file);
    if (problem) { setFileError(problem); return; }
    setFileName(file.name);
    try {
      const text = await file.text();
      const parsed = parseTransactionsCsv(text, existingIds);
      if (parsed.fatal) { setFileError(parsed.fatal); setFileName(""); return; }
      setResult(parsed);
    } catch {
      setFileError("Couldn't read this file. Make sure it is a plain CSV and try again.");
      setFileName("");
    }
  }

  async function confirmImport() {
    setImporting(true); setImportError("");
    try {
      await onImport(result.rows);
      onClose();
    } catch (err) {
      setImportError(err.message || "Import failed. Nothing was added.");
    } finally {
      setImporting(false);
    }
  }

  const valid = result?.rows.length ?? 0;
  const bad = result?.errors.length ?? 0;

  return (
    <Panel
      title="Import transactions from CSV"
      icon={UploadCloud}
      action={
        <button type="button" onClick={onClose} aria-label="Close upload panel" className="rounded-md p-1 text-slate-300 hover:text-white">
          <X className="h-5 w-5" />
        </button>
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-slate-300">
        <p>
          Required columns: <code className="text-brand-sky">transaction_id, party, type, amount, invoice_date, due_date</code>.
          Optional: <code className="text-brand-sky">payment_date, status</code>. Max {MAX_FILE_BYTES / 1048576} MB.
        </p>
        <button type="button" onClick={downloadTemplate} className={`${BTN_GHOST} !py-1.5 text-xs`}>
          <Download className="h-3.5 w-3.5" /> Download template
        </button>
      </div>

      <label
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files?.[0]); }}
        className={`mt-4 flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-4 py-8 text-center transition focus-within:border-brand-cyan ${
          dragOver ? "border-brand-cyan bg-brand-sky/10" : "border-sky-400/30 hover:border-brand-sky"
        }`}
      >
        <UploadCloud className="h-9 w-9 text-brand-sky" strokeWidth={1.5} />
        <span className="text-sm font-medium">{fileName || "Drop a CSV here, or click to choose a file"}</span>
        <input ref={inputRef} type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => handleFile(e.target.files?.[0])} />
      </label>

      {fileError && (
        <p role="alert" className="mt-3 flex items-start gap-2 rounded-lg border border-bad/40 bg-bad/10 p-3 text-sm text-red-200">
          <FileWarning className="mt-0.5 h-4 w-4 shrink-0 text-bad" /> {fileError}
        </p>
      )}

      {result && (
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap gap-3 text-sm" role="status">
            <span className="inline-flex items-center gap-1.5 rounded-md bg-good/15 px-3 py-1 text-good">
              <CheckCircle2 className="h-4 w-4" /> {valid} of {result.totalRows} rows ready to import
            </span>
            {bad > 0 && <span className="rounded-md bg-bad/15 px-3 py-1 text-red-200">{bad} row{bad === 1 ? "" : "s"} with problems (will be skipped)</span>}
          </div>

          {bad > 0 && (
            <div>
              <p className="mb-1 text-xs text-slate-300">Row numbers count data rows, not the header.</p>
              <ul className="max-h-40 space-y-1 overflow-y-auto rounded-lg border border-bad/30 bg-bad/5 p-3 text-xs text-red-100">
                {result.errors.slice(0, MAX_ERRORS_SHOWN).map((e) => (
                  <li key={e.row}><span className="font-semibold">Row {e.row}:</span> {e.message}</li>
                ))}
                {bad > MAX_ERRORS_SHOWN && <li className="text-slate-300">…and {bad - MAX_ERRORS_SHOWN} more.</li>}
              </ul>
            </div>
          )}

          {valid > 0 && (
            <div>
              <p className="mb-2 text-sm font-medium">Preview (first {Math.min(PREVIEW_ROWS, valid)} of {valid})</p>
              <div className="overflow-x-auto rounded-lg border border-sky-400/20">
                <table className="w-full min-w-[720px] text-left text-xs">
                  <thead className="bg-navy-800/60 text-slate-300">
                    <tr>{["ID", "Customer / Supplier", "Type", "Amount", "Invoice", "Due", "Paid", "Status"].map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr>
                  </thead>
                  <tbody>
                    {result.rows.slice(0, PREVIEW_ROWS).map((r) => (
                      <tr key={r.transactionId} className="border-t border-sky-400/10">
                        <td className="px-3 py-2 font-medium">{r.transactionId}</td>
                        <td className="px-3 py-2">{r.party}</td>
                        <td className="px-3 py-2">{r.type}</td>
                        <td className="px-3 py-2">{formatINR(r.amount)}</td>
                        <td className="px-3 py-2">{formatDate(r.invoiceDate)}</td>
                        <td className="px-3 py-2">{formatDate(r.dueDate)}</td>
                        <td className="px-3 py-2">{formatDate(r.paymentDate)}</td>
                        <td className="px-3 py-2"><StatusBadge status={r.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {importError && <p role="alert" className="rounded-lg border border-bad/40 bg-bad/10 p-3 text-sm text-red-200">{importError}</p>}

          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className={BTN_GHOST} onClick={reset} disabled={importing}>Choose another file</button>
            <button type="button" className={BTN_PRIMARY} onClick={confirmImport} disabled={valid === 0 || importing}>
              {importing && <Loader2 className="h-4 w-4 animate-spin" />}
              {importing ? "Importing…" : `Import ${valid} transaction${valid === 1 ? "" : "s"}`}
            </button>
          </div>
        </div>
      )}
    </Panel>
  );
}
