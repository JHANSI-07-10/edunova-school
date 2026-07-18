-- =============================================================================
-- MIGRATION: Fix schema-vs-views mismatches discovered during audit
-- Date: 2026-07-18
-- Safe to re-run (uses ADD COLUMN IF NOT EXISTS everywhere)
-- =============================================================================

-- 1. portal_timetable: add is_break / break_label
--    Referenced in admin_views.py, parent_views.py, timetable_workflow_views.py
--    (21+ references to is_break, 6+ to break_label on portal_timetable)
-- ---------------------------------------------------------------------------
ALTER TABLE public.portal_timetable
  ADD COLUMN IF NOT EXISTS is_break    boolean DEFAULT false;

ALTER TABLE public.portal_timetable
  ADD COLUMN IF NOT EXISTS break_label varchar(50) DEFAULT '';

-- 2. portal_question_bank: add type, options, correct_answer, difficulty, chapter
--    Referenced in teacher_views.py QuestionBankView (line 573+) and
--    exam_extras_views.py OMR grading (line 567+)
-- ---------------------------------------------------------------------------
ALTER TABLE public.portal_question_bank
  ADD COLUMN IF NOT EXISTS type           varchar(20)  NOT NULL DEFAULT 'MCQ';

ALTER TABLE public.portal_question_bank
  ADD COLUMN IF NOT EXISTS options        jsonb        DEFAULT '[]'::jsonb;

ALTER TABLE public.portal_question_bank
  ADD COLUMN IF NOT EXISTS correct_answer text         NOT NULL DEFAULT '';

ALTER TABLE public.portal_question_bank
  ADD COLUMN IF NOT EXISTS difficulty     varchar(30)  NOT NULL DEFAULT 'Medium';

ALTER TABLE public.portal_question_bank
  ADD COLUMN IF NOT EXISTS chapter        varchar(100) NOT NULL DEFAULT '';

-- 3. portal_exam_schedule: add academic_year
--    Referenced in exam_workflow_views.py CGPACalculationView (line 1890, 1899)
-- ---------------------------------------------------------------------------
ALTER TABLE public.portal_exam_schedule
  ADD COLUMN IF NOT EXISTS academic_year varchar(10) NOT NULL DEFAULT '2025-26';
