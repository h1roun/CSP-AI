from flask import Flask, render_template, request, jsonify, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from constraint import Problem, AllDifferentConstraint
import time
from collections import defaultdict
import random
import copy
from solver import OptimizedSolver

# Create Flask app with standard static path
app = Flask(__name__, static_url_path='/static')

# Handle reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Configure for /CPS_AI/ subpath but don't use it in static paths
app.config['APPLICATION_ROOT'] = '/CPS_AI'

def generate_timetable():
    start_time = time.time()
    
    solver = OptimizedSolver()
    problem = Problem(solver)
    
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
    slots_per_day = {"Sunday": 5, "Monday": 5, "Tuesday": 3, "Wednesday": 5, "Thursday": 5}
    time_slots = [f"{day}_{slot}" for day in days for slot in range(1, slots_per_day[day] + 1)]
    
    num_groups = 6

    courses = {
        "Sécurité": {
            "teachers": {"lecture": "Teacher 1", "td": "Teacher 1"},
            "sessions": ["lecture", "td"],
            "workload": 3
        },
        "Méthodes formelles": {
            "teachers": {"lecture": "Teacher 2", "td": "Teacher 2"},
            "sessions": ["lecture", "td"],
            "workload": 3
        },
        "Analyse numérique": {
            "teachers": {"lecture": "Teacher 3", "td": "Teacher 3"},
            "sessions": ["lecture", "td"],
            "workload": 3
        },
        "Entrepreneuriat": {
            "teachers": {"lecture": "Teacher 4"},
            "sessions": ["lecture"],
            "workload": 3
        },
        "Recherche opérationnelle 2": {
            "teachers": {"lecture": "Teacher 5", "td": "Teacher 5"},
            "sessions": ["lecture", "td"],
            "workload": 3
        },
        "Distributed Architecture": {
            "teachers": {"lecture": "Teacher 6", "td": "Teacher 6"},
            "sessions": ["lecture", "td"],
            "workload": 3
        },
        "Réseaux 2": {
            "teachers": {"lecture": "Teacher 7", "td": "Teacher 7", "tp": "Teacher 8"},
            "sessions": ["lecture", "td", "tp"],
            "workload": 4.5
        },
        "Artificial Intelligence": {
            "teachers": {"lecture": "Teacher 11", "td": "Teacher 11", "tp": "Teacher 12"},
            "sessions": ["lecture", "td", "tp"],
            "workload": 4.5
        }
    }

    # Keep track of all expected variables
    expected_vars = set()
    for course in courses:
        if "lecture" in courses[course]["sessions"]:
            expected_vars.add(f"{course}_lecture")
        for group in range(1, num_groups + 1):
            for session in courses[course]["sessions"]:
                if session != "lecture":
                    expected_vars.add(f"{course}_{session}_group{group}")

    # Add variables to problem
    for var in expected_vars:
        problem.addVariable(var, time_slots)

    # Refined Hard constraint: Maximum three successive slots
    def max_three_successive(*args):
        valid_args = [arg for arg in args if arg is not None and isinstance(arg, str) and '_' in arg]
        if len(valid_args) <= 1:
            return True
        
        try:
            slots_by_day = defaultdict(list)
            for arg in valid_args:
                day, slot_str = arg.split('_')
                slots_by_day[day].append(int(slot_str))

            for day, slots in slots_by_day.items():
                if len(slots) > 1:
                    slots.sort()
                    if any(slots[i] - slots[i-1] > 1 for i in range(1, len(slots))) or len(slots) > 3:
                        return False
            
            return True
        except (ValueError, AttributeError, IndexError):
            return False

    for course in courses:
        if "lecture" in courses[course]["sessions"]:
            lecture_var = f"{course}_lecture"
            for group in range(1, num_groups + 1):
                td_var = f"{course}_td_group{group}" if "td" in courses[course]["sessions"] else None
                tp_var = f"{course}_tp_group{group}" if "tp" in courses[course]["sessions"] else None
                
                vars_to_check = [v for v in [lecture_var, td_var, tp_var] if v is not None and v in problem._variables]
                
                if len(vars_to_check) >= 2:
                    problem.addConstraint(AllDifferentConstraint(), vars_to_check)
                    problem.addConstraint(max_three_successive, vars_to_check)

    for group in range(1, num_groups + 1):
        group_vars = []
        for course in courses:
            if "lecture" in courses[course]["sessions"]:
                group_vars.append(f"{course}_lecture")
            for session in courses[course]["sessions"]:
                if session != "lecture":
                    var_name = f"{course}_{session}_group{group}"
                    if var_name in problem._variables:
                        group_vars.append(var_name)
        problem.addConstraint(AllDifferentConstraint(), group_vars)
    
    teacher_sessions = defaultdict(list)
    for course in courses:
        for session_type in courses[course]["sessions"]:
            if session_type == "lecture":
                continue
            
            teacher = courses[course]["teachers"][session_type]
            for group in range(1, num_groups + 1):
                var_name = f"{course}_{session_type}_group{group}"
                if var_name in problem._variables:
                    teacher_sessions[teacher].append(var_name)
    
    constraints_added_teacher_conflict = 0
    for teacher, sessions in teacher_sessions.items():
        if len(sessions) > 1:
            problem.addConstraint(AllDifferentConstraint(), sessions)
            constraints_added_teacher_conflict += 1

    print(f"[{time.strftime('%H:%M:%S')}] Starting CSP solver...")
    solution = problem.getSolution()
    csp_end_time = time.time()
    csp_time = csp_end_time - start_time
    print(f"[{time.strftime('%H:%M:%S')}] CSP solver finished in {csp_time:.2f} seconds.")

    if solution is None:
        solution = {}

    optimization_start_time = time.time()
    spread_start_time = optimization_start_time

    if solution:
        # Calculate initial teacher days
        initial_teacher_days = defaultdict(set)
        for var, val in solution.items():
            if val is None or '_' not in var:
                continue
            parts = var.split('_')
            course_session = parts[1]
            if 'group' in course_session:
                course_session = course_session.split('group')[0]
            course_name = next((c for c in courses if var.startswith(f"{c}_")), None)
            if not course_name or course_session not in courses[course_name]["teachers"]:
                continue
            teacher = courses[course_name]["teachers"][course_session]
            day = val.split('_')[0]
            initial_teacher_days[teacher].add(day)

        # Apply teacher workday optimization
        print(f"[{time.strftime('%H:%M:%S')}] Starting teacher workday optimization...")
        optimized_solution = optimize_teacher_workdays(solution, courses, initial_teacher_days, time_slots, days)
        teacher_opt_end_time = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] Teacher workday optimization finished in {teacher_opt_end_time - optimization_start_time:.2f} seconds.")

        if optimized_solution:
            solution = optimized_solution
            
            # --- Add Day Spreading Step ---
            print(f"[{time.strftime('%H:%M:%S')}] Starting day spreading optimization...")
            spread_start_time = time.time()
            current_teacher_days = defaultdict(set)
            for var, val in solution.items():
                if val is None or '_' not in var:
                    continue
                parts = var.split('_')
                course_session = parts[1]
                if 'group' in course_session:
                    course_session = course_session.split('group')[0]
                course_name = next((c for c in courses if var.startswith(f"{c}_")), None)
                if not course_name or course_session not in courses[course_name]["teachers"]:
                    continue
                teacher = courses[course_name]["teachers"][course_session]
                day = val.split('_')[0]
                current_teacher_days[teacher].add(day)

            spread_solution = spread_sessions_across_days(solution, courses, current_teacher_days, time_slots, days)
            spread_end_time = time.time()
            print(f"[{time.strftime('%H:%M:%S')}] Day spreading finished in {spread_end_time - spread_start_time:.2f} seconds.")
            if spread_solution:
                solution = spread_solution
            # --- End Day Spreading Step ---

    end_time = time.time()

    teacher_days = defaultdict(set)
    if solution:
        for var, val in solution.items():
            if val is None or '_' not in var:
                continue
            parts = var.split('_')
            course_session = parts[1]
            if 'group' in course_session:
                course_session = course_session.split('group')[0]
            course_name = next((c for c in courses if var.startswith(f"{c}_")), None)
            if not course_name or course_session not in courses[course_name]["teachers"]:
                continue
            teacher = courses[course_name]["teachers"][course_session]
            day = val.split('_')[0]
            teacher_days[teacher].add(day)

    organized_solution = {}
    
    common_lectures = {}
    for course in courses:
        if "lecture" in courses[course]["sessions"]:
            var_name = f"{course}_lecture"
            common_lectures[var_name] = solution.get(var_name, "Unscheduled")
    organized_solution["common_lectures"] = common_lectures

    unscheduled_count = 0
    for group in range(1, num_groups + 1):
        group_sessions = {}
        for course in courses:
            for session in courses[course]["sessions"]:
                if session != "lecture":
                    var_name = f"{course}_{session}_group{group}"
                    assigned_slot = solution.get(var_name, "Unscheduled")
                    group_sessions[f"{course}_{session}"] = assigned_slot
                    if assigned_slot == "Unscheduled":
                        unscheduled_count += 1
        organized_solution[f"group_{group}"] = group_sessions

    parallel_sessions = defaultdict(list)
    if solution:
        for group in range(1, num_groups + 1):
            group_key = f"group_{group}"
            if group_key in organized_solution:
                for session_key, val in organized_solution[group_key].items():
                    if val != "Unscheduled":
                        course_name = session_key.rsplit('_', 1)[0]
                        session_type = session_key.rsplit('_', 1)[1]
                        session_info = f"Group {group}: {course_name}_{session_type}"
                        parallel_sessions[val].append(session_info)

    lecture_slots = {}
    if "common_lectures" in organized_solution:
        for var, slot in organized_solution["common_lectures"].items():
            if slot != "Unscheduled":
                lecture_slots[slot] = lecture_slots.get(slot, 0) + 1

    stats = {
        "execution_time": {
            "total": f"{end_time - start_time:.2f} seconds",
            "csp_solving": f"{csp_time:.2f} seconds",
            "teacher_opt": f"{teacher_opt_end_time - optimization_start_time:.2f} seconds" if solution else "N/A",
            "spread_opt": f"{spread_end_time - spread_start_time:.2f} seconds" if solution else "N/A"
        },
        "solver_approach": "Hybrid (CSP -> Teacher Opt -> Spread Opt)",
        "teacher_workdays": {teacher: list(days) for teacher, days in teacher_days.items()},
        "workday_violations": sum(1 for days in teacher_days.values() if len(days) > 2),
        "unscheduled_sessions": unscheduled_count,
        "shared_lectures": {
            "total": len(organized_solution.get("common_lectures", {})),
            "scheduled": len([s for s in organized_solution.get("common_lectures", {}).values() if s != "Unscheduled"]),
            "slots_usage": lecture_slots
        },
        "parallel_sessions": {
            slot: sessions for slot, sessions in parallel_sessions.items()
            if len(sessions) > 1
        },
        "teacher_conflict_prevention": {
            "method": "AllDifferentConstraint per Teacher",
            "teachers_with_multiple_groups": len([t for t, sessions in teacher_sessions.items() if len(sessions) > 1]),
            "constraints_added": constraints_added_teacher_conflict
        }
    }

    final_solution_data = organized_solution if solution else None

    return final_solution_data, stats

