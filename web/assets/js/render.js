/**
 * SkillUNO 网页商店 · 渲染工具
 */

/**
 * 单个模组卡片 → HTML 字符串
 * 兼容两种 id 键名：ID（大写） / id（官方模组）
 */
function renderModCard(mod) {
    const modId = mod.ID || mod.id || '?';
    const name = mod.name || '未命名模组';
    const author = mod.author || '匿名';
    const version = mod.version || '?';
    const skills = mod.skills != null ? mod.skills : 0;
    const desc = mod.description || '';
    const builtinBadge = mod.builtin
        ? '<span class="builtin-badge">内置</span>'
        : '';

    // 官方模组暂时没有详情页，用 # 占位
    const href = mod.builtin
        ? '#'
        : `mods/detail.html?id=${encodeURIComponent(modId)}`;

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
function renderModList(mods, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!mods || mods.length === 0) {
        container.innerHTML = '<p class="loading">暂无模组</p>';
        return;
    }
    container.innerHTML = mods.map(renderModCard).join('');
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
