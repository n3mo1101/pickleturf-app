// ── Shared Defaults ────────────────────────────────────────────────────────────
Chart.defaults.font.family = "'Outfit', system-ui, sans-serif";
Chart.defaults.font.size   = 12;
Chart.defaults.color       = '#6c757d';

const gridColor  = 'rgba(0,0,0,0.05)';
const greenColor = '#198754';
const blueColor  = '#0d6efd';

// ── 1. Daily Revenue Line Chart ───────────────────────────────────────────────
new Chart(document.getElementById('dailyRevenueChart'), {
    type: 'line',
    data: {
        labels: dailyLabels,
        datasets: [{
            label: 'Revenue (₱)',
            data: dailyData,
            borderColor: greenColor,
            backgroundColor: 'rgba(25,135,84,0.08)',
            borderWidth: 2,
            pointRadius: 2,
            pointHoverRadius: 5,
            fill: true,
            tension: 0.3,
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: ctx => ` ₱${ctx.parsed.y.toLocaleString()}`
                }
            }
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: {
                    maxTicksLimit: 10,
                    maxRotation: 0,
                }
            },
            y: {
                beginAtZero: true,
                grid: { color: gridColor },
                ticks: {
                    callback: v => '₱' + v.toLocaleString()
                }
            }
        }
    }
});

// ── 2. Revenue by Type Doughnut ────────────────────────────────────────────────
if (typeData && typeData.length > 0) {
    new Chart(document.getElementById('revenueTypeChart'), {
        type: 'doughnut',
        data: {
            labels: typeLabels,
            datasets: [{
                data: typeData,
                backgroundColor: typeLabels.map(label => {
                    const map = {
                        'Court Booking': '#198754',   // green
                        'Equipment Rental': '#F5C518', // yellow
                        'Item Sale': '#0d6efd',        // blue
                        'Open Play': '#0dcaf0',        // teal
                        'Manual Entry': '#6f42c1',     // purple
                    };
                    return map[label] || '#adb5bd';
                }),
                borderWidth: 2,
                borderColor: '#fff',
            }]
        },
        options: {
            responsive: true,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { padding: 12, boxWidth: 12 }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ₱${ctx.parsed.toLocaleString()}`
                    }
                }
            }
        }
    });
}

// ── 3. Monthly Revenue Bar Chart ───────────────────────────────────────────────
new Chart(document.getElementById('monthlyRevenueChart'), {
    type: 'bar',
    data: {
        labels: monthlyLabels,
        datasets: [{
            label: 'Revenue (₱)',
            data: monthlyData,
            backgroundColor: 'rgba(13,110,253,0.7)',
            borderRadius: 4,
            borderSkipped: false,
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: ctx => ` ₱${ctx.parsed.y.toLocaleString()}`
                }
            }
        },
        scales: {
            x: { grid: { display: false } },
            y: {
                beginAtZero: true,
                grid: { color: gridColor },
                ticks: { callback: v => '₱' + v.toLocaleString() }
            }
        }
    }
});

// ── 4. Court Utilization Bar Chart ─────────────────────────────────────────────
new Chart(document.getElementById('courtChart'), {
    type: 'bar',
    data: {
        labels: courtLabels,
        datasets: [{
            label: 'Bookings',
            data: courtData,
            backgroundColor: 'rgba(13,202,240,0.7)',
            borderRadius: 4,
        }]
    },
    options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { display: false } },
            y: {
                beginAtZero: true,
                ticks: { stepSize: 1 },
                grid: { color: gridColor },
            }
        }
    }
});