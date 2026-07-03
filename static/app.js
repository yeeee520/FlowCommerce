/**
 * AI Agent 电商客服系统 — 前端交互逻辑
 * V1 极简苹果风格 · 毛玻璃 · 柔和动画
 *
 * 纯原生 JavaScript 实现，无框架依赖。
 *
 * 功能清单：
 * - 聊天消息的发送和接收
 * - SSE 流式响应处理（EventSource → fetch ReadableStream）
 * - 消息渲染（用户消息和 AI 消息的不同样式）
 * - 检索来源展示
 * - 历史消息管理（sessionStorage 持久化）
 * - 侧边栏状态更新（知识库统计、来源统计）
 * - 错误处理和重连/重试机制
 * - 快捷问题点击发送
 * - 输入框 Enter 发送、Shift+Enter 换行
 * - 自动滚动到最新消息
 * - 流式/普通模式切换
 * - Toast 消息提示
 * - 健康检查轮询
 * - Apple 风格微交互：按钮缩放反馈、气泡淡入
 */

// ============================================================
// 全局状态
// ============================================================
const STATE = {
    /** 当前会话消息历史 [{role, content}] */
    chatHistory: [],
    /** 当前消息数（含用户+AI） */
    messageCount: 0,
    /** API 基础地址 */
    apiBase: window.location.origin,
    /** 是否正在等待 AI 回复 */
    isWaiting: false,
    /** 当前活跃的 AbortController，用于取消请求 */
    activeController: null,
    /** 侧边栏是否展开 */
    sidebarExpanded: true,
    /** 知识库统计缓存 */
    kbStats: null,
    /** 健康检查定时器 */
    healthCheckTimer: null,
    /** 检索来源统计 */
    sourceStats: {},
};

// ============================================================
// DOM 元素引用
// ============================================================
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const DOM = {
    // 顶部栏
    statusIndicator: $('#statusIndicator'),
    sidebarToggle: $('#sidebarToggle'),

    // 侧边栏
    sidebar: $('#sidebar'),
    statDocCount: $('#statDocCount'),
    statCollection: $('#statCollection'),
    statSystem: $('#statSystem'),
    statMsgCount: $('#statMsgCount'),
    sourceStats: $('#sourceStats'),
    btnClearSession: $('#btnClearSession'),

    // 聊天
    chatMessages: $('#chatMessages'),
    welcomeScreen: $('#welcomeScreen'),
    chatInput: $('#chatInput'),
    sendBtn: $('#sendBtn'),
    streamToggle: $('#streamToggle'),
    toggleModeText: $('#toggleModeText'),

    // Toast
    toastContainer: $('#toastContainer'),
};

// ============================================================
// 初始化
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadHistoryFromStorage();
    startHealthCheck();
    fetchKnowledgeBaseStats();
    updateSidebarMsgCount();
});

// ============================================================
// 事件绑定
// ============================================================
function initEventListeners() {
    // 发送按钮
    DOM.sendBtn.addEventListener('click', handleSend);
    // Apple 风格：发送按钮 mousedown 时缩放反馈
    DOM.sendBtn.addEventListener('mousedown', () => {
        DOM.sendBtn.style.transform = 'scale(0.92)';
    });
    DOM.sendBtn.addEventListener('mouseup', () => {
        DOM.sendBtn.style.transform = '';
    });
    DOM.sendBtn.addEventListener('mouseleave', () => {
        if (!DOM.sendBtn.disabled) {
            DOM.sendBtn.style.transform = '';
        }
    });

    // 输入框键盘事件
    DOM.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });

    // 输入框自动调整高度
    DOM.chatInput.addEventListener('input', autoResizeInput);

    // 流式模式切换
    DOM.streamToggle.addEventListener('change', () => {
        const isStream = DOM.streamToggle.checked;
        DOM.toggleModeText.textContent = isStream ? '流式模式' : '普通模式';
    });

    // 侧边栏切换
    DOM.sidebarToggle.addEventListener('click', toggleSidebar);

    // 清除会话
    DOM.btnClearSession.addEventListener('click', clearSession);

    // 快捷问题点击（事件委托）
    DOM.welcomeScreen.addEventListener('click', (e) => {
        const btn = e.target.closest('.quick-btn');
        if (!btn) return;
        const question = btn.dataset.question;
        if (question) {
            DOM.chatInput.value = question;
            handleSend();
        }
    });

    // 重试按钮（事件委托）
    DOM.chatMessages.addEventListener('click', (e) => {
        const retryBtn = e.target.closest('.retry-btn');
        if (!retryBtn) return;
        const messageText = retryBtn.dataset.message;
        if (messageText) {
            DOM.chatInput.value = messageText;
            handleSend();
        }
    });
}

