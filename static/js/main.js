// IRCTC Main Frontend JavaScript Engine

document.addEventListener('DOMContentLoaded', function() {
    
    // Station Swap Button on Search Form
    const swapBtn = document.getElementById('swapStationsBtn');
    if (swapBtn) {
        swapBtn.addEventListener('click', function() {
            const fromSelect = document.getElementById('from_station');
            const toSelect = document.getElementById('to_station');
            if (fromSelect && toSelect) {
                const temp = fromSelect.value;
                fromSelect.value = toSelect.value;
                toSelect.value = temp;
            }
        });
    }

    // Dynamic Passenger Row Manager (Book Ticket Form)
    const addPassengerBtn = document.getElementById('addPassengerBtn');
    const passengerRowsContainer = document.getElementById('passengerRows');

    if (addPassengerBtn && passengerRowsContainer) {
        addPassengerBtn.addEventListener('click', function() {
            const rowCount = passengerRowsContainer.getElementsByClassName('passenger-row').length;
            if (rowCount >= 6) {
                alert("Maximum 6 passengers allowed per booking.");
                return;
            }

            const newIndex = rowCount + 1;
            const newRow = document.createElement('div');
            newRow.className = 'passenger-row card mb-3 border-light shadow-sm p-3 position-relative';
            newRow.innerHTML = `
                <button type="button" class="btn-close position-absolute top-0 end-0 m-2 remove-passenger-btn" aria-label="Remove"></button>
                <div class="row g-3">
                    <div class="col-md-1 align-self-center text-center">
                        <span class="badge bg-primary rounded-circle p-2">${newIndex}</span>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label small fw-semibold text-muted">Full Name</label>
                        <input type="text" name="p_name[]" class="form-control" placeholder="Passenger Name" required>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small fw-semibold text-muted">Age</label>
                        <input type="number" name="p_age[]" class="form-control" min="1" max="120" value="30" required>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small fw-semibold text-muted">Gender</label>
                        <select name="p_gender[]" class="form-select" required>
                            <option value="Male">Male</option>
                            <option value="Female">Female</option>
                            <option value="Transgender">Transgender</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small fw-semibold text-muted">Berth Preference</label>
                        <select name="p_berth[]" class="form-select">
                            <option value="No Preference">No Preference</option>
                            <option value="Lower">Lower</option>
                            <option value="Middle">Middle</option>
                            <option value="Upper">Upper</option>
                            <option value="Side Lower">Side Lower</option>
                            <option value="Side Upper">Side Upper</option>
                        </select>
                    </div>
                </div>
            `;
            passengerRowsContainer.appendChild(newRow);
            updatePassengerCountBadge();
        });

        passengerRowsContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('remove-passenger-btn')) {
                const rows = passengerRowsContainer.getElementsByClassName('passenger-row');
                if (rows.length <= 1) {
                    alert("At least one passenger is required.");
                    return;
                }
                e.target.closest('.passenger-row').remove();
                reindexPassengerRows();
                updatePassengerCountBadge();
            }
        });
    }

    function reindexPassengerRows() {
        if (!passengerRowsContainer) return;
        const rows = passengerRowsContainer.getElementsByClassName('passenger-row');
        Array.from(rows).forEach((row, idx) => {
            const badge = row.querySelector('.badge');
            if (badge) badge.textContent = idx + 1;
        });
    }

    function updatePassengerCountBadge() {
        const countSpan = document.getElementById('passengerCountDisplay');
        if (countSpan && passengerRowsContainer) {
            const count = passengerRowsContainer.getElementsByClassName('passenger-row').length;
            countSpan.textContent = count;
        }
    }
});
