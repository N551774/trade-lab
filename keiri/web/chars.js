/* 経理ラボ キャラクター描画（SVG）
   charSVG(id, { expr, mode:'bust'|'full', cls })  … 人物
   monsterSVG(id, { cls })                         … モンスター
   すべてオリジナルのキャラクター。 */

const CHARS = {
  shiraishi: { name:'白石 ミオ', kana:'しらいし みお', role:'経理の先輩', color:'#1FA79B', age:'29歳',
    skin:'#FFE3CF', hair:'#1F5F5A', hairHi:'#3C8F86', eye:'#24A396', style:'bob', outfit:'#8FD6C8', inner:'#FFFFFF', tie:null, pants:'#3D4F5C',
    acc:['sticky','redpen','glassesRed'], line:'証憑は？',
    motif:'付箋のヘアピンと、耳にかけた赤ペン', skill:'証憑チェック', skillDesc:'まちがいの選択肢を見抜いて消す',
    likes:'付箋、ミントティー', dislikes:'「とりあえず雑費で」', bio:'几帳面で面倒見のいい先輩。根拠のない数字は1円も許さない。' },
  onizuka: { name:'鬼塚 権三', kana:'おにづか ごんぞう', role:'鬼の経理課長', color:'#C8102E', age:'54歳',
    skin:'#F1C9A5', hair:'#4B4B55', hairHi:'#6E6E7A', eye:'#5B3A2A', style:'oni', outfit:'#2B2D3A', inner:'#FFFFFF', tie:'#C8102E', pants:'#2B2D3A',
    acc:['armcover','mustache','thickBrow'], sharp:true, line:'数字は嘘をつかん',
    motif:'鬼の角のような寝ぐせと、黒いアームカバー', skill:'鬼の一喝', skillDesc:'敵の次の攻撃を止める',
    likes:'そろばん、羊羹', dislikes:'端数処理のミス', bio:'口は悪いが、数字と部下には誰より誠実。経理一筋30年。' },
  taiga: { name:'大河 ショウ', kana:'たいが しょう', role:'同期の営業マン', color:'#F07C2A', age:'22歳',
    skin:'#FFDDBE', hair:'#F07C2A', hairHi:'#FFB067', eye:'#C46A1C', style:'spiky', outfit:'#2F4A80', inner:'#FFFFFF', tie:'#F2B632', pants:'#2F4A80',
    acc:['receipt','bandaid'], line:'これ、経費で落ちる？',
    motif:'胸ポケットからはみ出た、くしゃくしゃの領収書', skill:'勢いで押し切る', skillDesc:'次の攻撃のダメージが2倍',
    likes:'焼肉、ノリ', dislikes:'経費精算の締め切り', bio:'ノリと勢いの営業マン。憎めない同期で、領収書はいつもくしゃくしゃ。' },
  koharu: { name:'春野 コハル', kana:'はるの こはる', role:'後輩', color:'#F27A6B', age:'22歳',
    skin:'#FFE6D4', hair:'#B85C45', hairHi:'#DE8A6E', eye:'#E0705A', style:'pony', outfit:'#F6B2A8', inner:'#FFFFFF', tie:'ribbon', pants:'#6B4A55',
    acc:['calcclip','checkbadge'], line:'ダブルチェックしました！',
    motif:'電卓のヘアクリップと「✓✓」バッジ', skill:'ダブルチェック', skillDesc:'次のミスを1回だけ帳消しにする',
    likes:'カラーペン、プリン', dislikes:'電話応対', bio:'真面目でがんばり屋の新人。ミスを隠さないのが一番の長所。' },
  kirishima: { name:'霧島 レイ', kana:'きりしま れい', role:'監査法人の会計士', color:'#4FA3E0', age:'35歳',
    skin:'#FCE6D8', hair:'#AEB6D6', hairHi:'#D8DEF2', eye:'#3F8FD0', style:'hime', outfit:'#22304A', inner:'#DDE6F5', tie:'#4FA3E0', pants:'#22304A',
    acc:['loupe'], sharp:true, line:'根拠を示してください',
    motif:'首から下げた、監査用のルーペ', skill:'監査意見', skillDesc:'次の正解をクリティカルにする',
    likes:'監査調書、ブラックコーヒー', dislikes:'「前任者がやったので」', bio:'冷静沈着な公認会計士。妥協はしないが、正しい人の味方。' },
  saisho: { name:'税所 剛', kana:'さいしょ つよし', role:'税務署の調査官', color:'#8A7A4A', age:'48歳',
    skin:'#EFC8A6', hair:'#4F3E2C', hairHi:'#77604A', eye:'#3A2E24', style:'side', outfit:'#5B5A3E', inner:'#F4F1E6', tie:'#2E4A2E', pants:'#4A4932',
    acc:['briefcase','glassesRound'], calm:true, line:'確認させてください',
    motif:'分厚いカバンと、笑っているのに笑っていない目', skill:'反面調査', skillDesc:'（敵専用）',
    likes:'盆栽、きれいな帳簿', dislikes:'「記憶にございません」', bio:'物静かで丁寧だが、帳簿の矛盾は絶対に見逃さない。' },
  amano: { name:'天野 豪', kana:'あまの ごう', role:'カリスマ社長', color:'#D9A21B', age:'52歳',
    skin:'#EDC29E', hair:'#18181F', hairHi:'#3A3A48', eye:'#D9A21B', style:'slick', outfit:'#F4F4F2', inner:'#18181F', tie:'#D9A21B', pants:'#F4F4F2',
    acc:['shades','goldpin'], line:'夢は上場だ！',
    motif:'白スーツに金のネクタイ、頭の上のサングラス', skill:'社長命令', skillDesc:'（ときどき無茶ぶり）',
    likes:'大きな夢、ゴルフ', dislikes:'赤字', bio:'一代で会社を育てた創業者。情熱は本物だが、ときどき数字に無茶を言う。' },
  nagisa: { name:'ナギサ', kana:'なぎさ', role:'パートナー', color:'#E8B84A', age:'主人公と同い年',
    skin:'#FFE2CC', hair:'#8A5A3C', hairHi:'#B07A55', eye:'#9A6A44', style:'wave', outfit:'#E8B84A', inner:'#FFF8E8', tie:null, pants:'#5A6B7A',
    acc:['camera'], line:'今日は何の日か、覚えてる？',
    motif:'からし色のニットと、いつも持ち歩くカメラ', skill:'家族の支え', skillDesc:'元気を回復する',
    likes:'写真、キャンプ', dislikes:'「あとでやる」', bio:'明るくてしっかり者。主人公の仕事を応援しているが、記念日には厳しい。' },
  sora: { name:'ソラ', kana:'そら', role:'子ども', color:'#6CC070', age:'3歳〜',
    skin:'#FFE6D6', hair:'#2A2A33', hairHi:'#4A4A58', eye:'#3A3A48', style:'kid', outfit:'#7CC36E', inner:'#C9EBB4', tie:null, pants:'#7CC36E',
    acc:['dino'], line:'でんたく、ピピピってして！',
    motif:'お気に入りの恐竜パーカー', skill:'笑顔', skillDesc:'家族の絆が上がる',
    likes:'恐竜、電卓のボタン連打', dislikes:'お迎えが遅いこと', bio:'電卓の音が大好き。熱を出すのは、なぜかいつも大事な日。' },
};

