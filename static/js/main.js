document.addEventListener('DOMContentLoaded', function() {
    let timerInterval = null; // Variable to hold the timer interval
    let startTime = 0; // Variable to hold the start time

    document.getElementById('generateBtn').addEventListener('click', function() {
        // Show loading indicator and hide others
        document.getElementById('loading').classList.remove('d-none');
        document.getElementById('timetableContainer').classList.add('d-none');
        document.getElementById('errorMessage').classList.add('d-none');
        
        // Reset and start timer
        startTime = Date.now();
        const elapsedTimeElement = document.getElementById('elapsedTime');
        elapsedTimeElement.textContent = 'Elapsed time: 0s'; // Reset display
        
        // Clear any existing timer before starting a new one
        if (timerInterval) {
            clearInterval(timerInterval);
        }

        timerInterval = setInterval(() => {
            const elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
            elapsedTimeElement.textContent = `Elapsed time: ${elapsedSeconds}s`;
        }, 1000); // Update every second

        // Use absolute path for API endpoint
        fetch('/CPS_AI/generate', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                clearInterval(timerInterval); // Stop the timer
                timerInterval = null; // Clear interval variable
                document.getElementById('loading').classList.add('d-none');
                
                if (data.success) {
                    document.getElementById('timetableContainer').classList.remove('d-none');
                    
                    // Access common lectures that are shared across all groups
                    const commonLectures = data.timetables.common_lectures || {};
                    
                    // Generate timetable for each group
                    for (let group = 1; group <= 6; group++) {
                        const groupKey = `group_${group}`;
                        const groupSpecificData = data.timetables[groupKey] || {};
                        const mergedData = { ...commonLectures, ...groupSpecificData };
                        generateTimetableForGroup(group, mergedData);
                    }
                    
                    // Update teacher statistics and parallel sessions
                    updateTeacherStatistics(data.statistics.teacher_workdays);
                    displayParallelSessions(data.timetables); // Ensure this is called
                    
                    // Optionally display final execution time from backend stats
                    const finalTimeElement = document.getElementById('elapsedTime'); // Reuse element or create new one
                    if (finalTimeElement && data.statistics && data.statistics.execution_time) {
                         finalTimeElement.textContent = `Backend processing time: ${data.statistics.execution_time}`;
                         // You might want to display this elsewhere, not in the loading div
                    }

                } else {
                    document.getElementById('errorMessage').classList.remove('d-none');
                    document.getElementById('errorMessage').querySelector('.error-text').textContent = data.message;
                }
            })
            .catch((error) => {
                clearInterval(timerInterval); // Stop the timer on error too
                timerInterval = null; // Clear interval variable
                document.getElementById('loading').classList.add('d-none');
                document.getElementById('errorMessage').classList.remove('d-none');
                document.getElementById('errorMessage').querySelector('.error-text').textContent = 'An error occurred. Please try again.';
                console.error('Error:', error);
            });
    });

    // Function to generate timetable for a specific group
    function generateTimetableForGroup(groupNumber, timetableData) {
        const timetableBody = document.getElementById(`timetableBody${groupNumber}`);
        timetableBody.innerHTML = '';

        const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"];
        const maxSlots = 5;

        days.forEach(day => {
            const row = document.createElement('tr');
            const dayCell = document.createElement('td');
            dayCell.innerHTML = `<i class="bi bi-calendar-day me-2"></i>${day}`;
            dayCell.className = 'fw-bold';
            row.appendChild(dayCell);

            for (let slot = 1; slot <= maxSlots; slot++) {
                const slotCell = document.createElement('td');
                slotCell.className = 'timetable-cell';
                
                if (day === "Tuesday" && slot > 3) {
                    slotCell.className = 'bg-light text-muted';
                    slotCell.innerHTML = '<i class="bi bi-slash-circle me-2"></i>No Classes';
                } else {
                    const courseTimeSlot = `${day}_${slot}`;
                    // Find session assigned to this slot in the merged data
                    const assignedSession = Object.entries(timetableData).find(([key, value]) => value === courseTimeSlot);
                    
                    if (assignedSession) {
                        const [sessionKey, assignedValue] = assignedSession; // Value is the time slot
                        
                        // Determine if this is a lecture (from common_lectures keys)
                        const isLecture = sessionKey.includes('_lecture');
                        // Extract base course name and type (td/tp/lecture)
                        let courseName = sessionKey;
                        let courseType = 'unknown';

                        if (isLecture) {
                            courseName = sessionKey.replace('_lecture', '');
                            courseType = 'lecture';
                        } else {
                            // Handle keys like "CourseName_td" or "CourseName_tp"
                            const parts = sessionKey.split('_');
                            if (parts.length >= 2) {
                                courseType = parts.pop(); // Get last part (td/tp)
                                courseName = parts.join('_'); // Rejoin remaining parts for course name
                            }
                        }
                        
                        slotCell.innerHTML = `
                            <div class="course-item ${courseType} ${isLecture ? 'shared-lecture' : ''}">
                                <div class="fw-bold">${courseName}</div>
                                <div class="small text-muted">${courseType.toUpperCase()} ${isLecture ? '(Shared)' : ''}</div>
                            </div>
                        `;
                    } else {
                         // Check if any session *should* be here but is unscheduled
                         const unscheduledSession = Object.entries(timetableData).find(([key, value]) => value === "Unscheduled" && key.includes(`_${day}_${slot}`)); // This check is complex, maybe simplify

                         // Simplified: Just leave cell empty if no session is scheduled
                         // If you want to show unscheduled, the backend needs to provide that info differently
                    }
                }
                row.appendChild(slotCell);
            }
            timetableBody.appendChild(row);
        });

        // Add a row/message indicating any unscheduled sessions for this group
        const unscheduledItems = Object.entries(timetableData).filter(([key, value]) => value === "Unscheduled" && !key.includes('_lecture')); // Filter group-specific unscheduled
        if (unscheduledItems.length > 0) {
            const unscheduledRow = document.createElement('tr');
            const unscheduledCell = document.createElement('td');
            unscheduledCell.colSpan = maxSlots + 1; // Span all columns
            unscheduledCell.className = 'text-danger small p-2';
            unscheduledCell.innerHTML = `<i class="bi bi-exclamation-triangle me-1"></i> Unscheduled: ${unscheduledItems.map(([key]) => key.replace(/_group\d+$/, '')).join(', ')}`;
            timetableBody.appendChild(unscheduledRow);
        }
    }
    
    // New function to display parallel session information
    function displayParallelSessions(timetables) {
        const statsContainer = document.getElementById('teacherStats');
        if (!statsContainer) return;
        
        // Create map of time slots to sessions
        let slotMap = {};
        
        // Process all group-specific sessions
        for (let i = 1; i <= 6; i++) {
            const groupKey = `group_${i}`;
            const groupData = timetables[groupKey] || {};
            
            for (const [session, timeSlot] of Object.entries(groupData)) {
                if (timeSlot !== "Unscheduled") { // Only map scheduled slots
                    if (!slotMap[timeSlot]) {
                        slotMap[timeSlot] = [];
                    }
                    // Clean session name for display
                    const cleanedSession = session.replace(/_group\d+$/, '');
                    slotMap[timeSlot].push(`Group ${i}: ${cleanedSession}`);
                }
            }
        }
        
        // Find slots with parallel sessions (more than 1 group)
        const parallelSlots = Object.entries(slotMap)
            .filter(([slot, sessions]) => sessions.length > 1)
            .sort((a, b) => a[0].localeCompare(b[0]));
            
        if (parallelSlots.length > 0) {
            let parallelHTML = `
                <div class="card mb-4">
                    <div class="card-header bg-light">
                        <h5 class="mb-0">
                            <i class="bi bi-grid-3x3-gap me-2"></i>
                            Parallel Sessions (Different Groups)
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Time Slot</th>
                                        <th>Parallel Sessions</th>
                                    </tr>
                                </thead>
                                <tbody>
            `;
            
            for (const [slot, sessions] of parallelSlots) {
                parallelHTML += `
                    <tr>
                        <td>${slot}</td>
                        <td>${sessions.join('<br>')}</td>
                    </tr>
                `;
            }
            
            parallelHTML += `
                                </tbody>
                            </table>
                        </div>
                        <div class="alert alert-info mt-3">
                            <i class="bi bi-info-circle me-2"></i>
                            Multiple groups can have TD/TP sessions simultaneously, allowing for efficient use of time slots.
                        </div>
                    </div>
                </div>
            `;
            
            // Add after teacher stats
            statsContainer.insertAdjacentHTML('beforeend', parallelHTML);
        }
    }
    
    // Function to update teacher workday statistics
    function updateTeacherStatistics(teacherWorkdays) {
        const statsContainer = document.getElementById('teacherStats');
        if (!statsContainer) return;
        
        let statsHTML = `
            <div class="card mb-4">
                <div class="card-header bg-light">
                    <h5 class="mb-0">
                        <i class="bi bi-person-badge me-2"></i>
                        Teacher Workday Schedule
                    </h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Teacher</th>
                                    <th>Workdays</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        for (const [teacher, days] of Object.entries(teacherWorkdays)) {
            const daysCount = days.length;
            const status = daysCount <= 2 
                ? '<span class="badge bg-success">Optimal</span>' 
                : '<span class="badge bg-warning">Exceeds Target</span>';
            
            statsHTML += `
                <tr>
                    <td>${teacher}</td>
                    <td>${days.join(', ')}</td>
                    <td>${status}</td>
                </tr>
            `;
        }
        
        statsHTML += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        
        statsContainer.innerHTML = statsHTML;
    }
});
