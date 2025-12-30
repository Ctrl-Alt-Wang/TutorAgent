/**
 * AI 智能教学助手 - 全新三栏界面
 * 左：上传区 | 中：讲解区（带语音控制） | 右：问答区
 */

// ==================== 全局状态 ====================
const state = {
    sessionId: generateUUID(),
    segments: [],
    currentSegmentIndex: -1,
    isTeaching: false,
    isPaused: false,
    imageBase64: null,
    contentText: '',
    
    // 语音
    utterance: null,
    isSpeaking: false,
    speechRate: 1.0,
    
    // QA历史
    qaHistory: []
};

// ==================== DOM 引用 ====================
const dom = {
    // 左侧上传区
    uploadZone: document.getElementById('uploadZone'),
    fileInput: document.getElementById('fileInput'),
    previewContainer: document.getElementById('previewContainer'),
    previewImage: document.getElementById('previewImage'),
    reuploadBtn: document.getElementById('reuploadBtn'),
    textInput: document.getElementById('textInput'),
    startLectureBtn: document.getElementById('startLectureBtn'),
    
    // 中间讲解区
    welcomeScreen: document.getElementById('welcomeScreen'),
    lectureScreen: document.getElementById('lectureScreen'),
    lectureContent: document.getElementById('contentCard'),  // 讲解内容容器
    contentCard: document.getElementById('contentCard'),      // 别名，保持兼容
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    statusIndicator: document.getElementById('statusIndicator'),
    
    // 语音控制条
    playPauseBtn: document.getElementById('playPauseBtn'),
    stopBtn: document.getElementById('stopBtn'),
    prevBtn: document.getElementById('prevBtn'),
    nextBtn: document.getElementById('nextBtn'),
    speedControl: document.getElementById('speedControl'),
    speedValue: document.getElementById('speedValue'),
    
    // 右侧问答区
    qaContainer: document.getElementById('qaContainer'),
    questionInput: document.getElementById('questionInput'),
    sendQuestionBtn: document.getElementById('sendQuestionBtn'),
    
    // 加载
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingText: document.getElementById('loadingText')
};

// ==================== 工具函数 ====================
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function showLoading(text = '处理中...') {
    dom.loadingText.textContent = text;
    dom.loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    dom.loadingOverlay.style.display = 'none';
}

