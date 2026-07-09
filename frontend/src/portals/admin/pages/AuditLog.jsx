import { useEffect, useState } from "react";
import api from "../lib/api";
import { Card, EmptyState, Loader } from "../components/Common";

export default function AuditLog() {
  const [items, setItems] = useState(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    api.get("/admin-portal/audit-log/").then(({ data }) => setItems(data)).catch(() => setItems([]));
  }, []);

  if (!items) return <Loader rows={5} />;

  const tabs = [
    { id: "all", label: "All Logs" },
    { id: "student", label: "Student Audits" },
    { id: "teacher", label: "Teacher Audits" },
    { id: "parent", label: "Parent Audits" },
  ];

  const filteredItems = items.filter((a) => {
    const act = a.action.toLowerCase();
    if (filter === "student") return act.includes("student");
    if (filter === "teacher") return act.includes("teacher");
    if (filter === "parent") return act.includes("parent");
    return true;
  });

  return (
    <Card>
      <div className="flex flex-wrap gap-2 mb-4 pb-3 border-b border-slate-100">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setFilter(t.id)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              filter === t.id
                ? "bg-academic-blue text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {filteredItems.length === 0 ? (
        <EmptyState label={`No ${filter !== "all" ? filter : ""} audit logs found.`} />
      ) : (
        <div className="divide-y divide-slate-100">
          {filteredItems.map((a) => (
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