def optimize_teacher_workdays(solution, courses, teacher_days, time_slots, all_days):
    if not solution:
        return None
    
    current_solution = copy.deepcopy(solution)
    current_violations = sum(1 for days in teacher_days.values() if len(days) > 2)
    
    if current_violations == 0:
        print("No workday violations found in initial solution.")
        return current_solution

    print(f"Optimizing for {current_violations} teacher workday violations...")
    
    teachers_to_optimize = sorted([t for t, days in teacher_days.items() if len(days) > 2], key=lambda t: len(teacher_days[t]), reverse=True)

    MAX_OPTIMIZATION_ITERATIONS = 5
    iterations = 0

    while current_violations > 0 and iterations < MAX_OPTIMIZATION_ITERATIONS:
        iterations += 1
        print(f"Optimization Iteration {iterations}, Violations: {current_violations}")
        made_change_in_iteration = False

        for teacher in teachers_to_optimize:
            current_teacher_days = set()
            teacher_vars = []
            for var, val in current_solution.items():
                if val is None or '_' not in var:
                    continue
                parts = var.split('_')
                course_session = parts[1]
                if 'group' in course_session:
                    course_session = course_session.split('group')[0]
                course_name = next((c for c in courses if var.startswith(f"{c}_")), None)
                if not course_name or course_session not in courses[course_name]["teachers"]:
                    continue
                if courses[course_name]["teachers"][course_session] == teacher:
                    teacher_vars.append(var)
                    current_teacher_days.add(val.split('_')[0])

            if len(current_teacher_days) <= 2:
                continue

            day_counts = defaultdict(int)
            for var in teacher_vars:
                day = current_solution[var].split('_')[0]
                day_counts[day] += 1
            
            sorted_days = sorted(day_counts.keys(), key=lambda d: day_counts[d], reverse=True)
            days_to_keep = set(sorted_days[:2])
            days_to_vacate = current_teacher_days - days_to_keep

            potential_target_days = days_to_keep.union(set(all_days) - current_teacher_days)

            sessions_to_move = [var for var in teacher_vars if current_solution[var].split('_')[0] in days_to_vacate]
            
            for var_to_move in sessions_to_move:
                moved = False
                for target_day in potential_target_days:
                    max_slot = 3 if target_day == "Tuesday" else 5
                    potential_slots = [f"{target_day}_{slot}" for slot in range(1, max_slot + 1)]
                    
                    random.shuffle(potential_slots)

                    for new_slot in potential_slots:
                        if is_valid_move(current_solution, var_to_move, new_slot, courses):
                            print(f"  Moving {var_to_move} for {teacher} from {current_solution[var_to_move]} to {new_slot}")
                            current_solution[var_to_move] = new_slot
                            moved = True
                            made_change_in_iteration = True
                            break
                    if moved:
                        break

        temp_teacher_days = defaultdict(set)
        for var, val in current_solution.items():
            if val is None or '_' not in var:
                continue
            parts = var.split('_')
            course_session = parts[1]
            if 'group' in course_session:
                course_session = course_session.split('group')[0]
            course_name = next((c for c in courses if var.startswith(f"{c}_")), None)
            if not course_name or course_session not in courses[course_name]["teachers"]:
                continue
            teacher = courses[course_name]["teachers"][course_session]
            day = val.split('_')[0]
            temp_teacher_days[teacher].add(day)
        current_violations = sum(1 for days in temp_teacher_days.values() if len(days) > 2)

        if not made_change_in_iteration:
            print("No improvement possible in this iteration.")
            break

    print(f"Optimization finished after {iterations} iterations. Final Violations: {current_violations}")
    return current_solution

