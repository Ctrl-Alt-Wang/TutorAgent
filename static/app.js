/**
 * AI 智能教学助手 - 前端逻辑
 * 功能：自动讲解、逐步呈现、打断提问、智能衔接
 */

// ==================== 全局状态管理 ====================
const state = {
    sessionId: generateUUID(),
    segments: [],              // 所有讲解分段
    currentSegmentIndex: -1,   // 当前讲解到的分段
    isTeaching: false,         // 是否正在教学
    isPaused: false,           // 是否暂停
    isInterrupted: false,      // 是否被打断（提问中）
    imageBase64: null,         // 上传的图片
    
    // 语音相关
    utterance: null,
    
    // 内容渲染
    renderedSegments: [],      // 已渲染的分段
    currentTyping: null,       // 当前打字效果的控制器
};

// ==================== DOM 元素 ====================
const dom = {
    // 侧边栏
    uploadArea: document.getElementById('uploadArea'),
    imageInput: document.getElementById('imageInput'),
    uploadPlaceholder: document.getElementById('uploadPlaceholder'),
    previewContainer: document.getElementById('previewContainer'),
    previewImage: document.getElementById('previewImage'),
    removeImageBtn: document.getElementById('removeImageBtn'),
    contentInput: document.getElementById('contentInput'),
    startBtn: document.getElementById('startBtn'),
    
    // 主区域
    welcomeSection: document.getElementById('welcomeSection'),
    teachingSection: document.getElementById('teachingSection'),
    contentCard: document.getElementById('contentCard'),
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    resetBtn: document.getElementById('resetBtn'),
    questionBtn: document.getElementById('questionBtn'),
    
    // 对话框
    questionModal: document.getElementById('questionModal'),
    questionInput: document.getElementById('questionInput'),
    submitQuestionBtn: document.getElementById('submitQuestionBtn'),
    cancelQuestionBtn: document.getElementById('cancelQuestionBtn'),
    closeModalBtn: document.getElementById('closeModalBtn'),
    
    // 加载
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingText: document.getElementById('loadingText'),
};

// ==================== 工具函数 ====================
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function showLoading(text = '正在处理...') {
    dom.loadingText.textContent = text;
    dom.loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    dom.loadingOverlay.classList.add('hidden');
}

function showError(message) {
    alert('❌ ' + message);
}

// ==================== 语音合成 ====================
const speech = {
    synth: window.speechSynthesis,
    voices: [],
    
    init() {
        this.loadVoices();
        if (this.synth.onvoiceschanged !== undefined) {
            this.synth.onvoiceschanged = () => this.loadVoices();
        }
    },
    
    loadVoices() {
        this.voices = this.synth.getVoices();
    },
    
    getChineseVoice() {
        return this.voices.find(v => v.lang.startsWith('zh')) || this.voices[0];
    },
    
    speak(text, onEnd = null) {
        return new Promise((resolve) => {
            this.stop();
            
            const utterance = new SpeechSynthesisUtterance(text);
            const voice = this.getChineseVoice();
            if (voice) utterance.voice = voice;
            
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;
            
            utterance.onend = () => {
                if (onEnd) onEnd();
                resolve();
            };
            
            utterance.onerror = () => {
                console.error('Speech synthesis error');
                resolve();
            };
            
            state.utterance = utterance;
            this.synth.speak(utterance);
        });
    },
    
    stop() {
        this.synth.cancel();
        state.utterance = null;
    },
    
    pause() {
        this.synth.pause();
    },
    
    resume() {
        this.synth.resume();
    }
};

// ==================== API 调用 ====================
const api = {
    async startTeaching(contentText, imageBase64) {
        const response = await fetch('/api/start-teaching', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                content_text: contentText,
                image_base64: imageBase64
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '请求失败');
        }
        
        return response.json();
    },
    
    async askQuestion(question, segmentIndex) {
        const response = await fetch('/api/ask-question', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                question: question,
                current_segment_index: segmentIndex
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '请求失败');
        }
        
        return response.json();
    }
};

// ==================== 内容渲染（带打字效果） ====================
function typeWriter(element, text, speed = 30) {
    return new Promise((resolve) => {
        let index = 0;
        element.textContent = '';
        
        const controller = {
            stop: false
        };
        
        state.currentTyping = controller;
        
        function type() {
            if (controller.stop || index >= text.length) {
                state.currentTyping = null;
                resolve();
                return;
            }
            
            element.textContent += text.charAt(index);
            index++;
            setTimeout(type, speed);
        }
        
        type();
    });
}

