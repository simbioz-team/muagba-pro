import sys; sys.path.insert(0,'.')
import test_registry as t
files = """courses/task_solutions/tests/test_types.py
courses/task_solutions/tests/test_current_solutions.py
courses/task_solutions/tests/test_journal.py
courses/task_solutions/tests/test_journal_concurrency.py
courses/task_solutions/tests/test_append_only.py
courses/exam_tasks/tests/test_answer_form.py
courses/tests/test_handler_registration.py
courses/exam_solver/tests/test_reference_solution_acceptance.py
courses/task_solving/tests/test_steps_reach_answer_acceptance.py
courses/exam_methodologist_queue/tests/test_reference_same_choice_acceptance.py
courses/exam_methodologist_queue/tests/test_steps_journal_acceptance.py
courses/tests/test_migration_0296_acceptance.py
courses/exam_solver/tests/test_task_solution_api_acceptance.py
courses/task_solutions/tests/test_catalog_merge_acceptance.py
courses/exam_methodologist_queue/tests/test_reference_origin.py
courses/exam_solver/tests/test_reference_batch.py
courses/task_solving/tests/test_answers.py
courses/exam_solver/tests/test_step_edits.py
courses/exam_methodologist_queue/tests/test_steps.py
courses/tests/test_migration_0296.py
courses/task_solutions/tests/test_catalog_merge.py
courses/exam_solver/tests/test_ksa_repoint.py
courses/exam_solver/tests/test_solution_writes.py""".split()
cfg = t.load_config() if False else None
import json,subprocess
cfg=json.loads(subprocess.check_output(['git','-C','/home/rustam/develop/simbioz_team/nastavnik_stage_1','show','4ba293f13:docs/engineering/test-registry.json']))
for f in files:
    k=t.normalize(f); print(t.classify(k,cfg.get('exceptions')), k)
