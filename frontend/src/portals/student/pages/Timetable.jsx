import { useEffect, useState } from "react";
import { Card, EmptyState, Loader } from "../components/Common";
import api from "../lib/api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export default function Timetable() {
  const [entries, setEntries] = useState(null);

  useEffect(() => {
    api
      .get("/student/timetable/")
      .then(({ data }) => setEntries(data))
      .catch(() => setEntries([]));
  }, []);

  if (!entries) return <Loader rows={6} />;
  if (!entries.length) return <EmptyState label="No timetable published for your class yet." />;

  const byDay = DAYS.map((day) => ({
    day,
    periods: entries.filter((e) => e.day_of_week === day).sort((a, b) => a.start_time.localeCompare(b.start_time)),
  }));

  return (
    <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
      {byDay.map(({ day, periods }) => (
        <Card key={day}>
          <p className="font-heading font-semibold mb-3">{day}</p>
          {periods.length ? (
            <ul className="space-y-3">
              {periods.map((p, idx) => (
                <li key={p.id} className="rounded-xl border border-slate-100/80 bg-slate-50/50 p-4 space-y-2.5 transition-all hover:shadow-sm">
                  {/* Period badge and time */}
                  <div className="flex items-center justify-between border-b border-slate-100/60 pb-2">
                    <span className="text-[10px] font-bold text-academic-orange uppercase tracking-wider">
                      Period {idx + 1}
                    </span>
                    <span className="text-[11px] font-numeric font-semibold text-academic-blue bg-academic-blue/5 px-2 py-0.5 rounded-md">
                      {p.start_time.slice(0, 5)} – {p.end_time.slice(0, 5)}
                    </span>
                  </div>

                  {/* Teacher & Subject */}
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-ink-primary">{p.subject_name}</p>
                    <p className="text-xs text-slate-500 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-academic-gold shrink-0"></span>
                      <span className="truncate">{p.teacher_name}</span>
                    </p>
                  </div>

                  {/* Room & Link */}
                  <div className="flex items-center justify-between pt-1 text-xs">
                    <div className="text-slate-500 font-medium">
                      🏢 Classroom: <span className="text-ink-primary font-semibold">{p.room_number}</span>
                    </div>
                    {p.meeting_link && (
                      <a
                        href={p.meeting_link}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 text-[10px] font-bold bg-academic-green/10 text-academic-green hover:bg-academic-green/20 px-2.5 py-1 rounded-lg transition-colors uppercase tracking-wider"
                      >
                        🎥 Join Online
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-ink-secondary">No periods scheduled.</p>
          )}
        </Card>
      ))}
    </div>
  );
}