function showNotification(message, type = 'info') {
    // 简单提示
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'error' ? '#ef4444' : '#10b981'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
    `;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
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
    
    speak(text) {
        return new Promise((resolve) => {
            this.stop();
            
            const utterance = new SpeechSynthesisUtterance(text);
            const voice = this.getChineseVoice();
            if (voice) utterance.voice = voice;
            
            utterance.rate = state.speechRate;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;
            
            utterance.onstart = () => {
                state.isSpeaking = true;
                updatePlayPauseButton();
                updateStatusIndicator('speaking');
            };
            
            utterance.onend = () => {
                state.isSpeaking = false;
                updatePlayPauseButton();
                resolve();
            };
            
            utterance.onerror = (e) => {
                console.error('Speech error:', e);
                state.isSpeaking = false;
                resolve();
            };
            
            state.utterance = utterance;
            this.synth.speak(utterance);
        });
    },
    
    stop() {
        this.synth.cancel();
        state.utterance = null;
        state.isSpeaking = false;
        updatePlayPauseButton();
    },
    
    pause() {
        if (state.isSpeaking) {
            this.synth.pause();
            state.isPaused = true;
            updatePlayPauseButton();
            updateStatusIndicator('paused');
        }
    },
    
    resume() {
        if (state.isPaused) {
            this.synth.resume();
            state.isPaused = false;
            updatePlayPauseButton();
            updateStatusIndicator('speaking');
        }
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
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || error.message || '启动教学失败');
        }
        
        return response.json();
    },
    
    async askQuestion(question) {
        const response = await fetch('/api/ask-question', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                question: question,
                current_segment_index: state.currentSegmentIndex
            })
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || error.message || '提问失败');
        }
        
        return response.json();
    }
};

// ==================== UI 更新函数 ====================
function updateStatusIndicator(status) {
    const indicators = {
        'idle': { text: '等待中', color: '#94a3b8' },
        'analyzing': { text: '分析中', color: '#f59e0b' },
        'speaking': { text: '讲解中', color: '#10b981' },
        'paused': { text: '已暂停', color: '#3b82f6' },
        'waiting': { text: '等待回答', color: '#8b5cf6' }
    };
    
    const indicator = indicators[status] || indicators.idle;
    dom.statusIndicator.textContent = indicator.text;
    dom.statusIndicator.style.background = indicator.color;
}

function updatePlayPauseButton() {
    const icon = dom.playPauseBtn.querySelector('.icon');
    if (state.isSpeaking && !state.isPaused) {
        icon.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="4" width="4" height="16" rx="1"/>
                <rect x="14" y="4" width="4" height="16" rx="1"/>
            </svg>
        `;
        dom.playPauseBtn.title = '暂停';
    } else {
        icon.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M8 5v14l11-7z"/>
            </svg>
        `;
        dom.playPauseBtn.title = state.isPaused ? '继续' : '播放';
    }
}

function updateProgress() {
    if (state.segments.length === 0) return;
    
    const progress = ((state.currentSegmentIndex + 1) / state.segments.length) * 100;
    dom.progressBar.style.width = `${progress}%`;
    dom.progressText.textContent = `第 ${state.currentSegmentIndex + 1} / ${state.segments.length} 段`;
}

// ==================== 内容渲染 ====================
function renderSegment(segment, index) {
    const isActive = index === state.currentSegmentIndex;
    
    const segmentDiv = document.createElement('div');
    segmentDiv.className = `lecture-segment${isActive ? ' active' : ''}`;
    segmentDiv.dataset.index = index;
    
    const header = document.createElement('div');
    header.className = 'segment-header';
    
    const number = document.createElement('div');
    number.className = 'segment-number';
    number.textContent = index + 1;
    
    const title = document.createElement('h3');
    title.className = 'segment-title';
    title.textContent = segment.title || `第${index + 1}段`;
    
    header.appendChild(number);
    header.appendChild(title);
    
    const content = document.createElement('div');
    content.className = 'segment-text';
    content.textContent = segment.content;
    
    // 添加高亮词点击
    if (segment.content) {
        content.innerHTML = highlightKeywords(segment.content);
        
        // 为高亮词添加点击事件
        content.querySelectorAll('.highlight-word').forEach(word => {
            word.onclick = () => {
                if (state.isTeaching) {
                    speech.pause();
                    dom.questionInput.value = `关于"${word.textContent}"我想问：`;
                    dom.questionInput.focus();
                    showNotification('讲解已暂停，请输入你的问题', 'info');
                }
            };
        });
    }
    
    // 关键点标签
    if (segment.key_points && segment.key_points.length > 0) {
        const keypoints = document.createElement('div');
        keypoints.className = 'segment-keypoints';
        
        segment.key_points.forEach(point => {
            const tag = document.createElement('span');
            tag.className = 'keypoint-tag';
            tag.textContent = point;
            keypoints.appendChild(tag);
        });
        
        segmentDiv.appendChild(header);
        segmentDiv.appendChild(content);
        segmentDiv.appendChild(keypoints);
    } else {
        segmentDiv.appendChild(header);
        segmentDiv.appendChild(content);
    }
    
    return segmentDiv;
}

function highlightKeywords(text) {
    // 简单的关键词高亮（可根据需要扩展）
    const keywords = ['定理', '公式', '概念', '方法', '步骤', '注意', '重点', '关键'];
    let result = text;
    
    keywords.forEach(keyword => {
        const regex = new RegExp(`(${keyword})`, 'g');
        result = result.replace(regex, '<span class="highlight-word">$1</span>');
    });
    
    return result;
}

function renderAllSegments() {
    dom.lectureContent.innerHTML = '';
    
    state.segments.forEach((segment, index) => {
        const segmentElement = renderSegment(segment, index);
        dom.lectureContent.appendChild(segmentElement);
    });
}

function scrollToCurrentSegment() {
    const activeSegment = dom.lectureContent.querySelector('.lecture-segment.active');
    if (activeSegment) {
        activeSegment.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// ==================== 问答区渲染 ====================
function addQAMessage(type, content) {
    const message = document.createElement('div');
    message.className = `qa-message qa-${type}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'qa-avatar';
    avatar.innerHTML = type === 'question' ? 
        '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>' :
        '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/></svg>';
    
    const bubble = document.createElement('div');
    bubble.className = 'qa-bubble';
    bubble.textContent = content;
    
    message.appendChild(avatar);
    message.appendChild(bubble);
    
    dom.qaContainer.appendChild(message);
    
    // 滚动到底部
    setTimeout(() => {
        dom.qaContainer.scrollTop = dom.qaContainer.scrollHeight;
    }, 100);
}