/* ── パーツ ── */
const _eye = (x, y, c, expr, sharp) => {
  const ry = sharp ? 11 : 14, lash = '#2A1F22';
  const base = `<ellipse cx="${x}" cy="${y}" rx="12" ry="${ry}" fill="#fff"/>
    <ellipse cx="${x}" cy="${y + 1.5}" rx="9.5" ry="${ry - 2}" fill="${c}"/>
    <ellipse cx="${x}" cy="${y - 3}" rx="9.5" ry="${(ry - 2) / 2}" fill="#000" opacity=".18"/>
    <ellipse cx="${x}" cy="${y + 3}" rx="4.6" ry="${ry / 2}" fill="#1B1622" opacity=".85"/>
    <circle cx="${x - 3.6}" cy="${y - 4}" r="3.4" fill="#fff"/><circle cx="${x + 3.4}" cy="${y + 5.5}" r="1.5" fill="#fff"/>
    <path d="M${x - 13} ${y - ry + 5} Q${x} ${y - ry - 7} ${x + 13} ${y - ry + 4}" stroke="${lash}" stroke-width="3.6" fill="none" stroke-linecap="round"/>`;
  const side = x < 100 ? -1 : 1; // 外側
  if (expr === 'happy') return `<path d="M${x - 11} ${y + 3} Q${x} ${y - 10} ${x + 11} ${y + 3}" stroke="${lash}" stroke-width="4" fill="none" stroke-linecap="round"/>`;
  if (expr === 'calm') return `<path d="M${x - 11} ${y} Q${x} ${y - 8} ${x + 11} ${y}" stroke="${lash}" stroke-width="3.6" fill="none" stroke-linecap="round"/>`;
  if (expr === 'surprised') return `<ellipse cx="${x}" cy="${y}" rx="12" ry="${ry + 1}" fill="#fff"/><ellipse cx="${x}" cy="${y + 1}" rx="5.5" ry="6.5" fill="${c}"/>
    <circle cx="${x}" cy="${y + 1}" r="2.6" fill="#1B1622"/><circle cx="${x - 2}" cy="${y - 2}" r="1.6" fill="#fff"/>
    <path d="M${x - 13} ${y - ry + 3} Q${x} ${y - ry - 8} ${x + 13} ${y - ry + 3}" stroke="${lash}" stroke-width="3.2" fill="none" stroke-linecap="round"/>`;
  if (expr === 'angry') { // 目頭側の上まぶたを下げる
    const ix = x - side * 15, ox = x + side * 15;
    return base + `<path d="M${ox} ${y - ry - 9} L${ix} ${y - ry - 9} L${ix} ${y - 2} Z" fill="var(--skin)"/>
      <path d="M${ox} ${y - ry + 2} L${ix} ${y - 3}" stroke="${lash}" stroke-width="3.6" stroke-linecap="round"/>`;
  }
  if (expr === 'sad') {
    const ix = x - side * 15, ox = x + side * 15;
    return base + `<path d="M${ix} ${y - ry - 9} L${ox} ${y - ry - 9} L${ox} ${y - 2} Z" fill="var(--skin)"/>
      <path d="M${ix} ${y - ry + 2} L${ox} ${y - 3}" stroke="${lash}" stroke-width="3.4" stroke-linecap="round"/>`;
  }
  return base;
};
const _brow = (x, y, expr, col, thick) => {
  const side = x < 100 ? -1 : 1, w = thick ? 6 : 3.4, ix = x - side * 10, ox = x + side * 11;
  const iy = { angry:y + 6, sad:y - 5, surprised:y - 6 }[expr] ?? y, oy = { angry:y - 3, sad:y + 2, surprised:y - 5 }[expr] ?? y - 1;
  return `<path d="M${ox} ${oy} Q${x} ${Math.min(iy, oy) - 3} ${ix} ${iy}" stroke="${col}" stroke-width="${w}" fill="none" stroke-linecap="round"/>`;
};
const _mouth = expr => ({
  happy:'<path d="M88 130 Q100 147 112 130 Z" fill="#9B2F35"/><ellipse cx="100" cy="139" rx="6" ry="3.5" fill="#FF8E8E"/>',
  angry:'<path d="M88 136 Q100 127 112 136 Q100 145 88 136Z" fill="#7A1F28"/><path d="M91 134 Q100 130 109 134" stroke="#fff" stroke-width="2.4" fill="none"/>',
  sad:'<path d="M91 138 Q100 131 109 138" stroke="#7A3A3A" stroke-width="3" fill="none" stroke-linecap="round"/>',
  surprised:'<ellipse cx="100" cy="136" rx="5.5" ry="7" fill="#7A1F28"/>',
  calm:'<path d="M90 132 Q100 140 110 132" stroke="#7A3A3A" stroke-width="3" fill="none" stroke-linecap="round"/>',
}[expr] || '<path d="M92 132 Q100 139 108 132" stroke="#7A3A3A" stroke-width="3" fill="none" stroke-linecap="round"/>');

