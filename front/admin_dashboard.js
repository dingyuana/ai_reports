const API_BASE_URL = '/api';

let charts = {};

async function fetchWithAuth(url, options = {}) {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login.html';
        return null;
    }

    const headers = {
        'Authorization': `Bearer ${token}`,
        ...options.headers
    };

    try {
        const response = await fetch(url, { ...options, headers });
        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/login.html';
            return null;
        }
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

async function loadOverviewStats() {
    try {
        const data = await fetchWithAuth(`${API_BASE_URL}/admin/stats/overview`);
        if (data) {
            document.getElementById('total-users').textContent = data.total_users || 0;
            document.getElementById('active-users-today').textContent = data.active_users_today || 0;
            document.getElementById('today-logs').textContent = data.today_logs || 0;
            document.getElementById('total-logs').textContent = data.total_logs || 0;
        }
    } catch (error) {
        console.error('Failed to load overview stats:', error);
        showError('加载概览统计数据失败');
    }
}

async function loadUserActivityChart() {
    try {
        const data = await fetchWithAuth(`${API_BASE_URL}/admin/stats/user-activity?days=30`);
        if (data && data.length > 0) {
            const ctx = document.getElementById('userActivityChart').getContext('2d');
            
            if (charts.userActivity) {
                charts.userActivity.destroy();
            }

            const labels = data.map(d => d.date).reverse();
            const activeUsers = data.map(d => d.active_users).reverse();
            const totalActions = data.map(d => d.total_actions).reverse();

            charts.userActivity = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: '活跃用户',
                            data: activeUsers,
                            borderColor: 'rgb(75, 192, 192)',
                            backgroundColor: 'rgba(75, 192, 192, 0.2)',
                            tension: 0.1,
                            fill: true
                        },
                        {
                            label: '总操作数',
                            data: totalActions,
                            borderColor: 'rgb(54, 162, 235)',
                            backgroundColor: 'rgba(54, 162, 235, 0.2)',
                            tension: 0.1,
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Failed to load user activity chart:', error);
    }
}

async function loadActionDistributionChart() {
    try {
        const data = await fetchWithAuth(`${API_BASE_URL}/admin/stats/action-distribution`);
        if (data && data.length > 0) {
            const ctx = document.getElementById('actionDistributionChart').getContext('2d');
            
            if (charts.actionDistribution) {
                charts.actionDistribution.destroy();
            }

            const labels = data.map(d => d.action);
            const counts = data.map(d => d.count);

            charts.actionDistribution = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: counts,
                        backgroundColor: [
                            'rgb(255, 99, 132)',
                            'rgb(54, 162, 235)',
                            'rgb(255, 205, 86)',
                            'rgb(75, 192, 192)',
                            'rgb(153, 102, 255)',
                            'rgb(255, 159, 64)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Failed to load action distribution chart:', error);
    }
}

async function loadDailySummaryChart() {
    try {
        const data = await fetchWithAuth(`${API_BASE_URL}/admin/stats/daily-summary?days=7`);
        if (data && data.length > 0) {
            const ctx = document.getElementById('dailySummaryChart').getContext('2d');
            
            if (charts.dailySummary) {
                charts.dailySummary.destroy();
            }

            const labels = data.map(d => d.date).reverse();
            const uploads = data.map(d => d.uploads).reverse();
            const downloads = data.map(d => d.downloads).reverse();
            const grades = data.map(d => d.grades).reverse();

            charts.dailySummary = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: '上传',
                            data: uploads,
                            backgroundColor: 'rgba(75, 192, 192, 0.6)'
                        },
                        {
                            label: '下载',
                            data: downloads,
                            backgroundColor: 'rgba(54, 162, 235, 0.6)'
                        },
                        {
                            label: '批阅',
                            data: grades,
                            backgroundColor: 'rgba(255, 205, 86, 0.6)'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Failed to load daily summary chart:', error);
    }
}

async function loadHourlyActivityChart() {
    try {
        const data = await fetchWithAuth(`${API_BASE_URL}/admin/stats/hourly-activity`);
        if (data && data.length > 0) {
            const ctx = document.getElementById('hourlyActivityChart').getContext('2d');
            
            if (charts.hourlyActivity) {
                charts.hourlyActivity.destroy();
            }

            const labels = data.map(d => `${d.hour}:00`);
            const counts = data.map(d => d.count);

            charts.hourlyActivity = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '操作数',
                        data: counts,
                        backgroundColor: 'rgba(153, 102, 255, 0.6)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Failed to load hourly activity chart:', error);
    }
}

async function loadTopUsersChart() {
    try {
        const data = await fetchWithAuth(`${API_BASE_URL}/admin/stats/top-users?limit=10`);
        if (data && data.length > 0) {
            const ctx = document.getElementById('topUsersChart').getContext('2d');
            
            if (charts.topUsers) {
                charts.topUsers.destroy();
            }

            const labels = data.map(d => d.username);
            const actions = data.map(d => d.total_actions);

            charts.topUsers = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '操作数',
                        data: actions,
                        backgroundColor: 'rgba(255, 99, 132, 0.6)'
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Failed to load top users chart:', error);
    }
}

async function loadUserWorkStats() {
    try {
        const data = await fetchWithAuth(`${API_BASE_URL}/admin/stats/user-work`);
        if (data) {
            const tbody = document.getElementById('user-work-table-body');
            tbody.innerHTML = '';

            data.forEach(user => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${user.username}</td>
                    <td>${user.email || '-'}</td>
                    <td><span class="role-badge ${user.role}">${user.role}</span></td>
                    <td>${user.upload_count || 0}</td>
                    <td>${user.download_count || 0}</td>
                    <td>${user.grade_count || 0}</td>
                    <td>${user.total_actions || 0}</td>
                    <td>${user.last_activity || '-'}</td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Failed to load user work stats:', error);
        showError('加载用户工作统计失败');
    }
}

async function loadRecentActivities() {
    try {
        const data = await fetchWithAuth(`${API_BASE_URL}/admin/stats/recent-activities?limit=20`);
        if (data) {
            const tbody = document.getElementById('recent-activities-table-body');
            tbody.innerHTML = '';

            data.forEach(activity => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${activity.created_at}</td>
                    <td>${activity.username || '-'}</td>
                    <td><span class="action-badge ${activity.action}">${activity.action}</span></td>
                    <td class="log-details">${activity.details || '-'}</td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Failed to load recent activities:', error);
        showError('加载最近活动失败');
    }
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    setTimeout(() => {
        errorDiv.classList.add('hidden');
    }, 5000);
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

async function loadAllData() {
    try {
        await Promise.all([
            loadOverviewStats(),
            loadUserActivityChart(),
            loadActionDistributionChart(),
            loadDailySummaryChart(),
            loadHourlyActivityChart(),
            loadTopUsersChart(),
            loadUserWorkStats(),
            loadRecentActivities()
        ]);
        hideLoading();
    } catch (error) {
        console.error('Failed to load data:', error);
        showError('加载数据失败');
        hideLoading();
    }
}

function setupEventListeners() {
    document.getElementById('logout-btn').addEventListener('click', async () => {
        localStorage.removeItem('access_token');
        window.location.href = '/login.html';
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadAllData();
    
    setInterval(loadAllData, 60000);
});