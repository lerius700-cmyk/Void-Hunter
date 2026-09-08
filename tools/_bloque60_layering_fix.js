// BLOQUE 60 Task 9/10 layering fix — Node.js implementation.
// Wraps the procedural fallback body of `_draw_goliath` in `else:` so
// the procedural layers do NOT overdraw the BLOQUE 60 sprite.
// The Phase 2 eye trail at the end of the function remains outside
// the if/else so it renders on both paths.
const fs = require('fs');
const path = require('path');

const TARGET = path.resolve(__dirname, '..', 'src', 'ui', 'gameplay_runtime.py');

const text = fs.readFileSync(TARGET, 'utf8');
const lines = text.split(/\r?\n/);

let startIdx = null;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].startsWith('    def _draw_goliath(')) {
    startIdx = i;
    break;
  }
}
if (startIdx === null) throw new Error('Could not find _draw_goliath');

let endIdx = null;
for (let i = startIdx + 1; i < lines.length; i++) {
  if (lines[i].startsWith('    def ')) {
    endIdx = i;
    break;
  }
}
if (endIdx === null) throw new Error('Could not find end of _draw_goliath');

let bossNoneIdx = null;
let spriteIfIdx = null;
let proceduralStartIdx = null;
let eyeTrailStartIdx = null;
for (let i = startIdx; i < endIdx; i++) {
  const s = lines[i];
  if (bossNoneIdx === null && s === '        if self._boss is None:') bossNoneIdx = i;
  if (spriteIfIdx === null && s === '        if sprite is not None:') spriteIfIdx = i;
  if (proceduralStartIdx === null && s.includes('# --- Procedural fallback'))
    proceduralStartIdx = i;
  if (eyeTrailStartIdx === null && s.includes('Layer 13: BLOQUE 60'))
    eyeTrailStartIdx = i;
}

if (
  bossNoneIdx === null ||
  spriteIfIdx === null ||
  proceduralStartIdx === null ||
  eyeTrailStartIdx === null
) {
  throw new Error(
    'Missing anchor: ' +
      JSON.stringify({ bossNoneIdx, spriteIfIdx, proceduralStartIdx, eyeTrailStartIdx })
  );
}

// 1) New head:
//    - if self._boss is None: return
//    - BLOQUE 60 sprite-load comment + import + sprite = _load_sprite(...)
//    - NEW: bob, cx, cy BEFORE the if/else
//    - sprite branch (no longer computes bob/cx/cy inside)
//    - else:
const newHead = [];
// if self._boss is None + return
newHead.push(lines[bossNoneIdx]);
newHead.push(lines[bossNoneIdx + 1]);
// BLOQUE 60 sprite-load block: 6 lines from `spriteIfIdx - 6` to `spriteIfIdx - 1`
for (let k = spriteIfIdx - 6; k <= spriteIfIdx - 1; k++) newHead.push(lines[k]);
// NEW: shared anchor values before if/else
newHead.push('        # Shared anchor values: used by both the sprite');
newHead.push('        # branch and the procedural fallback. Moved here');
newHead.push('        # (BLOQUE 60 layering fix) so the procedural body');
newHead.push('        # does NOT overdraw the sprite when one is loaded.');
newHead.push('        bob = math.sin(self._t * 1.0) * 1.5');
newHead.push('        cx = int(self._boss.x + ox)');
newHead.push('        cy = int(self._boss.y + oy)');
// Sprite branch
newHead.push('        if sprite is not None:');
newHead.push('            vw, vh = 96, 80');
newHead.push('            blit_x = cx - vw // 2');
newHead.push('            blit_y = cy - vh // 2 + int(bob)');
newHead.push('            target.blit(sprite, (blit_x, blit_y))');
// else: opens the procedural body
newHead.push('        else:');

// 2) Procedural body: lines from `proceduralStartIdx` to `eyeTrailStartIdx - 1`.
//    Re-indent +4. Drop the duplicate `bob`/`cx`/`cy` lines (already computed).
const bobLine = '        bob = math.sin(self._t * 1.0) * 1.5';
const cxLine = '        cx = int(self._boss.x + ox)';
const cyLine = '        cy = int(self._boss.y + oy)';

const procLines = [];
for (let i = proceduralStartIdx; i < eyeTrailStartIdx; i++) {
  const s = lines[i];
  if (s === bobLine || s === cxLine || s === cyLine) continue;
  if (s.length === 0) {
    // Empty line — keep as is.
    procLines.push(s);
  } else {
    // Every line in the procedural body gets +4 indent so it sits
    // properly inside the `else:` block. Continuation lines that
    // were at 12 spaces become 16 spaces; single-statement lines
    // that were at 8 spaces become 12 spaces.
    procLines.push('    ' + s);
  }
}

// 3) Eye trail block: lines from `eyeTrailStartIdx` to `endIdx - 1`. Unchanged.
const eyeTrailLines = lines.slice(eyeTrailStartIdx, endIdx);

// Assemble new function body
const newBody = [...newHead, ...procLines, ...eyeTrailLines];
const newLines = [...lines.slice(0, bossNoneIdx), ...newBody, ...lines.slice(endIdx)];

// Re-join with LF; preserve no trailing newline info beyond what's in lines.
// lines came from text.split(/\r?\n/), so the last element is "" if the file
// ended with a newline. We just join with '\n' to reconstruct.
const newText = newLines.join('\n');
fs.writeFileSync(TARGET, newText, 'utf8');
console.log('OK: rewrote ' + TARGET);
console.log('  before: ' + (endIdx - bossNoneIdx) + ' lines (function body)');
console.log('  after:  ' + newBody.length + ' lines (function body)');