// ============================================================
// 发送消息
// ============================================================
async function handleSend() {
    const message = DOM.chatInput.value.trim();
    if (!message || STATE.isWaiting) return;

    // 清空输入框
    DOM.chatInput.value = '';
    autoResizeInput();

    // 隐藏欢迎界面
    hideWelcome();

    // 渲染用户消息
    renderMessage('user', message);
    STATE.chatHistory.push({ role: 'user', content: message });
    STATE.messageCount++;
    updateSidebarMsgCount();

    // 显示正在输入指示器
    const typingBubble = renderTypingIndicator();
    scrollToBottom();

    // 创建 AbortController
    STATE.activeController = new AbortController();
    STATE.isWaiting = true;
    DOM.sendBtn.disabled = true;

    const isStream = DOM.streamToggle.checked;

    try {
        if (isStream) {
            await handleStreamResponse(message, typingBubble);
        } else {
            await handleNormalResponse(message, typingBubble);
        }
    } catch (err) {
        if (err.name === 'AbortError') {
            // 用户主动取消
            removeTypingIndicator(typingBubble);
        } else {
            // 网络或其他错误
            updateTypingToError(typingBubble, message, err.message);
        }
    } finally {
        STATE.isWaiting = false;
        STATE.activeController = null;
        DOM.sendBtn.disabled = false;
        scrollToBottom();
        saveHistoryToStorage();
    }
}

// ============================================================
// 普通模式（非流式）响应处理
// ============================================================
async function handleNormalResponse(message, typingBubble) {
    const response = await fetch(`${STATE.apiBase}/api/chat/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message,
            history: STATE.chatHistory.slice(0, -1), // 不包含刚发的这条
            stream: false,
        }),
        signal: STATE.activeController.signal,
    });

    if (!response.ok) {
        let detail = '';
        try {
            const errBody = await response.json();
            detail = errBody.detail ? `: ${errBody.detail}` : '';
        } catch (_) { /* 响应体非 JSON，忽略 */ }
        throw new Error(`服务器错误 (${response.status})${detail}`);
    }

    const data = await response.json();
    const reply = data.reply || '抱歉，我暂时无法回复你的问题。';

    // 替换 typing indicator 为 AI 消息
    removeTypingIndicator(typingBubble);
    renderMessage('assistant', reply, data.sources);
    STATE.chatHistory.push({ role: 'assistant', content: reply });
    STATE.messageCount++;
    updateSidebarMsgCount();

    // 更新检索来源统计
    if (data.sources && data.sources.length > 0) {
        updateSourceStats(data.sources);
    }

    // 更新意图标签（如果有）
    if (data.intent) {
        showToast(`识别意图: ${data.intent}`, 'info');
    }
}

// ============================================================
// SSE 流式响应处理（使用 fetch + ReadableStream）
// ============================================================
async function handleStreamResponse(message, typingBubble) {
    const response = await fetch(`${STATE.apiBase}/api/chat/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message,
            history: STATE.chatHistory.slice(0, -1),
            stream: true,
        }),
        signal: STATE.activeController.signal,
    });

    if (!response.ok) {
        let detail = '';
        try {
            const errBody = await response.json();
            detail = errBody.detail ? `: ${errBody.detail}` : '';
        } catch (_) { /* 响应体非 JSON，忽略 */ }
        throw new Error(`服务器错误 (${response.status})${detail}`);
    }

    // 替换 typing indicator 为 AI 消息气泡（带流式光标）
    removeTypingIndicator(typingBubble);
    const messageEl = renderMessage('assistant', '', null, true);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullContent = '';
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // 处理 SSE 数据行
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保留不完整的行

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith('data: ')) continue;

            const dataStr = trimmed.slice(6); // 去掉 "data: "

            // 检测结束标记
            if (dataStr === '[DONE]') {
                break;
            }

            try {
                const data = JSON.parse(dataStr);
                if (data.type === 'token' && data.content) {
                    fullContent += data.content;
                    updateStreamingMessage(messageEl, fullContent);
                }
                // 也支持直接返回内容的格式
                if (data.content && !data.type) {
                    fullContent += data.content;
                    updateStreamingMessage(messageEl, fullContent);
                }
                if (data.sources) {
                    attachSourcesToMessage(messageEl, data.sources);
                    updateSourceStats(data.sources);
                }
            } catch (parseErr) {
                // 非 JSON 数据行，可能是纯文本 token
                if (dataStr.length > 0 && dataStr !== '[DONE]') {
                    fullContent += dataStr;
                    updateStreamingMessage(messageEl, fullContent);
                }
            }
        }
    }

    // 流式结束，移除光标
    const bubble = messageEl.querySelector('.bubble');
    if (bubble) {
        bubble.classList.remove('streaming');
    }

    // 保存到历史
    const finalContent = fullContent || '抱歉，我暂时无法回复你的问题。';
    STATE.chatHistory.push({ role: 'assistant', content: finalContent });
    STATE.messageCount++;
    updateSidebarMsgCount();
}

