(() => {
  const player =
    document.querySelector('.media-player__player')?.player;

  const tracks =
    player?.tech_?.remoteTextTracks?.()?.tracks_ || [];

  const track =
    tracks.find(t =>
      /en|english/i.test(`${t.language} ${t.label}`)
    ) || tracks[0];

  const cues =
    track?.cues_ ||
    (track?.cues ? Array.from(track.cues) : []);

  if (!cues?.length) {
    console.error('Không tìm thấy subtitle cues');
    return;
  }

  const text = Array.from(cues)
    .map(cue =>
      String(cue.text || '')
        .replace(/<[^>]+>/g, '')
        .replace(/\s+/g, ' ')
        .trim()
    )
    .filter(Boolean)
    .join('\n');

  const blob = new Blob([text], {
    type: 'text/plain;charset=utf-8'
  });

  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = 'linkedin-transcript.txt';

  document.body.appendChild(a);
  a.click();
  a.remove();

  setTimeout(() => URL.revokeObjectURL(url), 1000);

  console.log(
    `✅ Đã lấy ngay ${cues.length} subtitle cues`
  );
})();