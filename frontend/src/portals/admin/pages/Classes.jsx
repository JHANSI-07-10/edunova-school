import { useEffect, useState } from "react";
import api from "../lib/api";
import { Card, EmptyState, Loader, SectionTitle, Toast } from "../components/Common";
import { BookOpen, UserCheck, GraduationCap, Pencil, Trash2, X, Check, CheckCircle, ArrowRight, Users, User } from "lucide-react";

// ── Tiny helpers ────────────────────────────────────────────────────────────
function Btn({ children, onClick, variant = "primary", disabled = false, className = "" }) {
  const base = "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-50 flex items-center gap-1.5";
  const variants = {
    primary: "bg-academic-blue text-white hover:bg-academic-blue/90",
    danger: "bg-red-50 text-red-600 border border-red-200 hover:bg-red-100",
    ghost: "bg-slate-100 text-slate-600 hover:bg-slate-200",
    success: "bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100",
  };
  return (
    <button onClick={onClick} disabled={disabled} className={`${base} ${variants[variant]} ${className}`}>
      {children}
    </button>
  );
}

function ConfirmDeleteModal({ label, onConfirm, onCancel }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.4)" }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
        <p className="text-base font-bold text-slate-800 mb-2">Delete?</p>
        <p className="text-sm text-slate-500 mb-5">{label}</p>
        <div className="flex gap-3 justify-end">
          <Btn variant="ghost" onClick={onCancel}>Cancel</Btn>
          <Btn variant="danger" onClick={onConfirm}><Trash2 size={12} /> Delete</Btn>
        </div>
      </div>
    </div>
  );
}