// ============================================================
// 消息渲染
// ============================================================

/**
 * 渲染一条消息到聊天区域
 * @param {'user'|'assistant'} role - 消息角色
 * @param {string} content - 消息内容
 * @param {Array} sources - 检索来源（仅 AI 消息）
 * @param {boolean} isStreaming - 是否为流式输出中
 * @returns {HTMLElement} 消息容器元素
 */
function renderMessage(role, content, sources, isStreaming) {
    const wrapper = document.createElement('div');
    wrapper.className = `message ${role}`;

    // 消息头部（头像 + 名称）
    const header = document.createElement('div');
    header.className = 'message-header';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '我' : 'AI';

    const name = document.createElement('span');
    name.textContent = role === 'user' ? '我' : 'AI 客服助手';

    header.appendChild(avatar);
    header.appendChild(name);
    wrapper.appendChild(header);

    // 消息气泡
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    if (isStreaming) {
        bubble.classList.add('streaming');
    }
    bubble.textContent = content;
    wrapper.appendChild(bubble);

    // 检索来源（仅 AI 消息且有来源时显示）
    if (role === 'assistant' && sources && sources.length > 0) {
        const sourcesEl = createSourcesElement(sources);
        wrapper.appendChild(sourcesEl);
    }

    // 时间戳
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = formatTime(new Date());
    wrapper.appendChild(time);

    DOM.chatMessages.appendChild(wrapper);
    scrollToBottom();
    return wrapper;
}

/**
 * 更新流式消息内容
 */
function updateStreamingMessage(messageEl, content) {
    const bubble = messageEl.querySelector('.bubble');
    if (bubble) {
        bubble.textContent = content;
    }
    scrollToBottom();
}

/**
 * 为已有消息附加检索来源
 */
function attachSourcesToMessage(messageEl, sources) {
    // 移除旧的来源元素（如果存在）
    const oldSources = messageEl.querySelector('.message-sources');
    if (oldSources) oldSources.remove();

    if (sources && sources.length > 0) {
        const sourcesEl = createSourcesElement(sources);
        messageEl.appendChild(sourcesEl);
    }
}

/**
 * 创建检索来源 DOM 元素
 */
function createSourcesElement(sources) {
    const container = document.createElement('div');
    container.className = 'message-sources';

    sources.forEach((src) => {
        const tag = document.createElement('span');
        tag.className = 'source-tag';

        const docName = document.createElement('span');
        docName.className = 'tag-doc';
        // 使用 metadata 中的文件名，或截取文本前几个字
        const name = src.metadata?.filename || src.text?.substring(0, 20) || '未知文档';
        docName.textContent = name;
        docName.title = name;

        const score = document.createElement('span');
        score.className = 'tag-score';
        const scoreVal = typeof src.score === 'number' ? src.score : parseFloat(src.score);
        score.textContent = !isNaN(scoreVal) ? `${(scoreVal * 100).toFixed(0)}%` : '--';

        tag.appendChild(docName);
        tag.appendChild(score);
        container.appendChild(tag);
    });

    return container;
}

/**
 * 渲染正在输入指示器
 * @returns {HTMLElement} typing 容器元素
 */
function renderTypingIndicator() {
    const wrapper = document.createElement('div');
    wrapper.className = 'message assistant typing-message';

    const header = document.createElement('div');
    header.className = 'message-header';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'AI';

    const name = document.createElement('span');
    name.textContent = 'AI 客服助手';

    header.appendChild(avatar);
    header.appendChild(name);
    wrapper.appendChild(header);

    const bubble = document.createElement('div');
    bubble.className = 'bubble typing-indicator';
    bubble.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    wrapper.appendChild(bubble);

    DOM.chatMessages.appendChild(wrapper);
    return wrapper;
}

