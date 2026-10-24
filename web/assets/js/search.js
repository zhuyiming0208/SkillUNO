/**
 * SkillUNO 网页商店 · 搜索工具
 */

/**
 * 按关键词过滤模组
 * 匹配字段：ID / id / name / author / author_github / tags
 * 大小写不敏感
 */
// 注意：此函数匹配字段包含 tags，因此当与外部标签栏筛选同时使用时，
// 会天然形成 AND 逻辑。若未来修改匹配字段，需留意此副作用。
function filterMods(mods, keyword) {
    if (!keyword || !keyword.trim()) return mods;
    const kw = keyword.trim().toLowerCase();
    return mods.filter(m => {
        const fields = [
            m.ID, m.id, m.name, m.author, m.author_github,
            ...(m.tags || []),
        ];
        return fields.some(f =>
            f && String(f).toLowerCase().includes(kw)
        );
    });
}

/**
 * 防抖：输入停止 delay 毫秒后才触发 fn
 */
function debounce(fn, delay) {
    let timer = null;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}


/**
 * 从模组列表中提取所有不重复标签，按字母序排列。
 */
function extractTags(mods) {
    const set = new Set();
    for (const m of mods) {
        if (Array.isArray(m.tags)) {
            for (const t of m.tags) {
                if (t && typeof t === 'string') set.add(t);
            }
        }
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh-CN'));
}

/**
 * 按标签过滤。tag 为空时原样返回。
 */
function filterByTag(mods, tag) {
    if (!tag) return mods;
    return mods.filter(m => Array.isArray(m.tags) && m.tags.includes(tag));
}
