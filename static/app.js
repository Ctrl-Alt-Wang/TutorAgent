/**
 * AI 交互式语音教学系统 - 前端逻辑
 */

// ==================== 全局状态 ====================
const state = {
    sessionId: generateUUID(),
    segments: [],
    currentSegmentIndex: -1,
    isPlaying: false,
    imageBase64: null,
    currentUtterance: null
};

// ==================== DOM 元素 ====================
const elements = {
    // 侧边栏
    uploadArea: document.getElementById('uploadArea'),
    imageInput: document.getElementById('imageInput'),
    uploadPlaceholder: document.getElementById('uploadPlaceholder'),
    previewImage: document.getElementById('previewImage'),
    contentInput: document.getElementById('contentInput'),
    startBtn: document.getElementById('startBtn'),
    resetBtn: document.getElementById('resetBtn'),

    // 主内容区
    welcomeSection: document.getElementById('welcomeSection'),
    teachingSection: document.getElementById('teachingSection'),
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    outlineView: document.getElementById('outlineView'),
    outlineList: document.getElementById('outlineList'),
    segmentView: document.getElementById('segmentView'),
    segmentTitle: document.getElementById('segmentTitle'),
    segmentContent: document.getElementById('segmentContent'),
    keyPoints: document.getElementById('keyPoints'),

    // 控制按钮
    prevBtn: document.getElementById('prevBtn'),
    playBtn: document.getElementById('playBtn'),
    playIcon: document.getElementById('playIcon'),
    playText: document.getElementById('playText'),
    nextBtn: document.getElementById('nextBtn'),
    questionBtn: document.getElementById('questionBtn'),

    // 弹窗
    questionModal: document.getElementById('questionModal'),
    questionInput: document.getElementById('questionInput'),
    submitQuestionBtn: document.getElementById('submitQuestionBtn'),
    cancelQuestionBtn: document.getElementById('cancelQuestionBtn'),
    answerModal: document.getElementById('answerModal'),
    displayQuestion: document.getElementById('displayQuestion'),
    displayAnswer: document.getElementById('displayAnswer'),
    transitionText: document.getElementById('transitionText'),
    continueBtn: document.getElementById('continueBtn'),

    // 加载
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingText: document.getElementById('loadingText')
};

// ==================== 工具函数 ====================
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function showLoading(text = '正在处理...') {
    elements.loadingText.textContent = text;
    elements.loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    elements.loadingOverlay.classList.add('hidden');
}

function showError(message) {
    alert('❌ 错误: ' + message);
}

