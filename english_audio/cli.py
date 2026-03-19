#!/usr/bin/env python3
import re
import subprocess
import sys
import readline
from pathlib import Path

VIDEO_PATH = Path("/Users/vadimkasse/Yandex.Disk.localized/Загрузки/Friends.S01E01.The.One.Where.Monica.Gets.a.Roommate.mkv")
SRT_PATH = Path("/Users/vadimkasse/Yandex.Disk.localized/Загрузки/Friends.S01E01.The.One.Where.Monica.Gets.a.Roommate.srt")
OUTPUT_DIR = Path("/Users/vadimkasse/Yandex.Disk.localized/Загрузки/audio")
AUDIO_STREAM = "0:2"


def normalize_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r"<[^>]+>", "", text)
    text = text.casefold()
    text = re.sub(r"[^\w\s]", " ", text)   # убрать пунктуацию
    text = re.sub(r"_", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_srt(srt_text: str):
    blocks = re.split(r"\n\s*\n", srt_text.strip(), flags=re.MULTILINE)
    items = []

    for block in blocks:
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue

        if re.fullmatch(r"\d+", lines[0]):
            time_line = lines[1]
            text_lines = lines[2:]
        else:
            time_line = lines[0]
            text_lines = lines[1:]

        m = re.match(
            r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
            time_line
        )
        if not m:
            continue

        start, end = m.groups()
        raw_text = "\n".join(text_lines).strip()

        items.append({
            "start": start,
            "end": end,
            "raw_text": raw_text,
            "normalized": normalize_text(raw_text),
        })

    return items


def find_matches(items, phrase: str):
    target = normalize_text(phrase)
    if not target:
        return []

    matches = []
    n = len(items)

    for i in range(n):
        combined_parts = []

        for j in range(i, n):
            combined_parts.append(items[j]["normalized"])
            combined_text = " ".join(combined_parts)
            combined_text = re.sub(r"\s+", " ", combined_text).strip()

            # Нашли запрос внутри непрерывной склейки соседних блоков
            if target in combined_text:
                raw_joined = " ".join(
                    items[k]["raw_text"].replace("\n", " ").strip()
                    for k in range(i, j + 1)
                )
                raw_joined = re.sub(r"\s+", " ", raw_joined).strip()

                matches.append({
                    "start": items[i]["start"],
                    "end": items[j]["end"],
                    "raw_text": raw_joined,
                    "normalized": combined_text,
                })

                # Важно: берём самый короткий диапазон от этой стартовой точки
                break

            # Если склейка уже длиннее запроса, и запроса в ней нет,
            # дальше обычно только хуже — останавливаемся
            if len(combined_text) > len(target) + 40:
                break

    return matches

    # 2. Поиск через несколько подряд идущих блоков
    n = len(items)
    for i in range(n):
        combined_parts = []
        for j in range(i, n):
            combined_parts.append(items[j]["normalized"])
            combined_text = " ".join(part for part in combined_parts if part).strip()
            combined_text = re.sub(r"\s+", " ", combined_text)

            # если длина сильно ушла дальше цели и точного вхождения нет — можно рано остановиться
            if len(combined_text) > len(target) + 80 and target not in combined_text:
                break

            if target in combined_text or combined_text in target:
                raw_joined = " ".join(items[k]["raw_text"].replace("\n", " ").strip() for k in range(i, j + 1))
                raw_joined = re.sub(r"\s+", " ", raw_joined).strip()

                matches.append({
                    "start": items[i]["start"],
                    "end": items[j]["end"],
                    "raw_text": raw_joined,
                    "normalized": combined_text,
                })
                break

    return matches


def sanitize_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[/:*?\"<>|]", "_", name)
    name = re.sub(r"\s+", "_", name)
    return name


def ffmpeg_time(srt_time: str) -> str:
    return srt_time.replace(",", ".")


def ask_yes_no(prompt: str) -> bool:
    while True:
        answer = input(prompt).strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False


def main():
    if not VIDEO_PATH.exists():
        print(f"Не найден видеофайл: {VIDEO_PATH}")
        sys.exit(1)

    if not SRT_PATH.exists():
        print(f"Не найден SRT: {SRT_PATH}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    srt_text = SRT_PATH.read_text(encoding="utf-8-sig")
    items = parse_srt(srt_text)

    if not items:
        print("Не удалось распарсить SRT.")
        sys.exit(1)

    print("Фраза целиком? (Enter 2 раза для окончания)")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)

    phrase = " ".join(lines).strip()
    if not phrase:
        sys.exit(1)

    matches = find_matches(items, phrase)

    if not matches:
        print("Не найдено.")
        sys.exit(1)

    if len(matches) == 1:
        match = matches[0]
    else:
        print("Найдено несколько совпадений:")
        for i, m in enumerate(matches, 1):
            one_line = re.sub(r"\s+", " ", m["raw_text"]).strip()
            print(f"{i}) {one_line} [{m['start']} --> {m['end']}]")

        choice = input("Номер?\n").strip()
        if not choice.isdigit() or not (1 <= int(choice) <= len(matches)):
            sys.exit(1)
        match = matches[int(choice) - 1]

    out_name = input("Название отрывка?\n")
    out_name = out_name.strip()
    if not out_name:
        sys.exit(1)

    out_name = sanitize_filename(out_name)
    out_path = OUTPUT_DIR / f"{out_name}.mp3"

    if out_path.exists():
        replace = ask_yes_no("Файл существует, заменить? y/n\n")
        if not replace:
            print("Файл не создан")
            sys.exit(0)
    else:
        ffmpeg_overwrite_flag = "-n"

    cmd = [
        "ffmpeg",
        ffmpeg_overwrite_flag,
        "-loglevel", "error",
        "-ss", ffmpeg_time(match["start"]),
        "-to", ffmpeg_time(match["end"]),
        "-i", str(VIDEO_PATH),
        "-map", AUDIO_STREAM,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        str(out_path),
    ]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("Ошибка ffmpeg.")
        sys.exit(result.returncode)

    print(f"Готово: {out_path}")
    subprocess.run(["open", "-R", str(out_path)])


if __name__ == "__main__":
    main()