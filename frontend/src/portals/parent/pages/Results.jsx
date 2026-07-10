import { useEffect, useState } from "react";
import api from "../lib/api";
import { Badge, Card, EmptyState, Loader } from "../components/Common";
import { useAuth } from "../context/AuthContext";
import { GraduationCap, Award, MessageSquare, Download } from "lucide-react";

export default function Results() {
  const { activeChildId } = useAuth();
  const [items, setItems] = useState(null);
  const [selectedExam, setSelectedExam] = useState("");

  useEffect(() => {
    if (!activeChildId) return;
    setItems(null);
    setSelectedExam("");
    api.get(`/parent/results/?child_id=${activeChildId}`)
      .then(({ data }) => {
        setItems(data);
        if (data.length > 0) {
          setSelectedExam(data[0].exam?.exam_name);
        }
      })
      .catch(() => setItems([]));
  }, [activeChildId]);

  if (!activeChildId) return <EmptyState label="Select a child from the top bar to view results." />;
  if (!items) return <Loader rows={4} />;

  const uniqueExams = [...new Set(items.map(r => r.exam?.exam_name))].filter(Boolean);
  const filtered = items.filter(r => r.exam?.exam_name === selectedExam);

  // Statistics calculation
  const totalMax = filtered.reduce((s, r) => s + (r.exam?.max_marks || 0), 0);
  const totalObtained = filtered.reduce((s, r) => s + (r.marks_obtained || 0), 0);
  const overallPercentage = totalMax ? Math.round((totalObtained * 100) / totalMax) : 0;
  const classRank = filtered.find(r => r.rank_position !== null)?.rank_position || "N/A";
  const teacherRemarks = filtered.map(r => r.remarks).filter(Boolean).join(". ") || "Consistent academic effort shown throughout the term.";

  const handleDownloadReport = () => {
    // Generate a printable report card view or print window
    window.print();
  };

  return (
    <div className="space-y-6 animate-[fadeIn_.2s_ease]">
      {/* Term / Exam Selector header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-heading text-2xl font-bold text-ink-primary">Academic Progress Report</h2>
          <p className="text-sm text-ink-secondary">Review child marks, rank positions, and overall performance.</p>
        </div>

        {uniqueExams.length > 0 && (
          <div className="flex items-center gap-2 bg-white p-2 rounded-xl border border-slate-100 shadow-sm self-start sm:self-auto">
            <label className="text-xs font-bold text-slate-500 whitespace-nowrap">Select Term:</label>
            <select
              value={selectedExam}
              onChange={e => setSelectedExam(e.target.value)}
              className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-semibold focus-ring outline-none bg-slate-50 cursor-pointer text-ink-primary"
            >
              {uniqueExams.map(name => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {items.length === 0 ? (
        <EmptyState label="No academic results published yet for this child." />
      ) : (
        <>
          {/* Performance Summary Metrics Cards */}
          <div className="grid sm:grid-cols-3 gap-4">
            <div className="bg-white rounded-card shadow-card p-5 border border-slate-100 flex items-start gap-4">
              <div className="w-11 h-11 rounded-xl bg-academic-blue/10 text-academic-blue flex items-center justify-center shrink-0">
                <GraduationCap size={20} />
              </div>
              <div>
                <p className="text-ink-secondary text-xs font-semibold uppercase tracking-wider">Overall score</p>
                <p className="text-2xl font-bold font-numeric text-ink-primary mt-0.5">{overallPercentage}%</p>
              </div>
            </div>

            <div className="bg-white rounded-card shadow-card p-5 border border-slate-100 flex items-start gap-4">
              <div className="w-11 h-11 rounded-xl bg-academic-gold/10 text-academic-gold flex items-center justify-center shrink-0">
                <Award size={20} />
              </div>
              <div>
                <p className="text-ink-secondary text-xs font-semibold uppercase tracking-wider">Class Rank</p>
                <p className="text-2xl font-bold font-numeric text-ink-primary mt-0.5">#{classRank}</p>
              </div>
            </div>

            <div className="bg-white rounded-card shadow-card p-5 border border-slate-100 flex items-start gap-4">
              <div className="w-11 h-11 rounded-xl bg-academic-green/10 text-academic-green flex items-center justify-center shrink-0">
                <MessageSquare size={20} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-ink-secondary text-xs font-semibold uppercase tracking-wider">Term remarks</p>
                <p className="text-xs text-ink-primary mt-1 line-clamp-2 italic">"{teacherRemarks}"</p>
              </div>
            </div>
          </div>

          {/* Subject wise Performance Breakdown */}
          <Card>
            <div className="flex items-center justify-between mb-4 border-b border-slate-100 pb-3">
              <span className="font-heading font-semibold text-sm text-ink-primary">Subject Performance Breakdown</span>
              <button 
                onClick={handleDownloadReport}
                className="flex items-center gap-1 text-[11px] font-bold text-academic-blue bg-academic-blue/5 hover:bg-academic-blue/10 px-3 py-1.5 rounded-lg transition-colors"
              >
                <Download size={12} /> Download Report
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                    <th className="py-2.5">Subject</th>
                    <th className="py-2.5 text-center">Marks Obtained</th>
                    <th className="py-2.5 text-center">Max Marks</th>
                    <th className="py-2.5 text-center">Percentage</th>
                    <th className="py-2.5 text-right">Grade</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filtered.map(r => (
                    <tr key={r.id} className="text-ink-primary">
                      <td className="py-3 font-medium">{r.exam?.subject_name}</td>
                      <td className="py-3 text-center font-numeric font-semibold">{r.marks_obtained}</td>
                      <td className="py-3 text-center font-numeric text-slate-500">{r.exam?.max_marks}</td>
                      <td className="py-3 text-center font-numeric text-academic-blue font-semibold">{r.percentage}%</td>
                      <td className="py-3 text-right">
                        <Badge tone={r.grade_letter === "F" ? "red" : "green"}>Grade {r.grade_letter}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
