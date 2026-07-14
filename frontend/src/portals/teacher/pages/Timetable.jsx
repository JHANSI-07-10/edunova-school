import { useEffect, useState } from "react";
import { Clock, BookOpen, Users, Building2, Calendar } from "lucide-react";
import { Card, EmptyState, Loader } from "../components/Common";
import api from "../lib/api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const DAY_COLORS = {
  Monday: { dot: "#3b82f6", bg: "bg-blue-50", text: "text-blue-700" },
  Tuesday: { dot: "#8b5cf6", bg: "bg-purple-50", text: "text-purple-700" },
  Wednesday: { dot: "#10b981", bg: "bg-emerald-50", text: "text-emerald-700" },
  Thursday: { dot: "#f59e0b", bg: "bg-amber-50", text: "text-amber-700" },
  Friday: { dot: "#ef4444", bg: "bg-red-50", text: "text-red-700" },
  Saturday: { dot: "#6366f1", bg: "bg-indigo-50", text: "text-indigo-700" },
};

function fmt(t) { return t ? t.slice(0, 5) : ""; }
function todayName() {
  return ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"][new Date().getDay()];
}

export default function Timetable() {
  const [entries, setEntries] = useState(null);
  const [activeDay, setActiveDay] = useState(todayName());

  useEffect(() => {
    api.get("/teacher/timetable/")
      .then(({ data }) => setEntries(data))
      .catch(() => setEntries([]));
  }, []);

  if (!entries) return <Loader rows={6} />;
  if (!entries.length) return <EmptyState label="No timetable assigned yet. Contact the administrator." />;

  const today = todayName();
  const activePeriods = entries
    .filter(e => e.day_of_week === activeDay)
    .sort((a, b) => (a.start_time || "").localeCompare(b.start_time || ""));

  // Weekly stats
  const totalPeriods = entries.length;
  const uniqueClasses = new Set(entries.map(e => e.class_name)).size;
  const uniqueSubjects = new Set(entries.map(e => e.subject_name)).size;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold text-ink-primary">My Teaching Schedule</h1>
        <p className="text-sm text-ink-secondary mt-1">Your weekly timetable across all assigned classes</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-blue-50 rounded-xl p-4 flex items-center gap-3">
          <Clock size={20} className="text-academic-blue" />
          <div>
            <p className="text-2xl font-bold text-academic-blue">{totalPeriods}</p>
            <p className="text-xs text-blue-600">Periods / Week</p>
          </div>
        </div>
        <div className="bg-emerald-50 rounded-xl p-4 flex items-center gap-3">
          <Users size={20} className="text-emerald-600" />
          <div>
            <p className="text-2xl font-bold text-emerald-700">{uniqueClasses}</p>
            <p className="text-xs text-emerald-600">Classes</p>
          </div>
        </div>
        <div className="bg-purple-50 rounded-xl p-4 flex items-center gap-3">
          <BookOpen size={20} className="text-purple-600" />
          <div>
            <p className="text-2xl font-bold text-purple-700">{uniqueSubjects}</p>
            <p className="text-xs text-purple-600">Subjects</p>
          </div>
        </div>
      </div>

      {/* Day selector */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {DAYS.map(day => {
          const hasPeriods = entries.some(e => e.day_of_week === day);
          const colors = DAY_COLORS[day];
          const isToday = day === today;
          const isActive = day === activeDay;
          return (
            <button
              key={day}
              onClick={() => hasPeriods && setActiveDay(day)}
              className={`flex-shrink-0 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? `${colors.bg} ${colors.text} ring-2 ring-current/30 shadow-sm`
                  : hasPeriods
                  ? "bg-white border border-slate-200 text-ink-secondary hover:bg-slate-50"
                  : "bg-slate-50 text-slate-300"
              }`}
            >
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{ background: hasPeriods ? colors.dot : "#cbd5e1" }} />
                {day.slice(0, 3)}
                {isToday && <span className="text-[9px] font-bold bg-academic-blue text-white px-1.5 py-0.5 rounded-full">NOW</span>}
              </div>
            </button>
          );
        })}
      </div>

      {/* Day schedule */}
      <div>
        <h2 className="font-heading font-semibold text-ink-primary mb-3">{activeDay}</h2>
        {activePeriods.length === 0 ? (
          <Card><p className="text-center text-slate-400 py-8 text-sm">No classes on {activeDay}</p></Card>
        ) : (
          <div className="space-y-3">
            {activePeriods.map(p => {
              const colors = DAY_COLORS[activeDay];
              return (
                <Card key={p.id} className="hover:shadow-md transition-all">
                  <div className="flex items-start gap-4">
                    <div className={`${colors.bg} ${colors.text} rounded-xl px-3 py-2 text-center shrink-0`}>
                      <p className="text-xs font-mono font-bold">{fmt(p.start_time)}</p>
                      <p className="text-[10px] text-current/60">–</p>
                      <p className="text-xs font-mono font-bold">{fmt(p.end_time)}</p>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-ink-primary">{p.class_name}</p>
                      <p className="text-sm text-ink-secondary">{p.subject_name}</p>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Weekly grid */}
      <div>
        <h2 className="font-heading font-semibold text-ink-primary mb-4 flex items-center gap-2">
          <Calendar size={18} /> Full Week View
        </h2>
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {DAYS.map(day => {
            const periods = entries.filter(e => e.day_of_week === day)
              .sort((a, b) => (a.start_time || "").localeCompare(b.start_time || ""));
            const isToday = day === today;
            const colors = DAY_COLORS[day];
            return (
              <Card key={day} className={`cursor-pointer hover:shadow-md transition-all ${isToday ? "ring-2 ring-academic-blue/40" : ""}`}
                onClick={() => periods.length && setActiveDay(day)}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ background: colors.dot }} />
                    <p className="font-heading font-bold text-sm text-ink-primary">{day}</p>
                    {isToday && <span className="text-[9px] font-bold bg-academic-blue text-white px-1.5 py-0.5 rounded-full">TODAY</span>}
                  </div>
                  <span className="text-xs text-slate-400">{periods.length} period{periods.length !== 1 ? "s" : ""}</span>
                </div>
                {periods.length === 0 ? (
                  <p className="text-xs text-slate-300 italic">No classes</p>
                ) : (
                  <div className="space-y-1.5">
                    {periods.map(p => (
                      <div key={p.id} className="flex items-center gap-2 text-xs">
                        <Clock size={11} className="text-slate-400 shrink-0" />
                        <span className="text-slate-600 truncate font-medium">{p.class_name}</span>
                        <span className="text-slate-400 truncate">{p.subject_name}</span>
                        <span className="ml-auto text-slate-400 font-mono shrink-0">{fmt(p.start_time)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