function stopTyping() {
    if (state.currentTyping) {
        state.currentTyping.stop = true;
        state.currentTyping = null;
    }
}

function renderSegment(segment, index) {
    const segmentDiv = document.createElement('div');
    segmentDiv.className = 'segment-item';
    segmentDiv.dataset.index = index;
    
    // 段落头部
    const header = document.createElement('div');
    header.className = 'segment-header';
    header.innerHTML = `
        <div class="segment-number">${index + 1}</div>
        <h3 class="segment-title">${segment.title || '讲解'}</h3>
    `;
    segmentDiv.appendChild(header);
    
    // 内容
    const content = document.createElement('div');
    content.className = 'segment-content';
    segmentDiv.appendChild(content);
    
    // 关键点
    if (segment.key_points && segment.key_points.length > 0) {
        const keypoints = document.createElement('div');
        keypoints.className = 'segment-keypoints';
        segment.key_points.forEach(point => {
            const tag = document.createElement('span');
            tag.className = 'keypoint-tag';
            tag.textContent = point;
            keypoints.appendChild(tag);
        });
        segmentDiv.appendChild(keypoints);
    }
    
    dom.contentCard.appendChild(segmentDiv);
    
    return { element: segmentDiv, contentElement: content };
}

function renderQAInterruption(question, answer, transition) {
    const qaDiv = document.createElement('div');
    qaDiv.className = 'qa-interruption';
    
    // 问题
    const questionBlock = document.createElement('div');
    questionBlock.className = 'qa-question-block';
    questionBlock.innerHTML = `
        <div class="qa-label">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            你的问题
        </div>
        <div class="qa-text">${question}</div>
    `;
    qaDiv.appendChild(questionBlock);
    
    // 答案
    const answerBlock = document.createElement('div');
    answerBlock.className = 'qa-answer-block';
    answerBlock.innerHTML = `
        <div class="qa-label">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            AI 解答
        </div>
        <div class="qa-text">${answer}</div>
    `;
    qaDiv.appendChild(answerBlock);
    
    // 过渡语
    if (transition) {
        const transitionDiv = document.createElement('div');
        transitionDiv.className = 'transition-hint';
        transitionDiv.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 18 15 12 9 6"/>
            </svg>
            ${transition}
        `;
        qaDiv.appendChild(transitionDiv);
    }
    
    dom.contentCard.appendChild(qaDiv);
    
    // 滚动到底部
    setTimeout(() => {
        dom.contentCard.scrollTop = dom.contentCard.scrollHeight;
    }, 100);
}

// ==================== 教学流程控制 ====================
async function startTeachingFlow() {
    state.isTeaching = true;
    state.isPaused = false;
    state.isInterrupted = false;
    state.currentSegmentIndex = 0;
    
    // 启用问题按钮
    dom.questionBtn.style.display = 'flex';
    
    for (let i = 0; i < state.segments.length; i++) {
        if (!state.isTeaching) break;
        
        // 如果被打断，等待恢复
        while (state.isInterrupted) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        if (!state.isTeaching) break;
        
        state.currentSegmentIndex = i;
        updateProgress();
        
        const segment = state.segments[i];
        
        // 渲染分段
        const { contentElement } = renderSegment(segment, i);
        
        // 滚动到最新内容
        setTimeout(() => {
            contentElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
        
        // 打字效果显示内容
        await typeWriter(contentElement, segment.content, 20);
        
        if (!state.isTeaching) break;
        
        // 语音播放
        await speech.speak(segment.content);
        
        // 段落之间稍作停顿
        if (i < state.segments.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 800));
        }
    }
    
    if (state.isTeaching) {
        // 全部讲解完成
        state.isTeaching = false;
        dom.progressText.textContent = '✅ 讲解完成！';
        dom.questionBtn.style.display = 'none';
    }
}

function updateProgress() {
    const progress = ((state.currentSegmentIndex + 1) / state.segments.length) * 100;
    dom.progressBar.style.width = `${progress}%`;
    dom.progressText.textContent = `📖 正在讲解第 ${state.currentSegmentIndex + 1} / ${state.segments.length} 段`;
}

// ==================== 问答打断流程 ====================
async function handleQuestionInterruption(question) {
    // 标记为打断状态
    state.isInterrupted = true;
    stopTyping();
    speech.stop();
    
    showLoading('🤔 AI 正在思考你的问题...');
    
    try {
        const result = await api.askQuestion(question, state.currentSegmentIndex);
        
        hideLoading();
        
        // 渲染问答内容
        renderQAInterruption(question, result.answer, result.transition);
        
        // 语音播放答案
        await speech.speak(result.answer);
        
        // 播放过渡语
        if (result.transition) {
            await new Promise(resolve => setTimeout(resolve, 500));
            await speech.speak(result.transition);
        }
        
        // 恢复讲解
        state.isInterrupted = false;
        
    } catch (error) {
        hideLoading();
        showError(error.message);
        state.isInterrupted = false;
    }
}

// ==================== 事件处理 ====================

// 图片上传
dom.uploadArea.onclick = () => dom.imageInput.click();

dom.uploadArea.ondragover = (e) => {
    e.preventDefault();
    dom.uploadArea.style.borderColor = 'var(--primary-light)';
};

dom.uploadArea.ondragleave = () => {
    dom.uploadArea.style.borderColor = '';
};

dom.uploadArea.ondrop = (e) => {
    e.preventDefault();
    dom.uploadArea.style.borderColor = '';
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
        handleImageFile(file);
    }
};

dom.imageInput.onchange = (e) => {
    const file = e.target.files[0];
    if (file) handleImageFile(file);
};

function handleImageFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const base64 = e.target.result.split(',')[1];
        state.imageBase64 = base64;
        
        dom.previewImage.src = e.target.result;
        dom.uploadPlaceholder.classList.add('hidden');
        dom.previewContainer.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
}

dom.removeImageBtn.onclick = (e) => {
    e.stopPropagation();
    state.imageBase64 = null;
    dom.previewContainer.classList.add('hidden');
    dom.uploadPlaceholder.classList.remove('hidden');
    dom.imageInput.value = '';
};

// 快速示例
document.querySelectorAll('.chip').forEach(chip => {
    chip.onclick = () => {
        dom.contentInput.value = chip.dataset.content;
    };
});

// 开始教学
dom.startBtn.onclick = async () => {
    const text = dom.contentInput.value.trim();
    const image = state.imageBase64;
    
    if (!text && !image) {
        showError('请上传图片或输入内容');
        return;
    }
    
    try {
        showLoading('🔍 AI 正在分析内容...');
        
        const result = await api.startTeaching(text, image);
        
        hideLoading();
        
        state.segments = result.segments || [];
        
        if (state.segments.length === 0) {
            showError('未能生成讲解内容');
            return;
        }
        
        // 切换到教学界面
        dom.welcomeSection.classList.add('hidden');
        dom.teachingSection.classList.remove('hidden');
        dom.contentCard.innerHTML = '';
        
        // 开始自动教学流程
        startTeachingFlow();
        
    } catch (error) {
        hideLoading();
        showError(error.message);
    }
};

// 重置
dom.resetBtn.onclick = () => {
    state.isTeaching = false;
    state.isInterrupted = false;
    stopTyping();
    speech.stop();
    
    state.segments = [];
    state.currentSegmentIndex = -1;
    
    dom.teachingSection.classList.add('hidden');
    dom.welcomeSection.classList.remove('hidden');
    dom.questionBtn.style.display = 'none';
};

// 提问按钮
dom.questionBtn.onclick = () => {
    dom.questionModal.classList.remove('hidden');
    dom.questionInput.value = '';
    dom.questionInput.focus();
};

// 关闭对话框
dom.closeModalBtn.onclick = () => {
    dom.questionModal.classList.add('hidden');
};

dom.cancelQuestionBtn.onclick = () => {
    dom.questionModal.classList.add('hidden');
};

// 点击遮罩关闭
dom.questionModal.onclick = (e) => {
    if (e.target === dom.questionModal || e.target.className === 'modal-overlay') {
        dom.questionModal.classList.add('hidden');
    }
};

// 提交问题
dom.submitQuestionBtn.onclick = async () => {
    const question = dom.questionInput.value.trim();
    
    if (!question) {
        showError('请输入问题');
        return;
    }
    
    dom.questionModal.classList.add('hidden');
    
    await handleQuestionInterruption(question);
};

// 回车提交
dom.questionInput.onkeydown = (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
        dom.submitQuestionBtn.click();
    }
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    speech.init();
    dom.questionBtn.style.display = 'none';
    console.log('🎓 AI 智能教学助手已加载');
});
