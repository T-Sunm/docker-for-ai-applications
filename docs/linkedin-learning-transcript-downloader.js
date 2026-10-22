(() => {
  const player = document.querySelector('.media-player__player')?.player;
  const tracks = player?.tech_?.remoteTextTracks?.()?.tracks_ ?? [];

  if (!tracks.length) {
    console.error('Không tìm thấy subtitle tracks. Hãy bật English CC trước.');
    return;
  }

  const track =
    tracks.find(({ language = '', label = '' }) =>
      /^en(?:-|$)/i.test(language) ||
      /english/i.test(label)
    ) ?? tracks[0];

  const cues = Array.from(track.cues_ ?? track.cues ?? []);

  if (!cues.length) {
    console.error('Không tìm thấy subtitle cues.');
    return;
  }

  const cleanText = text =>
    String(text ?? '')
      .replace(/<[^>]*>/g, '')
      .replace(/\s+/g, ' ')
      .trim();

  const lines = cues
    .map(({ text }) => cleanText(text))
    .filter(Boolean)
    .filter((text, index, arr) =>
      index === 0 || text !== arr[index - 1]
    );

  if (!lines.length) {
    console.error('Transcript rỗng.');
    return;
  }

  const transcript = lines.join('\n');

  // Lấy tên lesson từ URL LinkedIn Learning.
  const pathParts = location.pathname
    .split('/')
    .filter(Boolean);

  const lessonSlug =
    decodeURIComponent(pathParts.at(-1) || '')
      .toLowerCase()
      .replace(/[^a-z0-9-]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');

  const filename =
    lessonSlug || 'linkedin-learning-transcript';

  const blob = new Blob([transcript], {
    type: 'text/plain;charset=utf-8'
  });

  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}.txt`;

  document.body.appendChild(link);
  link.click();
  link.remove();

  setTimeout(() => URL.revokeObjectURL(url), 1000);

  console.log(
    `Đã tải ${lines.length} subtitle cues → ${filename}.txt`
  );
})();