const HAIR = {
  bob: { back:'M34 100 C28 38 172 38 166 100 L168 142 C160 152 146 152 140 144 L140 112 L60 112 L60 144 C54 152 40 152 32 142Z',
    front:'M40 98 C38 50 70 32 100 32 C130 32 162 50 160 98 C152 78 140 66 124 62 C122 72 116 78 106 80 C106 70 102 64 98 62 C92 72 80 80 64 82 C70 74 72 68 72 64 C58 70 48 82 40 98Z',
    hi:'M60 56 C72 44 88 40 100 40 C92 46 80 52 66 62Z' },
  oni: { back:'M40 100 C40 60 160 60 160 100 L156 112 L44 112Z',
    front:'M44 90 C42 50 70 36 100 36 C130 36 158 50 156 90 C142 72 122 64 100 64 C78 64 58 72 44 90Z M66 50 C54 36 50 18 60 4 C64 20 74 32 90 40Z M134 50 C146 36 150 18 140 4 C136 20 126 32 110 40Z',
    hi:'M60 10 C58 20 60 30 66 38 C62 28 61 18 63 12Z M140 10 C142 20 140 30 134 38 C138 28 139 18 137 12Z' },
  spiky: { back:'M40 100 C40 60 160 60 160 100Z',
    front:'M38 98 L34 66 L18 58 L42 50 L36 28 L62 40 L68 14 L86 36 L100 10 L114 36 L132 16 L138 42 L164 30 L158 54 L182 60 L162 70 L162 98 C150 78 132 66 116 64 L108 80 L98 64 L84 80 L80 64 C62 68 48 82 38 98Z',
    hi:'M86 36 L100 18 L104 36Z M62 40 L68 24 L76 40Z' },
  pony: { back:'M36 100 C30 40 170 40 164 100 L166 132 L34 132Z M150 66 C196 60 204 132 176 158 C184 126 174 100 152 92Z',
    front:'M40 98 C38 50 70 32 100 32 C130 32 162 50 160 98 C152 86 150 74 146 66 L130 76 L126 62 L110 74 L100 60 L88 74 L76 62 L68 76 L56 66 C50 76 46 86 40 98Z',
    hi:'M62 50 C74 40 88 38 98 38 C88 44 76 50 66 58Z' },
  hime: { back:'M32 96 C26 36 174 36 168 96 L178 206 L22 206Z',
    front:'M40 96 C38 48 70 30 100 30 C130 30 162 48 160 96 L160 80 L40 80Z M40 78 L60 78 L60 150 L44 150 C38 124 38 100 40 78Z M160 78 L140 78 L140 150 L156 150 C162 124 162 100 160 78Z',
    hi:'M56 52 C70 40 86 36 100 36 C88 42 74 48 62 58Z' },
  side: { back:'M40 100 C40 56 160 56 160 100 L158 110 L42 110Z',
    front:'M40 94 C38 46 72 32 104 34 C136 36 162 52 160 94 C150 72 128 60 96 60 C74 62 54 74 40 94Z',
    hi:'M92 36 C104 36 118 40 128 46 C116 46 104 46 94 48Z' },
  slick: { back:'M42 100 C42 56 158 56 158 100Z',
    front:'M42 86 C40 44 74 30 104 32 C136 34 160 50 158 86 C150 64 130 52 104 52 C80 52 56 62 42 86Z',
    hi:'M70 40 C88 34 112 34 132 42 C112 40 90 42 74 46Z' },
  wave: { back:'M30 100 C24 38 176 38 170 100 C176 132 168 162 150 170 C156 142 148 122 140 114 L60 114 C52 122 44 142 50 170 C32 162 24 132 30 100Z',
    front:'M40 98 C36 48 72 30 104 32 C140 34 164 56 160 98 C152 80 140 70 128 64 C112 76 86 78 60 74 C52 82 46 90 40 98Z',
    hi:'M74 44 C90 36 110 36 126 42 C110 44 92 46 78 50Z' },
  kid: { back:'',
    front:'M48 94 C46 58 74 46 100 46 C126 46 154 58 152 94 C142 82 130 74 116 72 L110 84 L100 72 L90 84 L84 72 C70 76 58 84 48 94Z M100 46 C94 32 112 28 106 16',
    hi:'M76 56 C86 50 96 50 104 50 C94 54 86 58 80 62Z' },
};

