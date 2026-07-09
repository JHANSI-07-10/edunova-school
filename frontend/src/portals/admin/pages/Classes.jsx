import { useEffect, useState } from "react";
import api from "../lib/api";
import { Card, EmptyState, Loader, SectionTitle, Toast } from "../components/Common";
import { BookOpen, UserCheck, GraduationCap } from "lucide-react";

export default function Classes() {
  const [activeTab, setActiveTab] = useState("config");
  const [classes, setClasses] = useState(null);
  const [subjects, setSubjects] = useState(null);
  const [students, setStudents] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [classTeachers, setClassTeachers] = useState([]);

  const [classForm, setClassForm] = useState({ name: "", section: "", curriculum: "CBSE", room_number: "" });
  const [subjectForm, setSubjectForm] = useState({ name: "", subject_code: "", type: "Theory" });
  const [enrollForm, setEnrollForm] = useState({ student_id: "", class_id: "", roll_number: "", academic_year: "2025-26" });
  const [teacherAssignForm, setTeacherAssignForm] = useState({ class_id: "", teacher_id: "" });
  
  const [toast, setToast] = useState("");
  const [busy, setBusy] = useState(false);

  function loadClasses() {
    api.get("/admin-portal/classes/").then(({ data }) => setClasses(data)).catch(() => setClasses([]));
  }
  function loadSubjects() {
    api.get("/admin-portal/subjects/").then(({ data }) => setSubjects(data)).catch(() => setSubjects([]));
  }
  function loadStudents() {
    api.get("/admin-portal/users/?role=Student").then(({ data }) => setStudents(data)).catch(() => setStudents([]));
  }
  function loadTeachers() {
    api.get("/admin-portal/users/?role=Teacher").then(({ data }) => setTeachers(data)).catch(() => setTeachers([]));
  }
  function loadEnrollments() {
    api.get("/admin-portal/enrollments/").then(({ data }) => setEnrollments(data)).catch(() => setEnrollments([]));
  }
  function loadClassTeachers() {
    api.get("/admin-portal/class-teachers/").then(({ data }) => setClassTeachers(data)).catch(() => setClassTeachers([]));
  }

  useEffect(() => {
    loadClasses();
    loadSubjects();
    loadStudents();
    loadTeachers();
    loadEnrollments();
    loadClassTeachers();
  }, []);

  async function addClass(e) {
    e.preventDefault();
    try {
      await api.post("/admin-portal/classes/", classForm);
      setClassForm({ name: "", section: "", curriculum: "CBSE", room_number: "" });
      loadClasses();
      setToast("Class created successfully.");
    } catch { setToast("Could not create class."); }
  }

  async function addSubject(e) {
    e.preventDefault();
    try {
      await api.post("/admin-portal/subjects/", subjectForm);
      setSubjectForm({ name: "", subject_code: "", type: "Theory" });
      loadSubjects();
      setToast("Subject created successfully.");
    } catch { setToast("Could not create subject."); }
  }

  async function handleEnroll(e) {
    e.preventDefault();
    if (!enrollForm.student_id || !enrollForm.class_id) {
      setToast("Please select both a student and a class.");
      return;
    }
    setBusy(true);
    try {
      await api.post("/admin-portal/enrollments/", enrollForm);
      setEnrollForm({ student_id: "", class_id: "", roll_number: "", academic_year: "2025-26" });
      loadEnrollments();
      setToast("Student enrolled successfully.");
    } catch (err) {
      setToast(err?.response?.data?.detail || "Could not enroll student.");
    } finally {
      setBusy(false);
    }
  }

  async function handleTeacherAssign(e) {
    e.preventDefault();
    if (!teacherAssignForm.class_id || !teacherAssignForm.teacher_id) {
      setToast("Please select both a class and a teacher.");
      return;
    }
    setBusy(true);
    try {
      await api.post("/admin-portal/class-teachers/", teacherAssignForm);
      setTeacherAssignForm({ class_id: "", teacher_id: "" });
      loadClassTeachers();
      setToast("Class teacher assigned successfully.");
    } catch (err) {
      setToast(err?.response?.data?.detail || "Could not assign teacher.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Premium Tabbed Navigation Bar */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab("config")}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "config"
              ? "border-academic-blue text-academic-blue"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <BookOpen size={16} /> Classes & Subjects
        </button>
        <button
          onClick={() => setActiveTab("enroll")}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "enroll"
              ? "border-academic-blue text-academic-blue"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <GraduationCap size={16} /> Student Enrollments
        </button>
        <button
          onClick={() => setActiveTab("teachers")}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === "teachers"
              ? "border-academic-blue text-academic-blue"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <UserCheck size={16} /> Class Teachers
        </button>
      </div>

      {/* Tab 1: Config */}
      {activeTab === "config" && (
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <Card>
              <SectionTitle>Add Class</SectionTitle>
              <form onSubmit={addClass} className="grid grid-cols-2 gap-3">
                <input required placeholder="Name (e.g. Grade 6)" value={classForm.name} onChange={(e) => setClassForm({ ...classForm, name: e.target.value })} className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus-ring outline-none" />
                <input required placeholder="Section (e.g. A)" value={classForm.section} onChange={(e) => setClassForm({ ...classForm, section: e.target.value })} className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus-ring outline-none" />
                <select value={classForm.curriculum} onChange={(e) => setClassForm({ ...classForm, curriculum: e.target.value })} className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus-ring outline-none">
                  <option>CBSE</option><option>Cambridge</option>
                </select>
                <input placeholder="Room number" value={classForm.room_number} onChange={(e) => setClassForm({ ...classForm, room_number: e.target.value })} className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus-ring outline-none" />
                <button className="col-span-2 bg-academic-blue text-white rounded-xl py-2.5 font-medium hover:bg-academic-blue/90">Add Class</button>
              </form>
            </Card>
            <Card>
              <SectionTitle>All Classes</SectionTitle>
              {!classes ? <Loader rows={3} /> : classes.length === 0 ? <EmptyState label="No classes yet." /> : (
                <div className="divide-y divide-slate-100">
                  {classes.map((c) => (
                    <div key={c.id} className="py-2.5 text-sm flex justify-between">
                      <span className="font-medium text-slate-700">{c.name}-{c.section}</span>
                      <span className="text-ink-secondary">{c.curriculum} · Room {c.room_number || "—"}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          <div className="space-y-4">
            <Card>
              <SectionTitle>Add Subject</SectionTitle>
              <form onSubmit={addSubject} className="grid grid-cols-2 gap-3">
                <input required placeholder="Name" value={subjectForm.name} onChange={(e) => setSubjectForm({ ...subjectForm, name: e.target.value })} className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus-ring outline-none" />
                <input required placeholder="Subject code" value={subjectForm.subject_code} onChange={(e) => setSubjectForm({ ...subjectForm, subject_code: e.target.value })} className="rounded-xl border border-slate-200 px-3 py-2 text-sm focus-ring outline-none" />
                <select value={subjectForm.type} onChange={(e) => setSubjectForm({ ...subjectForm, type: e.target.value })} className="col-span-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus-ring outline-none">
                  {["Theory", "Practical", "Lab", "Skill_Development"].map((t) => <option key={t}>{t}</option>)}
                </select>
                <button className="col-span-2 bg-academic-blue text-white rounded-xl py-2.5 font-medium hover:bg-academic-blue/90">Add Subject</button>
              </form>
            </Card>
            <Card>
              <SectionTitle>All Subjects</SectionTitle>
              {!subjects ? <Loader rows={3} /> : subjects.length === 0 ? <EmptyState label="No subjects yet." /> : (
                <div className="divide-y divide-slate-100">
                  {subjects.map((s) => (
                    <div key={s.id} className="py-2.5 text-sm flex justify-between">
                      <span className="font-medium text-slate-700">{s.name}</span>
                      <span className="text-ink-secondary">{s.subject_code} · {s.type}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {/* Tab 2: Enrollments */}
      {activeTab === "enroll" && (
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <Card>
              <SectionTitle>Enroll Student in Class</SectionTitle>
              <form onSubmit={handleEnroll} className="space-y-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-slate-500 uppercase">Select Student</label>
                  <select
                    required
                    value={enrollForm.student_id}
                    onChange={(e) => setEnrollForm({ ...enrollForm, student_id: e.target.value })}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus-ring"
                  >
                    <option value="">-- Choose Student --</option>
                    {students.map((s) => (
                      <option key={s.id} value={s.id}>{s.name} ({s.username})</option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-slate-500 uppercase">Select Class</label>
                  <select
                    required
                    value={enrollForm.class_id}
                    onChange={(e) => setEnrollForm({ ...enrollForm, class_id: e.target.value })}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus-ring"
                  >
                    <option value="">-- Choose Class --</option>
                    {classes?.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}-{c.section} ({c.curriculum})</option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-semibold text-slate-500 uppercase">Roll Number (Optional)</label>
                    <input
                      type="number"
                      placeholder="Roll No"
                      value={enrollForm.roll_number}
                      onChange={(e) => setEnrollForm({ ...enrollForm, roll_number: e.target.value })}
                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus-ring"
                    />
                  </div>

                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-semibold text-slate-500 uppercase">Academic Year</label>
                    <input
                      required
                      type="text"
                      placeholder="e.g. 2025-26"
                      value={enrollForm.academic_year}
                      onChange={(e) => setEnrollForm({ ...enrollForm, academic_year: e.target.value })}
                      className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus-ring"
                    />
                  </div>
                </div>

                <button
                  disabled={busy}
                  className="w-full bg-academic-blue text-white rounded-xl py-2.5 font-medium hover:bg-academic-blue/90 disabled:opacity-60"
                >
                  {busy ? "Enrolling..." : "Enroll Student"}
                </button>
              </form>
            </Card>
          </div>

          <div className="space-y-4">
            <Card>
              <SectionTitle>Enrolled Roster</SectionTitle>
              {enrollments.length === 0 ? (
                <EmptyState label="No students enrolled yet." />
              ) : (
                <div className="divide-y divide-slate-100 max-h-[500px] overflow-y-auto pr-1">
                  {enrollments.map((e) => (
                    <div key={e.id} className="py-2.5 text-sm flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-slate-700">{e.student_name}</p>
                        <p className="text-xs text-ink-secondary">Username: {e.student_username} · Year: {e.academic_year}</p>
                      </div>
                      <div className="text-right">
                        <span className="bg-academic-blue/10 text-academic-blue px-2.5 py-1 rounded-full text-xs font-semibold">
                          {e.class_name}
                        </span>
                        {e.roll_number && (
                          <p className="text-xs text-ink-secondary mt-1">Roll No: {e.roll_number}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {/* Tab 3: Class Teachers */}
      {activeTab === "teachers" && (
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <Card>
              <SectionTitle>Assign Class Teacher</SectionTitle>
              <form onSubmit={handleTeacherAssign} className="space-y-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-slate-500 uppercase">Select Class</label>
                  <select
                    required
                    value={teacherAssignForm.class_id}
                    onChange={(e) => setTeacherAssignForm({ ...teacherAssignForm, class_id: e.target.value })}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus-ring"
                  >
                    <option value="">-- Choose Class --</option>
                    {classes?.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}-{c.section}</option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-slate-500 uppercase">Select Class Teacher</label>
                  <select
                    required
                    value={teacherAssignForm.teacher_id}
                    onChange={(e) => setTeacherAssignForm({ ...teacherAssignForm, teacher_id: e.target.value })}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus-ring"
                  >
                    <option value="">-- Choose Teacher --</option>
                    {teachers.map((t) => (
                      <option key={t.id} value={t.id}>{t.name} ({t.email})</option>
                    ))}
                  </select>
                </div>

                <button
                  disabled={busy}
                  className="w-full bg-academic-blue text-white rounded-xl py-2.5 font-medium hover:bg-academic-blue/90 disabled:opacity-60"
                >
                  {busy ? "Assigning..." : "Assign Class Teacher"}
                </button>
              </form>
            </Card>
          </div>

          <div className="space-y-4">
            <Card>
              <SectionTitle>Class Teacher Directory</SectionTitle>
              {classTeachers.length === 0 ? (
                <EmptyState label="No class teachers assigned yet." />
              ) : (
                <div className="divide-y divide-slate-100">
                  {classTeachers.map((ct) => (
                    <div key={ct.class_id} className="py-2.5 text-sm flex items-center justify-between">
                      <span className="font-semibold text-slate-700">{ct.class_name}</span>
                      <span className="bg-emerald-50 text-emerald-700 border border-emerald-100 px-2.5 py-1 rounded-full text-xs font-semibold">
                        👤 {ct.teacher_name}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      <Toast message={toast} onClose={() => setToast("")} />
    </div>
  );
}
