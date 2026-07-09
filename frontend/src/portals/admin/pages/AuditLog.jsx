import { useEffect, useState } from "react";
import api from "../lib/api";
import { Card, EmptyState, Loader } from "../components/Common";

export default function AuditLog() {
  const [items, setItems] = useState(null);

  useEffect(() => {
    api.get("/admin-portal/audit-log/").then(({ data }) => setItems(data)).catch(() => setItems([]));
  }, []);

  if (!items) return <Loader rows={5} />;

  return (
    <Card>
      {items.length === 0 ? (
        <EmptyState label="No audit entries yet — every admin action (approvals, user changes, payments, library issue/return) is logged here." />
      ) : (
        <div className="divide-y divide-slate-100">
          {items.map((a) => (
            <div key={a.id} className="py-3 text-sm flex items-center justify-between gap-4">
              <div>
                <p className="font-semibold text-slate-800">{a.action}</p>
                <p className="text-xs text-ink-secondary mt-0.5">
                  by {a.actor_name} · {a.target_type} #{a.target_id}
                </p>
              </div>
              <span className="text-xs text-slate-400 font-medium whitespace-nowrap">{new Date(a.created_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