function charSVG(id, o = {}) {
  const c = CHARS[id]; if (!c) return '';
  const expr = o.expr || (c.calm ? 'calm' : 'normal'), full = o.mode === 'full';
  const h = HAIR[c.style], a = new Set(c.acc), skin = c.skin, skinD = '#E7B596';
  const vb = full ? '0 0 200 268' : '14 8 172 196';
  let g = '';
  // 恐竜フード（後ろ）
  if (a.has('dino')) g += `<path d="M22 108 C16 26 184 26 178 108 L180 152 L20 152Z" fill="${c.outfit}"/>
    <path d="M64 34 L74 12 L86 30Z M92 28 L102 4 L112 26Z M118 30 L130 10 L138 36Z" fill="#4E9A49"/>`;
  if (h.back) g += `<path d="${h.back}" fill="${c.hair}"/>`;
  // 体
  if (full) g += `<rect x="78" y="214" width="17" height="34" rx="6" fill="${c.pants}"/><rect x="105" y="214" width="17" height="34" rx="6" fill="${c.pants}"/>
    <ellipse cx="85" cy="250" rx="13" ry="7" fill="#2A2A33"/><ellipse cx="115" cy="250" rx="13" ry="7" fill="#2A2A33"/>`;
  g += `<path d="M56 220 C54 178 72 160 100 160 C128 160 146 178 144 220Z" fill="${c.outfit}"/>`;
  if (c.inner) g += a.has('dino') ? `<ellipse cx="100" cy="196" rx="24" ry="22" fill="${c.inner}"/>` : `<path d="M86 160 L100 186 L114 160Z" fill="${c.inner}"/>`;
  if (c.tie === 'ribbon') g += `<path d="M100 170 L88 164 L88 178Z M100 170 L112 164 L112 178Z" fill="${c.color}"/><circle cx="100" cy="171" r="3.5" fill="${c.color}"/>`;
  else if (c.tie) g += `<path d="M100 168 L95 174 L100 206 L105 174Z" fill="${c.tie}"/><path d="M96 166 h8 l-4 5z" fill="${c.tie}"/>`;
  g += `<path d="M58 176 C44 184 42 204 48 214 C56 216 62 208 64 198Z" fill="${c.outfit}"/><path d="M142 176 C156 184 158 204 152 214 C144 216 138 208 136 198Z" fill="${c.outfit}"/>
    <circle cx="49" cy="214" r="7" fill="${skin}"/><circle cx="151" cy="214" r="7" fill="${skin}"/>`;
  if (a.has('armcover')) g += `<path d="M46 196 C44 204 44 210 46 214 L60 210 C62 204 62 200 62 196Z M154 196 C156 204 156 210 154 214 L140 210 C138 204 138 200 138 196Z" fill="#1E1E24"/>
    <path d="M46 200 L62 199 M154 200 L138 199" stroke="#44444F" stroke-width="2"/>`;
  if (a.has('receipt')) g += `<path d="M116 172 L132 168 L128 174 L136 176 L130 182 L134 188 L118 186Z" fill="#FFFDF5" stroke="#C9C2AE" stroke-width="1.2"/><path d="M120 176 h8 M120 180 h6" stroke="#B0A88F" stroke-width="1.2"/>`;
  if (a.has('checkbadge')) g += `<circle cx="126" cy="184" r="9" fill="#fff" stroke="${c.color}" stroke-width="2.5"/><path d="M120 184 l3 3 5-6 M125 184 l3 3 5-6" stroke="${c.color}" stroke-width="2" fill="none" stroke-linecap="round"/>`;
  if (a.has('loupe')) g += `<path d="M88 162 C90 176 108 184 116 190" stroke="#C9D3E6" stroke-width="1.6" fill="none"/><circle cx="122" cy="196" r="9" fill="rgba(200,230,255,.5)" stroke="#C9D3E6" stroke-width="3"/><path d="M128 203 l7 8" stroke="#8A6A3A" stroke-width="4" stroke-linecap="round"/>`;
  if (a.has('camera')) g += `<path d="M84 162 C86 178 96 186 100 188 C104 186 114 178 116 162" stroke="#3A3A44" stroke-width="2" fill="none"/><rect x="86" y="186" width="28" height="18" rx="4" fill="#3A3A44"/><circle cx="100" cy="195" r="6" fill="#7AA8D8" stroke="#22222A" stroke-width="2"/>`;
  if (a.has('goldpin')) g += `<circle cx="80" cy="180" r="3.5" fill="#D9A21B"/>`;
  if (a.has('briefcase') && full) g += `<rect x="146" y="206" width="40" height="30" rx="5" fill="#6B4A2A"/><path d="M158 206 v-5 h16 v5" stroke="#4A321C" stroke-width="3" fill="none"/><rect x="146" y="217" width="40" height="3" fill="#4A321C"/>`;
  // 首と顔
  g += `<rect x="90" y="146" width="20" height="18" rx="6" fill="${skinD}"/>
    <ellipse cx="42" cy="104" rx="8" ry="10" fill="${skin}"/><ellipse cx="158" cy="104" rx="8" ry="10" fill="${skin}"/>
    <path d="M42 96 C42 44 158 44 158 96 C158 132 130 156 100 156 C70 156 42 132 42 96Z" fill="${skin}"/>`;
  const blush = expr === 'happy' || expr === 'surprised' ? .55 : .3;
  g += `<ellipse cx="68" cy="126" rx="10" ry="5.5" fill="#FF8A80" opacity="${blush}"/><ellipse cx="132" cy="126" rx="10" ry="5.5" fill="#FF8A80" opacity="${blush}"/>`;
  g += _eye(78, 106, c.eye, expr, c.sharp) + _eye(122, 106, c.eye, expr, c.sharp);
  g += _brow(78, 84, expr, c.hair, a.has('thickBrow')) + _brow(122, 84, expr, c.hair, a.has('thickBrow'));
  g += `<path d="M100 118 l-2.5 5 h4" stroke="${skinD}" stroke-width="2" fill="none" stroke-linecap="round"/>`;
  g += a.has('mustache') ? `<path d="M100 126 C92 122 82 124 78 130 C86 129 94 130 100 128 C106 130 114 129 122 130 C118 124 108 122 100 126Z" fill="${c.hair}"/>` + _mouth(expr === 'happy' ? 'happy' : expr === 'angry' ? 'angry' : 'sad').replace(/M91 138 Q100 131 109 138/, 'M92 139 Q100 134 108 139')
    : _mouth(expr);
  if (a.has('bandaid')) g += `<rect x="126" y="116" width="16" height="7" rx="3" fill="#F4C9A0" transform="rotate(-18 134 120)"/><path d="M131 117 l0 6 M136 116 l0 6" stroke="#D9A57A" stroke-width="1" transform="rotate(-18 134 120)"/>`;
  // 前髪
  g += `<path d="${h.front}" fill="${c.hair}"/>` + (h.hi ? `<path d="${h.hi}" fill="${c.hairHi}" opacity=".9"/>` : '');
  if (a.has('dino')) g += `<path d="M30 110 C26 64 52 40 100 40 C148 40 174 64 170 110 C160 72 136 56 100 56 C64 56 40 72 30 110Z" fill="${c.outfit}"/>
    <circle cx="70" cy="50" r="5" fill="#fff"/><circle cx="130" cy="50" r="5" fill="#fff"/><circle cx="71" cy="51" r="2.5" fill="#222"/><circle cx="129" cy="51" r="2.5" fill="#222"/>
    <path d="M84 58 l4 6 4-6 4 6 4-6 4 6 4-6 4 6" stroke="#fff" stroke-width="2.4" fill="none" stroke-linejoin="round"/>`;
  // アクセサリー（顔まわり）
  if (a.has('glassesRed')) g += `<g fill="none" stroke="#D2363A" stroke-width="2.6"><rect x="62" y="94" width="32" height="24" rx="8"/><rect x="106" y="94" width="32" height="24" rx="8"/><path d="M94 104 h12"/></g>`;
  if (a.has('glassesRound')) g += `<g fill="rgba(255,255,255,.12)" stroke="#2A2420" stroke-width="3.2"><circle cx="78" cy="106" r="15"/><circle cx="122" cy="106" r="15"/><path d="M93 104 h14" fill="none"/></g>`;
  if (a.has('sticky')) g += `<g transform="rotate(14 136 62)"><rect x="126" y="52" width="20" height="20" fill="#FFE066"/><path d="M140 72 L146 66 L146 72Z" fill="#E8C33A"/></g>`;
  if (a.has('redpen')) g += `<path d="M150 98 L172 66" stroke="#D2363A" stroke-width="5" stroke-linecap="round"/><path d="M168 72 L174 63" stroke="#fff" stroke-width="2"/>`;
  if (a.has('calcclip')) g += `<g transform="rotate(-10 150 72)"><rect x="140" y="62" width="18" height="22" rx="3" fill="#3A3A48"/><rect x="143" y="65" width="12" height="5" rx="1" fill="#B9F0D5"/>
    <g fill="#fff"><rect x="143" y="72" width="3" height="2.5"/><rect x="147.5" y="72" width="3" height="2.5"/><rect x="152" y="72" width="3" height="2.5"/><rect x="143" y="76" width="3" height="2.5"/><rect x="147.5" y="76" width="3" height="2.5"/><rect x="152" y="76" width="3" height="2.5" fill="#F27A6B"/></g></g>`;
  if (a.has('shades')) g += `<g><rect x="62" y="40" width="30" height="14" rx="6" fill="#1A1A22" stroke="#D9A21B" stroke-width="2"/><rect x="108" y="40" width="30" height="14" rx="6" fill="#1A1A22" stroke="#D9A21B" stroke-width="2"/><path d="M92 46 h16" stroke="#D9A21B" stroke-width="2"/><path d="M68 44 l8 0" stroke="#fff" stroke-width="1.6" opacity=".6"/></g>`;
  return `<svg class="${o.cls || ''}" viewBox="${vb}" role="img" aria-label="${c.name}" style="--skin:${skin}" xmlns="http://www.w3.org/2000/svg">${g}</svg>`;
}

