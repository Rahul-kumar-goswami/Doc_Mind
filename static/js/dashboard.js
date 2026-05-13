document.addEventListener('DOMContentLoaded', () => {
    // Chart Colors
    const colors = {
        purple: '#8b5cf6',
        blue: '#3b82f6',
        text: '#94a3b8',
        grid: 'rgba(255, 255, 255, 0.05)'
    };

    // Activity Chart (Line Chart)
    const activityCtx = document.getElementById('activityChart').getContext('2d');
    new Chart(activityCtx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [
                {
                    label: 'AI Usage',
                    data: [650, 780, 920, 850, 980, 1100, 1240],
                    borderColor: colors.purple,
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointRadius: 4,
                    pointBackgroundColor: colors.purple
                },
                {
                    label: 'Doc Uploads',
                    data: [120, 150, 180, 140, 210, 250, 280],
                    borderColor: colors.blue,
                    backgroundColor: 'transparent',
                    fill: false,
                    tension: 0.4,
                    borderWidth: 3,
                    pointRadius: 4,
                    pointBackgroundColor: colors.blue
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: { size: 11 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: colors.text, font: { size: 11 } }
                }
            }
        }
    });

    // Distribution Chart (Doughnut)
    const distCtx = document.getElementById('distributionChart').getContext('2d');
    new Chart(distCtx, {
        type: 'doughnut',
        data: {
            labels: ['Engineering', 'Product', 'Marketing', 'Sales'],
            datasets: [{
                data: [45, 25, 15, 15],
                backgroundColor: [
                    '#8b5cf6',
                    '#3b82f6',
                    '#10b981',
                    '#f59e0b'
                ],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: colors.text,
                        padding: 20,
                        usePointStyle: true,
                        font: { size: 12 }
                    }
                }
            },
            cutout: '70%'
        }
    });

    // Quick Action Listeners
    document.querySelectorAll('.qa-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.innerText.trim();
            Swal.fire({
                title: action,
                text: `Initializing ${action} workflow...`,
                icon: 'info',
                background: '#111827',
                color: '#fff',
                confirmButtonColor: '#8b5cf6'
            });
        });
    });

    // Sidebar Active State (already handled by Django but good for client-side too)
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function() {
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            this.classList.add('active');
        });
    });
});