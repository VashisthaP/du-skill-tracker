/* ============================================================
   SkillHive – Main JavaScript
   Common utilities, chart helpers, UI interactions
   ============================================================ */
'use strict';

document.addEventListener('DOMContentLoaded', () => {

    /* -- Auto-dismiss flash messages after 5 seconds -- */
    document.querySelectorAll('.alert-dismissible').forEach(alert => {
        setTimeout(() => {
            const btn = alert.querySelector('[data-bs-dismiss]');
            if (btn) btn.click();
        }, 5000);
    });

    /* -- Confirm before destructive actions -- */
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', e => {
            if (!confirm(el.dataset.confirm || 'Are you sure?')) e.preventDefault();
        });
    });

    /* -- Skill Cloud Loader (landing page) -- */
    const cloudContainer = document.getElementById('skillCloud');
    if (cloudContainer) {
        fetch('/api/skill-cloud')
            .then(r => r.json())
            .then(data => {
                if (!data.length) { cloudContainer.innerHTML = '<p class="text-muted">No skill data yet</p>'; return; }
                const maxCount = Math.max(...data.map(s => s.count));
                cloudContainer.innerHTML = data.map(s => {
                    const ratio = s.count / maxCount;
                    const cls = ratio > .75 ? 'xl' : ratio > .5 ? 'lg' : ratio > .25 ? 'md' : 'sm';
                    return `<span class="skill-cloud-tag skill-cloud-${cls}" title="${s.count} demands">${s.name}</span>`;
                }).join('');
            })
            .catch(() => { cloudContainer.innerHTML = '<p class="text-muted">Unable to load skill data</p>'; });
    }

    /* -- Trending Skills Chart (Chart.js bar/doughnut) -- */
    const trendingCtx = document.getElementById('trendingChart');
    if (trendingCtx) {
        fetch('/api/skill-cloud')
            .then(r => r.json())
            .then(data => {
                const top10 = data.slice(0, 10);
                new Chart(trendingCtx, {
                    type: 'bar',
                    data: {
                        labels: top10.map(s => s.name),
                        datasets: [{
                            label: 'Open Demands',
                            data: top10.map(s => s.count),
                            backgroundColor: 'rgba(161, 0, 255, 0.7)',
                            borderColor: '#A100FF', borderWidth: 1,
                            borderRadius: 6, maxBarThickness: 40
                        }]
                    },
                    options: {
                        responsive: true,
                        indexAxis: 'y',
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { display: false } },
                            y: { grid: { display: false } }
                        }
                    }
                });
            })
            .catch(() => {});
    }

    /* -- Dashboard Doughnut Chart -- */
    const doughnutCtx = document.getElementById('dashboardDoughnut');
    if (doughnutCtx) {
        fetch('/api/stats')
            .then(r => r.json())
            .then(data => {
                new Chart(doughnutCtx, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(data.demands_by_status || {}),
                        datasets: [{
                            data: Object.values(data.demands_by_status || {}),
                            backgroundColor: ['#198754', '#0d6efd', '#6c757d', '#adb5bd'],
                            borderWidth: 2, borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true, cutout: '60%',
                        plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } }
                    }
                });
            })
            .catch(() => {});
    }

    /* -- Skill Search Autocomplete (demand form) -- */
    const skillInput = document.getElementById('skillInput');
    const skillTags  = document.getElementById('skillTags');
    const skillHidden = document.getElementById('skillsHidden');
    if (skillInput && skillTags && skillHidden) {
        let selectedSkills = [];
        // pre-populate from hidden field
        const existing = skillHidden.value;
        if (existing) {
            existing.split(',').forEach(s => { s = s.trim(); if (s) selectedSkills.push(s); });
            renderTags();
        }

        skillInput.addEventListener('keydown', e => {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                addSkill(skillInput.value);
            }
        });
        skillInput.addEventListener('blur', () => { addSkill(skillInput.value); });

        function addSkill(name) {
            name = name.replace(/,/g, '').trim();
            if (name && !selectedSkills.some(s => s.toLowerCase() === name.toLowerCase())) {
                selectedSkills.push(name);
                renderTags();
            }
            skillInput.value = '';
        }
        function removeSkill(name) {
            selectedSkills = selectedSkills.filter(s => s !== name);
            renderTags();
        }
        function renderTags() {
            skillTags.innerHTML = selectedSkills.map(s =>
                `<span class="skill-tag">${s} <span class="ms-1" style="cursor:pointer" onclick="window.__removeSkill('${s}')">&times;</span></span>`
            ).join('');
            skillHidden.value = selectedSkills.join(',');
        }
        window.__removeSkill = removeSkill;
    }

    /* -- Print-friendly: hide nav when printing -- */
    if (window.matchMedia) {
        window.matchMedia('print').addEventListener('change', e => {
            document.querySelectorAll('.navbar, .footer-skillhive').forEach(el => {
                el.style.display = e.matches ? 'none' : '';
            });
        });
    }
});