/* ── モンスター ── */
const MONSTERS = {
  kusha: { name:'クシャレシート', desc:'財布の奥で眠っていた、くしゃくしゃの領収書。日付がにじんで読めない。', weak:'証憑チェック', color:'#E9E2CC' },
  karibarai: { name:'カリバライ', desc:'精算されずに半年さまよう仮払金のおばけ。「まだ使い道が決まってないんだ……」', weak:'期日管理', color:'#C9D6F2' },
  futago: { name:'フタゴセイキュー', desc:'郵送とPDFで2通届く、そっくりな請求書の双子。二重払いを狙っている。', weak:'請求書番号の照合', color:'#F6C9C4' },
  kizure: { name:'キズレドケイ', desc:'針がずれた時計の魔物。3月の売上を4月に連れ去る。', weak:'発生主義', color:'#CDB8F0' },
  refslime: { name:'リファレンスライム', desc:'行を削除したら現れる緑のスライム。体に「#REF!」と書いてある。', weak:'ダブルチェック', color:'#9ED89A' },
  denpyou: { name:'デンピョウマウンテン', desc:'月末に現れる伝票の山。締め日が近づくほど大きくなる。', weak:'段取り', color:'#F2E6C2', boss:true },
};
function monsterSVG(id, o = {}) {
  const m = MONSTERS[id]; let g = '';
  const eyes = (y, angry = true) => `<ellipse cx="82" cy="${y}" rx="8" ry="10" fill="#fff"/><ellipse cx="118" cy="${y}" rx="8" ry="10" fill="#fff"/>
    <circle cx="84" cy="${y + 2}" r="5" fill="#1B1622"/><circle cx="116" cy="${y + 2}" r="5" fill="#1B1622"/><circle cx="82" cy="${y}" r="1.8" fill="#fff"/><circle cx="114" cy="${y}" r="1.8" fill="#fff"/>
    ${angry ? `<path d="M70 ${y - 14} L92 ${y - 8} M130 ${y - 14} L108 ${y - 8}" stroke="#1B1622" stroke-width="4" stroke-linecap="round"/>` : ''}`;
  if (id === 'kusha') g = `<path d="M44 70 L70 52 L96 64 L122 48 L156 66 L150 96 L166 122 L146 150 L156 176 L120 168 L96 184 L72 168 L44 178 L52 146 L36 120 L54 96Z" fill="${m.color}" stroke="#B9AE8C" stroke-width="3" stroke-linejoin="round"/>
      <path d="M70 70 L84 92 M128 66 L118 90 M60 140 L80 128 M140 140 L122 130" stroke="#C9BFA0" stroke-width="2"/>${eyes(104)}
      <path d="M86 136 Q100 128 114 136" stroke="#1B1622" stroke-width="4" fill="none" stroke-linecap="round"/><text x="100" y="166" font-size="16" font-weight="800" text-anchor="middle" fill="#9A8E6A" font-family="sans-serif">¥?,???</text>`;
  if (id === 'karibarai') g = `<path d="M50 120 C50 60 150 60 150 120 L150 176 L136 164 L122 178 L108 164 L94 178 L80 164 L66 178 L50 166Z" fill="${m.color}" stroke="#9AAAD6" stroke-width="3"/>
      ${eyes(110, false)}<path d="M90 140 Q100 134 110 140" stroke="#1B1622" stroke-width="3.5" fill="none" stroke-linecap="round"/>
      <rect x="84" y="70" width="32" height="22" rx="4" fill="#fff" stroke="#9AAAD6" stroke-width="2"/><text x="100" y="87" font-size="15" font-weight="800" text-anchor="middle" fill="#3D4F8A" font-family="sans-serif">仮</text>
      <circle cx="160" cy="132" r="14" fill="#F2B632" stroke="#C98A0C" stroke-width="3"/><text x="160" y="137" font-size="13" font-weight="800" text-anchor="middle" fill="#8A5A00" font-family="sans-serif">¥</text>`;
  if (id === 'futago') { const one = (dx, s) => `<g transform="translate(${dx} 0) scale(${s})"><path d="M40 60 L120 60 L120 170 L40 170Z" fill="${m.color}" stroke="#D99A92" stroke-width="3"/>
      <path d="M52 76 h56 M52 86 h40" stroke="#D99A92" stroke-width="3"/><text x="80" y="160" font-size="12" font-weight="800" text-anchor="middle" fill="#B05A50" font-family="sans-serif">INV-0412</text>
      <circle cx="66" cy="112" r="6" fill="#1B1622"/><circle cx="94" cy="112" r="6" fill="#1B1622"/><path d="M68 132 Q80 140 92 132" stroke="#1B1622" stroke-width="3" fill="none"/></g>`;
    g = one(-14, 1) + one(64, .85); }
  if (id === 'kizure') g = `<circle cx="100" cy="110" r="64" fill="${m.color}" stroke="#7A5BC0" stroke-width="5"/><circle cx="100" cy="110" r="52" fill="#F6F0FF"/>
      ${[0,1,2,3,4,5,6,7,8,9,10,11].map(i => { const t = i / 12 * Math.PI * 2; return `<circle cx="${100 + Math.sin(t) * 44}" cy="${110 - Math.cos(t) * 44}" r="2.5" fill="#7A5BC0"/>`; }).join('')}
      <path d="M100 110 L126 86 M100 110 L84 140" stroke="#3A2A66" stroke-width="5" stroke-linecap="round"/>${eyes(104).replace(/cy="(\d+)"/g, (s, n) => s)}
      <path d="M60 46 L48 30 M140 46 L152 30" stroke="#7A5BC0" stroke-width="6" stroke-linecap="round"/><text x="100" y="158" font-size="12" font-weight="800" text-anchor="middle" fill="#7A5BC0" font-family="sans-serif">3月→4月</text>`;
  if (id === 'refslime') g = `<path d="M36 176 C30 130 54 76 100 72 C146 76 170 130 164 176 Z" fill="${m.color}" stroke="#4E9A49" stroke-width="3"/>
      <path d="M58 100 C66 88 78 82 90 80" stroke="#E6F8E2" stroke-width="6" fill="none" stroke-linecap="round"/>${eyes(118, false)}
      <path d="M88 144 Q100 152 112 144" stroke="#1B1622" stroke-width="3.5" fill="none" stroke-linecap="round"/>
      <rect x="70" y="152" width="60" height="18" rx="4" fill="#fff"/><text x="100" y="166" font-size="13" font-weight="800" text-anchor="middle" fill="#D2363A" font-family="monospace">#REF!</text>`;
  if (id === 'denpyou') g = `${[0,1,2,3,4,5,6].map(i => `<rect x="${40 + (i % 2) * 6}" y="${176 - i * 20}" width="${120 - i * 6}" height="22" rx="3" fill="${i % 2 ? '#FFF8E2' : m.color}" stroke="#C9B57A" stroke-width="2.5" transform="rotate(${(i % 3 - 1) * 4} 100 ${186 - i * 20})"/>`).join('')}
      ${eyes(110)}<path d="M84 140 Q100 130 116 140" stroke="#1B1622" stroke-width="4" fill="none" stroke-linecap="round"/>
      <path d="M100 52 L92 34 L108 34Z" fill="#E5432F"/><text x="100" y="196" font-size="11" font-weight="800" text-anchor="middle" fill="#9A8340" font-family="sans-serif">締め日まであと3日</text>`;
  return `<svg class="${o.cls || ''}" viewBox="20 24 170 180" role="img" aria-label="${m.name}" xmlns="http://www.w3.org/2000/svg">${g}</svg>`;
}