// ── Tab 1: Classes & Subjects ────────────────────────────────────────────────
function TabConfig({ classes, subjects, loadClasses, loadSubjects, setToast, onClassCreated }) {
  const [classForm, setClassForm] = useState({ name: "", section: "", curriculum: "CBSE", room_number: "" });
  const [subjectForm, setSubjectForm] = useState({ name: "", subject_code: "", type: "Theory" });
  const [editingClass, setEditingClass] = useState(null); // { id, name, section, curriculum, room_number }
  const [editingSubject, setEditingSubject] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null); // { kind, id, label }

  async function addClass(e) {
    e.preventDefault();
    try {
      const { data } = await api.post("/admin-portal/classes/", classForm);
      setClassForm({ name: "", section: "", curriculum: "CBSE", room_number: "" });
      loadClasses();
      setToast({ message: `Class "${data.name}-${data.section}" created! Complete setup ↓`, tone: "success" });
      if (onClassCreated) onClassCreated(data);
    } catch (err) { setToast({ message: err?.response?.data?.detail || "Could not create class.", tone: "error" }); }
  }

  async function saveEditClass() {
    try {
      await api.patch(`/admin-portal/classes/${editingClass.id}/`, editingClass);
      setEditingClass(null);
      loadClasses();
      setToast({ message: "Class updated.", tone: "success" });
    } catch (err) { setToast({ message: err?.response?.data?.detail || "Could not update class.", tone: "error" }); }
  }

  async function deleteClass(id) {
    try {
      await api.delete(`/admin-portal/classes/${id}/`);
      loadClasses();
      setToast({ message: "Class deleted.", tone: "success" });
    } catch (err) {
      setToast({ message: err?.response?.data?.detail || "Could not delete class. It may have enrollments.", tone: "error" });
    } finally { setDeleteTarget(null); }
  }

  async function addSubject(e) {
    e.preventDefault();
    try {
      await api.post("/admin-portal/subjects/", subjectForm);
      setSubjectForm({ name: "", subject_code: "", type: "Theory" });
      loadSubjects();
      setToast({ message: "Subject created successfully.", tone: "success" });
    } catch (err) { setToast({ message: err?.response?.data?.detail || "Could not create subject.", tone: "error" }); }
  }

  async function saveEditSubject() {
    try {
      await api.patch(`/admin-portal/subjects/${editingSubject.id}/`, editingSubject);
      setEditingSubject(null);
      loadSubjects();
      setToast({ message: "Subject updated.", tone: "success" });
    } catch (err) { setToast({ message: err?.response?.data?.detail || "Could not update subject.", tone: "error" }); }
  }

  async function deleteSubject(id) {
    try {
      await api.delete(`/admin-portal/subjects/${id}/`);
      loadSubjects();
      setToast({ message: "Subject deleted.", tone: "success" });
    } catch (err) {
      setToast({ message: err?.response?.data?.detail || "Could not delete subject.", tone: "error" });
    } finally { setDeleteTarget(null); }
  }

  return (
    <>
      {deleteTarget && (
        <ConfirmDeleteModal
          label={`Are you sure you want to delete "${deleteTarget.label}"? This cannot be undone.`}
          onConfirm={() => deleteTarget.kind === "class" ? deleteClass(deleteTarget.id) : deleteSubject(deleteTarget.id)}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        {/* ── Classes ── */}
        <div className="space-y-4">
          <Card>
            <SectionTitle>Add Class</SectionTitle>
            <form onSubmit={addClass} className="grid grid-cols-2 gap-3">
              <input required placeholder="Name (e.g. Grade 6)" value={classForm.name}
                onChange={(e) => setClassForm({ ...classForm, name: e.target.value })}
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus-ring outline-none" />
              <input required placeholder="Section (e.g. A)" value={classForm.section}
                onChange={(e) => setClassForm({ ...classForm, section: e.target.value })}
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus-ring outline-none" />
              <select value={classForm.curriculum}
                onChange={(e) => setClassForm({ ...classForm, curriculum: e.target.value })}
                className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus-ring outline-none">
                <option>CBSE</option><option>Cambridge</option>
              </select>
              <input placeholder="Room number" value={classForm.room_number}
                onChange={(e) => setClassForm({ ...classForm, room_number: e.target.value })}
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus-ring outline-none" />
              <button className="col-span-2 bg-academic-blue text-white rounded-xl py-2.5 font-medium hover:bg-academic-blue/90">
                Add Class
              </button>
            </form>
          </Card>

          <Card>
            <SectionTitle>All Classes</SectionTitle>
            {!classes ? <Loader rows={3} /> : classes.length === 0 ? <EmptyState label="No classes yet." /> : (
              <div className="divide-y divide-slate-100">
                {classes.map((c) => (
                  <div key={c.id} className="py-2.5 text-sm">
                    {editingClass?.id === c.id ? (
                      <div className="space-y-2">
                        <div className="grid grid-cols-2 gap-2">
                          <input value={editingClass.name}
                            onChange={(e) => setEditingClass({ ...editingClass, name: e.target.value })}
                            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm outline-none focus-ring" />
                          <input value={editingClass.section}
                            onChange={(e) => setEditingClass({ ...editingClass, section: e.target.value })}
                            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm outline-none focus-ring" />
                          <select value={editingClass.curriculum}
                            onChange={(e) => setEditingClass({ ...editingClass, curriculum: e.target.value })}
                            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm outline-none focus-ring">
                            <option>CBSE</option><option>Cambridge</option>
                          </select>
                          <input value={editingClass.room_number || ""}
                            onChange={(e) => setEditingClass({ ...editingClass, room_number: e.target.value })}
                            placeholder="Room"
                            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm outline-none focus-ring" />
                        </div>
                        <div className="flex gap-2">
                          <Btn variant="success" onClick={saveEditClass}><Check size={12} /> Save</Btn>
                          <Btn variant="ghost" onClick={() => setEditingClass(null)}><X size={12} /> Cancel</Btn>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <span className="font-medium text-slate-700">{c.name}-{c.section}</span>
                          <span className="text-ink-secondary ml-2">{c.curriculum} · Room {c.room_number || "—"}</span>
                        </div>
                        <div className="flex gap-1.5 shrink-0">
                          <Btn variant="ghost" onClick={() => setEditingClass({ ...c })}><Pencil size={12} /> Edit</Btn>
                          <Btn variant="danger" onClick={() => setDeleteTarget({ kind: "class", id: c.id, label: `${c.name}-${c.section}` })}><Trash2 size={12} /></Btn>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* ── Subjects ── */}
        <div className="space-y-4">
          <Card>
            <SectionTitle>Add Subject</SectionTitle>
            <form onSubmit={addSubject} className="grid grid-cols-2 gap-3">
              <input required placeholder="Name" value={subjectForm.name}
                onChange={(e) => setSubjectForm({ ...subjectForm, name: e.target.value })}
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus-ring outline-none" />
              <input required placeholder="Subject code" value={subjectForm.subject_code}
                onChange={(e) => setSubjectForm({ ...subjectForm, subject_code: e.target.value })}
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus-ring outline-none" />
              <select value={subjectForm.type}
                onChange={(e) => setSubjectForm({ ...subjectForm, type: e.target.value })}
                className="col-span-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus-ring outline-none">
                {["Theory", "Practical", "Lab", "Skill_Development"].map((t) => <option key={t}>{t}</option>)}
              </select>
              <button className="col-span-2 bg-academic-blue text-white rounded-xl py-2.5 font-medium hover:bg-academic-blue/90">
                Add Subject
              </button>
            </form>
          </Card>

          <Card>
            <SectionTitle>All Subjects</SectionTitle>
            {!subjects ? <Loader rows={3} /> : subjects.length === 0 ? <EmptyState label="No subjects yet." /> : (
              <div className="divide-y divide-slate-100">
                {subjects.map((s) => (
                  <div key={s.id} className="py-2.5 text-sm">
                    {editingSubject?.id === s.id ? (
                      <div className="space-y-2">
                        <div className="grid grid-cols-2 gap-2">
                          <input value={editingSubject.name}
                            onChange={(e) => setEditingSubject({ ...editingSubject, name: e.target.value })}
                            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm outline-none focus-ring" />
                          <input value={editingSubject.subject_code}
                            onChange={(e) => setEditingSubject({ ...editingSubject, subject_code: e.target.value })}
                            className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm outline-none focus-ring" />
                          <select value={editingSubject.type}
                            onChange={(e) => setEditingSubject({ ...editingSubject, type: e.target.value })}
                            className="col-span-2 rounded-lg border border-slate-200 px-2 py-1.5 text-sm outline-none focus-ring">
                            {["Theory", "Practical", "Lab", "Skill_Development"].map((t) => <option key={t}>{t}</option>)}
                          </select>
                        </div>
                        <div className="flex gap-2">
                          <Btn variant="success" onClick={saveEditSubject}><Check size={12} /> Save</Btn>
                          <Btn variant="ghost" onClick={() => setEditingSubject(null)}><X size={12} /> Cancel</Btn>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <span className="font-medium text-slate-700">{s.name}</span>
                          <span className="text-ink-secondary ml-2">{s.subject_code} · {s.type}</span>
                        </div>
                        <div className="flex gap-1.5 shrink-0">
                          <Btn variant="ghost" onClick={() => setEditingSubject({ ...s })}><Pencil size={12} /> Edit</Btn>
                          <Btn variant="danger" onClick={() => setDeleteTarget({ kind: "subject", id: s.id, label: s.name })}><Trash2 size={12} /></Btn>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}

// ── Tab 2: Student Enrollments ───────────────────────────────────────────────
function TabEnroll({ classes, students, enrollments, loadEnrollments, setToast }) {
  const [enrollForm, setEnrollForm] = useState({
    student_id: "", class_id: "", roll_number: "", academic_year: "2025-26",
  });
  const [editingRow, setEditingRow] = useState(null); // { id, class_id, roll_number, academic_year }
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [busy, setBusy] = useState(false);
  const [classFilter, setClassFilter] = useState("");

  async function handleEnroll(e) {
    e.preventDefault();
    if (!enrollForm.student_id || !enrollForm.class_id) {
      setToast({ message: "Please select both a student and a class.", tone: "error" });
      return;
    }
    setBusy(true);
    try {
      await api.post("/admin-portal/enrollments/", enrollForm);
      setEnrollForm({ student_id: "", class_id: "", roll_number: "", academic_year: "2025-26" });
      loadEnrollments();
      setToast({ message: "Student enrolled successfully.", tone: "success" });
    } catch (err) {
      setToast({ message: err?.response?.data?.detail || "Could not enroll student.", tone: "error" });
    } finally { setBusy(false); }
  }

  async function saveEdit() {
    try {
      await api.patch(`/admin-portal/enrollments/${editingRow.id}/`, {
        class_id: editingRow.class_id,
        roll_number: editingRow.roll_number,
        academic_year: editingRow.academic_year,
      });
      setEditingRow(null);
      loadEnrollments();
      setToast({ message: "Enrollment updated.", tone: "success" });
    } catch (err) {
      setToast({ message: err?.response?.data?.detail || "Could not update enrollment.", tone: "error" });
    }
  }

  async function doDelete(id) {
    try {
      await api.delete(`/admin-portal/enrollments/${id}/`);
      loadEnrollments();
      setToast({ message: "Enrollment removed.", tone: "success" });
    } catch (err) {
      setToast({ message: err?.response?.data?.detail || "Could not remove enrollment.", tone: "error" });
    } finally { setDeleteTarget(null); }
  }

  const filtered = classFilter
    ? enrollments.filter((e) => String(e.class_id) === classFilter)
    : enrollments;

  return (
    <>
      {deleteTarget && (
        <ConfirmDeleteModal
          label={`Remove ${deleteTarget.name} from ${deleteTarget.class}? This action cannot be undone.`}
          onConfirm={() => doDelete(deleteTarget.id)}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Form */}
        <Card>
          <SectionTitle>Enroll Student in Class</SectionTitle>
          <form onSubmit={handleEnroll} className="space-y-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Select Student</label>
              <select required value={enrollForm.student_id}
                onChange={(e) => setEnrollForm({ ...enrollForm, student_id: e.target.value })}
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus-ring">
                <option value="">-- Choose Student --</option>
                {students.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.username})</option>)}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Select Class</label>
              <select required value={enrollForm.class_id}
                onChange={(e) => setEnrollForm({ ...enrollForm, class_id: e.target.value })}
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus-ring">
                <option value="">-- Choose Class --</option>
                {classes?.map((c) => <option key={c.id} value={c.id}>{c.name}-{c.section} ({c.curriculum})</option>)}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-500 uppercase">Roll Number (Optional)</label>
                <input type="number" placeholder="Roll No" value={enrollForm.roll_number}
                  onChange={(e) => setEnrollForm({ ...enrollForm, roll_number: e.target.value })}
                  className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus-ring" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-500 uppercase">Academic Year</label>
                <input required placeholder="2025-26" value={enrollForm.academic_year}
                  onChange={(e) => setEnrollForm({ ...enrollForm, academic_year: e.target.value })}
                  className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus-ring" />
              </div>
            </div>

            <button disabled={busy}
              className="w-full bg-academic-blue text-white rounded-xl py-2.5 font-medium hover:bg-academic-blue/90 disabled:opacity-60">
              {busy ? "Enrolling..." : "Enroll Student"}
            </button>
          </form>
        </Card>

        {/* Roster */}
        <Card>
          <SectionTitle
            action={
              <select value={classFilter} onChange={(e) => setClassFilter(e.target.value)}
                className="rounded-lg border border-slate-200 px-2 py-1 text-xs">
                <option value="">All Classes</option>
                {classes?.map((c) => <option key={c.id} value={c.id}>{c.name}-{c.section}</option>)}
              </select>
            }
          >
            Enrolled Roster
          </SectionTitle>

          {filtered.length === 0 ? (
            <EmptyState label="No students enrolled yet." />
          ) : (
            <div className="divide-y divide-slate-100 max-h-[520px] overflow-y-auto pr-1">
              {filtered.map((e) => (
                <div key={e.id} className="py-2.5 text-sm">
                  {editingRow?.id === e.id ? (
                    <div className="space-y-2">
                      <p className="font-semibold text-slate-700">{e.student_name}</p>
                      <div className="grid grid-cols-3 gap-2">
                        <select value={editingRow.class_id}
                          onChange={(ev) => setEditingRow({ ...editingRow, class_id: ev.target.value })}
                          className="col-span-2 rounded-lg border border-slate-200 px-2 py-1.5 text-xs outline-none focus-ring">
                          {classes?.map((c) => <option key={c.id} value={c.id}>{c.name}-{c.section}</option>)}
                        </select>
                        <input type="number" placeholder="Roll" value={editingRow.roll_number || ""}
                          onChange={(ev) => setEditingRow({ ...editingRow, roll_number: ev.target.value })}
                          className="rounded-lg border border-slate-200 px-2 py-1.5 text-xs outline-none focus-ring" />
                      </div>
                      <input placeholder="Academic year" value={editingRow.academic_year}
                        onChange={(ev) => setEditingRow({ ...editingRow, academic_year: ev.target.value })}
                        className="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-xs outline-none focus-ring" />
                      <div className="flex gap-2">
                        <Btn variant="success" onClick={saveEdit}><Check size={12} /> Save</Btn>
                        <Btn variant="ghost" onClick={() => setEditingRow(null)}><X size={12} /> Cancel</Btn>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="font-semibold text-slate-700">{e.student_name}</p>
                        <p className="text-xs text-ink-secondary">
                          {e.student_username} · Year: {e.academic_year}
                          {e.roll_number ? ` · Roll: ${e.roll_number}` : ""}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="bg-academic-blue/10 text-academic-blue px-2.5 py-1 rounded-full text-xs font-semibold">
                          {e.class_name}
                        </span>
                        <Btn variant="ghost" onClick={() => setEditingRow({ ...e })}><Pencil size={12} /></Btn>
                        <Btn variant="danger" onClick={() => setDeleteTarget({ id: e.id, name: e.student_name, class: e.class_name })}><Trash2 size={12} /></Btn>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}

// ── Tab 3: Class Teachers ────────────────────────────────────────────────────
function TabTeachers({ classes, subjects, teachers, classTeachers, loadClassTeachers, setToast }) {
  const [teacherAssignForm, setTeacherAssignForm] = useState({ class_id: "", teacher_id: "", subject_id: "" });
  const [editingCT, setEditingCT] = useState(null); // { class_id, teacher_id }
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleTeacherAssign(e) {
    e.preventDefault();
    if (!teacherAssignForm.class_id || !teacherAssignForm.teacher_id) {
      setToast({ message: "Please select both a class and a teacher.", tone: "error" });
      return;
    }
    setBusy(true);
    try {
      await api.post("/admin-portal/class-teachers/", teacherAssignForm);
      setTeacherAssignForm({ class_id: "", teacher_id: "", subject_id: "" });
      loadClassTeachers();
      setToast({ message: "Class teacher assigned successfully.", tone: "success" });
    } catch (err) {
      setToast({ message: err?.response?.data?.detail || "Could not assign class teacher.", tone: "error" });
    } finally { setBusy(false); }
  }

  async function saveEditCT() {
    try {
      await api.patch(`/admin-portal/class-teachers/${editingCT.class_id}/`, { teacher_id: editingCT.teacher_id });
      setEditingCT(null);
      loadClassTeachers();
      setToast({ message: "Class teacher updated.", tone: "success" });
    } catch (err) {
      setToast({ message: err?.response?.data?.detail || "Could not update class teacher.", tone: "error" });
    }
  }

  async function doDelete(class_id) {
    try {
      await api.delete(`/admin-portal/class-teachers/${class_id}/`);
      loadClassTeachers();
      setToast({ message: "Class teacher assignment removed.", tone: "success" });
    } catch (err) {
      setToast({ message: err?.response?.data?.detail || "Could not remove assignment.", tone: "error" });
    } finally { setDeleteTarget(null); }
  }

  return (
    <>
      {deleteTarget && (
        <ConfirmDeleteModal
          label={`Remove the teacher assignment from ${deleteTarget.className}?`}
          onConfirm={() => doDelete(deleteTarget.class_id)}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Form */}
        <Card>
          <SectionTitle>Assign Class Teacher</SectionTitle>
          <form onSubmit={handleTeacherAssign} className="space-y-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Select Class</label>
              <select required value={teacherAssignForm.class_id}
                onChange={(e) => setTeacherAssignForm({ ...teacherAssignForm, class_id: e.target.value })}
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus-ring">
                <option value="">-- Choose Class --</option>
                {classes?.map((c) => <option key={c.id} value={c.id}>{c.name}-{c.section}</option>)}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Select Class Teacher</label>
              <select required value={teacherAssignForm.teacher_id}
                onChange={(e) => setTeacherAssignForm({ ...teacherAssignForm, teacher_id: e.target.value })}
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus-ring">
                <option value="">-- Choose Teacher --</option>
                {teachers.map((t) => <option key={t.id} value={t.id}>{t.name} ({t.email})</option>)}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Assign Subject (Optional)</label>
              <select value={teacherAssignForm.subject_id}
                onChange={(e) => setTeacherAssignForm({ ...teacherAssignForm, subject_id: e.target.value })}
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus-ring">
                <option value="">-- Choose Subject --</option>
                {subjects?.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.subject_code})</option>)}
              </select>
            </div>

            <button disabled={busy}
              className="w-full bg-academic-blue text-white rounded-xl py-2.5 font-medium hover:bg-academic-blue/90 disabled:opacity-60">
              {busy ? "Assigning..." : "Assign Class Teacher & Subject"}
            </button>
          </form>
        </Card>

        {/* Directory */}
        <Card>
          <SectionTitle>Class Teacher Directory</SectionTitle>
          {classTeachers.length === 0 ? (
            <EmptyState label="No class teachers assigned yet." />
          ) : (
            <div className="divide-y divide-slate-100">
              {classTeachers.map((ct) => (
                <div key={ct.class_id} className="py-3 text-sm">
                  {editingCT?.class_id === ct.class_id ? (
                    <div className="space-y-2">
                      <p className="font-semibold text-slate-700">{ct.class_name}</p>
                      <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold text-slate-500 uppercase">New Teacher</label>
                        <select value={editingCT.teacher_id}
                          onChange={(e) => setEditingCT({ ...editingCT, teacher_id: e.target.value })}
                          className="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm outline-none focus-ring">
                          {teachers.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                        </select>
                      </div>
                      <div className="flex gap-2">
                        <Btn variant="success" onClick={saveEditCT}><Check size={12} /> Save</Btn>
                        <Btn variant="ghost" onClick={() => setEditingCT(null)}><X size={12} /> Cancel</Btn>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="font-semibold text-slate-700 block">{ct.class_name}</span>
                        {ct.assigned_subjects?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {ct.assigned_subjects.map((sub) => (
                              <span key={sub.id} className="bg-slate-100 text-slate-600 text-[10px] font-semibold px-2 py-0.5 rounded border border-slate-200">
                                {sub.name}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="bg-emerald-50 text-emerald-700 border border-emerald-100 px-2.5 py-1 rounded-full text-xs font-semibold">
                          👤 {ct.teacher_name}
                        </span>
                        <Btn variant="ghost" onClick={() => setEditingCT({ class_id: ct.class_id, teacher_id: String(ct.teacher_id) })}><Pencil size={12} /></Btn>
                        <Btn variant="danger" onClick={() => setDeleteTarget({ class_id: ct.class_id, className: ct.class_name })}><Trash2 size={12} /></Btn>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}

// ── Root Page ────────────────────────────────────────────────────────────────
export default function Classes() {
  const [activeTab, setActiveTab] = useState("config");
  const [classes, setClasses] = useState(null);
  const [subjects, setSubjects] = useState(null);
  const [students, setStudents] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [classTeachers, setClassTeachers] = useState([]);
  const [toast, setToast] = useState(null);
  const [newlyCreated, setNewlyCreated] = useState(null);
  const [prefilledEnrollClassId, setPrefilledEnrollClassId] = useState("");
  const [prefilledTeacherClassId, setPrefilledTeacherClassId] = useState("");

  function loadClasses() { api.get("/admin-portal/classes/").then(({ data }) => setClasses(data)).catch(() => setClasses([])); }
  function loadSubjects() { api.get("/admin-portal/subjects/").then(({ data }) => setSubjects(data)).catch(() => setSubjects([])); }
  function loadStudents() { api.get("/admin-portal/users/?role=Student").then(({ data }) => setStudents(data)).catch(() => setStudents([])); }
  function loadTeachers() { api.get("/admin-portal/users/?role=Teacher").then(({ data }) => setTeachers(data)).catch(() => setTeachers([])); }
  function loadEnrollments() { api.get("/admin-portal/enrollments/").then(({ data }) => setEnrollments(data)).catch(() => setEnrollments([])); }
  function loadClassTeachers() { api.get("/admin-portal/class-teachers/").then(({ data }) => setClassTeachers(data)).catch(() => setClassTeachers([])); }

  useEffect(() => {
    loadClasses(); loadSubjects(); loadStudents();
    loadTeachers(); loadEnrollments(); loadClassTeachers();
  }, []);

  function handleClassCreated(cls) {
    setNewlyCreated(cls);
    setPrefilledEnrollClassId(String(cls.id));
    setPrefilledTeacherClassId(String(cls.id));
  }

  function goAssignTeacher() {
    setActiveTab("teachers");
  }

  function goEnrollStudents() {
    setActiveTab("enroll");
  }

  const TABS = [
    { key: "config", icon: BookOpen, label: "Classes & Subjects" },
    { key: "enroll", icon: GraduationCap, label: "Student Enrollments" },
    { key: "teachers", icon: UserCheck, label: "Class Teachers" },
  ];

  return (
    <div className="space-y-6">
      {/* Tab Bar */}
      <div className="flex border-b border-slate-200">
        {TABS.map(({ key, icon: Icon, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-all ${activeTab === key
                ? "border-academic-blue text-academic-blue"
                : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
          >
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {/* ─── Guided Setup Banner ─────────────────────────────────────── */}
      {newlyCreated && (
        <div className="relative rounded-2xl border-2 border-academic-blue/30 bg-gradient-to-br from-blue-50 via-indigo-50 to-sky-50 p-5 shadow-sm">
          <button onClick={() => setNewlyCreated(null)} className="absolute top-3 right-3 text-slate-400 hover:text-slate-700" title="Dismiss">
            <X size={16} />
          </button>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-academic-blue/10 border border-academic-blue/20 flex items-center justify-center text-academic-blue">
              <CheckCircle size={20} />
            </div>
            <div>
              <p className="font-bold text-academic-blue">Class "{newlyCreated.name}-{newlyCreated.section}" ({newlyCreated.curriculum}) Created!</p>
              <p className="text-xs text-slate-500 mt-0.5">Complete 2 more steps so it appears in teacher &amp; student portals.</p>
            </div>
          </div>
          <div className="grid sm:grid-cols-3 gap-3 mb-5">
            <div className="bg-green-50 border border-green-200 rounded-xl p-3 flex items-center gap-3">
              <span className="w-7 h-7 rounded-full bg-green-500 text-white flex items-center justify-center text-xs font-bold shrink-0">✓</span>
              <div><p className="text-xs font-bold text-green-700">Step 1 — Done</p><p className="text-xs text-green-600">Class exists in the system</p></div>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-center gap-3">
              <span className="w-7 h-7 rounded-full bg-amber-400 text-white flex items-center justify-center text-xs font-bold shrink-0">2</span>
              <div><p className="text-xs font-bold text-amber-700">Step 2 — Assign Teacher</p><p className="text-xs text-amber-600">Teacher portal shows this class</p></div>
            </div>
            <div className="bg-slate-100 border border-slate-200 rounded-xl p-3 flex items-center gap-3">
              <span className="w-7 h-7 rounded-full bg-slate-400 text-white flex items-center justify-center text-xs font-bold shrink-0">3</span>
              <div><p className="text-xs font-bold text-slate-600">Step 3 — Enroll Students</p><p className="text-xs text-slate-500">Students &amp; parents see their class</p></div>
            </div>
          </div>
          <div className="bg-white/80 rounded-xl border border-slate-200 p-4 mb-4">
            <p className="text-xs font-bold text-slate-700 mb-2">📡 How this class propagates to other portals:</p>
            <div className="grid sm:grid-cols-3 gap-3 text-xs text-slate-600">
              <div className="flex items-start gap-2"><User size={12} className="mt-0.5 text-academic-blue shrink-0" /><span><strong>Teacher Portal:</strong> Appears under "My Classes" once a teacher is assigned.</span></div>
              <div className="flex items-start gap-2"><GraduationCap size={12} className="mt-0.5 text-academic-green shrink-0" /><span><strong>Student Portal:</strong> Students see their class, timetable &amp; homework once enrolled.</span></div>
              <div className="flex items-start gap-2"><Users size={12} className="mt-0.5 text-amber-500 shrink-0" /><span><strong>Parent Portal:</strong> Inherits the child's enrollment automatically.</span></div>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <button onClick={goAssignTeacher} className="flex items-center gap-2 bg-academic-blue text-white rounded-xl px-4 py-2 text-sm font-semibold hover:bg-academic-blue/90 transition-colors">
              <UserCheck size={15} /> Assign Teacher to this Class <ArrowRight size={14} />
            </button>
            <button onClick={goEnrollStudents} className="flex items-center gap-2 bg-academic-green text-white rounded-xl px-4 py-2 text-sm font-semibold hover:bg-academic-green/90 transition-colors">
              <GraduationCap size={15} /> Enroll Students into this Class <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {activeTab === "config" && (
        <TabConfig
          classes={classes}
          subjects={subjects}
          loadClasses={loadClasses}
          loadSubjects={loadSubjects}
          setToast={setToast}
          onClassCreated={handleClassCreated}
        />
      )}

      {activeTab === "enroll" && (
        <TabEnroll
          classes={classes}
          students={students}
          enrollments={enrollments}
          loadEnrollments={loadEnrollments}
          setToast={setToast}
          prefilledClassId={prefilledEnrollClassId}
          newlyCreated={newlyCreated}
          onEnrolled={loadClasses}
        />
      )}

      {activeTab === "teachers" && (
        <TabTeachers
          classes={classes}
          subjects={subjects}
          teachers={teachers}
          classTeachers={classTeachers}
          loadClassTeachers={loadClassTeachers}
          setToast={setToast}
          prefilledClassId={prefilledTeacherClassId}
          newlyCreated={newlyCreated}
          onAssigned={loadClasses}
        />
      )}

      <Toast message={toast?.message} tone={toast?.tone} onClose={() => setToast(null)} />
    </div>
  );
}