function addTransitionMessage(transition) {
    const message = document.createElement('div');
    message.className = 'qa-transition';
    message.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
        </svg>
        <span>${transition}</span>
    `;
    
    dom.qaContainer.appendChild(message);
    
    setTimeout(() => {
        dom.qaContainer.scrollTop = dom.qaContainer.scrollHeight;
    }, 100);
}

// ==================== 教学流程 ====================
async function startTeaching() {
    state.isTeaching = true;
    state.currentSegmentIndex = 0;
    
    updateStatusIndicator('speaking');
    renderAllSegments();
    scrollToCurrentSegment();
    
    // 自动播放
    await playCurrentSegment();
}

async function playCurrentSegment() {
    if (state.currentSegmentIndex < 0 || state.currentSegmentIndex >= state.segments.length) {
        return;
    }
    
    const segment = state.segments[state.currentSegmentIndex];
    
    // 高亮当前段
    updateActiveSegment();
    updateProgress();
    scrollToCurrentSegment();
    
    // 播放语音
    await speech.speak(segment.content);
    
    // 自动进入下一段
    if (state.isTeaching && state.currentSegmentIndex < state.segments.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 800));
        state.currentSegmentIndex++;
        await playCurrentSegment();
    } else if (state.currentSegmentIndex >= state.segments.length - 1) {
        // 讲解完成
        state.isTeaching = false;
        updateStatusIndicator('idle');
        showNotification('✅ 讲解完成！', 'success');
    }
}

function updateActiveSegment() {
    dom.lectureContent.querySelectorAll('.lecture-segment').forEach((seg, idx) => {
        if (idx === state.currentSegmentIndex) {
            seg.classList.add('active');
        } else {
            seg.classList.remove('active');
        }
    });
}

// ==================== 事件处理 ====================

// 上传区域
dom.uploadZone.onclick = () => dom.fileInput.click();

dom.uploadZone.ondragover = (e) => {
    e.preventDefault();
    dom.uploadZone.style.borderColor = 'var(--primary)';
    dom.uploadZone.style.background = 'rgba(99, 102, 241, 0.05)';
};

dom.uploadZone.ondragleave = (e) => {
    e.preventDefault();
    dom.uploadZone.style.borderColor = '';
    dom.uploadZone.style.background = '';
};

dom.uploadZone.ondrop = (e) => {
    e.preventDefault();
    dom.uploadZone.style.borderColor = '';
    dom.uploadZone.style.background = '';
    
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
        handleImageUpload(file);
    }
};

dom.fileInput.onchange = (e) => {
    const file = e.target.files[0];
    if (file) handleImageUpload(file);
};

function handleImageUpload(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const base64 = e.target.result.split(',')[1];
        state.imageBase64 = base64;
        
        dom.previewImage.src = e.target.result;
        dom.uploadZone.style.display = 'none';
        dom.previewContainer.style.display = 'block';
    };
    reader.readAsDataURL(file);
}

dom.reuploadBtn.onclick = () => {
    state.imageBase64 = null;
    dom.previewContainer.style.display = 'none';
    dom.uploadZone.style.display = 'flex';
    dom.fileInput.value = '';
};

// 开始讲解
dom.startLectureBtn.onclick = async () => {
    const text = dom.textInput.value.trim();
    const image = state.imageBase64;
    
    if (!text && !image) {
        showNotification('请上传图片或输入文本内容', 'error');
        return;
    }
    
    try {
        showLoading('🔍 AI 正在分析内容...');
        updateStatusIndicator('analyzing');
        
        const result = await api.startTeaching(text, image);
        
        hideLoading();
        
        if (!result.segments || result.segments.length === 0) {
            showNotification('未能生成讲解内容', 'error');
            return;
        }
        
        state.segments = result.segments;
        state.contentText = result.content_text || text;
        
        // 切换界面
        dom.welcomeScreen.style.display = 'none';
        dom.lectureScreen.style.display = 'flex';
        
        // 开始教学
        await startTeaching();
        
    } catch (error) {
        hideLoading();
        updateStatusIndicator('idle');
        showNotification(error.message, 'error');
        console.error('Start teaching error:', error);
    }
};

// 语音控制
dom.playPauseBtn.onclick = () => {
    if (state.isSpeaking && !state.isPaused) {
        speech.pause();
    } else if (state.isPaused) {
        speech.resume();
    } else {
        // 从当前段重新播放
        playCurrentSegment();
    }
};

dom.stopBtn.onclick = () => {
    speech.stop();
    state.isTeaching = false;
    updateStatusIndicator('idle');
};

dom.prevBtn.onclick = () => {
    if (state.currentSegmentIndex > 0) {
        speech.stop();
        state.currentSegmentIndex--;
        playCurrentSegment();
    }
};

dom.nextBtn.onclick = () => {
    if (state.currentSegmentIndex < state.segments.length - 1) {
        speech.stop();
        state.currentSegmentIndex++;
        playCurrentSegment();
    }
};

dom.speedControl.oninput = (e) => {
    state.speechRate = parseFloat(e.target.value);
    dom.speedValue.textContent = `${state.speechRate.toFixed(1)}x`;
};

// 提问
dom.sendQuestionBtn.onclick = async () => {
    const question = dom.questionInput.value.trim();
    
    if (!question) {
        showNotification('请输入问题', 'error');
        return;
    }
    
    // 暂停讲解
    const wasTeaching = state.isTeaching;
    speech.pause();
    state.isTeaching = false;
    updateStatusIndicator('waiting');
    
    // 显示用户问题
    addQAMessage('question', question);
    dom.questionInput.value = '';
    
    try {
        showLoading('🤔 AI 正在思考...');
        
        const result = await api.askQuestion(question);
        
        hideLoading();
        
        // 显示AI回答
        addQAMessage('answer', result.answer);
        
        // 播放回答
        await speech.speak(result.answer);
        
        // 如果有过渡语
        if (result.transition) {
            await new Promise(resolve => setTimeout(resolve, 500));
            addTransitionMessage(result.transition);
            await speech.speak(result.transition);
        }
        
        // 恢复讲解
        if (wasTeaching) {
            await new Promise(resolve => setTimeout(resolve, 800));
            state.isTeaching = true;
            await playCurrentSegment();
        } else {
            updateStatusIndicator('idle');
        }
        
    } catch (error) {
        hideLoading();
        showNotification(error.message, 'error');
        updateStatusIndicator('idle');
    }
};

// 回车发送
dom.questionInput.onkeydown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        dom.sendQuestionBtn.click();
    }
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    speech.init();
    updateStatusIndicator('idle');
    console.log('✨ AI 智能教学助手已就绪');
});
