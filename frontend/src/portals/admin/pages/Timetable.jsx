import { useEffect, useState, useCallback } from "react";
import {
  Calendar, Plus, Trash2, Edit3, AlertTriangle,
  CheckCircle2, Clock, BookOpen, User, Building2,
  Link2, Coffee, Eye, EyeOff, X, RefreshCw,
} from "lucide-react";
import { Card, SectionTitle, Loader, Toast } from "../components/Common";
import api from "../lib/api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const DAY_COLORS = {
  Monday: "#3b82f6", Tuesday: "#8b5cf6", Wednesday: "#10b981",
  Thursday: "#f59e0b", Friday: "#ef4444", Saturday: "#6366f1",
};

const TABS = [
  { key: "grid", label: "Timetable Grid", icon: Calendar },
  { key: "conflicts", label: "Conflict Report", icon: AlertTriangle },
];

function fmt(t) {
  if (!t) return "";
  return t.slice(0, 5);
}

function todayName() {
  return ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"][new Date().getDay()];
}

// ── Period card ──────────────────────────────────────────────────────────────
function PeriodCard({ entry, onEdit, onDelete, isPublished }) {
  if (entry.is_break) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-amber-50 border border-amber-200">
        <Coffee size={14} className="text-amber-500 shrink-0" />
        <span className="text-xs font-medium text-amber-700">{entry.break_label || "Break"}</span>
        <span className="text-xs text-amber-500 ml-auto font-mono">
          {fmt(entry.start_time)}–{fmt(entry.end_time)}
        </span>
        {!isPublished && (
          <button onClick={() => onDelete(entry.id)} className="ml-1 text-amber-400 hover:text-red-500 transition-colors">
            <X size={12} />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="group rounded-xl border border-slate-200 bg-white p-3 hover:shadow-md transition-all hover:border-academic-blue/30">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-bold text-academic-blue truncate">
            P{entry.period_number} · {fmt(entry.start_time)}–{fmt(entry.end_time)}
          </p>
          <p className="text-sm font-semibold text-ink-primary truncate mt-0.5">
            {entry.subject_name || <span className="italic text-slate-400">No subject</span>}
          </p>
          <p className="text-xs text-slate-500 flex items-center gap-1 mt-1 truncate">
            <User size={10} className="shrink-0" />
            {entry.teacher_name || "—"}
          </p>
          {entry.room_number && (
            <p className="text-xs text-slate-400 flex items-center gap-1 truncate">
              <Building2 size={10} className="shrink-0" />
              {entry.room_number}
            </p>
          )}
          {entry.meeting_link && (
            <a
              href={entry.meeting_link}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-academic-blue flex items-center gap-1 hover:underline mt-0.5"
            >
              <Link2 size={10} />
              Online Link
            </a>
          )}
        </div>
        {!isPublished && (
          <div className="flex gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => onEdit(entry)}
              className="p-1 rounded-lg text-slate-400 hover:text-academic-blue hover:bg-blue-50 transition-colors"
            >
              <Edit3 size={13} />
            </button>
            <button
              onClick={() => onDelete(entry.id)}
              className="p-1 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
            >
              <Trash2 size={13} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Add/Edit Modal ───────────────────────────────────────────────────────────
function PeriodModal({ meta, classId, academicYear, editEntry, onSave, onClose }) {
  const isEdit = !!(editEntry?.id);
  const [form, setForm] = useState({
    class_id: classId,
    day_of_week: editEntry?.day_of_week || "Monday",
    period_number: editEntry?.period_number || 1,
    start_time: editEntry?.start_time ? fmt(editEntry.start_time) : "08:00",
    end_time: editEntry?.end_time ? fmt(editEntry.end_time) : "08:45",
    subject_id: editEntry?.subject_id || "",
    teacher_id: editEntry?.teacher_id || "",
    room_number: editEntry?.room_number || "",
    meeting_link: editEntry?.meeting_link || "",
    is_break: editEntry?.is_break || false,
    break_label: editEntry?.break_label || "Break",
    academic_year: academicYear,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (isEdit) {
        await api.patch(`/admin-portal/timetable/${editEntry.id}/`, form);
      } else {
        await api.post("/admin-portal/timetable/", form);
      }
      onSave();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail || "Failed to save period.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.5)" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden max-h-[90vh] flex flex-col">
        <div className="bg-academic-blue px-6 py-4 flex items-center justify-between shrink-0">
          <p className="font-bold text-white text-base">
            {isEdit ? "Edit Period" : "Add Period / Break"}
          </p>
          <button onClick={onClose} className="text-white/70 hover:text-white">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 flex items-start gap-2">
              <AlertTriangle size={16} className="shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {/* Is Break toggle */}
          <label className="flex items-center gap-3 cursor-pointer">
            <div
              onClick={() => setForm(f => ({ ...f, is_break: !f.is_break }))}
              className={`w-11 h-6 rounded-full transition-colors flex items-center px-1 cursor-pointer ${form.is_break ? "bg-amber-400" : "bg-slate-200"}`}
            >
              <div className={`w-4 h-4 rounded-full bg-white shadow transition-transform ${form.is_break ? "translate-x-5" : ""}`} />
            </div>
            <span className="text-sm font-medium text-ink-primary">This is a break / recess</span>
          </label>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">Day *</label>
              <select
                required
                value={form.day_of_week}
                onChange={e => setForm(f => ({ ...f, day_of_week: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-academic-blue/30"
              >
                {DAYS.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>
            {!form.is_break ? (
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">Period #</label>
                <input
                  type="number" min={1} max={12}
                  value={form.period_number}
                  onChange={e => setForm(f => ({ ...f, period_number: e.target.value }))}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-academic-blue/30"
                />
              </div>
            ) : (
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">Break Label</label>
                <input
                  value={form.break_label}
                  onChange={e => setForm(f => ({ ...f, break_label: e.target.value }))}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-academic-blue/30"
                  placeholder="Lunch Break"
                />
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">Start Time *</label>
              <input
                required type="time"
                value={form.start_time}
                onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-academic-blue/30"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">End Time *</label>
              <input
                required type="time"
                value={form.end_time}
                onChange={e => setForm(f => ({ ...f, end_time: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-academic-blue/30"
              />
            </div>
          </div>

          {!form.is_break && (
            <>
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">Subject</label>
                <select
                  value={form.subject_id}
                  onChange={e => setForm(f => ({ ...f, subject_id: e.target.value }))}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-academic-blue/30"
                >
                  <option value="">— Select subject —</option>
                  {meta.subjects.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">Teacher</label>
                <select
                  value={form.teacher_id}
                  onChange={e => setForm(f => ({ ...f, teacher_id: e.target.value }))}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-academic-blue/30"
                >
                  <option value="">— Select teacher —</option>
                  {meta.teachers.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">Room / Lab</label>
                  <input
                    value={form.room_number}
                    onChange={e => setForm(f => ({ ...f, room_number: e.target.value }))}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-academic-blue/30"
                    placeholder="e.g. A101"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">Online Link</label>
                  <input
                    value={form.meeting_link}
                    onChange={e => setForm(f => ({ ...f, meeting_link: e.target.value }))}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-academic-blue/30"
                    placeholder="https://meet.google.com/..."
                  />
                </div>
              </div>
            </>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-medium text-ink-secondary hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={loading}
              className="flex-1 rounded-xl bg-academic-blue text-white py-2.5 text-sm font-semibold hover:bg-academic-blue/90 disabled:opacity-60 transition-colors"
            >
              {loading ? "Saving…" : isEdit ? "Update Period" : "Add Period"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Stat card ────────────────────────────────────────────────────────────────
function Stat({ label, value, icon, bgClass }) {
  return (
    <div className={`rounded-xl p-4 flex items-center gap-3 ${bgClass}`}>
      {icon}
      <div>
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-xs font-medium opacity-75">{label}</p>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────
export default function Timetable() {
  const [tab, setTab] = useState("grid");
  const [meta, setMeta] = useState(null);
  const [selectedClass, setSelectedClass] = useState("");
  const [academicYear, setAcademicYear] = useState("2025-26");
  const [entries, setEntries] = useState(null);
  const [conflicts, setConflicts] = useState(null);
  const [isPublished, setIsPublished] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editEntry, setEditEntry] = useState(null);
  const [toast, setToast] = useState(null);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    api.get("/admin-portal/timetable/meta/")
      .then(({ data }) => {
        setMeta(data);
        if (data.classes?.length) setSelectedClass(String(data.classes[0].id));
      })
      .catch(() => setMeta({ classes: [], subjects: [], teachers: [], days: DAYS, academic_years: ["2025-26"] }));
  }, []);

  const loadEntries = useCallback(() => {
    if (!selectedClass) return;
    setEntries(null);
    api.get(`/admin-portal/timetable/?class_id=${selectedClass}&academic_year=${academicYear}`)
      .then(({ data }) => {
        setEntries(data);
        setIsPublished(data.length > 0 && data.every(e => e.is_published));
      })
      .catch(() => setEntries([]));
  }, [selectedClass, academicYear]);

  useEffect(() => { loadEntries(); }, [loadEntries]);

  const loadConflicts = useCallback(() => {
    if (tab !== "conflicts") return;
    setConflicts(null);
    api.get(`/admin-portal/timetable/conflicts/?academic_year=${academicYear}`)
      .then(({ data }) => setConflicts(data))
      .catch(() => setConflicts({ teacher_conflicts: [], room_conflicts: [] }));
  }, [tab, academicYear]);

  useEffect(() => { loadConflicts(); }, [loadConflicts]);

  async function handleDelete(id) {
    if (!window.confirm("Remove this period?")) return;
    try {
      await api.delete(`/admin-portal/timetable/${id}/`);
      setToast({ message: "Period removed.", tone: "success" });
      loadEntries();
    } catch {
      setToast({ message: "Could not delete period.", tone: "error" });
    }
  }

  async function handlePublish() {
    setPublishing(true);
    try {
      const publish = !isPublished;
      await api.post("/admin-portal/timetable/publish/", {
        class_id: selectedClass, academic_year: academicYear, publish,
      });
      setIsPublished(publish);
      setToast({
        message: publish
          ? "Timetable published! Students and teachers can now view it."
          : "Timetable unpublished.",
        tone: publish ? "success" : "info",
      });
      loadEntries();
    } catch {
      setToast({ message: "Could not update publish status.", tone: "error" });
    } finally {
      setPublishing(false);
    }
  }

  function handleModalSave() {
    setShowModal(false);
    setEditEntry(null);
    loadEntries();
    setToast({ message: "Period saved successfully.", tone: "success" });
  }

  const byDay = DAYS.map(day => ({
    day,
    entries: (entries || [])
      .filter(e => e.day_of_week === day)
      .sort((a, b) => (a.start_time || "").localeCompare(b.start_time || "")),
  }));

  const today = todayName();

  return (
    <div className="space-y-6">
      {toast && <Toast message={toast.message} tone={toast.tone} onClose={() => setToast(null)} />}

      {showModal && meta && (
        <PeriodModal
          meta={meta}
          classId={selectedClass}
          academicYear={academicYear}
          editEntry={editEntry}
          onSave={handleModalSave}
          onClose={() => { setShowModal(false); setEditEntry(null); }}
        />
      )}

      {/* Header */}
      <div className="flex flex-wrap items-start gap-4 justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-ink-primary">Timetable Management</h1>
          <p className="text-sm text-ink-secondary mt-1">
            Build and publish class schedules. Changes sync to student, teacher and parent portals automatically.
          </p>
        </div>
        {tab === "grid" && selectedClass && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => { setEditEntry(null); setShowModal(true); }}
              disabled={isPublished}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-academic-blue text-white text-sm font-semibold hover:bg-academic-blue/90 disabled:opacity-50 transition-colors"
            >
              <Plus size={16} /> Add Period
            </button>
            <button
              onClick={handlePublish}
              disabled={publishing || !entries?.length}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 ${
                isPublished
                  ? "bg-amber-500 text-white hover:bg-amber-600"
                  : "bg-emerald-600 text-white hover:bg-emerald-700"
              }`}
            >
              {publishing ? <RefreshCw size={16} className="animate-spin" /> : isPublished ? <EyeOff size={16} /> : <Eye size={16} />}
              {publishing ? "Updating…" : isPublished ? "Unpublish" : "Publish Timetable"}
            </button>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-xl p-1 w-fit">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === key ? "bg-white text-academic-blue shadow-sm" : "text-slate-500 hover:text-ink-primary"
            }`}
          >
            <Icon size={15} /> {label}
          </button>
        ))}
      </div>

      {/* ── GRID TAB ─────────────────────────────────────────────────────── */}
      {tab === "grid" && (
        <>
          <Card>
            <div className="flex flex-wrap gap-4 items-end">
              <div className="min-w-[200px]">
                <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">Class</label>
                {!meta ? <div className="h-9 rounded-xl bg-slate-100 animate-pulse" /> : (
                  <select
                    value={selectedClass}
                    onChange={e => setSelectedClass(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-academic-blue/30"
                  >
                    {meta.classes.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                  </select>
                )}
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">Academic Year</label>
                <select
                  value={academicYear}
                  onChange={e => setAcademicYear(e.target.value)}
                  className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-academic-blue/30"
                >
                  {(meta?.academic_years || ["2025-26"]).map(y => <option key={y}>{y}</option>)}
                </select>
              </div>
              {isPublished && (
                <div className="flex items-center gap-2 px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-sm font-medium">
                  <CheckCircle2 size={15} /> Published — students can see this timetable
                </div>
              )}
            </div>
          </Card>

          {!entries ? (
            <Loader rows={4} />
          ) : entries.length === 0 ? (
            <Card>
              <div className="text-center py-14">
                <Calendar size={44} className="mx-auto text-slate-300 mb-3" />
                <p className="font-semibold text-slate-500">No timetable entries yet.</p>
                <p className="text-sm text-slate-400 mt-1">Click "Add Period" to start building the schedule.</p>
              </div>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
              {byDay.map(({ day, entries: dayEntries }) => {
                const isToday = day === today;
                const color = DAY_COLORS[day];
                return (
                  <Card key={day} className={isToday ? "ring-2 ring-academic-blue/40 shadow-md" : ""}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
                        <p className="font-heading font-bold text-ink-primary">{day}</p>
                        {isToday && (
                          <span className="text-[10px] font-bold bg-academic-blue text-white px-2 py-0.5 rounded-full">TODAY</span>
                        )}
                      </div>
                      <span className="text-xs text-slate-400">{dayEntries.length} slot{dayEntries.length !== 1 ? "s" : ""}</span>
                    </div>

                    {dayEntries.length === 0 ? (
                      <p className="text-xs text-slate-400 italic text-center py-4">No classes scheduled</p>
                    ) : (
                      <div className="space-y-2">
                        {dayEntries.map(entry => (
                          <PeriodCard
                            key={entry.id}
                            entry={entry}
                            isPublished={isPublished}
                            onEdit={e => { setEditEntry(e); setShowModal(true); }}
                            onDelete={handleDelete}
                          />
                        ))}
                      </div>
                    )}

                    {!isPublished && (
                      <button
                        onClick={() => { setEditEntry({ day_of_week: day, is_break: false }); setShowModal(true); }}
                        className="mt-3 w-full flex items-center justify-center gap-1.5 py-1.5 rounded-xl border border-dashed border-slate-200 text-xs text-slate-400 hover:border-academic-blue/40 hover:text-academic-blue transition-colors"
                      >
                        <Plus size={12} /> Add to {day}
                      </button>
                    )}
                  </Card>
                );
              })}
            </div>
          )}

          {entries?.length > 0 && (
            <Card>
              <SectionTitle>Schedule Summary</SectionTitle>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <Stat label="Total Periods" value={entries.filter(e => !e.is_break).length}
                  icon={<Clock size={20} className="text-academic-blue" />} bgClass="bg-blue-50 text-academic-blue" />
                <Stat label="Subjects" value={new Set(entries.filter(e => e.subject_id).map(e => e.subject_id)).size}
                  icon={<BookOpen size={20} className="text-academic-gold" />} bgClass="bg-yellow-50 text-yellow-700" />
                <Stat label="Teachers" value={new Set(entries.filter(e => e.teacher_id).map(e => e.teacher_id)).size}
                  icon={<User size={20} className="text-emerald-600" />} bgClass="bg-emerald-50 text-emerald-700" />
                <Stat label="Breaks" value={entries.filter(e => e.is_break).length}
                  icon={<Coffee size={20} className="text-amber-500" />} bgClass="bg-amber-50 text-amber-700" />
              </div>
            </Card>
          )}
        </>
      )}

      {/* ── CONFLICTS TAB ─────────────────────────────────────────────────── */}
      {tab === "conflicts" && (
        <div className="space-y-4">
          <Card>
            <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">Academic Year</label>
            <select
              value={academicYear}
              onChange={e => { setAcademicYear(e.target.value); setConflicts(null); }}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-academic-blue/30"
            >
              {(meta?.academic_years || ["2025-26"]).map(y => <option key={y}>{y}</option>)}
            </select>
          </Card>

          {!conflicts ? <Loader rows={3} /> : (
            <>
              <Card>
                <SectionTitle>Teacher Conflicts</SectionTitle>
                {conflicts.teacher_conflicts.length === 0 ? (
                  <div className="flex items-center gap-2 text-emerald-600 text-sm py-3">
                    <CheckCircle2 size={18} /> No teacher conflicts found.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {conflicts.teacher_conflicts.map((c, i) => (
                      <div key={i} className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm">
                        <div className="flex items-start gap-2">
                          <AlertTriangle size={16} className="text-red-500 shrink-0 mt-0.5" />
                          <div>
                            <p className="font-bold text-red-800">{c.teacher_name}</p>
                            <p className="text-red-700">
                              Assigned to <strong>{c.class_a}</strong> ({c.subject_a}) and{" "}
                              <strong>{c.class_b}</strong> ({c.subject_b}) on <strong>{c.day_of_week}</strong>{" "}
                              at {fmt(c.start_time)}–{fmt(c.end_time)}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              <Card>
                <SectionTitle>Room Conflicts</SectionTitle>
                {conflicts.room_conflicts.length === 0 ? (
                  <div className="flex items-center gap-2 text-emerald-600 text-sm py-3">
                    <CheckCircle2 size={18} /> No room conflicts found.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {conflicts.room_conflicts.map((c, i) => (
                      <div key={i} className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm">
                        <div className="flex items-start gap-2">
                          <Building2 size={16} className="text-amber-600 shrink-0 mt-0.5" />
                          <div>
                            <p className="font-bold text-amber-800">Room {c.room_number}</p>
                            <p className="text-amber-700">
                              Double-booked for <strong>{c.class_a}</strong> and <strong>{c.class_b}</strong>{" "}
                              on <strong>{c.day_of_week}</strong> at {fmt(c.start_time)}–{fmt(c.end_time)}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  );
}
