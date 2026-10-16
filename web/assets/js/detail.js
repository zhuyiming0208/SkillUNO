/**
 * SkillUNO 网页商店 · 模组详情页逻辑
 */

function getModIdFromUrl() {
    return new URLSearchParams(location.search).get('id');
}

/**
 * 兼容 ID（大写）/ id（官方）
 */
async function findModById(modId) {
    // loadAllMods 已包含官方 + 第三方，并按 ID 去重
    const all = await loadAllMods();
    return all.find(m => (m.ID || m.id) === modId) || null;
}

/**
 * 详情页入口
 */
async function renderDetail() {
    const container = document.getElementById('detail-container');
    const modId = getModIdFromUrl();

    if (!modId) {
        container.innerHTML = renderErrorState('缺少模组 ID 参数');
        return;
    }

    let mod;
    try {
        mod = await findModById(modId);
    } catch (err) {
        console.error(err);
        container.innerHTML = renderErrorState('无法加载模组数据，请检查网络');
        return;
    }

    if (!mod) {
        container.innerHTML = renderErrorState(`未找到该模组：${escapeHtml(modId)}`);
        return;
    }

    container.innerHTML = renderDetailHtml(mod);

    // 绑定复制按钮
    const btn = document.getElementById('copy-install-btn');
    if (btn) {
        btn.addEventListener('click', () => copyInstallCommand(modId));
    }
}

function renderErrorState(msg) {
    return `
        <div class="detail-error">
            <p class="error">${msg}</p>
            <p><a href="index.html" class="back-link">← 返回列表</a></p>
        </div>
    `;
}

function renderDetailHtml(mod) {
    const modId = mod.ID || mod.id || '?';
    const name = mod.name || '未命名模组';
    const author = mod.author || '匿名';
    const authorGithub = mod.author_github || '';
    const version = mod.version || '?';
    const license = mod.license || '';
    const repo = mod.repo || '';
    const desc = mod.description || '（无简介）';
    const micover = mod.micover || '?';
    const lacover = mod.lacover;
    const skills = mod.skills != null ? mod.skills : 0;
    const achievements = mod.achievements != null ? mod.achievements : 0;

    // 作者行
    const authorHtml = authorGithub
        ? `${escapeHtml(author)}（<a href="https://github.com/${encodeURIComponent(authorGithub)}"
              target="_blank" rel="noopener">@${escapeHtml(authorGithub)}</a>）`
        : escapeHtml(author);

    // 兼容性
    const compat = lacover == null
        ? `需要 SkillUNO v${escapeHtml(micover)} 及以上`
        : `需要 SkillUNO v${escapeHtml(micover)} ~ v${escapeHtml(lacover)}`;

    // GitHub 链接
    const repoHtml = repo
        ? `<a href="${escapeHtml(repo)}" target="_blank" rel="noopener">${escapeHtml(repo)}</a>`
        : '<span class="muted">未声明</span>';

    // 协议
    const licenseHtml = license
        ? escapeHtml(license)
        : '<span class="muted">未声明</span>';

    // 标签
    const tagsHtml = renderTags(mod.tags);

    return `
        <div class="detail-card">
            <h1 class="detail-name">${escapeHtml(name)}</h1>
            ${tagsHtml ? `<div class="detail-tags">${tagsHtml}</div>` : ''}

            <div class="detail-meta-grid">
                <div class="meta-row">
                    <span class="meta-label">作者</span>
                    <span class="meta-value">${authorHtml}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">版本</span>
                    <span class="meta-value">v${escapeHtml(version)}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">协议</span>
                    <span class="meta-value">${licenseHtml}</span>
                </div>
                <div class="meta-row">
                    <span class="meta-label">仓库</span>
                    <span class="meta-value">${repoHtml}</span>
                </div>
            </div>
        </div>

        <div class="detail-section">
            <h2 class="detail-section-title">&gt; 简介</h2>
            <p class="detail-desc">${escapeHtml(desc)}</p>
        </div>

        <div class="detail-section">
            <h2 class="detail-section-title">&gt; 兼容性</h2>
            <p>${compat}</p>
        </div>

        <div class="detail-section">
            <h2 class="detail-section-title">&gt; 内容</h2>
            <p>技能 × ${skills}</p>
            <p>成就 × ${achievements}</p>
        </div>

        <div class="detail-section">
            <h2 class="detail-section-title">&gt; 关系</h2>
            <div class="meta-row">
                <span class="meta-label">依赖</span>
                <span class="meta-value">${renderRelations(mod.rely_on)}</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">排斥</span>
                <span class="meta-value">${renderRelations(mod.reject)}</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">白名单</span>
                <span class="meta-value">${renderStringList(mod.only_tolerate)}</span>
            </div>
        </div>

        <div class="detail-section">
            <h2 class="detail-section-title">&gt; 权限声明</h2>
            <p>${renderStringList(mod.needs, '未声明')}</p>
        </div>

        <div class="install-section">
            <h2 class="detail-section-title">&gt; 安装</h2>
            <p class="install-hint">在终端运行以下命令安装：</p>
            <div class="install-cmd-row">
                <code class="install-cmd">skilluno mod install ${escapeHtml(modId)}</code>
                <button id="copy-install-btn" class="copy-btn" type="button">复制</button>
            </div>
            <p class="install-note">重启游戏后生效</p>
        </div>
    `;
}

document.addEventListener('DOMContentLoaded', renderDetail);