/**
 * 移除正在输入指示器
 */
function removeTypingIndicator(typingEl) {
    if (typingEl && typingEl.parentNode) {
        typingEl.parentNode.removeChild(typingEl);
    }
}

/**
 * 将 typing 指示器替换为错误提示
 */
function updateTypingToError(typingEl, originalMessage, errorMsg) {
    if (!typingEl || !typingEl.parentNode) return;

    const bubble = typingEl.querySelector('.bubble');
    if (bubble) {
        bubble.classList.remove('typing-indicator');
        bubble.classList.add('error-bubble');
        bubble.innerHTML = '';

        const errorText = document.createElement('span');
        errorText.textContent = `请求失败: ${errorMsg || '网络错误，请稍后重试。'}`;
        bubble.appendChild(errorText);

        const retryBtn = document.createElement('button');
        retryBtn.className = 'retry-btn';
        retryBtn.dataset.message = originalMessage;
        retryBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
            </svg>
            重试
        `;
        bubble.appendChild(retryBtn);
    }
}

// ============================================================
// 快捷问题 & 欢迎界面
// ============================================================

/** 隐藏欢迎界面 */
function hideWelcome() {
    if (DOM.welcomeScreen) {
        DOM.welcomeScreen.style.display = 'none';
    }
}

/** 显示欢迎界面（清空消息后） */
function showWelcome() {
    if (DOM.welcomeScreen) {
        DOM.welcomeScreen.style.display = '';
    }
}

// ============================================================
// 侧边栏操作
// ============================================================

/** 切换侧边栏展开/折叠 */
function toggleSidebar() {
    STATE.sidebarExpanded = !STATE.sidebarExpanded;
    if (STATE.sidebarExpanded) {
        DOM.sidebar.classList.remove('sidebar-collapsed');
    } else {
        DOM.sidebar.classList.add('sidebar-collapsed');
    }
}

/** 更新侧边栏消息计数 */
function updateSidebarMsgCount() {
    if (DOM.statMsgCount) {
        DOM.statMsgCount.textContent = STATE.messageCount;
    }
}

/** 更新检索来源统计 */
function updateSourceStats(sources) {
    if (!sources || sources.length === 0) return;

    sources.forEach((src) => {
        const name = src.metadata?.filename || src.text?.substring(0, 30) || '未知文档';
        if (!STATE.sourceStats[name]) {
            STATE.sourceStats[name] = { count: 0, maxScore: 0 };
        }
        STATE.sourceStats[name].count++;
        const scoreVal = typeof src.score === 'number' ? src.score : parseFloat(src.score);
        if (!isNaN(scoreVal) && scoreVal > STATE.sourceStats[name].maxScore) {
            STATE.sourceStats[name].maxScore = scoreVal;
        }
    });

    renderSourceStats();
}

/** 渲染来源统计到侧边栏 */
function renderSourceStats() {
    if (!DOM.sourceStats) return;

    const entries = Object.entries(STATE.sourceStats);
    if (entries.length === 0) {
        DOM.sourceStats.innerHTML = '<p class="source-empty">暂无数据</p>';
        return;
    }

    // 按引用次数降序排列
    entries.sort((a, b) => b[1].count - a[1].count);

    DOM.sourceStats.innerHTML = entries
        .map(([name, stat]) => `
            <div class="source-item">
                <span class="source-name" title="${escapeHtml(name)}">${escapeHtml(name)}</span>
                <span class="source-score">${(stat.maxScore * 100).toFixed(0)}% x${stat.count}</span>
            </div>
        `)
        .join('');
}

// ============================================================
// 知识库统计 API
// ============================================================

async function fetchKnowledgeBaseStats() {
    try {
        const response = await fetch(`${STATE.apiBase}/api/data/stats`);
        if (response.ok) {
            const data = await response.json();
            STATE.kbStats = data;
            DOM.statDocCount.textContent = data.document_count ?? '--';
            DOM.statCollection.textContent = data.collection_name ?? '--';
            DOM.statSystem.textContent = '正常';
        } else {
            DOM.statDocCount.textContent = '--';
            DOM.statCollection.textContent = '--';
        }
    } catch (err) {
        DOM.statDocCount.textContent = '--';
        DOM.statCollection.textContent = '--';
        DOM.statSystem.textContent = '未连接';
    }
}

// ============================================================
// 健康检查
// ============================================================

function startHealthCheck() {
    // 立即检查一次
    performHealthCheck();

    // 每 30 秒轮询一次
    STATE.healthCheckTimer = setInterval(performHealthCheck, 30000);
}

async function performHealthCheck() {
    try {
        const response = await fetch(`${STATE.apiBase}/health`);
        if (response.ok) {
            setSystemStatus(true);
        } else {
            setSystemStatus(false);
        }
    } catch (err) {
        setSystemStatus(false);
    }
}

function setSystemStatus(online) {
    if (online) {
        DOM.statusIndicator.classList.remove('offline');
        DOM.statusIndicator.querySelector('.status-text').textContent = '在线';
        DOM.statSystem.textContent = '正常';
    } else {
        DOM.statusIndicator.classList.add('offline');
        DOM.statusIndicator.querySelector('.status-text').textContent = '离线';
        DOM.statSystem.textContent = '离线';
    }
}

// ============================================================
// 会话历史持久化（sessionStorage）
// ============================================================

function saveHistoryToStorage() {
    try {
        const data = {
            chatHistory: STATE.chatHistory,
            messageCount: STATE.messageCount,
            sourceStats: STATE.sourceStats,
        };
        sessionStorage.setItem('ai_agent_chat', JSON.stringify(data));
    } catch (err) {
        // sessionStorage 可能已满，忽略
    }
}

function loadHistoryFromStorage() {
    try {
        const raw = sessionStorage.getItem('ai_agent_chat');
        if (!raw) return;

        const data = JSON.parse(raw);
        STATE.chatHistory = data.chatHistory || [];
        STATE.messageCount = data.messageCount || 0;
        STATE.sourceStats = data.sourceStats || {};

        // 重新渲染历史消息
        if (STATE.chatHistory.length > 0) {
            hideWelcome();
            for (let i = 0; i < STATE.chatHistory.length; i++) {
                const msg = STATE.chatHistory[i];
                // 简单判断：user 消息直接渲染，assistant 消息查找对应的 sources
                if (msg.role === 'user') {
                    renderMessage('user', msg.content);
                } else {
                    // 尝试从下一条消息的 metadata 获取 sources
                    renderMessage('assistant', msg.content, null);
                }
            }
            renderSourceStats();
        }

        updateSidebarMsgCount();
        scrollToBottom();
    } catch (err) {
        // 解析失败，重置
        STATE.chatHistory = [];
        STATE.messageCount = 0;
    }
}

/** 清除当前会话 */
function clearSession() {
    STATE.chatHistory = [];
    STATE.messageCount = 0;
    STATE.sourceStats = {};

    // 清除 DOM 中的消息（保留欢迎界面）
    const messages = DOM.chatMessages.querySelectorAll('.message');
    messages.forEach((msg) => msg.remove());

    // 显示欢迎界面
    showWelcome();

    // 清除 sessionStorage
    sessionStorage.removeItem('ai_agent_chat');

    // 更新侧边栏
    updateSidebarMsgCount();
    renderSourceStats();

    showToast('会话已清除', 'info');
}

// ============================================================
// Toast 提示
// ============================================================

/**
 * 显示 Toast 提示
 * @param {string} message - 提示内容
 * @param {'success'|'error'|'warning'|'info'} type - 类型
 * @param {number} duration - 持续时间（毫秒）
 */
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    DOM.toastContainer.appendChild(toast);

    // 自动移除
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, duration);
}

// ============================================================
// 工具函数
// ============================================================

/** 滚动到最新消息 */
function scrollToBottom() {
    if (DOM.chatMessages) {
        DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
    }
}

/** 自动调整输入框高度 */
function autoResizeInput() {
    const input = DOM.chatInput;
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
}

/** 格式化时间 */
function formatTime(date) {
    const h = String(date.getHours()).padStart(2, '0');
    const m = String(date.getMinutes()).padStart(2, '0');
    return `${h}:${m}`;
}

/** HTML 转义 */
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ============================================================
// 页面卸载时清理
// ============================================================
window.addEventListener('beforeunload', () => {
    // 取消进行中的请求
    if (STATE.activeController) {
        STATE.activeController.abort();
    }
    // 清除健康检查定时器
    if (STATE.healthCheckTimer) {
        clearInterval(STATE.healthCheckTimer);
    }
});