/* マスコット「チョーボ」（帳簿の妖精） */
function choboSVG(wear = [], mood = 'happy', cls = '') {
  const eye = mood === 'sad' ? '<path d="M44 58q5-5 10 0M66 58q5-5 10 0" stroke="#16261F" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
    : '<ellipse cx="49" cy="58" rx="4.5" ry="6" fill="#16261F"/><ellipse cx="71" cy="58" rx="4.5" ry="6" fill="#16261F"/><circle cx="50.5" cy="56" r="1.6" fill="#fff"/><circle cx="72.5" cy="56" r="1.6" fill="#fff"/>';
  const mouth = mood === 'sad' ? '<path d="M53 76q7-5 14 0" stroke="#16261F" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
    : '<path d="M52 71q8 8 16 0" stroke="#16261F" stroke-width="3.5" fill="#E5432F" stroke-linecap="round"/>';
  const calc = (body, scr, keys) => '<g transform="translate(86 74) rotate(12)"><rect width="24" height="32" rx="4" fill="' + body + '"/><rect x="4" y="4" width="16" height="7" rx="1.5" fill="' + scr + '"/><g fill="' + keys + '">' + [0,1,2].map(r => [0,1,2].map(c => '<rect x="' + (4 + c * 6) + '" y="' + (14 + r * 5.5) + '" width="4" height="3.5" rx="1"/>').join('')).join('') + '</g></g>';
  const items = {
    glasses:'<g fill="none" stroke="#16261F" stroke-width="3"><circle cx="49" cy="58" r="9"/><circle cx="71" cy="58" r="9"/><path d="M58 58h4"/></g>',
    tie:'<path d="M60 88l-6 6 6 20 6-20z" fill="#E5432F"/><path d="M55 86h10l-5 6z" fill="#B42C1C"/>',
    calc:calc('#16261F', '#B9F0D5', '#fff'), goldcalc:calc('#E2A21C', '#FFF6D6', '#FFE59A'),
    crown:'<path d="M40 30l8 8 12-14 12 14 8-8-4 18H44z" fill="#F2A516" stroke="#B06F00" stroke-width="2" stroke-linejoin="round"/>',
    headband:'<path d="M32 38q28-14 56 0" stroke="#E5432F" stroke-width="7" fill="none"/><circle cx="60" cy="31" r="7" fill="#fff" stroke="#E5432F" stroke-width="2"/><circle cx="60" cy="31" r="3" fill="#E5432F"/>',
    armcover:'<rect x="14" y="62" width="18" height="16" rx="5" fill="#2A2F3A"/><rect x="88" y="62" width="18" height="16" rx="5" fill="#2A2F3A"/>',
    soroban:'<g transform="translate(2 84) rotate(-14)"><rect width="34" height="18" rx="3" fill="#7A4B22"/><rect x="2.5" y="2.5" width="29" height="13" rx="2" fill="#E9D3A8"/><path d="M2.5 7h29" stroke="#7A4B22" stroke-width="1.5"/>' + [0,1,2,3,4].map(c => '<circle cx="' + (6 + c * 5.5) + '" cy="4.8" r="1.8" fill="#3B2410"/><circle cx="' + (6 + c * 5.5) + '" cy="' + (10 + (c % 2) * 2.5) + '" r="1.8" fill="#3B2410"/>').join('') + '</g>',
  };
  return '<svg class="mascot ' + cls + '" viewBox="0 0 120 120" role="img" aria-label="チョーボ" xmlns="http://www.w3.org/2000/svg"><ellipse cx="60" cy="112" rx="30" ry="5" fill="rgba(0,0,0,.12)"/>'
    + '<rect x="26" y="26" width="68" height="82" rx="14" fill="#0C7A50"/><rect x="30" y="30" width="64" height="76" rx="12" fill="#14A06B"/><rect x="86" y="34" width="6" height="68" rx="3" fill="#F3F6F4"/>'
    + '<rect x="38" y="40" width="44" height="50" rx="10" fill="#F3FFF8"/><g stroke="#CDE7DA" stroke-width="1.5"><path d="M42 50h36M42 82h36"/></g>'
    + eye + mouth + '<ellipse cx="42" cy="68" rx="4" ry="2.5" fill="#FFB4A8" opacity=".8"/><ellipse cx="78" cy="68" rx="4" ry="2.5" fill="#FFB4A8" opacity=".8"/>'
    + '<rect x="18" y="66" width="12" height="8" rx="4" fill="#0C7A50"/><rect x="90" y="66" width="12" height="8" rx="4" fill="#0C7A50"/>'
    + wear.map(k => items[k] || '').join('') + '</svg>';
}
