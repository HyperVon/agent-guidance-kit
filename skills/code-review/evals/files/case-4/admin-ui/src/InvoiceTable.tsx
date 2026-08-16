import { useMemo, useState } from "react";

type Invoice = {
  invoice_id: string;
  tenant: string;
  currency: string;
  total_minor: number;
  period_start: string;
};

type SortKey = "invoice_id" | "tenant" | "total_minor" | "period_start";

const MINOR_SCALE: Record<string, number> = { USD: 100, EUR: 100, JPY: 1 };

function formatAmount(totalMinor: number, currency: string): string {
  const scale = MINOR_SCALE[currency] ?? 100;
  const major = totalMinor / scale;
  return `${major.toFixed(2)} ${currency}`;
}

export function InvoiceTable({ invoices }: { invoices: Invoice[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("period_start");
  const [descending, setDescending] = useState(true);

  const sorted = useMemo(() => {
    const copy = [...invoices];
    copy.sort((a, b) => {
      const left = a[sortKey];
      const right = b[sortKey];
      if (typeof left === "number" && typeof right === "number") {
        return left - right;
      }
      return String(left).localeCompare(String(right));
    });
    return descending ? copy.reverse() : copy;
  }, [invoices, sortKey, descending]);

  return (
    <table>
      <thead>
        <tr>
          {(["invoice_id", "tenant", "total_minor", "period_start"] as SortKey[]).map((key) => (
            <th key={key}>
              <button
                onClick={() => {
                  if (key === sortKey) {
                    setDescending(!descending);
                  } else {
                    setSortKey(key);
                  }
                }}
              >
                {key}
              </button>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sorted.map((invoice) => (
          <tr key={invoice.invoice_id}>
            <td>{invoice.invoice_id}</td>
            <td>{invoice.tenant}</td>
            <td>{formatAmount(invoice.total_minor, invoice.currency)}</td>
            <td>{invoice.period_start.slice(0, 10)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
