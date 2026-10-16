/**
 * SkillUNO 网页商店 · 搜索工具
 */

/**
 * 按关键词过滤模组
 * 匹配字段：ID / id / name / author / author_github / tags
 * 大小写不敏感
 */
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