// ==================== 语音合成 ====================
const speech = {
    synth: window.speechSynthesis,
    voices: [],

    init() {
        // 加载语音列表
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
        this.stop();

        const utterance = new SpeechSynthesisUtterance(text);
        const voice = this.getChineseVoice();
        if (voice) utterance.voice = voice;

        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        if (onEnd) {
            utterance.onend = onEnd;
        }

        state.currentUtterance = utterance;
        this.synth.speak(utterance);
    },

    pause() {
        this.synth.pause();
    },

    resume() {
        this.synth.resume();
    },

    stop() {
        this.synth.cancel();
        state.currentUtterance = null;
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

// ==================== UI 更新 ====================
function updateUI() {
    const { segments, currentSegmentIndex, isPlaying } = state;
    const total = segments.length;

    // 更新进度条
    if (currentSegmentIndex >= 0) {
        const progress = ((currentSegmentIndex + 1) / total) * 100;
        elements.progressBar.style.width = `${progress}%`;
        elements.progressText.textContent = `📖 讲解进度: ${currentSegmentIndex + 1} / ${total}`;
    } else {
        elements.progressBar.style.width = '0%';
        elements.progressText.textContent = '📖 准备开始讲解...';
    }

    // 更新按钮状态
    elements.prevBtn.disabled = currentSegmentIndex <= 0;
    elements.nextBtn.disabled = currentSegmentIndex >= total - 1 || currentSegmentIndex < 0;
    elements.questionBtn.disabled = currentSegmentIndex < 0;

    // 更新播放按钮
    if (currentSegmentIndex < 0) {
        elements.playIcon.textContent = '▶️';
        elements.playText.textContent = '开始讲解';
    } else if (isPlaying) {
        elements.playIcon.textContent = '⏸️';
        elements.playText.textContent = '暂停';
    } else {
        elements.playIcon.textContent = '▶️';
        elements.playText.textContent = '继续';
    }

    // 更新内容显示
    if (currentSegmentIndex >= 0 && currentSegmentIndex < total) {
        const segment = segments[currentSegmentIndex];
        elements.outlineView.classList.add('hidden');
        elements.segmentView.classList.remove('hidden');

        elements.segmentTitle.textContent = `📌 ${segment.title || '讲解'}`;
        elements.segmentContent.textContent = segment.content || '';

        // 渲染关键点
        elements.keyPoints.innerHTML = '';
        if (segment.key_points && segment.key_points.length > 0) {
            const title = document.createElement('h4');
            title.textContent = '📋 本段要点:';
            title.style.marginBottom = '10px';
            title.style.width = '100%';
            elements.keyPoints.appendChild(title);

            segment.key_points.forEach((point, i) => {
                const span = document.createElement('span');
                span.className = 'key-point-item';
                span.textContent = `${i + 1}. ${point}`;
                elements.keyPoints.appendChild(span);
            });
        }
    } else {
        elements.outlineView.classList.remove('hidden');
        elements.segmentView.classList.add('hidden');
    }
}

function renderOutline() {
    elements.outlineList.innerHTML = '';
    state.segments.forEach((seg, i) => {
        const item = document.createElement('div');
        item.className = 'outline-item';
        item.innerHTML = `<span class="item-number">第 ${i + 1} 段</span>${seg.title || '讲解'}`;
        item.onclick = () => jumpToSegment(i);
        elements.outlineList.appendChild(item);
    });
}

function jumpToSegment(index) {
    state.currentSegmentIndex = index;
    state.isPlaying = true;
    updateUI();
    speech.speak(state.segments[index].content);
}

// ==================== 事件处理 ====================
// 图片上传
elements.uploadArea.onclick = () => elements.imageInput.click();

elements.uploadArea.ondragover = (e) => {
    e.preventDefault();
    elements.uploadArea.classList.add('dragover');
};

elements.uploadArea.ondragleave = () => {
    elements.uploadArea.classList.remove('dragover');
};

elements.uploadArea.ondrop = (e) => {
    e.preventDefault();
    elements.uploadArea.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
        handleImageFile(file);
    }
};

elements.imageInput.onchange = (e) => {
    const file = e.target.files[0];
    if (file) {
        handleImageFile(file);
    }
};

function handleImageFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const base64 = e.target.result.split(',')[1];
        state.imageBase64 = base64;

        elements.previewImage.src = e.target.result;
        elements.previewImage.classList.remove('hidden');
        elements.uploadPlaceholder.classList.add('hidden');
    };
    reader.readAsDataURL(file);
}

