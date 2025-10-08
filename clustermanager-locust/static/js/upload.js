/**
 * 文件上传页面JavaScript
 * 处理拖拽上传、文件验证、预览等功能
 */

class FileUploader {
    constructor() {
        this.allowedTypes = ['.py'];
        this.maxFileSize = 10 * 1024 * 1024; // 10MB
        this.uploadArea = null;
        this.fileInput = null;
        this.previewArea = null;
        this.currentFile = null;
        this.init();
    }

    /**
     * 初始化上传器
     */
    init() {
        this.uploadArea = document.getElementById('upload-area');
        this.fileInput = document.getElementById('script-file');
        this.previewArea = document.getElementById('script-preview');
        
        if (!this.uploadArea || !this.fileInput) {
            console.error('上传组件初始化失败：缺少必要元素');
            return;
        }

        this.bindEvents();
        this.setupValidation();
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 拖拽事件
        this.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.uploadArea.classList.add('dragover');
        });

        this.uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            this.uploadArea.classList.remove('dragover');
        });

        this.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFile(files[0]);
            }
        });

        // 点击上传区域
        this.uploadArea.addEventListener('click', () => {
            this.fileInput.click();
        });

        // 文件选择
        this.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFile(e.target.files[0]);
            }
        });

        // 表单提交
        const form = document.getElementById('upload-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitForm();
            });
        }

        // 清除文件按钮
        const clearBtn = document.getElementById('clear-file-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearFile();
            });
        }

        // 示例脚本按钮
        const exampleBtn = document.getElementById('load-example-btn');
        if (exampleBtn) {
            exampleBtn.addEventListener('click', () => {
                this.loadExampleScript();
            });
        }
    }

    /**
     * 设置表单验证
     */
    setupValidation() {
        const form = document.getElementById('upload-form');
        if (!form) return;

        // 自定义验证规则
        const scriptNameInput = document.getElementById('script-name');
        if (scriptNameInput) {
            scriptNameInput.addEventListener('input', (e) => {
                this.validateScriptName(e.target);
            });
        }

        const descriptionInput = document.getElementById('script-description');
        if (descriptionInput) {
            descriptionInput.addEventListener('input', (e) => {
                this.updateCharacterCount(e.target);
            });
        }
    }

    /**
     * 处理文件
     */
    async handleFile(file) {
        // 验证文件
        const validation = this.validateFile(file);
        if (!validation.valid) {
            Notification.error(validation.message);
            return;
        }

        this.currentFile = file;
        
        // 更新UI
        this.updateUploadArea(file);
        
        // 读取并预览文件内容
        try {
            const content = await this.readFileContent(file);
            this.previewScript(content);
            this.validateScriptContent(content);
            
            // 自动填充脚本名称（如果为空）
            const scriptNameInput = document.getElementById('script-name');
            if (scriptNameInput && !scriptNameInput.value) {
                const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '');
                scriptNameInput.value = nameWithoutExt;
                this.validateScriptName(scriptNameInput);
            }
            
        } catch (error) {
            console.error('读取文件失败:', error);
            Notification.error('读取文件失败: ' + error.message);
        }
    }

    /**
     * 验证文件
     */
    validateFile(file) {
        // 检查文件类型
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.allowedTypes.includes(fileExtension)) {
            return {
                valid: false,
                message: `不支持的文件类型。仅支持: ${this.allowedTypes.join(', ')}`
            };
        }

        // 检查文件大小
        if (file.size > this.maxFileSize) {
            return {
                valid: false,
                message: `文件大小超过限制。最大允许: ${Utils.formatBytes(this.maxFileSize)}`
            };
        }

        // 检查文件名
        if (!/^[a-zA-Z0-9_\-\.]+$/.test(file.name)) {
            return {
                valid: false,
                message: '文件名只能包含字母、数字、下划线、连字符和点'
            };
        }

        return { valid: true };
    }

    /**
     * 读取文件内容
     */
    readFileContent(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                resolve(e.target.result);
            };
            
            reader.onerror = () => {
                reject(new Error('文件读取失败'));
            };
            
            reader.readAsText(file, 'UTF-8');
        });
    }

    /**
     * 更新上传区域UI
     */
    updateUploadArea(file) {
        const fileInfo = document.getElementById('file-info');
        const uploadPrompt = document.getElementById('upload-prompt');
        
        if (fileInfo && uploadPrompt) {
            uploadPrompt.style.display = 'none';
            fileInfo.style.display = 'block';
            
            fileInfo.innerHTML = `
                <div class="d-flex align-items-center justify-content-between">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-file-code fa-2x text-primary me-3"></i>
                        <div>
                            <div class="fw-bold">${file.name}</div>
                            <div class="text-muted small">
                                ${Utils.formatBytes(file.size)} • 
                                ${new Date(file.lastModified).toLocaleString('zh-CN')}
                            </div>
                        </div>
                    </div>
                    <button type="button" class="btn btn-outline-danger btn-sm" 
                            id="remove-file-btn" title="移除文件">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            
            // 绑定移除文件按钮
            const removeBtn = document.getElementById('remove-file-btn');
            if (removeBtn) {
                removeBtn.addEventListener('click', () => {
                    this.clearFile();
                });
            }
        }
        
        // 更新上传区域样式
        this.uploadArea.classList.add('has-file');
    }

    /**
     * 预览脚本内容
     */
    previewScript(content) {
        if (!this.previewArea) return;

        // 显示预览区域
        const previewContainer = document.getElementById('preview-container');
        if (previewContainer) {
            previewContainer.style.display = 'block';
        }

        // 设置内容
        this.previewArea.textContent = content;
        
        // 如果有语法高亮库，可以在这里应用
        if (window.hljs) {
            hljs.highlightElement(this.previewArea);
        }

        // 添加行号
        this.addLineNumbers();
    }

    /**
     * 添加行号
     */
    addLineNumbers() {
        const lines = this.previewArea.textContent.split('\n');
        const lineNumbers = lines.map((_, index) => index + 1).join('\n');
        
        let lineNumbersElement = document.getElementById('line-numbers');
        if (!lineNumbersElement) {
            lineNumbersElement = document.createElement('div');
            lineNumbersElement.id = 'line-numbers';
            lineNumbersElement.className = 'line-numbers';
            this.previewArea.parentNode.insertBefore(lineNumbersElement, this.previewArea);
        }
        
        lineNumbersElement.textContent = lineNumbers;
    }

    /**
     * 验证脚本内容
     */
    validateScriptContent(content) {
        const validationResults = document.getElementById('validation-results');
        if (!validationResults) return;

        const issues = [];
        const warnings = [];

        // 检查必要的导入
        if (!content.includes('from locust import') && !content.includes('import locust')) {
            issues.push('缺少 Locust 导入语句');
        }

        // 检查用户类
        if (!content.match(/class\s+\w+\s*\([^)]*User[^)]*\)/)) {
            issues.push('未找到继承自 User 的类');
        }

        // 检查任务方法
        if (!content.includes('@task') && !content.includes('def ')) {
            warnings.push('未找到任务方法（使用 @task 装饰器）');
        }

        // 检查语法错误（简单检查）
        const syntaxIssues = this.checkBasicSyntax(content);
        issues.push(...syntaxIssues);

        // 显示验证结果
        this.displayValidationResults(issues, warnings);
    }

    /**
     * 基本语法检查
     */
    checkBasicSyntax(content) {
        const issues = [];
        const lines = content.split('\n');

        // 检查缩进
        let indentationIssues = 0;
        lines.forEach((line, index) => {
            if (line.trim() && line.match(/^\s*\S/) && line.match(/^\s{1,3}\S/)) {
                indentationIssues++;
            }
        });

        if (indentationIssues > lines.length * 0.1) {
            issues.push('可能存在缩进问题');
        }

        // 检查括号匹配
        const openBrackets = (content.match(/\(/g) || []).length;
        const closeBrackets = (content.match(/\)/g) || []).length;
        if (openBrackets !== closeBrackets) {
            issues.push('括号不匹配');
        }

        return issues;
    }

    /**
     * 显示验证结果
     */
    displayValidationResults(issues, warnings) {
        const validationResults = document.getElementById('validation-results');
        if (!validationResults) return;

        let html = '';

        if (issues.length === 0 && warnings.length === 0) {
            html = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle"></i>
                    脚本验证通过，未发现问题
                </div>
            `;
        } else {
            if (issues.length > 0) {
                html += `
                    <div class="alert alert-danger">
                        <h6><i class="fas fa-exclamation-triangle"></i> 发现问题:</h6>
                        <ul class="mb-0">
                            ${issues.map(issue => `<li>${issue}</li>`).join('')}
                        </ul>
                    </div>
                `;
            }

            if (warnings.length > 0) {
                html += `
                    <div class="alert alert-warning">
                        <h6><i class="fas fa-exclamation-circle"></i> 警告:</h6>
                        <ul class="mb-0">
                            ${warnings.map(warning => `<li>${warning}</li>`).join('')}
                        </ul>
                    </div>
                `;
            }
        }

        validationResults.innerHTML = html;
    }

    /**
     * 验证脚本名称
     */
    validateScriptName(input) {
        const value = input.value.trim();
        const feedback = input.parentNode.querySelector('.invalid-feedback');
        
        if (!value) {
            input.setCustomValidity('请输入脚本名称');
            if (feedback) feedback.textContent = '请输入脚本名称';
            return false;
        }

        if (!/^[a-zA-Z0-9_\-]+$/.test(value)) {
            input.setCustomValidity('脚本名称只能包含字母、数字、下划线和连字符');
            if (feedback) feedback.textContent = '脚本名称只能包含字母、数字、下划线和连字符';
            return false;
        }

        if (value.length < 2 || value.length > 50) {
            input.setCustomValidity('脚本名称长度应在2-50个字符之间');
            if (feedback) feedback.textContent = '脚本名称长度应在2-50个字符之间';
            return false;
        }

        input.setCustomValidity('');
        return true;
    }

    /**
     * 更新字符计数
     */
    updateCharacterCount(input) {
        const maxLength = parseInt(input.getAttribute('maxlength')) || 500;
        const currentLength = input.value.length;
        const counter = document.getElementById('description-counter');
        
        if (counter) {
            counter.textContent = `${currentLength}/${maxLength}`;
            
            if (currentLength > maxLength * 0.9) {
                counter.className = 'text-warning small';
            } else if (currentLength === maxLength) {
                counter.className = 'text-danger small';
            } else {
                counter.className = 'text-muted small';
            }
        }
    }

    /**
     * 清除文件
     */
    clearFile() {
        this.currentFile = null;
        this.fileInput.value = '';
        
        // 重置上传区域
        const fileInfo = document.getElementById('file-info');
        const uploadPrompt = document.getElementById('upload-prompt');
        
        if (fileInfo && uploadPrompt) {
            fileInfo.style.display = 'none';
            uploadPrompt.style.display = 'block';
        }
        
        this.uploadArea.classList.remove('has-file');
        
        // 隐藏预览区域
        const previewContainer = document.getElementById('preview-container');
        if (previewContainer) {
            previewContainer.style.display = 'none';
        }
        
        // 清除验证结果
        const validationResults = document.getElementById('validation-results');
        if (validationResults) {
            validationResults.innerHTML = '';
        }
    }

    /**
     * 加载示例脚本
     */
    loadExampleScript() {
        const exampleContent = `from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """用户开始时执行的操作"""
        pass
    
    @task(3)
    def view_homepage(self):
        """访问首页"""
        self.client.get("/")
    
    @task(2)
    def view_about(self):
        """访问关于页面"""
        self.client.get("/about")
    
    @task(1)
    def view_contact(self):
        """访问联系页面"""
        self.client.get("/contact")
    
    def on_stop(self):
        """用户停止时执行的操作"""
        pass
`;

        // 创建虚拟文件对象
        const blob = new Blob([exampleContent], { type: 'text/plain' });
        const file = new File([blob], 'example_script.py', { type: 'text/plain' });
        
        this.handleFile(file);
        
        // 填充表单
        const scriptNameInput = document.getElementById('script-name');
        const descriptionInput = document.getElementById('script-description');
        
        if (scriptNameInput) {
            scriptNameInput.value = 'example_script';
            this.validateScriptName(scriptNameInput);
        }
        
        if (descriptionInput) {
            descriptionInput.value = '示例负载测试脚本，包含基本的HTTP请求任务';
            this.updateCharacterCount(descriptionInput);
        }
    }

    /**
     * 提交表单
     */
    async submitForm() {
        const form = document.getElementById('upload-form');
        if (!form) return;

        // 验证表单
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return;
        }

        if (!this.currentFile) {
            Notification.error('请选择要上传的脚本文件');
            return;
        }

        try {
            Loading.show('正在上传脚本...');

            const formData = new FormData(form);
            formData.append('script_file', this.currentFile);

            const response = await fetch('/api/scripts/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.success) {
                Notification.success('脚本上传成功');
                
                // 延迟跳转，让用户看到成功消息
                setTimeout(() => {
                    window.location.href = '/scripts';
                }, 1500);
            } else {
                Notification.error('上传失败: ' + (result.message || '未知错误'));
            }

        } catch (error) {
            console.error('上传脚本失败:', error);
            Notification.error('上传失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否在上传页面
    if (document.body.dataset.page === 'upload') {
        window.fileUploader = new FileUploader();
    }
});

// 添加CSS样式
const style = document.createElement('style');
style.textContent = `
    .upload-area.dragover {
        border-color: var(--primary-color);
        background-color: rgba(0, 123, 255, 0.1);
    }
    
    .upload-area.has-file {
        border-color: var(--success-color);
        background-color: rgba(40, 167, 69, 0.05);
    }
    
    .line-numbers {
        position: absolute;
        left: 0;
        top: 0;
        padding: 1rem 0.5rem;
        background-color: #f8f9fa;
        border-right: 1px solid #dee2e6;
        color: #6c757d;
        font-family: 'Courier New', monospace;
        font-size: 0.875rem;
        line-height: 1.5;
        text-align: right;
        user-select: none;
        width: 50px;
    }
    
    .code-block {
        position: relative;
        padding-left: 60px;
    }
    
    #validation-results .alert {
        margin-bottom: 0.5rem;
    }
    
    #validation-results .alert:last-child {
        margin-bottom: 0;
    }
`;
document.head.appendChild(style);