def spread_sessions_across_days(solution, courses, current_teacher_days, time_slots, all_days):
    if not solution:
        return None

    current_solution = copy.deepcopy(solution)
    
    day_session_counts = defaultdict(int)
    scheduled_sessions = []
    for var, val in current_solution.items():
        if val != "Unscheduled" and isinstance(val, str) and '_' in val:
            day = val.split('_')[0]
            day_session_counts[day] += 1
            scheduled_sessions.append(var)

    total_scheduled = len(scheduled_sessions)
    avg_sessions_per_day = total_scheduled / len(all_days) if len(all_days) > 0 else 0
    
    underutilized_threshold = max(1, int(avg_sessions_per_day * 0.5)) 
    overutilized_threshold = int(avg_sessions_per_day * 1.5)

    empty_or_underutilized_days = {day for day in all_days if day_session_counts[day] <= underutilized_threshold}
    busy_days = {day for day, count in day_session_counts.items() if count > overutilized_threshold}

    if not empty_or_underutilized_days or not busy_days:
        print("Day distribution seems balanced or no target days found for spreading.")
        return current_solution

    print(f"Attempting to spread sessions. Underutilized: {empty_or_underutilized_days}, Busy: {busy_days}")

    sessions_to_consider_moving = [var for var in scheduled_sessions if current_solution[var].split('_')[0] in busy_days]
    random.shuffle(sessions_to_consider_moving)

    moved_count = 0
    MAX_SPREAD_MOVES = 10

    for var_to_move in sessions_to_consider_moving:
        if moved_count >= MAX_SPREAD_MOVES:
            break

        current_slot = current_solution[var_to_move]
        current_day = current_slot.split('_')[0]

        parts = var_to_move.split('_')
        course_session = parts[1]
        if 'group' in course_session:
            course_session = course_session.split('group')[0]
        course_name = next((c for c in courses if var_to_move.startswith(f"{c}_")), None)
        if not course_name or course_session not in courses[course_name]["teachers"]:
            continue
        teacher = courses[course_name]["teachers"][course_session]
        
        teacher_current_days = current_teacher_days.get(teacher, set())

        moved = False
        target_days_shuffled = list(empty_or_underutilized_days)
        random.shuffle(target_days_shuffled)

        for target_day in target_days_shuffled:
            if target_day == current_day:
                continue

            if len(teacher_current_days) <= 2 and target_day not in teacher_current_days:
                if len(teacher_current_days) > 1:
                    continue

            max_slot = 3 if target_day == "Tuesday" else 5
            potential_slots = [f"{target_day}_{slot}" for slot in range(1, max_slot + 1)]
            random.shuffle(potential_slots)

            for new_slot in potential_slots:
                if is_valid_move(current_solution, var_to_move, new_slot, courses):
                    print(f"  Spreading: Moving {var_to_move} for {teacher} from {current_slot} to {new_slot}")
                    current_solution[var_to_move] = new_slot
                    moved = True
                    moved_count += 1
                    break
            if moved:
                break

    print(f"Spreading phase moved {moved_count} sessions.")
    return current_solution