// 开始教学
elements.startBtn.onclick = async () => {
    const text = elements.contentInput.value.trim();
    const image = state.imageBase64;

    if (!text && !image) {
        showError('请上传图片或输入内容');
        return;
    }

    try {
        showLoading('🔄 正在分析内容并生成讲解...');
        const result = await api.startTeaching(text, image);

        state.segments = result.segments || [];
        state.currentSegmentIndex = -1;
        state.isPlaying = false;

        if (state.segments.length > 0) {
            elements.welcomeSection.classList.add('hidden');
            elements.teachingSection.classList.remove('hidden');
            elements.resetBtn.classList.remove('hidden');

            renderOutline();
            updateUI();
        } else {
            showError('未能生成讲解内容');
        }
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
};

// 重置
elements.resetBtn.onclick = () => {
    speech.stop();
    state.segments = [];
    state.currentSegmentIndex = -1;
    state.isPlaying = false;
    state.imageBase64 = null;

    elements.welcomeSection.classList.remove('hidden');
    elements.teachingSection.classList.add('hidden');
    elements.resetBtn.classList.add('hidden');
    elements.previewImage.classList.add('hidden');
    elements.uploadPlaceholder.classList.remove('hidden');
    elements.contentInput.value = '';
};


// 播放控制
elements.playBtn.onclick = () => {
    if (state.currentSegmentIndex < 0) {
        // 开始讲解
        state.currentSegmentIndex = 0;
        state.isPlaying = true;
        updateUI();
        speech.speak(state.segments[0].content);
    } else if (state.isPlaying) {
        // 暂停
        speech.pause();
        state.isPlaying = false;
        updateUI();
    } else {
        // 继续
        speech.resume();
        state.isPlaying = true;
        updateUI();
    }
};

// 上一段
elements.prevBtn.onclick = () => {
    if (state.currentSegmentIndex > 0) {
        state.currentSegmentIndex--;
        state.isPlaying = true;
        updateUI();
        speech.speak(state.segments[state.currentSegmentIndex].content);
    }
};

// 下一段
elements.nextBtn.onclick = () => {
    if (state.currentSegmentIndex < state.segments.length - 1) {
        state.currentSegmentIndex++;
        state.isPlaying = true;
        updateUI();
        speech.speak(state.segments[state.currentSegmentIndex].content);
    }
};

// 提问
elements.questionBtn.onclick = () => {
    speech.pause();
    state.isPlaying = false;
    updateUI();
    elements.questionModal.classList.remove('hidden');
    elements.questionInput.focus();
};

elements.cancelQuestionBtn.onclick = () => {
    elements.questionModal.classList.add('hidden');
    elements.questionInput.value = '';
};

elements.submitQuestionBtn.onclick = async () => {
    const question = elements.questionInput.value.trim();
    if (!question) {
        showError('请输入问题');
        return;
    }

    try {
        elements.questionModal.classList.add('hidden');
        showLoading('🤔 正在思考你的问题...');

        const result = await api.askQuestion(question, state.currentSegmentIndex);

        elements.displayQuestion.textContent = question;
        elements.displayAnswer.textContent = result.answer || '';

        if (result.transition) {
            elements.transitionText.textContent = `🔗 过渡: ${result.transition}`;
            elements.transitionText.classList.remove('hidden');
            state.pendingTransition = result.transition;
        } else {
            elements.transitionText.classList.add('hidden');
            state.pendingTransition = null;
        }

        elements.answerModal.classList.remove('hidden');

        // 朗读答案
        speech.speak(result.answer);

    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
        elements.questionInput.value = '';
    }
};

elements.continueBtn.onclick = () => {
    elements.answerModal.classList.add('hidden');
    state.isPlaying = true;
    updateUI();

    // 如果有过渡语，先朗读过渡语再朗读当前内容
    const currentContent = state.segments[state.currentSegmentIndex]?.content || '';
    const fullText = state.pendingTransition
        ? `${state.pendingTransition} ${currentContent}`
        : currentContent;

    speech.speak(fullText);
    state.pendingTransition = null;
};

// 示例按钮
document.querySelectorAll('.btn-example').forEach(btn => {
    btn.onclick = async () => {
        const content = btn.dataset.content;
        elements.contentInput.value = content;

        try {
            showLoading('🔄 正在分析内容并生成讲解...');
            const result = await api.startTeaching(content, null);

            state.segments = result.segments || [];
            state.currentSegmentIndex = -1;
            state.isPlaying = false;

            if (state.segments.length > 0) {
                elements.welcomeSection.classList.add('hidden');
                elements.teachingSection.classList.remove('hidden');
                elements.resetBtn.classList.remove('hidden');

                renderOutline();
                updateUI();
            } else {
                showError('未能生成讲解内容');
            }
        } catch (error) {
            showError(error.message);
        } finally {
            hideLoading();
        }
    };
});

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    speech.init();
    console.log('🎤 AI 交互式语音教学系统已加载');
});

