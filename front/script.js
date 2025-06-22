document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://127.0.0.1:8000';

    let selectedDirectory = null;

    // 左侧面板元素
    const studentReportsPanel = document.getElementById('student-reports-panel');
    const dirLoadingEl = document.getElementById('dir-loading');
    const directoryListEl = document.getElementById('directory-list');
    const uploadBtn = document.getElementById('upload-btn');
    const fileInput = document.getElementById('file-input');
    
    // 中间面板元素
    const criteriaFormEl = document.getElementById('criteria-form');
    const criteriaInputEl = document.getElementById('criteria-input');
    const criteriaStatusEl = document.getElementById('criteria-status');
    const addMarkingsCheckbox = document.getElementById('option-add-markings');
    const aiReviewCheckbox = document.getElementById('option-ai-review');
    const autoGradingCheckbox = document.getElementById('option-auto-grading');

    // 右侧面板元素
    const gradedLoadingEl = document.getElementById('graded-loading');
    const gradedListEl = document.getElementById('graded-list');

    // 提交按钮
    const submitGradingBtn = document.getElementById('submit-grading-btn');

    // 结果面板元素
    const resultsContainerEl = document.getElementById('results-container');
    const resultsTitleEl = document.getElementById('results-title');
    const reportListEl = document.getElementById('report-list');
    const reportLoadingEl = document.getElementById('report-loading');
    const csvDownloadLinkEl = document.getElementById('csv-download-link');

    /**
     * 通用函数：创建文件/目录树
     */
    function createTreeView(items, container, isStudentReports) {
        container.innerHTML = '';
        if (items.length === 0) {
            container.innerHTML = '<p style="padding: 1rem; text-align: center; color: #888;">未找到任何项目。</p>';
            return;
        }

        const tree = document.createElement('ul');
        tree.className = 'tree';
        items.forEach(item => {
            const itemLi = document.createElement('li');
            itemLi.className = 'tree-item is-directory';
            itemLi.dataset.directoryName = item.name; // 将目录名存储在li元素上

            const itemRow = document.createElement('div');
            itemRow.className = 'tree-row';
            const fileCount = item.files ? item.files.length : 0;
            
            const downloadButtonHtml = !isStudentReports
                ? `<button class="button small-button download-btn" data-download-dir="${item.name}">下载</button>`
                : '';

            itemRow.innerHTML = `
                <span class="caret"></span>
                <span class="icon folder-icon"></span>
                <span class="name">${item.name}</span>
                <span class="file-count">(${fileCount}个)</span>
                ${downloadButtonHtml}
            `;

            const fileUl = document.createElement('ul');
            fileUl.className = 'nested-list';

            if (item.files && item.files.length > 0) {
                item.files.forEach(file => {
                    const fileLi = document.createElement('li');
                    fileLi.className = 'tree-item is-file';
                    
                    const fileHtml = !isStudentReports 
                        ? `<a href="${API_BASE_URL}/graded_reports/${item.name}/${file}" target="_blank" class="name">${file}</a>`
                        : `<span class="name">${file}</span>`;

                    fileLi.innerHTML = `
                        <div class="tree-row">
                            <span class="icon file-icon"></span>
                            ${fileHtml}
                        </div>
                    `;
                    fileUl.appendChild(fileLi);
                });
            } else {
                const emptyLi = document.createElement('li');
                emptyLi.className = 'tree-item is-empty';
                emptyLi.innerHTML = `<div class="tree-row" style="cursor: default; color: #aaa;">此目录为空</div>`;
                fileUl.appendChild(emptyLi);
            }
            
            itemLi.appendChild(itemRow);
            itemLi.appendChild(fileUl);
            tree.appendChild(itemLi);
        });
        container.appendChild(tree);
    }

    /**
     * 获取并渲染待批阅报告目录
     */
    async function fetchAndRenderStudentReports() {
        dirLoadingEl.classList.remove('hidden');
        directoryListEl.innerHTML = '';
        try {
            const response = await fetch(`${API_BASE_URL}/api/reports/`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const directories = await response.json();
            createTreeView(directories, directoryListEl, true);
        } catch (error) {
            console.error('获取待批阅报告失败:', error);
            directoryListEl.innerHTML = `<p class="error">无法加载目录列表。</p>`;
        } finally {
            dirLoadingEl.classList.add('hidden');
        }
    }

    /**
     * 获取并渲染已批阅报告目录
     */
    async function fetchAndRenderGradedReports() {
        gradedLoadingEl.classList.remove('hidden');
        gradedListEl.innerHTML = '';
        try {
            const response = await fetch(`${API_BASE_URL}/api/graded-reports/`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const directories = await response.json();
            createTreeView(directories, gradedListEl, false);
        } catch (error) {
            console.error('获取已批阅报告失败:', error);
            gradedListEl.innerHTML = `<p class="error">无法加载目录列表。</p>`;
        } finally {
            gradedLoadingEl.classList.add('hidden');
        }
    }

    /**
     * 获取并设置当前的评分标准
     */
    async function fetchAndSetCriteria() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/criteria`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            criteriaInputEl.value = data.criteria;
        } catch (error) {
            console.error('获取评分标准失败:', error);
        }
    }

    /**
     * 提交评分标准
     */
    async function handleCriteriaSubmit(event) {
        event.preventDefault();
        const criteria = criteriaInputEl.value;
        criteriaStatusEl.textContent = '保存中...';
        criteriaStatusEl.className = 'status-message';

        try {
            const response = await fetch(`${API_BASE_URL}/api/criteria`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ criteria }),
            });
            if (!response.ok) throw new Error('保存失败');
            const data = await response.json();
            criteriaStatusEl.textContent = data.message;
            criteriaStatusEl.classList.add('success');
        } catch (error) {
            criteriaStatusEl.textContent = error.message;
            criteriaStatusEl.classList.add('error');
        } finally {
            setTimeout(() => {
                criteriaStatusEl.textContent = '';
                criteriaStatusEl.className = 'status-message';
            }, 3000);
        }
    }

    /**
     * 处理文件上传
     */
    async function handleFileUpload() {
        const file = fileInput.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        const originalBtnText = uploadBtn.textContent;
        uploadBtn.textContent = '上传中...';
        uploadBtn.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/api/upload`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '上传失败');
            }

            await fetchAndRenderStudentReports();
        } catch (error) {
            alert(`上传出错: ${error.message}`);
        } finally {
            uploadBtn.textContent = '上传文件';
            uploadBtn.disabled = false;
            fileInput.value = '';
        }
    }
    
    /**
     * 提交批阅任务
     */
    async function submitGrading() {
        if (!selectedDirectory) {
            alert("请先在左侧选择一个要批阅的目录。");
            return;
        }

        resultsContainerEl.classList.remove('hidden');
        resultsTitleEl.textContent = `批阅结果: ${selectedDirectory}`;
        reportListEl.innerHTML = '';
        reportLoadingEl.classList.remove('hidden');
        csvDownloadLinkEl.classList.add('hidden');
        
        submitGradingBtn.textContent = '正在批阅...';
        submitGradingBtn.disabled = true;

        const payload = {
            directory: selectedDirectory,
            add_markings: addMarkingsCheckbox.checked,
            ai_review: aiReviewCheckbox.checked,
            auto_grading: autoGradingCheckbox.checked,
        };

        try {
            const response = await fetch(`${API_BASE_URL}/api/annotate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                 const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const result = await response.json();
            
            renderReportResults(result.documents);
            await fetchAndRenderGradedReports();

            if (result.failed_count > 0 && result.csv_file) {
                csvDownloadLinkEl.href = `${API_BASE_URL}/${result.csv_file}`;
                csvDownloadLinkEl.classList.remove('hidden');
            }

        } catch (error) {
            console.error('批阅时出错:', error);
            reportListEl.innerHTML = `<p class="error">批阅失败: ${error.message}</p>`;
        } finally {
            reportLoadingEl.classList.add('hidden');
            submitGradingBtn.textContent = '开始批阅选定目录';
            submitGradingBtn.disabled = false;
        }
    }


    /**
     * 渲染报告评估结果
     */
    function renderReportResults(reports) {
        reportListEl.innerHTML = '';
        if (!reports || reports.length === 0) {
            reportListEl.innerHTML = '<p>目录中没有找到可处理的报告。</p>';
            return;
        }

        reports.forEach(report => {
            const isQualified = report.status === '合格';
            const card = document.createElement('div');
            card.className = `report-card ${isQualified ? 'qualified' : 'unqualified'}`;
            
            card.innerHTML = `
                <h3>
                    <span>${report.filename}</span>
                    <span class="score ${isQualified ? 'qualified' : 'unqualified'}">${report.score}分</span>
                </h3>
                <div class="details">
                    <p><strong>状态:</strong> ${report.status}</p>
                    <p><strong>文件类型:</strong> ${report.type}</p>
                    <p><strong>文件大小:</strong> ${(report.size / 1024).toFixed(2)} KB</p>
                </div>
                <div class="comments">
                    <strong>AI评语:</strong>
                    <p>${report.comments || '无'}</p>
                </div>
            `;
            reportListEl.appendChild(card);
        });
    }

    /**
     * 下载已批阅目录
     */
    async function downloadGradedDirectory(directoryName) {
        const button = document.querySelector(`.download-btn[data-download-dir="${directoryName}"]`);
        const originalText = button.innerHTML;
        button.innerHTML = '打包中...';
        button.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/api/download-graded?directory=${encodeURIComponent(directoryName)}`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '下载失败');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `${directoryName}_graded.zip`; 
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

        } catch (error) {
            alert(`下载失败: ${error.message}`);
        } finally {
            button.innerHTML = '下载';
            button.disabled = false;
        }
    }

    // --- 全局事件委托 ---
    document.body.addEventListener('click', (event) => {
        const target = event.target;
        const row = target.closest('.tree-row');

        // 关闭结果弹窗
        if (target.classList.contains('close-results')) {
            resultsContainerEl.classList.add('hidden');
        }

        // 点击左侧面板中的目录行
        if (studentReportsPanel.contains(target) && row) {
            const li = row.parentElement;
            if (li.classList.contains('is-directory')) {
                // 切换展开/折叠
                li.classList.toggle('expanded');
                
                // 设置选中状态
                if (selectedDirectory !== li.dataset.directoryName) {
                     // 移除旧的选中
                    const currentSelected = studentReportsPanel.querySelector('.tree-item.selected');
                    if (currentSelected) {
                        currentSelected.classList.remove('selected');
                    }
                    // 添加新的选中
                    li.classList.add('selected');
                    selectedDirectory = li.dataset.directoryName;
                } else {
                    // 如果再次点击已选中的，则取消选中
                    li.classList.remove('selected');
                    selectedDirectory = null;
                }
            }
        }
        
        // 点击右侧面板中的目录行 (仅展开/折叠)
        if (gradedListEl.contains(target) && row) {
            const li = row.parentElement;
            if (li.classList.contains('is-directory')) {
                li.classList.toggle('expanded');
            }
        }

        // 点击下载按钮
        if (target.classList.contains('download-btn')) {
            const dirName = target.dataset.downloadDir;
            downloadGradedDirectory(dirName);
        }
    });

    // --- 独立事件监听 ---
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileUpload);
    criteriaFormEl.addEventListener('submit', handleCriteriaSubmit);
    submitGradingBtn.addEventListener('click', submitGrading);

    // --- 初始加载 ---
    fetchAndRenderStudentReports();
    fetchAndRenderGradedReports();
    fetchAndSetCriteria();
}); 