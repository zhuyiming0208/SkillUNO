/**
 * SkillUNO 网页商店 · 渲染工具
 */

/**
 * 单个模组卡片 → HTML 字符串
 * basePath: 用于拼接详情页链接的前缀
 *   首页调用：renderModCard(mod)       → mods/detail.html?id=xxx
 *   列表页调用：renderModCard(mod, '../') → ../mods/detail.html?id=xxx
 */
function renderModCard(mod, basePath = '') {
    const modId = mod.ID || mod.id || '?';
    const name = mod.name || '未命名模组';
    const author = mod.author || '匿名';
    const version = mod.version || '?';
    const skills = mod.skills != null ? mod.skills : 0;
    const desc = mod.description || '';
    const builtinBadge = mod.builtin
        ? '<span class="builtin-badge">内置</span>'
        : '';

    const href = mod.builtin
        ? '#'
        : `${basePath}mods/detail.html?id=${encodeURIComponent(modId)}`;

    return `
        <a class="mod-card" href="${href}">
            <h3>${escapeHtml(name)}${builtinBadge}</h3>
            <p class="meta"><span class="label">by</span>${escapeHtml(author)}</p>
            <p class="meta"><span class="label">v</span>${escapeHtml(version)}</p>
            <p class="meta"><span class="label">技能×</span>${skills}</p>
            ${desc ? `<p class="desc">${escapeHtml(desc)}</p>` : ''}
        </a>
    `;
}

/**
 * 渲染模组列表到指定容器
 */
function renderModList(mods, containerId, basePath = '') {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!mods || mods.length === 0) {
        container.innerHTML = '<p class="loading">暂无模组</p>';
        return;
    }
    container.innerHTML = mods.map(m => renderModCard(m, basePath)).join('');
}

/**
 * 简单 HTML 转义，防止 XSS
 */
function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
