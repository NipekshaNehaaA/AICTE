// scripts/test-contrast.js
// Automated WCAG AA contrast tester for Cherry Blossom + Ink Wash design tokens

function hexToRgb(hex) {
  const cleanHex = hex.replace('#', '');
  const bigint = parseInt(cleanHex, 16);
  return {
    r: (bigint >> 16) & 255,
    g: (bigint >> 8) & 255,
    b: bigint & 255,
  };
}

function sRgbToLinear(c) {
  const norm = c / 255;
  return norm <= 0.03928 ? norm / 12.92 : Math.pow((norm + 0.055) / 1.055, 2.4);
}

function getRelativeLuminance(hex) {
  const { r, g, b } = hexToRgb(hex);
  const R = sRgbToLinear(r);
  const G = sRgbToLinear(g);
  const B = sRgbToLinear(b);
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}

function getContrastRatio(hex1, hex2) {
  const L1 = getRelativeLuminance(hex1);
  const L2 = getRelativeLuminance(hex2);
  const lighter = Math.max(L1, L2);
  const darker = Math.min(L1, L2);
  return (lighter + 0.05) / (darker + 0.05);
}

// Token mapping as specified
const TOKENS = {
  // Surfaces
  blossom100: '#F2C7C7',
  blossom300: '#FFB7C5',
  mint100: '#D5F3D8',
  white: '#FFFFFF',
  ivory: '#FFFFE3',
  amber100: '#FFF1D6',
  rose100: '#FFE0E3',

  // Ink Wash Neutrals & Text
  text: '#4A4A4A',
  textStrong: '#2E2E2E',
  textMuted: '#55687C',
  slate: '#6D8196',
  line: '#CBCBCB',

  // Derived Action & Status Tokens
  blossom600: '#C2456B',
  blossom700: '#9E3256',
  mint700: '#26693D', // tuned from 2F7D4A to pass strict 4.5:1 AA on mint-100
  amber700: '#8A5A00',
  rose700: '#A3213A',
};

// Required test pairs and minimum WCAG thresholds
const PAIRS = [
  {
    name: 'Body text (--text) on White (--white)',
    fg: TOKENS.text,
    bg: TOKENS.white,
    target: 4.5,
    scope: 'Normal Text (AA)',
  },
  {
    name: 'Strong text (--text-strong) on White (--white)',
    fg: TOKENS.textStrong,
    bg: TOKENS.white,
    target: 4.5,
    scope: 'Normal Text (AA)',
  },
  {
    name: 'Muted text (--text-muted) on White (--white)',
    fg: TOKENS.textMuted,
    bg: TOKENS.white,
    target: 4.5,
    scope: 'Normal Text (AA)',
  },
  {
    name: 'Muted text (--text-muted) on Ivory (--ivory)',
    fg: TOKENS.textMuted,
    bg: TOKENS.ivory,
    target: 4.5,
    scope: 'Normal Text (AA)',
  },
  {
    name: 'Body text (--text) on Blossom 100 (--blossom-100)',
    fg: TOKENS.text,
    bg: TOKENS.blossom100,
    target: 4.5,
    scope: 'Normal Text (AA)',
  },
  {
    name: 'Body text (--text) on Mint 100 (--mint-100)',
    fg: TOKENS.text,
    bg: TOKENS.mint100,
    target: 4.5,
    scope: 'Normal Text (AA)',
  },
  {
    name: 'Button text (White) on Blossom 600 (--blossom-600)',
    fg: TOKENS.white,
    bg: TOKENS.blossom600,
    target: 4.5,
    scope: 'Normal Text (AA)',
  },
  {
    name: 'Success text (--mint-700) on Mint 100 (--mint-100)',
    fg: TOKENS.mint700,
    bg: TOKENS.mint100,
    target: 4.5,
    scope: 'Normal Text (AA)',
  },
  {
    name: 'Warning text (--amber-700) on Amber 100 (--amber-100)',
    fg: TOKENS.amber700,
    bg: TOKENS.amber100,
    target: 4.5,
    scope: 'Normal Text (AA)',
  },
  {
    name: 'Critical text (--rose-700) on Rose 100 (--rose-100)',
    fg: TOKENS.rose700,
    bg: TOKENS.rose100,
    target: 4.5,
    scope: 'Normal Text (AA)',
  },
  {
    name: 'Dark element text (--ivory) on Dark container (--text)',
    fg: TOKENS.ivory,
    bg: TOKENS.text,
    target: 4.5,
    scope: 'Normal Text (AA)',
  },
  {
    name: 'Slate header / large text (--slate) on White (--white)',
    fg: TOKENS.slate,
    bg: TOKENS.white,
    target: 3.0,
    scope: 'Large Text >= 18px (AA)',
  },
  {
    name: 'Card border divider (--line) on White (--white)',
    fg: TOKENS.line,
    bg: TOKENS.white,
    target: 1.5,
    scope: 'Decorative divider',
  },
];

console.log('===============================================================');
console.log('  WCAG AA AUTOMATED CONTRAST TEST: CHERRY BLOSSOM & INK WASH  ');
console.log('===============================================================');

let failedCount = 0;

PAIRS.forEach((pair) => {
  const ratio = getContrastRatio(pair.fg, pair.bg);
  const passed = ratio >= pair.target;
  const statusIcon = passed ? '✅ PASS' : '❌ FAIL';

  console.log(
    `${statusIcon} [${ratio.toFixed(2)}:1 >= ${pair.target}:1] ${pair.name} (${pair.scope})`
  );

  if (!passed) {
    failedCount++;
  }
});

console.log('===============================================================');
if (failedCount > 0) {
  console.error(`FAILED: ${failedCount} token pairs violated WCAG AA requirements.`);
  process.exit(1);
} else {
  console.log(`SUCCESS: All ${PAIRS.length} token pairs passed WCAG AA compliance!`);
  process.exit(0);
}
