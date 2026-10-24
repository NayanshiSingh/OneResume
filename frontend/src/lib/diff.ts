/** Word-level diff: marks which words of `after` are not in `before` (longest common subsequence). */
export function addedWords(before: string, after: string): { word: string; added: boolean }[] {
    const a = before.split(/\s+/).filter(Boolean);
    const b = after.split(/\s+/).filter(Boolean);
    const norm = (w: string) => w.toLowerCase().replace(/[.,;:!?]+$/, "");
    const lcs = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
    for (let i = a.length - 1; i >= 0; i--) {
        for (let j = b.length - 1; j >= 0; j--) {
            lcs[i][j] = norm(a[i]) === norm(b[j]) ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
        }
    }
    const result: { word: string; added: boolean }[] = [];
    let i = 0;
    for (let j = 0; j < b.length; j++) {
        if (i < a.length && norm(a[i]) === norm(b[j])) {
            result.push({ word: b[j], added: false });
            i++;
        } else if (i < a.length && lcs[i + 1][j] >= lcs[i][j + 1]) {
            i++;
            j--;
        } else {
            result.push({ word: b[j], added: true });
        }
    }
    return result;
}