def is_valid_move(solution, var_to_move, new_slot, courses):
    parts = var_to_move.split('_')
    if len(parts) < 2:
        return False
    
    course_name = None
    for c in courses:
        if var_to_move.startswith(f"{c}_"):
            course_name = c
            break
            
    if not course_name:
        return False
    
    is_group_session = 'group' in var_to_move
    group_num = None
    if is_group_session:
        for part in parts:
            if part.startswith('group'):
                try:
                    group_num = int(part[5:])
                    break
                except ValueError:
                    return False
    
    if group_num:
        for var, val in solution.items():
            if var != var_to_move and f"_group{group_num}" in var and val == new_slot:
                return False
    
    if "_lecture" in var_to_move:
        for var, val in solution.items():
            if var != var_to_move and "_lecture" in var and val == new_slot:
                return False
    
    course_session = parts[1]
    if 'group' in course_session:
        session_type = course_session.split('group')[0]
    else:
        session_type = course_session
    
    if session_type not in courses[course_name]["teachers"]:
        return False
    
    teacher = courses[course_name]["teachers"][session_type]
    
    for var, val in solution.items():
        if var != var_to_move and val == new_slot:
            var_parts = var.split('_')
            if len(var_parts) < 2:
                continue
            
            var_course = None
            for c in courses:
                if var.startswith(f"{c}_"):
                    var_course = c
                    break
            
            if not var_course or var_course not in courses:
                continue
            
            var_session = var_parts[1]
            if 'group' in var_session:
                var_session_type = var_session.split('group')[0]
            else:
                var_session_type = var_session
            
            if var_session_type not in courses[var_course]["teachers"]:
                continue
            
            var_teacher = courses[var_course]["teachers"][var_session_type]
            
            if var_teacher == teacher:
                return False
    
    return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    solution_data, stats = generate_timetable()
    if solution_data:
        return jsonify({
            'success': True,
            'timetables': solution_data,
            'statistics': stats,
            'notes': "Hard constraints enforced by CSP. Soft constraints optimized. Some sessions might be unscheduled if constraints conflict."
        })
    else:
        return jsonify({
            'success': False,
            'message': f'CSP solver failed to find a solution satisfying hard constraints in {stats["execution_time"]["csp_solving"]}. Constraints might be too strict.',
            'statistics': stats
        })

# Run the app directly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)

