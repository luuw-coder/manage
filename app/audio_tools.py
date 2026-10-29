"""Đọc âm thanh, tạo hình sóng, cắt đoạn và xuất WAV mới. Không bao giờ sửa tệp gốc."""
import array
import os
import sys
import wave

BYTEORDER_LITTLE = sys.byteorder == "little"


class Pcm:
    """Âm thanh PCM 16-bit xen kẽ các kênh."""

    def __init__(self, samples, rate, channels):
        self.samples = samples
        self.rate = int(rate)
        self.channels = max(1, int(channels))

    @property
    def frames(self):
        return len(self.samples) // self.channels

    @property
    def duration(self):
        return self.frames / self.rate if self.rate else 0.0

    def mono(self):
        return self.samples[0::self.channels] if self.channels > 1 else self.samples

    def frame_at(self, seconds):
        return min(max(0, int(round(seconds * self.rate))), self.frames)

    def slice(self, start_s, end_s):
        a, b = sorted((self.frame_at(start_s), self.frame_at(end_s)))
        return Pcm(self.samples[a * self.channels:b * self.channels], self.rate, self.channels)


def _to_int16(raw, width):
    if width == 2:
        arr = array.array("h")
        arr.frombytes(raw)
        if not BYTEORDER_LITTLE:
            arr.byteswap()
        return arr
    if width == 1:
        return array.array("h", [(b - 128) << 8 for b in raw])
    if width in (3, 4):
        lo, hi = raw[width - 2::width], raw[width - 1::width]
        out = bytearray(len(lo) * 2)
        out[0::2], out[1::2] = lo, hi
        arr = array.array("h")
        arr.frombytes(bytes(out))
        if not BYTEORDER_LITTLE:
            arr.byteswap()
        return arr
    raise ValueError("Độ sâu bit không hỗ trợ")


def read_wav(path):
    try:
        with wave.open(path, "rb") as w:
            ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(n)
    except (wave.Error, EOFError) as e:
        raise ValueError(str(e))
    keep = (len(raw) // (ch * width)) * ch * width
    return Pcm(_to_int16(raw[:keep], width), rate, ch)


def load_pcm(path):
    """Đọc đồng bộ: WAV bằng thư viện chuẩn, các định dạng khác bằng miniaudio nếu có. None nếu không đọc được."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".wav", ".wave"):
        try:
            return read_wav(path)
        except ValueError:
            pass
    try:
        import miniaudio
        d = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.SIGNED16,
                                  nchannels=2, sample_rate=44100)
        return Pcm(array.array("h", d.samples), 44100, 2)
    except Exception:
        return None


def write_wav(path, pcm):
    """Ghi một tệp WAV MỚI chứa pcm. Không ghi đè lên tệp nguồn."""
    data = array.array("h", pcm.samples)
    if not BYTEORDER_LITTLE:
        data.byteswap()
    with wave.open(path, "wb") as w:
        w.setnchannels(pcm.channels)
        w.setsampwidth(2)
        w.setframerate(pcm.rate)
        w.writeframes(data.tobytes())
    return path


def unique_path(folder, stem, ext):
    os.makedirs(folder, exist_ok=True)
    cand = os.path.join(folder, stem + ext)
    n = 2
    while os.path.exists(cand):
        cand = os.path.join(folder, f"{stem}_{n}{ext}")
        n += 1
    return cand


MP3_RATES = (8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000)


def mp3_available(pcm):
    """Có thể xuất MP3 (nhẹ hơn WAV khoảng 10 lần) cho âm thanh này không."""
    if pcm.rate not in MP3_RATES or pcm.channels > 2:
        return False
    try:
        import lameenc  # noqa: F401
        return True
    except Exception:
        return False


def write_mp3(path, pcm, bitrate=128):
    """Ghi một tệp MP3 MỚI chứa pcm (Moho đọc được MP3)."""
    import lameenc
    enc = lameenc.Encoder()
    enc.set_bit_rate(bitrate)
    enc.set_in_sample_rate(pcm.rate)
    enc.set_channels(pcm.channels)
    enc.set_quality(2)
    data = array.array("h", pcm.samples)
    if not BYTEORDER_LITTLE:
        data.byteswap()
    out = enc.encode(data.tobytes()) + enc.flush()
    with open(path, "wb") as f:
        f.write(out)
    return path


def segment_path(pcm, start_s, end_s, folder, source_path, fmt="mp3"):
    """Đường dẫn tệp sẽ xuất cho đoạn [start_s, end_s]. Tên cố định theo đoạn cắt: cắt lại đúng đoạn đó
    thì dùng lại tệp cũ, không đẻ thêm tệp mới."""
    stem = os.path.splitext(os.path.basename(source_path))[0]
    a, b = sorted((start_s, end_s))
    ext = ".mp3" if fmt == "mp3" and mp3_available(pcm) else ".wav"
    return os.path.join(folder, f"{stem}_{a:.2f}-{b:.2f}s{ext}")


def export_segment(pcm, start_s, end_s, folder, source_path, fmt="mp3"):
    """Xuất đoạn [start_s, end_s] ra tệp MỚI (MP3 nhẹ, hoặc WAV nếu chọn WAV / không xuất được MP3).
    Đã có tệp đúng đoạn này rồi thì trả về tệp đó. Không bao giờ sửa tệp gốc."""
    seg = pcm.slice(start_s, end_s)
    if seg.frames == 0:
        raise ValueError("Đoạn chọn rỗng")
    os.makedirs(folder, exist_ok=True)
    path = segment_path(pcm, start_s, end_s, folder, source_path, fmt)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    tmp = path + ".tmp"
    try:
        (write_mp3 if path.endswith(".mp3") else write_wav)(tmp, seg)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        if path.endswith(".mp3"):  # không mã hóa được MP3 thì dùng WAV
            return export_segment(pcm, start_s, end_s, folder, source_path, "wav")
        raise
    return path


class Peaks:
    """Bảng đỉnh để vẽ hình sóng nhanh khi phóng to/thu nhỏ."""

    def __init__(self, mono):
        n = len(mono)
        self.bucket = 256 if n < 5_000_000 else 2048
        self.mins, self.maxs = array.array("h"), array.array("h")
        for i in range(0, n, self.bucket):
            chunk = mono[i:i + self.bucket]
            self.mins.append(min(chunk))
            self.maxs.append(max(chunk))


def column_peaks(mono, peaks, start, end, width):
    """Trả về danh sách (min, max) cho mỗi cột pixel trong [start, end) khung."""
    n = len(mono)
    out = []
    span = max(1, end - start)
    for col in range(width):
        a = start + int(col * span / width)
        b = max(a + 1, start + int((col + 1) * span / width))
        if a >= n:
            out.append((0, 0))
            continue
        b = min(b, n)
        if b - a >= peaks.bucket * 2:
            ba, bb = a // peaks.bucket, (b + peaks.bucket - 1) // peaks.bucket
            out.append((min(peaks.mins[ba:bb]), max(peaks.maxs[ba:bb])))
        else:
            chunk = mono[a:b]
            out.append((min(chunk), max(chunk)))
    return out


def fmt_time(seconds):
    seconds = max(0.0, float(seconds))
    m = int(seconds // 60)
    return f"{m:02d}:{seconds - 60 * m:06.3f}"
