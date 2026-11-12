import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, FlaskConical, Loader2, RefreshCw, Upload, X } from "lucide-react";
import Panel from "../components/ui/Panel.jsx";
import SummaryCards from "../components/transactions/SummaryCards.jsx";
import TransactionFilters from "../components/transactions/TransactionFilters.jsx";
import TransactionTable from "../components/transactions/TransactionTable.jsx";
import CsvUploadPanel from "../components/transactions/CsvUploadPanel.jsx";
import { BTN_GHOST, BTN_PRIMARY } from "../components/transactions/fieldStyles.js";
import { USE_MOCK, getTransactions, importTransactions } from "../services/transactionsApi.js";
import { EMPTY_FILTERS, filterTransactions, sortByInvoiceDateDesc } from "../utils/transactionUtils.js";

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [showUpload, setShowUpload] = useState(false);
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setLoadError("");
    try {
      setTransactions(sortByInvoiceDateDesc(await getTransactions()));
    } catch (err) {
      setLoadError(err.message || "Couldn't load transactions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const visible = useMemo(() => filterTransactions(transactions, filters), [transactions, filters]);
  const existingIds = useMemo(() => new Set(transactions.map((t) => t.transactionId)), [transactions]);

  // Called by the upload panel after the user confirms. Throwing here shows the message in the panel.
  async function handleImport(rows) {
    const { imported, skipped } = await importTransactions(rows);
    await load();
    setNotice(`Imported ${imported} transaction${imported === 1 ? "" : "s"}${skipped ? ` (${skipped} skipped as duplicates)` : ""}.`);
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Transactions</h1>
          <p className="mt-1 text-slate-200">Track what customers owe you and what you owe suppliers.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {USE_MOCK && (
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-warn/40 bg-warn/10 px-3 py-1.5 text-xs font-medium text-warn"
              title="Set USE_MOCK = false in services/transactionsApi.js to use the backend">
              <FlaskConical className="h-3.5 w-3.5" /> Mock data
            </span>
          )}
          <button type="button" className={BTN_PRIMARY} onClick={() => { setShowUpload((v) => !v); setNotice(""); }} aria-expanded={showUpload}>
            <Upload className="h-4 w-4" /> Upload CSV
          </button>
        </div>
      </header>

      {notice && (
        <p role="status" className="flex items-center justify-between gap-3 rounded-lg border border-good/40 bg-good/10 p-3 text-sm text-good">
          <span className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4" /> {notice}</span>
          <button type="button" aria-label="Dismiss" onClick={() => setNotice("")}><X className="h-4 w-4" /></button>
        </p>
      )}

      {showUpload && <CsvUploadPanel existingIds={existingIds} onImport={handleImport} onClose={() => setShowUpload(false)} />}

      {loading && transactions.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-slate-300" role="status">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading transactions…
        </p>
      ) : loadError ? (
        <Panel title="Couldn't load transactions">
          <p role="alert" className="text-sm text-red-200">{loadError}</p>
          <button type="button" onClick={load} className={`${BTN_GHOST} mt-3`}><RefreshCw className="h-4 w-4" /> Try again</button>
        </Panel>
      ) : (
        <>
          <SummaryCards transactions={transactions} onSelectOverdue={() => setFilters({ ...EMPTY_FILTERS, status: "Overdue" })} />
          <Panel title="All transactions">
            <TransactionFilters filters={filters} onChange={setFilters} shown={visible.length} total={transactions.length} />
            <div className="mt-4">
              <TransactionTable rows={visible} hasAnyData={transactions.length > 0} onClearFilters={() => setFilters(EMPTY_FILTERS)} />
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
